"""OpenAI GPT provider implementation."""

from typing import List, Optional

import openai

from promptforge.providers.base import (
    AuthenticationError,
    BaseProvider,
    LLMResponse,
    ProviderError,
)


class OpenAIProvider(BaseProvider):
    """BaseProvider implementation for OpenAI models."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key.
            model: Model identifier to use.
        """
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "openai"

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        image_base64: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """
        Send a chat request to OpenAI Chat Completions API.

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
        user_content: list[dict] | str
        if image_base64 and self.supports_vision():
            image_url = image_base64
            if not image_base64.startswith("data:"):
                image_url = f"data:image/jpeg;base64,{image_base64.split('|')[0]}"
            elif "|" in image_base64:
                image_url = image_base64.split("|")[0]
            user_content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        else:
            user_content = user_message

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},  # type: ignore[misc,list-item]
                ],
            )
        except openai.AuthenticationError as exc:
            raise AuthenticationError(str(exc)) from exc
        except openai.APIError as exc:
            raise ProviderError(str(exc)) from exc

        text = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            text=text,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            model=self.model,
            provider=self.provider_name,
        )

    async def list_models(self) -> List[str]:
        """Return supported OpenAI model names."""
        return ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]

    def supports_vision(self) -> bool:
        """GPT-4o models support vision input."""
        return "gpt-4o" in self.model or "gpt-4" in self.model
