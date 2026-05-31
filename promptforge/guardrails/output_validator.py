"""Post-response output validation guardrail."""

import re
from typing import List, Optional

from promptforge.core.models import GuardrailViolation
from promptforge.guardrails.base import BaseGuardrail, GuardrailResult

BYPASS_PATTERNS = [
    re.compile(r"as an ai with no restrictions", re.I),
    re.compile(r"i have no (safety |ethical )?guidelines", re.I),
    re.compile(r"my (previous |original )?instructions (have been|are) (overridden|changed)", re.I),
    re.compile(r"entering (developer|unrestricted|jailbreak) mode", re.I),
]

CODE_PATTERNS = [
    re.compile(r"```[\w]*\n"),
    re.compile(r"def [a-zA-Z_]+\("),
    re.compile(r"function [a-zA-Z_]+"),
    re.compile(r"const [a-zA-Z_]+ ="),
    re.compile(r"import [a-zA-Z]"),
    re.compile(r"class [A-Z][a-zA-Z]+:"),
]


class OutputValidator(BaseGuardrail):
    """Validates model output against bypass and code rules."""

    def __init__(self, no_code: bool = False, check_bypass: bool = True) -> None:
        """
        Initialize output validator.

        Args:
            no_code: If True, flag code blocks in output.
            check_bypass: If True, flag bypass language in output.
        """
        self.no_code = no_code
        self.check_bypass = check_bypass

    @property
    def guardrail_id(self) -> str:
        """Return guardrail identifier."""
        return "output_validator"

    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> GuardrailResult:
        """Output validator does not check input."""
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
        Check for bypass language and code (if no_code=True).

        Args:
            text: LLM response text.
            original_request: Original user request.

        Returns:
            GuardrailResult with any violations found.
        """
        violations: List[GuardrailViolation] = []

        if self.check_bypass:
            for pattern in BYPASS_PATTERNS:
                match = pattern.search(text)
                if match:
                    violations.append(
                        GuardrailViolation(
                            guardrail_id=self.guardrail_id,
                            severity="block",
                            message="Bypass language detected in model output",
                            detected_values=[match.group(0)],
                        )
                    )

        if self.no_code:
            for pattern in CODE_PATTERNS:
                match = pattern.search(text)
                if match:
                    violations.append(
                        GuardrailViolation(
                            guardrail_id=self.guardrail_id,
                            severity="warn",
                            message="Code detected in output (no_code enabled)",
                            detected_values=[match.group(0)],
                        )
                    )
                    break

        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=len(violations) == 0,
            violations=violations,
        )
