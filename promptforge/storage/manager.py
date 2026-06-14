"""Unified storage manager interface."""

from typing import Any, Dict, List, Optional

from promptforge.core.models import Comment, Project, PromptTemplate, SavedPrompt
from promptforge.storage.gist_storage import GistStorage
from promptforge.storage.local_storage import LocalStorage


class StorageManager:
    """Provides unified access to local and gist storage backends."""

    def __init__(
        self,
        local_path: str = "./prompts",
        github_token: Optional[str] = None,
    ) -> None:
        self.local = LocalStorage(local_path)
        self._github_token = github_token

    def get_gist_storage(self, github_token: Optional[str] = None) -> GistStorage:
        token = github_token or self._github_token or ""
        return GistStorage(token)

    async def save_local(self, prompt: SavedPrompt, format: str = "json") -> str:
        return await self.local.save(prompt, format=format)

    async def load_local(self, prompt_id: str) -> Optional[SavedPrompt]:
        return await self.local.load(prompt_id)

    async def list_local(self) -> List[Dict[str, Any]]:
        return await self.local.list_all()

    async def delete_local(self, prompt_id: str) -> bool:
        return await self.local.delete(prompt_id)

    async def get_versions(self, name: str) -> List[Dict[str, Any]]:
        return await self.local.get_versions(name)

    async def save_comment(self, comment: Comment) -> str:
        return await self.local.save_comment(comment)

    async def list_comments(self, run_id: str) -> List[Comment]:
        return await self.local.list_comments(run_id)

    async def save_template(self, template: PromptTemplate) -> str:
        return await self.local.save_template(template)

    async def load_template(self, template_id: str) -> Optional[PromptTemplate]:
        return await self.local.load_template(template_id)

    async def list_templates(self) -> List[Dict[str, Any]]:
        return await self.local.list_templates()

    async def save_project(self, project: Project) -> str:
        return await self.local.save_project(project)

    async def load_project(self, project_id: str) -> Optional[Project]:
        return await self.local.load_project(project_id)

    async def list_projects(self) -> List[Dict[str, Any]]:
        return await self.local.list_projects()
