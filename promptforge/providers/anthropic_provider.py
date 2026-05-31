"""Anthropic Claude provider implementation."""

from typing import List, Optional

import anthropic

from promptforge.providers.base import (
    AuthenticationError,
    BaseProvider,
    LLMResponse,
    ProviderError,
)


class AnthropicProvider(BaseProvider):
    """BaseProvider implementation for Anthropic Claude models."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key.
            model: Model identifier to use.
        """
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "anthropic"

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        image_base64: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """
        Send a chat request to Anthropic Messages API.

        Args:
            system_prompt: System instructions.
            user_message: User message text.
            image_base64: Optional base64 image data URI.
            max_tokens: Maximum tokens in response.

        Returns:
            Standardized LLMResponse.

        Raises:
            AuthenticationError: On invalid API key.
            ProviderError: On other API failures.
        """
        content: list[dict] = []
        if image_base64 and self.supports_vision():
            image_data = image_base64
            media_type = "image/jpeg"
            if image_base64.startswith("data:"):
                header, _, data = image_base64.partition(",")
                media_type = header.split(";")[0].replace("data:", "")
                image_data = data.split("|")[0] if "|" in data else data
            else:
                image_data = image_base64.split("|")[0] if "|" in image_base64 else image_base64

            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )
        content.append({"type": "text", "text": user_message})

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],  # type: ignore[typeddict-item]
            )
        except anthropic.AuthenticationError as exc:
            raise AuthenticationError(str(exc)) from exc
        except anthropic.APIError as exc:
            raise ProviderError(str(exc)) from exc

        text = ""
        if response.content:
            block = response.content[0]
            if hasattr(block, "text"):
                text = block.text

        return LLMResponse(
            text=text,
            input_tokens=response.usage.input_tokens if response.usage else None,
            output_tokens=response.usage.output_tokens if response.usage else None,
            model=self.model,
            provider=self.provider_name,
        )

    async def list_models(self) -> List[str]:
        """Return supported Anthropic model names."""
        return [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-5",
            "claude-opus-4-5",
        ]

    def supports_vision(self) -> bool:
        """Anthropic Claude models support vision input."""
        return True
