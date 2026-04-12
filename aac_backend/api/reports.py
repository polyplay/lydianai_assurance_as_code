from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.audit import EvidenceReference, GeneratedReport
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.services.job_service import job_data, run_tracked_job

router = APIRouter(tags=["reports"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.post("/projects/{project_id}/evidence", response_model=ApiEnvelope)
async def create_evidence(
    project_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    evidence = EvidenceReference(
        project_id=project_id,
        evidence_type=payload.get("evidence_type", "external"),
        uri=payload["uri"],
        checksum=payload.get("checksum"),
        metadata_json=payload.get("metadata", {}),
        created_by=current.user.user_id,
        created_at=datetime.now(UTC),
    )
    session.add(evidence)
    await session.commit()
    return ApiEnvelope(data={"evidence_id": evidence.evidence_id})


@router.get("/projects/{project_id}/evidence/{evidence_id}", response_model=ApiEnvelope)
async def get_evidence(
    project_id: str,
    evidence_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    evidence = await session.get(EvidenceReference, evidence_id)
    if not evidence or evidence.project_id != project_id:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return ApiEnvelope(
        data={
            "evidence_id": evidence.evidence_id,
            "evidence_type": evidence.evidence_type,
            "uri": evidence.uri,
            "checksum": evidence.checksum,
            "metadata": evidence.metadata_json,
        }
    )


@router.post("/projects/{project_id}/reports", response_model=ApiEnvelope)
async def generate_report(
    project_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    async def operation(job):
        report = GeneratedReport(
            project_id=project_id,
            baseline_id=payload.get("baseline_id"),
            report_type=payload.get("report_type", "evidence_bundle"),
            state="completed",
            format=payload.get("format", "json"),
            generated_by=current.user.user_id,
            generated_at=datetime.now(UTC),
            payload_ref_json=payload,
        )
        session.add(report)
        await session.flush()
        job.result_ref_json = {"resource_type": "GeneratedReport", "resource_id": report.report_id}
        return report

    job, report = await run_tracked_job(
        session,
        project_id=project_id,
        job_type="report_generation",
        submitted_by=current.user.user_id,
        operation=operation,
    )
    await session.commit()
    return ApiEnvelope(
        status="accepted",
        data={"job": job_data(job), "report_id": report.report_id, "state": report.state},
    )


@router.get("/projects/{project_id}/reports", response_model=ApiEnvelope)
async def list_reports(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    reports = list(await session.scalars(select(GeneratedReport).where(GeneratedReport.project_id == project_id)))
    return ApiEnvelope(
        data=[
            {"report_id": report.report_id, "report_type": report.report_type, "state": report.state}
            for report in reports
        ]
    )


@router.get("/projects/{project_id}/reports/{report_id}", response_model=ApiEnvelope)
async def get_report(
    project_id: str,
    report_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    report = await session.get(GeneratedReport, report_id)
    if not report or report.project_id != project_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiEnvelope(data=_report_data(report))


@router.delete("/projects/{project_id}/reports/{report_id}", response_model=ApiEnvelope)
async def delete_report(
    project_id: str,
    report_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    report = await session.get(GeneratedReport, report_id)
    if not report or report.project_id != project_id:
        raise HTTPException(status_code=404, detail="Report not found")
    report.state = "obsolete"
    await session.commit()
    return ApiEnvelope(data=_report_data(report))


def _report_data(report: GeneratedReport) -> dict:
    return {
        "report_id": report.report_id,
        "project_id": report.project_id,
        "baseline_id": report.baseline_id,
        "report_type": report.report_type,
        "state": report.state,
        "format": report.format,
        "uri": report.uri,
        "payload_ref": report.payload_ref_json,
    }
