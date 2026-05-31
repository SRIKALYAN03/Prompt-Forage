"""Base provider interface and shared types."""

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""

    text: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    model: str
    provider: str


class ProviderError(Exception):
    """Base exception for provider failures."""


class AuthenticationError(ProviderError):
    """Raised when API authentication fails."""


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out."""


class OllamaNotRunningError(ProviderError):
    """Raised when Ollama is not reachable."""


class ConfigurationError(Exception):
    """Raised when provider configuration is invalid or incomplete."""


class BaseProvider(ABC):
    """Abstract base class all LLM providers must implement."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        image_base64: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Send a chat request and return LLMResponse."""

    @abstractmethod
    async def list_models(self) -> List[str]:
        """Return list of available model names."""

    @abstractmethod
    def supports_vision(self) -> bool:
        """Return True if this provider supports image input."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier string."""
