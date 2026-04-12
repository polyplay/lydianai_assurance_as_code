from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, ArtefactRevision, Relationship, RelationshipRevision
from aac_backend.models.baselines import Baseline
from aac_backend.models.jobs import ProjectUpdateLock
from aac_backend.models.projects import Project, ProjectConfiguration
from aac_backend.models.validation import ValidationIssue
from aac_backend.repositories.base import Repository


class ProjectRepository(Repository[Project]):
    model = Project

    async def by_key(self, project_key: str) -> Project | None:
        return await self.session.scalar(select(Project).where(Project.project_key == project_key))


class ProjectConfigurationRepository(Repository[ProjectConfiguration]):
    model = ProjectConfiguration


class ArtefactRepository(Repository[Artefact]):
    model = Artefact

    async def list_for_project(self, project_id: str) -> list[Artefact]:
        result = await self.session.scalars(
            select(Artefact).where(Artefact.project_id == project_id, Artefact.deleted_at.is_(None))
        )
        return list(result)

    async def by_source_identity(
        self,
        project_id: str,
        source_document: str,
        source_object_id: str,
    ) -> Artefact | None:
        return await self.session.scalar(
            select(Artefact).where(
                Artefact.project_id == project_id,
                Artefact.source_document == source_document,
                Artefact.source_object_id == source_object_id,
            )
        )

    async def next_revision_number(self, artefact_id: str) -> int:
        value = await self.session.scalar(
            select(func.max(ArtefactRevision.revision_number)).where(
                ArtefactRevision.artefact_id == artefact_id
            )
        )
        return int(value or 0) + 1


class RelationshipRepository(Repository[Relationship]):
    model = Relationship

    async def list_for_project(self, project_id: str) -> list[Relationship]:
        result = await self.session.scalars(
            select(Relationship).where(
                Relationship.project_id == project_id,
                Relationship.deleted_at.is_(None),
            )
        )
        return list(result)

    async def next_revision_number(self, relationship_id: str) -> int:
        value = await self.session.scalar(
            select(func.max(RelationshipRevision.revision_number)).where(
                RelationshipRevision.relationship_id == relationship_id
            )
        )
        return int(value or 0) + 1


class BaselineRepository(Repository[Baseline]):
    model = Baseline

    async def list_for_project(self, project_id: str) -> list[Baseline]:
        result = await self.session.scalars(select(Baseline).where(Baseline.project_id == project_id))
        return list(result)


class ValidationIssueRepository(Repository[ValidationIssue]):
    model = ValidationIssue


async def has_project_update_lock(session: AsyncSession, project_id: str) -> bool:
    lock = await session.get(ProjectUpdateLock, project_id)
    return lock is not None
