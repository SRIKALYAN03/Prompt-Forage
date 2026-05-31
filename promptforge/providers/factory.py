"""Factory for creating LLM provider instances from configuration."""

from promptforge.config import Settings
from promptforge.core.models import ProviderConfig, ProviderType
from promptforge.providers.anthropic_provider import AnthropicProvider
from promptforge.providers.base import BaseProvider, ConfigurationError
from promptforge.providers.compat_provider import CompatProvider
from promptforge.providers.ollama_provider import OllamaProvider
from promptforge.providers.openai_provider import OpenAIProvider


class ProviderFactory:
    """Creates the correct provider from a ProviderConfig."""

    @staticmethod
    def create(config: ProviderConfig, settings: Settings) -> BaseProvider:
        """
        Factory method returning the correct provider instance.

        Args:
            config: Provider configuration from the request.
            settings: Application settings for fallback keys/URLs.

        Returns:
            Configured BaseProvider instance.

        Raises:
            ConfigurationError: If required keys or URLs are missing.
            ValueError: If provider type is unknown.
        """
        if config.provider_type == ProviderType.ANTHROPIC:
            key = config.api_key or settings.anthropic_api_key
            if not key:
                raise ConfigurationError("Anthropic API key not configured")
            return AnthropicProvider(api_key=key, model=config.model)

        if config.provider_type == ProviderType.OPENAI:
            key = config.api_key or settings.openai_api_key
            if not key:
                raise ConfigurationError("OpenAI API key not configured")
            return OpenAIProvider(api_key=key, model=config.model)

        if config.provider_type == ProviderType.OLLAMA:
            return OllamaProvider(
                base_url=config.base_url or settings.ollama_base_url,
                model=config.model or settings.ollama_default_model,
            )

        if config.provider_type == ProviderType.COMPAT:
            base_url = config.base_url or settings.custom_endpoint_url
            if not base_url:
                raise ConfigurationError("Custom endpoint URL not configured")
            api_key = config.api_key or settings.custom_endpoint_key or "local"
            model = config.model or settings.custom_endpoint_model or "default"
            return CompatProvider(base_url=base_url, model=model, api_key=api_key)

        raise ValueError(f"Unknown provider type: {config.provider_type}")
