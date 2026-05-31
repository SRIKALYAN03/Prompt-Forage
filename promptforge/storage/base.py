"""Abstract base class for prompt storage backends."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from promptforge.core.models import SavedPrompt


class StorageError(Exception):
    """Base exception for storage failures."""


class AuthError(StorageError):
    """Raised when storage authentication fails."""


class BaseStorage(ABC):
    """Abstract base class for prompt storage."""

    @abstractmethod
    async def save(self, prompt: SavedPrompt, **kwargs) -> str:
        """Save a prompt and return storage location identifier."""

    @abstractmethod
    async def load(self, prompt_id: str) -> Optional[SavedPrompt]:
        """Load a prompt by ID. Returns None if not found."""

    @abstractmethod
    async def list_all(self) -> List[Dict]:
        """Return summary list of all saved prompts."""

    @abstractmethod
    async def delete(self, prompt_id: str) -> bool:
        """Delete a prompt. Returns True if deleted."""
