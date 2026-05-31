# tests/test_provider_factory.py
"""Tests for promptforge.providers.factory."""

import pytest

from promptforge.core.models import ProviderConfig, ProviderType
from promptforge.providers.anthropic_provider import AnthropicProvider
from promptforge.providers.base import ConfigurationError
from promptforge.providers.compat_provider import CompatProvider
from promptforge.providers.factory import ProviderFactory
from promptforge.providers.ollama_provider import OllamaProvider
from promptforge.providers.openai_provider import OpenAIProvider


class TestProviderFactory:
    """Test provider factory creation."""

    def test_creates_anthropic(self, settings, anthropic_provider_config) -> None:
        """Anthropic provider created with API key."""
        provider = ProviderFactory.create(anthropic_provider_config, settings)
        assert isinstance(provider, AnthropicProvider)

    def test_creates_openai(self, settings, openai_provider_config) -> None:
        """OpenAI provider created with API key."""
        provider = ProviderFactory.create(openai_provider_config, settings)
        assert isinstance(provider, OpenAIProvider)

    def test_creates_ollama(self, settings, ollama_provider_config) -> None:
        """Ollama provider created without API key."""
        provider = ProviderFactory.create(ollama_provider_config, settings)
        assert isinstance(provider, OllamaProvider)

    def test_creates_compat(self, settings) -> None:
        """Compat provider created with base URL."""
        config = ProviderConfig(
            provider_type=ProviderType.COMPAT,
            base_url="http://localhost:8080/v1",
            model="local-model",
        )
        settings.custom_endpoint_url = "http://localhost:8080/v1"
        provider = ProviderFactory.create(config, settings)
        assert isinstance(provider, CompatProvider)

    def test_missing_anthropic_key_raises(self, settings) -> None:
        """Missing Anthropic key raises ConfigurationError."""
        settings.anthropic_api_key = None
        config = ProviderConfig(
            provider_type=ProviderType.ANTHROPIC,
            model="claude-haiku-4-5-20251001",
        )
        with pytest.raises(ConfigurationError, match="Anthropic"):
            ProviderFactory.create(config, settings)

    def test_missing_openai_key_raises(self, settings) -> None:
        """Missing OpenAI key raises ConfigurationError."""
        settings.openai_api_key = None
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            model="gpt-4o-mini",
        )
        with pytest.raises(ConfigurationError, match="OpenAI"):
            ProviderFactory.create(config, settings)

    def test_unknown_provider_raises(self, settings) -> None:
        """Unknown provider type raises ValueError."""
        from unittest.mock import MagicMock

        config = MagicMock()
        config.provider_type = "invalid"
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderFactory.create(config, settings)
