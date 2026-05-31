"""Unified storage manager interface."""

from typing import Dict, List, Optional

from promptforge.core.models import SavedPrompt
from promptforge.storage.gist_storage import GistStorage
from promptforge.storage.local_storage import LocalStorage


class StorageManager:
    """Provides unified access to local and gist storage backends."""

    def __init__(
        self,
        local_path: str = "./prompts",
        github_token: Optional[str] = None,
    ) -> None:
        """
        Initialize storage manager.

        Args:
            local_path: Path for local JSON/YAML storage.
            github_token: Optional GitHub token for gist storage.
        """
        self.local = LocalStorage(local_path)
        self._github_token = github_token

    def get_gist_storage(self, github_token: Optional[str] = None) -> GistStorage:
        """
        Return GistStorage with the given or configured token.

        Args:
            github_token: Override token for this operation.

        Returns:
            Configured GistStorage instance.
        """
        token = github_token or self._github_token or ""
        return GistStorage(token)

    async def save_local(
        self,
        prompt: SavedPrompt,
        format: str = "json",
    ) -> str:
        """Save prompt to local storage."""
        return await self.local.save(prompt, format=format)

    async def load_local(self, prompt_id: str) -> Optional[SavedPrompt]:
        """Load prompt from local storage."""
        return await self.local.load(prompt_id)

    async def list_local(self) -> List[Dict]:
        """List all locally saved prompts."""
        return await self.local.list_all()

    async def delete_local(self, prompt_id: str) -> bool:
        """Delete prompt from local storage."""
        return await self.local.delete(prompt_id)
