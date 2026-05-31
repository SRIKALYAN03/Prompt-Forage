"""Abstract base class for all guardrails."""

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel, Field

from promptforge.core.models import GuardrailViolation


class GuardrailResult(BaseModel):
    """Result of a guardrail check."""

    guardrail_id: str
    passed: bool
    violations: List[GuardrailViolation] = Field(default_factory=list)
    modified_text: Optional[str] = None


class BaseGuardrail(ABC):
    """Abstract base class all guardrails must implement."""

    @property
    @abstractmethod
    def guardrail_id(self) -> str:
        """Unique identifier for this guardrail."""

    @abstractmethod
    async def check_input(
        self,
        text: str,
        context: Optional[str] = None,
    ) -> GuardrailResult:
        """Run guardrail on user input before LLM call."""

    @abstractmethod
    async def check_output(
        self,
        text: str,
        original_request: Optional[str] = None,
    ) -> GuardrailResult:
        """Run guardrail on LLM response after the call."""
