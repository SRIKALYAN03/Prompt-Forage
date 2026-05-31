"""Local JSON/YAML file storage for saved prompts."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles  # type: ignore[import-untyped]
import yaml  # type: ignore[import-untyped]

from promptforge.core.models import SavedPrompt
from promptforge.storage.base import BaseStorage, StorageError


class LocalStorage(BaseStorage):
    """Saves and loads prompts as JSON and YAML files on disk."""

    def __init__(self, storage_path: str = "./prompts") -> None:
        """
        Initialize local storage.

        Args:
            storage_path: Directory path for prompt files.
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _file_path(self, prompt_id: str, fmt: str = "json") -> Path:
        """Return file path for a prompt ID."""
        return self.storage_path / f"{prompt_id}.{fmt}"

    async def save(self, prompt: SavedPrompt, **kwargs: object) -> str:
        """
        Save prompt to disk.

        Args:
            prompt: SavedPrompt to persist.
            **kwargs: format ('json' or 'yaml').

        Returns:
            File path string.

        Raises:
            StorageError: On write failure.
        """
        format = str(kwargs.get("format", "json"))
        file_path = self._file_path(prompt.id, format)
        data = prompt.model_dump()

        try:
            if format == "yaml":
                content = yaml.dump(data, default_flow_style=False)
            else:
                content = json.dumps(data, indent=2)

            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
        except OSError as exc:
            raise StorageError(f"Failed to save prompt: {exc}") from exc

        return str(file_path)

    async def load(self, prompt_id: str) -> Optional[SavedPrompt]:
        """
        Load prompt by ID from json or yaml file.

        Args:
            prompt_id: Prompt identifier.

        Returns:
            SavedPrompt if found, else None.
        """
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

    async def list_all(self) -> List[Dict]:
        """
        Return summary list of all saved prompts.

        Returns:
            List of dicts with id, name, saved_at, score.
        """
        results: List[Dict] = []
        for file_path in self.storage_path.glob("*.json"):
            try:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    data = json.loads(await f.read())
                results.append(
                    {
                        "id": data.get("id", file_path.stem),
                        "name": data.get("name"),
                        "saved_at": data.get("saved_at"),
                        "score": data.get("run_result", {}).get("score"),
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
        return results

    async def delete(self, prompt_id: str) -> bool:
        """
        Delete prompt file.

        Args:
            prompt_id: Prompt identifier.

        Returns:
            True if a file was deleted.
        """
        deleted = False
        for fmt in ("json", "yaml"):
            file_path = self._file_path(prompt_id, fmt)
            if file_path.exists():
                file_path.unlink()
                deleted = True
        return deleted
