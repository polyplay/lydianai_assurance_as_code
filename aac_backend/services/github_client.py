from __future__ import annotations

import base64
import time
from typing import Any
from urllib.parse import quote

import httpx
import jwt

from aac_backend.config import get_settings


class GitHubClient:
    def __init__(
        self,
        *,
        app_id: str | None = None,
        installation_id: str | None = None,
        private_key_pem: str | None = None,
        access_token: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        self.app_id = app_id
        self.installation_id = installation_id
        self.private_key_pem = private_key_pem
        self.access_token = access_token
        self.api_base_url = api_base_url or get_settings().github_api_base_url
        self._installation_token: str | None = None

    async def get_repository(self, owner: str, repository: str) -> dict[str, Any]:
        return await self._request("GET", f"/repos/{owner}/{repository}")

    async def get_commit(self, owner: str, repository: str, ref: str) -> dict[str, Any]:
        return await self._request("GET", f"/repos/{owner}/{repository}/commits/{quote(ref, safe='')}")

    async def get_file_text(self, owner: str, repository: str, path: str, ref: str) -> str:
        encoded_path = "/".join(quote(part, safe="") for part in path.split("/"))
        payload = await self._request(
            "GET",
            f"/repos/{owner}/{repository}/contents/{encoded_path}",
            params={"ref": ref},
        )
        if payload.get("encoding") != "base64" or "content" not in payload:
            raise ValueError(f"GitHub content response for {path} is not base64 file content")
        return base64.b64decode(payload["content"]).decode("utf-8")

    async def get_tree_paths(self, owner: str, repository: str, commit_sha: str) -> set[str]:
        commit = await self.get_commit(owner, repository, commit_sha)
        tree_sha = ((commit.get("commit") or {}).get("tree") or {}).get("sha")
        if not tree_sha:
            return set()
        payload = await self._request(
            "GET",
            f"/repos/{owner}/{repository}/git/trees/{tree_sha}",
            params={"recursive": "1"},
        )
        return {
            item["path"]
            for item in payload.get("tree", [])
            if item.get("type") == "blob" and item.get("path")
        }

    async def list_check_runs(self, owner: str, repository: str, ref: str) -> list[dict[str, Any]]:
        payload = await self._request(
            "GET",
            f"/repos/{owner}/{repository}/commits/{quote(ref, safe='')}/check-runs",
        )
        return list(payload.get("check_runs") or [])

    async def get_combined_status(self, owner: str, repository: str, ref: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/repos/{owner}/{repository}/commits/{quote(ref, safe='')}/status",
        )

    async def create_check_run(
        self,
        *,
        owner: str,
        repository: str,
        name: str,
        commit_sha: str,
        status: str,
        conclusion: str | None,
        summary: str,
        details_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "head_sha": commit_sha,
            "status": status,
            "output": {"title": name, "summary": summary},
        }
        if conclusion:
            payload["conclusion"] = conclusion
        if details_url:
            payload["details_url"] = details_url
        return await self._request("POST", f"/repos/{owner}/{repository}/check-runs", json=payload)

    async def create_commit_status(
        self,
        *,
        owner: str,
        repository: str,
        commit_sha: str,
        state: str,
        context: str,
        description: str,
        target_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "state": state,
            "context": context,
            "description": description[:140],
        }
        if target_url:
            payload["target_url"] = target_url
        return await self._request("POST", f"/repos/{owner}/{repository}/statuses/{commit_sha}", json=payload)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        token = await self._auth_token()
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=30) as client:
            response = await client.request(method, path, headers=headers, json=json, params=params)
            response.raise_for_status()
            return response.json()

    async def _auth_token(self) -> str:
        if self.access_token:
            return self.access_token
        if self._installation_token:
            return self._installation_token
        if not self.app_id or not self.installation_id or not self.private_key_pem:
            raise ValueError("GitHub App credentials or access token are required")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._app_jwt()}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=30) as client:
            response = await client.post(
                f"/app/installations/{self.installation_id}/access_tokens",
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
        self._installation_token = payload["token"]
        return self._installation_token

    def _app_jwt(self) -> str:
        now = int(time.time())
        return jwt.encode(
            {"iat": now - 60, "exp": now + 540, "iss": self.app_id},
            self.private_key_pem,
            algorithm="RS256",
        )
