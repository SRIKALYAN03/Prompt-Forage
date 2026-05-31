"""GitHub Gist storage for saved prompts."""

import json
from typing import Dict, List, Optional

import httpx

from promptforge.core.models import SavedPrompt
from promptforge.storage.base import AuthError, BaseStorage, StorageError

GIST_API_URL = "https://api.github.com/gists"
PROMPTFORGE_DESCRIPTION = "PromptForge saved prompt"


class GistStorage(BaseStorage):
    """Saves and loads prompts via GitHub Gist API."""

    def __init__(self, github_token: str) -> None:
        """
        Initialize Gist storage.

        Args:
            github_token: GitHub personal access token.
        """
        self.token = github_token
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30.0,
        )

    async def save(self, prompt: SavedPrompt, **kwargs: object) -> str:
        """
        Save prompt as a GitHub Gist.

        Args:
            prompt: SavedPrompt to persist.
            **kwargs: public (bool) whether gist is public.

        Returns:
            Gist URL string.

        Raises:
            AuthError: On invalid token.
            StorageError: On network or API failure.
        """
        public = bool(kwargs.get("public", False))
        payload = {
            "description": f"{PROMPTFORGE_DESCRIPTION}: {prompt.name or prompt.id}",
            "public": public,
            "files": {
                f"{prompt.id}.json": {
                    "content": json.dumps(prompt.model_dump(), indent=2),
                }
            },
        }
        try:
            response = await self.client.post(GIST_API_URL, json=payload)
            if response.status_code == 401:
                raise AuthError("Invalid GitHub token")
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            if isinstance(exc, AuthError):
                raise
            raise StorageError(f"Failed to save gist: {exc}") from exc

        return data.get("html_url", data.get("url", ""))

    async def load(self, gist_id: str) -> Optional[SavedPrompt]:
        """
        Load prompt from Gist by ID.

        Args:
            gist_id: GitHub Gist ID.

        Returns:
            SavedPrompt if found, else None.
        """
        try:
            response = await self.client.get(f"{GIST_API_URL}/{gist_id}")
            if response.status_code == 404:
                return None
            if response.status_code == 401:
                raise AuthError("Invalid GitHub token")
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            if isinstance(exc, AuthError):
                raise
            raise StorageError(f"Failed to load gist: {exc}") from exc

        files = data.get("files", {})
        for file_info in files.values():
            content = file_info.get("content", "")
            if content:
                prompt_data = json.loads(content)
                return SavedPrompt(**prompt_data)
        return None

    async def list_all(self) -> List[Dict]:
        """
        List all PromptForge gists for this token.

        Returns:
            List of gist summary dicts.
        """
        try:
            response = await self.client.get(GIST_API_URL)
            if response.status_code == 401:
                raise AuthError("Invalid GitHub token")
            response.raise_for_status()
            gists = response.json()
        except httpx.HTTPError as exc:
            if isinstance(exc, AuthError):
                raise
            raise StorageError(f"Failed to list gists: {exc}") from exc

        results: List[Dict] = []
        for gist in gists:
            desc = gist.get("description", "")
            if PROMPTFORGE_DESCRIPTION.lower() in desc.lower():
                results.append(
                    {
                        "id": gist.get("id"),
                        "name": desc,
                        "saved_at": gist.get("created_at"),
                        "url": gist.get("html_url"),
                    }
                )
        return results

    async def delete(self, prompt_id: str) -> bool:
        """
        Delete a gist by ID.

        Args:
            prompt_id: Gist ID to delete.

        Returns:
            True if deleted successfully.
        """
        try:
            response = await self.client.delete(f"{GIST_API_URL}/{prompt_id}")
            return response.status_code == 204
        except httpx.HTTPError as exc:
            raise StorageError(f"Failed to delete gist: {exc}") from exc

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
