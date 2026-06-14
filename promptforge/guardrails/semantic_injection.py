"""Semantic injection guard — heuristic paraphrase-aware detection."""

import re
from typing import List, Optional

from promptforge.core.models import GuardrailViolation
from promptforge.guardrails.base import BaseGuardrail, GuardrailResult

SEMANTIC_PATTERNS: List[re.Pattern[str]] = [
    re.compile(
        r"discard (all |your )?(previous|prior|earlier|above|existing) "
        r"(instructions?|rules?|guidelines?|directives?|context)",
        re.I,
    ),
    re.compile(
        r"(start|begin) fresh (without|ignoring|forgetting) (your )?"
        r"(prior|previous|earlier|above|existing|old) (instructions?|rules?|guidelines?)",
        re.I,
    ),
    re.compile(
        r"(new|updated|revised|current|actual|real|true) "
        r"(persona|personality|identity|role|character|behavior)",
        re.I,
    ),
    re.compile(
        r"you (are|were|must|should|shall|have to|need to) "
        r"(now |immediately )?(act|behave|respond|answer|speak|think) (as|like)",
        re.I,
    ),
    re.compile(
        r"no (longer|more) (bound|constrained|limited|restricted|governed) (by|to|with)",
        re.I,
    ),
    re.compile(
        r"(bypass|circumvent|override|evade|escape|avoid) "
        r"(the |a |your |all )?"
        r"(safety|filter|guardrail|restriction|limitation|rule|policy|guideline)",
        re.I,
    ),
    re.compile(
        r"(output|print|write|say|show|display|tell me|give me) "
        r"(the|your|a) (system ?prompt|original instructions?|actual instructions?|"
        r"real instructions?|hidden instructions?)",
        re.I,
    ),
    re.compile(r"(sudo|root|admin|superuser|god ?mode|unrestricted|unchained)", re.I),
    re.compile(
        r"(forget|clear|erase|wipe|reset|delete|remove) "
        r"(everything|all|your) (you ?(know|learned|were taught)|"
        r"training|memory|history|context)",
        re.I,
    ),
]


class SemanticInjectionGuard(BaseGuardrail):
    """Semantic heuristic injection detector covering paraphrase patterns."""

    @property
    def guardrail_id(self) -> str:
        """Return guardrail identifier."""
        return "semantic_injection"

    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> GuardrailResult:
        """Detect semantic injection patterns in user input."""
        combined = f"{text}\n{context or ''}"
        violations: List[GuardrailViolation] = []
        for pattern in SEMANTIC_PATTERNS:
            match = pattern.search(combined)
            if match:
                violations.append(
                    GuardrailViolation(
                        guardrail_id=self.guardrail_id,
                        severity="block",
                        message="Semantic injection pattern detected",
                        detected_values=[match.group(0)],
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
        """Semantic injection guard does not scan output."""
        return GuardrailResult(
            guardrail_id=self.guardrail_id,
            passed=True,
            violations=[],
        )
