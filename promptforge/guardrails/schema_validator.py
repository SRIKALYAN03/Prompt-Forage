"""JSON schema output validator guardrail."""

import json
import re
from typing import Any, Dict, List, Optional

from promptforge.core.models import GuardrailViolation
from promptforge.guardrails.base import BaseGuardrail, GuardrailResult

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


class SchemaValidator(BaseGuardrail):
    """Validates LLM JSON output against a supplied schema (required fields)."""

    def __init__(self, json_schema: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize with an optional JSON schema dict.

        Args:
            json_schema: Dict with at least a 'required' list of field names.
        """
        self.json_schema = json_schema

    @property
    def guardrail_id(self) -> str:
        """Return guardrail identifier."""
        return "schema_validator"

    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> GuardrailResult:
        """Schema validator does not scan input."""
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
        """Validate that output is valid JSON matching the schema."""
        if not self.json_schema:
            return GuardrailResult(
                guardrail_id=self.guardrail_id,
                passed=True,
                violations=[],
            )

        # Extract JSON from fenced code block if present
        fence_match = _FENCE.search(text)
        json_text = fence_match.group(1).strip() if fence_match else text.strip()

        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            return GuardrailResult(
                guardrail_id=self.guardrail_id,
                passed=False,
                violations=[
                    GuardrailViolation(
                        guardrail_id=self.guardrail_id,
                        severity="warn",
                        message=f"Output is not valid JSON: {exc}",
                        detected_values=[str(exc)],
                    )
                ],
            )

        violations: List[GuardrailViolation] = []
        required = self.json_schema.get("required", [])
        if isinstance(parsed, dict):
            for field in required:
                if field not in parsed:
                    violations.append(
                        GuardrailViolation(
                            guardrail_id=self.guardrail_id,
                            severity="warn",
                            message=f"Required field '{field}' missing from JSON output",
                            detected_values=[field],
                        )
                    )
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=len(violations) == 0,
            violations=violations,
        )
