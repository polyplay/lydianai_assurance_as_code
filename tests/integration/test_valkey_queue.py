import asyncio
import os
from uuid import uuid4

from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker
import pytest


async def _broker_echo(_context, payload):
    return payload


@pytest.mark.asyncio
async def test_acc_lic_013_arq_executes_a_job_against_real_valkey() -> None:
    broker_url = os.getenv("AAC_TEST_VALKEY_URL")
    if not broker_url:
        pytest.skip("AAC_TEST_VALKEY_URL is required for the disposable Valkey broker test")

    identifier = uuid4().hex
    queue_name = f"aac:valkey-test:{identifier}"
    job_id = f"aac-valkey-test-{identifier}"
    pool = await create_pool(RedisSettings.from_dsn(broker_url), default_queue_name=queue_name)
    worker = None
    try:
        server_info = await pool.info("server")
        assert server_info.get("valkey_version"), "The integration target must be a Valkey server"
        payload = {"marker": identifier, "transport": "existing-redis-client"}
        job = await pool.enqueue_job("_broker_echo", payload, _job_id=job_id)
        assert job is not None

        worker = Worker(
            [_broker_echo],
            redis_pool=pool,
            queue_name=queue_name,
            burst=True,
            max_burst_jobs=1,
            handle_signals=False,
            job_timeout=5,
            poll_delay=0.01,
        )
        await asyncio.wait_for(worker.async_run(), timeout=15)

        assert await job.result(timeout=3) == payload
        assert worker.jobs_complete == 1
        assert worker.jobs_failed == 0
    finally:
        await pool.delete(
            queue_name,
            f"{queue_name}:health-check",
            f"arq:job:{job_id}",
            f"arq:result:{job_id}",
            f"arq:in-progress:{job_id}",
            f"arq:retry:{job_id}",
        )
        if worker is None:
            await pool.aclose()
        else:
            await worker.close()
