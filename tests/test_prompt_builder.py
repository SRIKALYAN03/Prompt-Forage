# tests/test_prompt_builder.py
"""Tests for promptforge.core.prompt_builder."""

import pytest

from promptforge.core.models import (
    GuardrailConfig,
    OutputFormat,
    Role,
    Tone,
)
from promptforge.core.prompt_builder import build_system_prompt


class TestRolePrompts:
    """Test each role produces correct base prompt."""

    @pytest.mark.parametrize("role", list(Role))
    def test_role_produces_non_empty_prompt(self, role: Role) -> None:
        """Every role produces a non-empty system prompt."""
        if role == Role.CUSTOM:
            prompt = build_system_prompt(
                role=role,
                tone=Tone.NEUTRAL,
                output_format=OutputFormat.PLAIN_TEXT,
                context=None,
                guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
                custom_role="You are a custom expert.",
            )
        else:
            prompt = build_system_prompt(
                role=role,
                tone=Tone.NEUTRAL,
                output_format=OutputFormat.PLAIN_TEXT,
                context=None,
                guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
            )
        assert prompt
        assert len(prompt) > 20

    def test_senior_dev_contains_engineer(self) -> None:
        """Senior dev role includes engineer language."""
        prompt = build_system_prompt(
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
        )
        assert "engineer" in prompt.lower()


class TestToneAndFormat:
    """Test tone and format instructions."""

    def test_tone_appended(self) -> None:
        """Tone instruction appears in system prompt."""
        prompt = build_system_prompt(
            role=Role.SENIOR_DEV,
            tone=Tone.FORMAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
        )
        assert "formal" in prompt.lower()

    def test_format_instruction_appended(self) -> None:
        """Format instruction appears in system prompt."""
        prompt = build_system_prompt(
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.BULLET_POINTS,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
        )
        assert "bullet" in prompt.lower()


class TestContextInjection:
    """Test context block injection."""

    def test_context_block_injected(self) -> None:
        """Context is wrapped with separators."""
        prompt = build_system_prompt(
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context="Document content here.",
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
        )
        assert "--- CONTEXT ---" in prompt
        assert "Document content here." in prompt
        assert "--- END CONTEXT ---" in prompt


class TestGuardrailInjections:
    """Test guardrail instructions in system prompt."""

    def test_injection_hardening_when_enabled(self) -> None:
        """Injection guard adds security instruction."""
        prompt = build_system_prompt(
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=True, hallucination_guard=False),
        )
        assert "SECURITY INSTRUCTION" in prompt

    def test_hallucination_guard_when_enabled(self) -> None:
        """Hallucination guard adds factual accuracy instruction."""
        prompt = build_system_prompt(
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=True),
        )
        assert "FACTUAL ACCURACY" in prompt


class TestCustomRoleAndRegenerate:
    """Test custom role and regenerate flag."""

    def test_custom_role_overrides(self) -> None:
        """Custom role text replaces default role prompt."""
        prompt = build_system_prompt(
            role=Role.CUSTOM,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
            custom_role="You are a blockchain expert.",
        )
        assert "blockchain expert" in prompt

    def test_regenerate_adds_instruction(self) -> None:
        """Regenerate flag adds stronger variation instruction."""
        prompt = build_system_prompt(
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
            regenerate=True,
        )
        assert "different response" in prompt.lower()

    def test_output_never_empty(self) -> None:
        """System prompt is never empty."""
        prompt = build_system_prompt(
            role=Role.CUSTOM,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
            context=None,
            guardrail_config=GuardrailConfig(injection_detect=False, hallucination_guard=False),
        )
        assert prompt.strip()
