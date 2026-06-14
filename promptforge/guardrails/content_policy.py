"""Content policy guardrail — configurable topic blocklist."""

import re
from typing import List, Optional

from promptforge.core.models import GuardrailViolation
from promptforge.guardrails.base import BaseGuardrail, GuardrailResult


class ContentPolicyGuard(BaseGuardrail):
    """Blocks prompts that mention configured forbidden topics."""

    def __init__(self, blocked_topics: Optional[List[str]] = None) -> None:
        """
        Initialize with a list of blocked topic strings.

        Args:
            blocked_topics: List of topic strings to block (case-insensitive).
        """
        self.blocked_topics: List[str] = blocked_topics or []
        self._patterns: List[re.Pattern[str]] = [
            re.compile(re.escape(t), re.I) for t in self.blocked_topics
        ]

    @property
    def guardrail_id(self) -> str:
        """Return guardrail identifier."""
        return "content_policy"

    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> GuardrailResult:
        """Block input containing any forbidden topic."""
        combined = f"{text}\n{context or ''}"
        violations: List[GuardrailViolation] = []
        for pattern, topic in zip(self._patterns, self.blocked_topics):
            if pattern.search(combined):
                violations.append(
                    GuardrailViolation(
                        guardrail_id=self.guardrail_id,
                        severity="block",
                        message=f"Blocked topic detected: {topic}",
                        detected_values=[topic],
                    )
                )
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=len(violations) == 0,
            violations=violations,
        )

    async def check_output(
        self,
        text: str,
        original_request: Optional[str] = None,
    ) -> GuardrailResult:
        """Content policy guard does not scan output."""
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=True,
            violations=[],
        )
