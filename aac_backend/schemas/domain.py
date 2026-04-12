from typing import Any, Literal

from pydantic import BaseModel, Field

from aac_backend.schemas.common import OrmModel


ArtefactStatus = Literal["draft", "under_review", "reviewed", "approved", "released", "obsolete"]


class ProjectCreate(BaseModel):
    project_key: str
    name: str
    description: str = ""
    active_profile_id: str | None = None


class ProjectRead(OrmModel):
    project_id: str
    project_key: str
    name: str
    description: str
    active_profile_id: str | None
    status: str


class ArtefactSource(BaseModel):
    source_kind: str = "api"
    source_tool: str | None = None
    source_object_id: str
    source_document: str = ""
    external_uri: str | None = None


class ArtefactCreate(BaseModel):
    artefact_type: str
    title: str
    description: str = ""
    status: ArtefactStatus = "draft"
    owner_user_id: str | None = None
    source: ArtefactSource
    standards_refs: list[str] = Field(default_factory=list)
    work_product_kind: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ArtefactUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: ArtefactStatus | None = None
    standards_refs: list[str] | None = None
    payload: dict[str, Any] | None = None
    base_revision_id: str | None = None
    change_reason: str = "api update"


class ArtefactRead(OrmModel):
    artefact_id: str
    project_id: str
    artefact_type: str
    title: str
    description: str
    status: str
    current_revision_id: str | None
    source_kind: str
    source_tool: str | None
    source_object_id: str
    source_document: str
    standards_refs_json: list
    payload_json: dict


class RelationshipCreate(BaseModel):
    relationship_type: str
    source_artefact_id: str
    target_artefact_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RelationshipRead(OrmModel):
    relationship_id: str
    project_id: str
    relationship_type: str
    source_artefact_id: str
    target_artefact_id: str
    status: str
    current_revision_id: str | None
    payload_json: dict


class ImportStart(BaseModel):
    source_root: str
    version_update_mode: Literal["automatic_new_version", "ask_user"] | None = None
    sphinx_needs: list[dict[str, Any]] = Field(default_factory=list)


class BaselineCreate(BaseModel):
    name: str
    description: str = ""
    profile_id: str | None = None
    scope: dict[str, Any] = Field(default_factory=dict)


class ReleaseGateRun(BaseModel):
    baseline_id: str
