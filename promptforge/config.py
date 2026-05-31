"""Application settings loaded from environment variables and .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to project root (parent of promptforge/), not the cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Runtime configuration for PromptForge."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "PromptForge"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Providers
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.2"
    custom_endpoint_url: Optional[str] = None
    custom_endpoint_key: Optional[str] = None
    custom_endpoint_model: Optional[str] = None

    # Guardrails
    default_token_limit: int = 4000
    enable_pii_scan: bool = True
    enable_injection_guard: bool = True
    enable_hallucination_guard: bool = True

    # Storage
    local_storage_path: str = "./prompts"
    github_token: Optional[str] = None

    @field_validator(
        "anthropic_api_key",
        "openai_api_key",
        "custom_endpoint_url",
        "custom_endpoint_key",
        "custom_endpoint_model",
        "github_token",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, value: object) -> object:
        """Treat blank env values as unset (None)."""
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
