"""Hallucination reduction via uncertainty injection and output signals."""

import re
from typing import List, Optional

from promptforge.core.models import GuardrailViolation
from promptforge.guardrails.base import BaseGuardrail, GuardrailResult

UNCERTAINTY_INJECTION = """
FACTUAL ACCURACY INSTRUCTION:
- If you are not 100% certain of a specific fact, preface it with "I believe" or "I'm not certain, but"
- Do not fabricate citations, paper titles, author names, statistics, or URLs
- If you don't know something, say "I don't have reliable information about this"
- Never invent specific numbers, dates, or names to fill gaps in your knowledge
"""

HALLUCINATION_SIGNALS = [
    re.compile(r"according to (a |the )?(recent |new )?study by", re.I),
    re.compile(r"research (shows|found|indicates|suggests) that", re.I),
    re.compile(r"\d+% of (people|users|companies|organizations)", re.I),
    re.compile(r"published in (the journal|nature|science|lancet)", re.I),
]


def get_uncertainty_system_injection() -> str:
    """
    Return uncertainty injection text for system prompt.

    Returns:
        Uncertainty instruction block string.
    """
    return UNCERTAINTY_INJECTION.strip()


class HallucinationGuard(BaseGuardrail):
    """Injects uncertainty language and detects hallucination signals."""

    @property
    def guardrail_id(self) -> str:
        """Return guardrail identifier."""
        return "hallucination_guard"

    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> GuardrailResult:
        """Always passes — uncertainty injection applied via orchestrator."""
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=True,
            violations=[],
        )

    async def check_output(
        self,
        text: str,
        original_request: Optional[str] = None,
    ) -> GuardrailResult:
        """
        Detect potential hallucination signals in output.

        Returns warnings (not blocks) when signals found.
        """
        violations: List[GuardrailViolation] = []
        for pattern in HALLUCINATION_SIGNALS:
            match = pattern.search(text)
            if match:
                violations.append(
                    GuardrailViolation(
                        guardrail_id=self.guardrail_id,
                        severity="warn",
                        message="Potential hallucination signal detected in output",
                        detected_values=[match.group(0)],
                    )
                )
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=len(violations) == 0,
            violations=violations,
        )
