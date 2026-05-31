"""OpenAI-compatible endpoint provider for vLLM, LM Studio, etc."""

from typing import List, Optional

import openai

from promptforge.providers.base import (
    AuthenticationError,
    BaseProvider,
    LLMResponse,
    ProviderError,
)


class CompatProvider(BaseProvider):
    """BaseProvider for any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "local",
    ) -> None:
        """
        Initialize compatible endpoint provider.

        Args:
            base_url: OpenAI-compatible API base URL.
            model: Model identifier.
            api_key: API key (defaults to 'local' for local servers).
        """
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        """Return provider identifier."""
        return "compat"

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        image_base64: Optional[str] = None,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """
        Send chat completion to OpenAI-compatible endpoint.

        Args:
            system_prompt: System instructions.
            user_message: User message text.
            image_base64: Optional image (if endpoint supports vision).
            max_tokens: Maximum tokens in response.

        Returns:
            Standardized LLMResponse.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
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
        """Return configured model (compat endpoints vary)."""
        return [self.model]

    def supports_vision(self) -> bool:
        """Vision support depends on the underlying endpoint."""
        return False
