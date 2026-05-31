"""Token estimation and input truncation guardrail."""

import re
from typing import Optional, Tuple

from promptforge.core.models import GuardrailViolation
from promptforge.guardrails.base import BaseGuardrail, GuardrailResult

TRUNCATION_MARKER = "[...truncated to fit token limit]"


def estimate_tokens(text: str) -> int:
    """
    Approximate token count for text.

    Rule: 1 token ≈ 4 characters for English.
    For CJK characters: 1 token ≈ 1.5 characters.

    Args:
        text: Input text.

    Returns:
        Estimated token count.
    """
    if not text:
        return 0
    cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]")
    cjk_chars = len(cjk_pattern.findall(text))
    other_chars = len(text) - cjk_chars
    return int(cjk_chars / 1.5 + other_chars / 4) + 1


def truncate_to_token_limit(
    text: str,
    max_tokens: int,
    preserve_start: bool = True,
) -> Tuple[str, bool]:
    """
    Truncate text to fit within max_tokens.

    Args:
        text: Input text to truncate.
        max_tokens: Maximum allowed tokens.
        preserve_start: If True, keep start of text; else keep end.

    Returns:
        Tuple of (truncated_text, was_truncated).
    """
    if estimate_tokens(text) <= max_tokens:
        return text, False

    low, high = 0, len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid] if preserve_start else text[-mid:]
        tokens = estimate_tokens(candidate)
        if tokens <= max_tokens - estimate_tokens(TRUNCATION_MARKER):
            best = candidate
            low = mid + 1
        else:
            high = mid - 1

    if preserve_start:
        result = f"{best.rstrip()} {TRUNCATION_MARKER}"
    else:
        result = f"{TRUNCATION_MARKER} {best.lstrip()}"
    return result, True


class TokenLimiter(BaseGuardrail):
    """Estimates and enforces token limits on combined input."""

    def __init__(self, limit: int = 4000) -> None:
        """
        Initialize token limiter.

        Args:
            limit: Maximum token budget for combined input.
        """
        self.limit = limit

    @property
    def guardrail_id(self) -> str:
        """Return guardrail identifier."""
        return "token_limiter"

    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> GuardrailResult:
        """
        Estimate combined tokens and truncate user message if over limit.

        Args:
            text: User message text.
            context: Optional context text.
            system_prompt: Optional system prompt for budget calculation.

        Returns:
            GuardrailResult with modified_text if truncation occurred.
        """
        if self.limit <= 0:
            return GuardrailResult(
                guardrail_id=self.guardrail_id,
                passed=True,
                violations=[],
            )

        overhead = estimate_tokens(system_prompt or "") + estimate_tokens(context or "")
        user_budget = max(self.limit - overhead, 100)
        truncated, was_truncated = truncate_to_token_limit(text, user_budget)

        violations = []
        if was_truncated:
            violations.append(
                GuardrailViolation(
                    guardrail_id=self.guardrail_id,
                    severity="warn",
                    message=f"User message truncated to fit token limit of {self.limit}",
                    detected_values=None,
                )
            )

        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=True,
            violations=violations,
            modified_text=truncated if was_truncated else None,
        )

    async def check_output(
        self,
        text: str,
        original_request: Optional[str] = None,
    ) -> GuardrailResult:
        """Token limiter does not modify output."""
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=True,
            violations=[],
        )
