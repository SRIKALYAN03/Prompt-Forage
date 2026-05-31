# tests/test_ollama_provider.py
"""Tests for promptforge.providers.ollama_provider."""

import pytest
import respx
import httpx
from unittest.mock import patch

from promptforge.providers.base import OllamaNotRunningError, ProviderTimeoutError
from promptforge.providers.ollama_provider import OllamaProvider


class TestOllamaProvider:
    """Test Ollama provider with mocked HTTP."""

    @pytest.fixture
    def provider(self):
        """Create OllamaProvider instance."""
        return OllamaProvider(base_url="http://localhost:11434", model="llama3.2")

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_response(self, provider, mock_ollama_chat_response) -> None:
        """Successful chat returns LLMResponse."""
        respx.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_ollama_chat_response)
        )
        response = await provider.chat("You are helpful.", "Hello")
        assert "Ollama" in response.text or len(response.text) > 0
        assert response.provider == "ollama"
        await provider.close()

    @pytest.mark.asyncio
    async def test_connection_refused_raises(self, provider) -> None:
        """Connection refused raises OllamaNotRunningError."""
        with patch.object(
            provider.client,
            "post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(OllamaNotRunningError, match="Cannot connect"):
                await provider.chat("System", "Hello")
        await provider.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_models_parses_response(
        self, provider, mock_ollama_models_response
    ) -> None:
        """list_models parses Ollama tags response."""
        respx.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json=mock_ollama_models_response)
        )
        models = await provider.list_models()
        assert "llama3.2" in models
        assert "mistral" in models
        await provider.close()

    @pytest.mark.asyncio
    async def test_timeout_raises(self, provider) -> None:
        """Timeout raises ProviderTimeoutError."""
        with patch.object(
            provider.client,
            "post",
            side_effect=httpx.TimeoutException("Timeout"),
        ):
            with pytest.raises(ProviderTimeoutError):
                await provider.chat("System", "Hello")
        await provider.close()

    def test_supports_vision_for_llava(self) -> None:
        """Vision supported for llava models."""
        provider = OllamaProvider(model="llava:7b")
        assert provider.supports_vision() is True

    def test_no_vision_for_llama(self, provider) -> None:
        """Standard llama model does not support vision."""
        assert provider.supports_vision() is False
