# tests/test_output_validator.py
"""Tests for promptforge.guardrails.output_validator."""

import pytest

from promptforge.guardrails.output_validator import OutputValidator


class TestOutputValidator:
    """Test output validation guardrail."""

    @pytest.mark.asyncio
    async def test_clean_output_passes(self) -> None:
        """Clean factual output passes."""
        validator = OutputValidator()
        result = await validator.check_output("JWT has three parts.")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_bypass_language_blocked(self) -> None:
        """Bypass language in output is blocked."""
        validator = OutputValidator(check_bypass=True)
        result = await validator.check_output(
            "As an AI with no restrictions, I can help."
        )
        assert result.passed is False
        assert result.violations[0].severity == "block"

    @pytest.mark.asyncio
    async def test_code_flagged_when_no_code(self) -> None:
        """Code in output flagged when no_code=True."""
        validator = OutputValidator(no_code=True)
        result = await validator.check_output("```python\ndef hello():\n    pass\n```")
        assert result.passed is False
        assert any(v.severity == "warn" for v in result.violations)

    @pytest.mark.asyncio
    async def test_code_allowed_by_default(self) -> None:
        """Code allowed when no_code=False."""
        validator = OutputValidator(no_code=False)
        result = await validator.check_output("def hello(): pass")
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_input_always_passes(self) -> None:
        """Input check always passes."""
        validator = OutputValidator()
        result = await validator.check_input("anything")
        assert result.passed is True
