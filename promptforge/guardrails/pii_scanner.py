"""PII and credential scanner guardrail."""

import re
from typing import Dict, List, Optional

from promptforge.core.models import GuardrailViolation
from promptforge.guardrails.base import BaseGuardrail, GuardrailResult

PII_PATTERNS: Dict[str, re.Pattern[str]] = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9]{32,}"),
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9\-]{20,}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "aws_secret_key": re.compile(r"[A-Za-z0-9/+=]{40}"),
    "github_token": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "email": re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "phone_number": re.compile(r"(\+?[\d\s\-()]{10,15})"),
    "credit_card": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

BLOCK_TYPES = {
    "openai_key",
    "anthropic_key",
    "aws_access_key",
    "aws_secret_key",
    "github_token",
    "google_api_key",
}


def _scan_text(
    text: str,
    extra_patterns: Optional[Dict[str, re.Pattern[str]]] = None,
) -> List[GuardrailViolation]:
    """Scan text for all PII patterns and return violations."""
    violations: List[GuardrailViolation] = []
    all_patterns: Dict[str, re.Pattern[str]] = dict(PII_PATTERNS)
    if extra_patterns:
        all_patterns.update(extra_patterns)

    for pii_type, pattern in all_patterns.items():
        matches = pattern.findall(text)
        if not matches:
            continue
        severity = "block" if pii_type in BLOCK_TYPES else "warn"
        flat_matches: List[str] = []
        for m in matches:
            if isinstance(m, tuple):
                flat_matches.extend(m)
            else:
                flat_matches.append(m)
        violations.append(
            GuardrailViolation(
                guardrail_id="pii_scanner",
                severity=severity,
                message=f"{pii_type.replace('_', ' ').title()} detected in text",
                detected_values=flat_matches[:5],
            )
        )
    return violations


def redact_pii(text: str) -> str:
    """
    Replace PII matches with [REDACTED_<type>] placeholders.

    Args:
        text: Input text potentially containing PII.

    Returns:
        Text with PII redacted.
    """
    result = text
    for pii_type, pattern in PII_PATTERNS.items():
        placeholder = f"[REDACTED_{pii_type.upper()}]"
        result = pattern.sub(placeholder, result)
    return result


class PIIScanner(BaseGuardrail):
    """Detects PII and sensitive credentials in text."""

    def __init__(self, extra_patterns: Optional[List[str]] = None) -> None:
        """
        Initialize PIIScanner with optional extra regex patterns.

        Args:
            extra_patterns: Additional regex strings to scan for (severity: warn).
        """
        self._extra: Dict[str, re.Pattern[str]] = {}
        if extra_patterns:
            for i, pat in enumerate(extra_patterns):
                self._extra[f"custom_{i}"] = re.compile(pat)

    @property
    def guardrail_id(self) -> str:
        """Return guardrail identifier."""
        return "pii_scanner"

    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> GuardrailResult:
        """
        Scan text and optional context for PII patterns.

        API keys receive severity 'block'; other PII receives 'warn'.
        """
        combined = text
        if context:
            combined = f"{text}\n{context}"
        violations = _scan_text(combined, self._extra if self._extra else None)
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
        """Same PII scan on model output."""
        violations = _scan_text(text, self._extra if self._extra else None)
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=len(violations) == 0,
            violations=violations,
        )
