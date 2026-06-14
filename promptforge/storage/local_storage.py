"""Local JSON/YAML file storage for saved prompts, comments, templates, and projects."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles  # type: ignore[import-untyped]
import yaml  # type: ignore[import-untyped]

from promptforge.core.models import Comment, Project, PromptTemplate, SavedPrompt
from promptforge.storage.base import BaseStorage, StorageError


class LocalStorage(BaseStorage):
    """Saves and loads prompts as JSON and YAML files on disk."""

    def __init__(self, storage_path: str = "./prompts") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "comments").mkdir(parents=True, exist_ok=True)
        (self.storage_path / "templates").mkdir(parents=True, exist_ok=True)
        (self.storage_path / "projects").mkdir(parents=True, exist_ok=True)

    def _file_path(self, prompt_id: str, fmt: str = "json") -> Path:
        return self.storage_path / f"{prompt_id}.{fmt}"

    async def _find_latest_by_name(self, name: str) -> Optional[SavedPrompt]:
        best: Optional[SavedPrompt] = None
        for file_path in self.storage_path.glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                if data.get("name") == name:
                    candidate = SavedPrompt(**data)
                    if best is None or candidate.version > best.version:
                        best = candidate
            except (OSError, json.JSONDecodeError, ValueError):
                continue
        return best

    async def save(self, prompt: SavedPrompt, **kwargs: Any) -> str:
        fmt = str(kwargs.get("format", "json"))
        if prompt.name:
            existing = await self._find_latest_by_name(prompt.name)
            if existing and existing.id != prompt.id:
                prompt = prompt.model_copy(
                    update={"version": existing.version + 1, "parent_id": existing.id}
                )
        file_path = self._file_path(prompt.id, fmt)
        data = prompt.model_dump()
        try:
            if fmt == "yaml":
                content = yaml.dump(data, default_flow_style=False)
            else:
                content = json.dumps(data, indent=2)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
        except OSError as exc:
            raise StorageError(f"Failed to save prompt: {exc}") from exc
        return str(file_path)

    async def load(self, prompt_id: str) -> Optional[SavedPrompt]:
        for fmt in ("json", "yaml"):
            file_path = self._file_path(prompt_id, fmt)
            if not file_path.exists():
                continue
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                if fmt == "yaml":
                    data = yaml.safe_load(content)
                else:
                    data = json.loads(content)
                return SavedPrompt(**data)
            except (OSError, yaml.YAMLError, json.JSONDecodeError, ValueError):
                continue
        return None

    async def list_all(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for file_path in self.storage_path.glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                results.append({
                    "id": data.get("id", file_path.stem),
                    "name": data.get("name"),
                    "saved_at": data.get("saved_at"),
                    "score": data.get("run_result", {}).get("score"),
                    "version": data.get("version", 1),
                    "author": data.get("author"),
                })
            except (OSError, json.JSONDecodeError):
                continue
        return results

    async def get_versions(self, name: str) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for file_path in self.storage_path.glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                if data.get("name") == name:
                    results.append({
                        "id": data.get("id"),
                        "version": data.get("version", 1),
                        "parent_id": data.get("parent_id"),
                        "saved_at": data.get("saved_at"),
                        "score": data.get("run_result", {}).get("score"),
                        "author": data.get("author"),
                    })
            except (OSError, json.JSONDecodeError):
                continue
        results.sort(key=lambda x: x.get("version", 1))
        return results

    async def delete(self, prompt_id: str) -> bool:
        deleted = False
        for fmt in ("json", "yaml"):
            file_path = self._file_path(prompt_id, fmt)
            if file_path.exists():
                file_path.unlink()
                deleted = True
        return deleted

    # Comments
    async def save_comment(self, comment: Comment) -> str:
        file_path = self.storage_path / "comments" / f"{comment.run_id}_{comment.id}.json"
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(comment.model_dump(), indent=2))
        except OSError as exc:
            raise StorageError(f"Failed to save comment: {exc}") from exc
        return str(file_path)

    async def list_comments(self, run_id: str) -> List[Comment]:
        results: List[Comment] = []
        prefix = f"{run_id}_"
        for file_path in (self.storage_path / "comments").glob(f"{prefix}*.json"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                results.append(Comment(**data))
            except (OSError, json.JSONDecodeError, ValueError):
                continue
        return results

    # Templates
    async def save_template(self, template: PromptTemplate) -> str:
        file_path = self.storage_path / "templates" / f"{template.id}.json"
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(template.model_dump(), indent=2))
        except OSError as exc:
            raise StorageError(f"Failed to save template: {exc}") from exc
        return str(file_path)

    async def load_template(self, template_id: str) -> Optional[PromptTemplate]:
        file_path = self.storage_path / "templates" / f"{template_id}.json"
        if not file_path.exists():
            return None
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            return PromptTemplate(**data)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    async def list_templates(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for file_path in (self.storage_path / "templates").glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                results.append({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "variables": data.get("variables", []),
                    "created_at": data.get("created_at"),
                })
            except (OSError, json.JSONDecodeError):
                continue
        return results

    # Projects
    async def save_project(self, project: Project) -> str:
        file_path = self.storage_path / "projects" / f"{project.id}.json"
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(project.model_dump(), indent=2))
        except OSError as exc:
            raise StorageError(f"Failed to save project: {exc}") from exc
        return str(file_path)

    async def load_project(self, project_id: str) -> Optional[Project]:
        file_path = self.storage_path / "projects" / f"{project_id}.json"
        if not file_path.exists():
            return None
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            return Project(**data)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    async def list_projects(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for file_path in (self.storage_path / "projects").glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                results.append({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "description": data.get("description"),
                    "tags": data.get("tags", []),
                    "prompt_count": len(data.get("prompt_ids", [])),
                    "created_at": data.get("created_at"),
                })
            except (OSError, json.JSONDecodeError):
                continue
        return results
