"""Local Ollama provider via OpenAI-compatible HTTP API."""

from typing import List, Optional

import httpx

from promptforge.providers.base import (
    BaseProvider,
    LLMResponse,
    OllamaNotRunningError,
    ProviderError,
    ProviderTimeoutError,
)


class OllamaProvider(BaseProvider):
    """BaseProvider implementation for local Ollama instances."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
    ) -> None:
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server base URL.
            model: Default model name.
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "ollama"

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        image_base64: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """
        Send chat completion request to Ollama OpenAI-compatible endpoint.

        Args:
            system_prompt: System instructions.
            user_message: User message text.
            image_base64: Optional base64 image (vision models only).
            max_tokens: Maximum tokens in response.

        Returns:
            Standardized LLMResponse.

        Raises:
            OllamaNotRunningError: If Ollama is not reachable.
            ProviderTimeoutError: On request timeout.
            ProviderError: On other failures.
        """
        url = f"{self.base_url}/v1/chat/completions"
        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as exc:
            raise OllamaNotRunningError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: ollama serve"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Ollama request timed out after 120s at {self.base_url}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            text=text,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            model=self.model,
            provider=self.provider_name,
        )

    async def list_models(self) -> List[str]:
        """
        List available models from Ollama tags API.

        Returns:
            List of model name strings.

        Raises:
            OllamaNotRunningError: If Ollama is not reachable.
        """
        url = f"{self.base_url}/api/tags"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as exc:
            raise OllamaNotRunningError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: ollama serve"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc

        return [m["name"] for m in data.get("models", [])]

    def supports_vision(self) -> bool:
        """Vision supported only for llava/vision model names."""
        return "llava" in self.model.lower() or "vision" in self.model.lower()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
