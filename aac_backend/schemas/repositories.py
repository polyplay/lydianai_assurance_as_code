from typing import Any, Literal

from pydantic import BaseModel, Field


AuthMode = Literal["github_app", "access_token"]


class GitHubAppConnectorConfig(BaseModel):
    app_id: str
    installation_id: str
    private_key_pem: str | None = None
    webhook_secret: str | None = None


class GitHubAccessTokenConfig(BaseModel):
    access_token: str | None = None
    webhook_secret: str | None = None


class RepositoryConnectorCreate(BaseModel):
    provider: Literal["github"] = "github"
    auth_mode: AuthMode = "github_app"
    name: str | None = None
    owner: str
    repository: str
    repository_url: str | None = None
    default_branch: str = "main"
    github_app: GitHubAppConnectorConfig | None = None
    access_token: GitHubAccessTokenConfig | None = None
    scan_policy: dict[str, Any] = Field(default_factory=dict)
    mapping_policy: dict[str, Any] = Field(default_factory=dict)


class RepositoryConnectorUpdate(BaseModel):
    name: str | None = None
    repository_url: str | None = None
    default_branch: str | None = None
    status: Literal["active", "disabled", "deleted"] | None = None
    auth_mode: AuthMode | None = None
    github_app: GitHubAppConnectorConfig | None = None
    access_token: GitHubAccessTokenConfig | None = None
    scan_policy: dict[str, Any] | None = None
    mapping_policy: dict[str, Any] | None = None


class RepositoryScanStart(BaseModel):
    trigger: str = "manual"
    commit_sha: str | None = None
    branch: str | None = None
    pull_request_id: str | int | None = None


class RepositoryApprovalPublish(BaseModel):
    baseline_id: str
    details_url: str | None = None
