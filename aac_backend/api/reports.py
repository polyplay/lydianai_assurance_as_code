import hashlib
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.config import get_settings
from aac_backend.database import get_session
from aac_backend.models.artefacts import Relationship
from aac_backend.models.audit import AuditEvent, EvidenceReference, GeneratedReport
from aac_backend.models.baselines import (
    Baseline,
    BaselineArtefactRevision,
    BaselineRelationshipRevision,
)
from aac_backend.models.impact import TestResultRecord
from aac_backend.models.validation import ValidationIssue
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.services.job_service import job_data, run_tracked_job
from aac_backend.services.event_service import record_event

router = APIRouter(tags=["reports"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")
REQUIREMENT_UPLOAD_EXTENSIONS = {".pdf", ".doc", ".docx"}


@router.post("/projects/{project_id}/test-results/import", response_model=ApiEnvelope)
async def import_test_results(
    project_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    imported = []
    for item in payload.get("results", []):
        record = TestResultRecord(
            project_id=project_id,
            artefact_id=item.get("artefact_id"),
            test_specification_id=item.get("test_specification_id") or item.get("test_spec_ref"),
            baseline_id=item.get("baseline_id"),
            build_ref=item.get("build_ref"),
            environment_ref=item.get("environment_ref"),
            verdict=item["verdict"],
            executed_at=item.get("executed_at"),
            payload_json=item,
        )
        session.add(record)
        imported.append(record)
    await session.flush()
    await record_event(
        session,
        event_type="test_result.imported",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={
            "imported_count": len(imported),
            "test_result_ids": [item.test_result_record_id for item in imported],
        },
    )
    await session.commit()
    return ApiEnvelope(data={"imported_count": len(imported), "test_result_ids": [r.test_result_record_id for r in imported]})


@router.get("/projects/{project_id}/test-results", response_model=ApiEnvelope)
async def list_test_results(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    results = list(
        await session.scalars(select(TestResultRecord).where(TestResultRecord.project_id == project_id))
    )
    return ApiEnvelope(data=[_test_result_data(result) for result in results])


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
    await session.flush()
    await record_event(
        session,
        event_type="evidence.created",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={"evidence_id": evidence.evidence_id, "evidence_type": evidence.evidence_type},
    )
    await session.commit()
    return ApiEnvelope(data={"evidence_id": evidence.evidence_id})


@router.post("/projects/{project_id}/evidence/upload", response_model=ApiEnvelope)
async def upload_evidence(
    project_id: str,
    file: UploadFile = File(...),
    evidence_type: str = Form(default="requirement_source_document"),
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    filename = _safe_filename(file.filename or "upload")
    extension = Path(filename).suffix.lower()
    if evidence_type == "requirement_source_document" and extension not in REQUIREMENT_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=409, detail="Requirement uploads must be PDF, DOC, or DOCX")

    project_dir = Path(get_settings().upload_dir) / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    max_bytes = get_settings().max_evidence_bytes
    size_bytes = 0
    digest = hashlib.sha256()
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=project_dir, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            while chunk := await file.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Evidence upload exceeds {max_bytes} bytes",
                    )
                digest.update(chunk)
                temporary.write(chunk)
        checksum = digest.hexdigest()
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    stored_name = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{checksum[:12]}_{filename}"
    stored_path = project_dir / stored_name
    temporary_path.replace(stored_path)

    evidence = EvidenceReference(
        project_id=project_id,
        evidence_type=evidence_type,
        uri=str(stored_path),
        checksum=checksum,
        metadata_json={
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": size_bytes,
        },
        created_by=current.user.user_id,
        created_at=datetime.now(UTC),
    )
    session.add(evidence)
    await session.flush()
    await record_event(
        session,
        event_type="evidence.uploaded",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={"evidence_id": evidence.evidence_id, "size_bytes": size_bytes},
    )
    await session.commit()
    return ApiEnvelope(
        data={
            "evidence_id": evidence.evidence_id,
            "evidence_type": evidence.evidence_type,
            "uri": evidence.uri,
            "checksum": evidence.checksum,
            "metadata": evidence.metadata_json,
        }
    )


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
        report_payload = await _build_report_payload(session, project_id, payload)
        report = GeneratedReport(
            project_id=project_id,
            baseline_id=payload.get("baseline_id"),
            report_type=payload.get("report_type", "evidence_bundle"),
            state="completed",
            format=payload.get("format", "json"),
            generated_by=current.user.user_id,
            generated_at=datetime.now(UTC),
            payload_ref_json=report_payload,
        )
        session.add(report)
        await session.flush()
        await record_event(
            session,
            event_type="report.generated",
            project_id=project_id,
            actor_user_id=current.user.user_id,
            payload={"report_id": report.report_id, "report_type": report.report_type},
        )
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
    current: CurrentUser = Depends(project_role_dependency("admin", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    report = await session.get(GeneratedReport, report_id)
    if not report or report.project_id != project_id:
        raise HTTPException(status_code=404, detail="Report not found")
    report.state = "obsolete"
    await record_event(
        session,
        event_type="report.obsoleted",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={"report_id": report.report_id},
    )
    await session.commit()
    return ApiEnvelope(data=_report_data(report))


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "upload"


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


async def _build_report_payload(session: AsyncSession, project_id: str, payload: dict) -> dict:
    report_type = payload.get("report_type", "evidence_bundle")
    if report_type == "traceability_matrix":
        relationships = list(
            await session.scalars(
                select(Relationship).where(
                    Relationship.project_id == project_id,
                    Relationship.deleted_at.is_(None),
                )
            )
        )
        return {
            "report_type": report_type,
            "relationships": [
                {
                    "relationship_id": relationship.relationship_id,
                    "relationship_type": relationship.relationship_type,
                    "source_artefact_id": relationship.source_artefact_id,
                    "target_artefact_id": relationship.target_artefact_id,
                }
                for relationship in relationships
            ],
        }
    if report_type == "validation_summary":
        issues = list(
            await session.scalars(
                select(ValidationIssue).where(
                    ValidationIssue.project_id == project_id,
                    ValidationIssue.status == "open",
                )
            )
        )
        by_severity: dict[str, list[dict]] = {}
        for issue in issues:
            by_severity.setdefault(issue.severity, []).append(
                {
                    "validation_issue_id": issue.validation_issue_id,
                    "rule_id": issue.rule_id,
                    "message": issue.message,
                    "blocking_contexts": issue.blocking_contexts_json,
                }
            )
        return {
            "report_type": report_type,
            "open_issue_count": len(issues),
            "issues_by_severity": by_severity,
        }
    if report_type == "baseline_comparison":
        left_id = payload["left_baseline_id"]
        right_id = payload["right_baseline_id"]
        if left_id == right_id:
            raise HTTPException(status_code=409, detail="Comparison baselines must be different")
        left = await session.get(Baseline, left_id)
        right = await session.get(Baseline, right_id)
        if (
            left is None
            or right is None
            or left.project_id != project_id
            or right.project_id != project_id
        ):
            raise HTTPException(status_code=404, detail="Comparison baseline not found")
        return {
            "report_type": report_type,
            "left_baseline_id": left_id,
            "right_baseline_id": right_id,
            "artefacts": _revision_map_delta(
                await _baseline_artefact_map(session, left_id),
                await _baseline_artefact_map(session, right_id),
            ),
            "relationships": _revision_map_delta(
                await _baseline_relationship_map(session, left_id),
                await _baseline_relationship_map(session, right_id),
            ),
        }
    return {"report_type": report_type, "request": payload}


async def _baseline_artefact_map(session: AsyncSession, baseline_id: str) -> dict[str, str]:
    return {
        row.artefact_id: row.artefact_revision_id
        for row in await session.scalars(
            select(BaselineArtefactRevision).where(BaselineArtefactRevision.baseline_id == baseline_id)
        )
    }


async def _baseline_relationship_map(session: AsyncSession, baseline_id: str) -> dict[str, str]:
    return {
        row.relationship_id: row.relationship_revision_id
        for row in await session.scalars(
            select(BaselineRelationshipRevision).where(
                BaselineRelationshipRevision.baseline_id == baseline_id
            )
        )
    }


def _revision_map_delta(left: dict[str, str], right: dict[str, str]) -> dict:
    left_ids = set(left)
    right_ids = set(right)
    common = left_ids & right_ids
    return {
        "added": sorted(right_ids - left_ids),
        "removed": sorted(left_ids - right_ids),
        "changed": sorted(item_id for item_id in common if left[item_id] != right[item_id]),
        "unchanged": sorted(item_id for item_id in common if left[item_id] == right[item_id]),
    }


@router.get("/projects/{project_id}/audit-events", response_model=ApiEnvelope)
async def audit_events(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    events = list(
        await session.scalars(select(AuditEvent).where(AuditEvent.project_id == project_id))
    )
    return ApiEnvelope(
        data=[
            {
                "audit_event_id": event.audit_event_id,
                "event_type": event.event_type,
                "actor_user_id": event.actor_user_id,
                "created_at": event.created_at,
                "affected_artefact_ids": event.affected_artefact_ids_json,
                "affected_relationship_ids": event.affected_relationship_ids_json,
                "payload": event.payload_json,
            }
            for event in events
        ]
    )


def _test_result_data(result: TestResultRecord) -> dict:
    return {
        "test_result_record_id": result.test_result_record_id,
        "artefact_id": result.artefact_id,
        "test_specification_id": result.test_specification_id,
        "baseline_id": result.baseline_id,
        "build_ref": result.build_ref,
        "environment_ref": result.environment_ref,
        "verdict": result.verdict,
        "executed_at": result.executed_at,
        "payload": result.payload_json,
    }
