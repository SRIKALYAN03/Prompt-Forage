# tests/test_models.py
"""Tests for promptforge.core.models."""

import pytest
from pydantic import ValidationError

from promptforge.core.models import (
    GuardrailConfig,
    OutputFormat,
    PromptRequest,
    ProviderType,
    Role,
    SavedPrompt,
    Tone,
)


class TestEnums:
    """Test enum values."""

    def test_role_values(self) -> None:
        """All role enum members have string values."""
        assert Role.SENIOR_DEV.value == "senior_dev"
        assert Role.CUSTOM.value == "custom"

    def test_tone_values(self) -> None:
        """Tone enum includes neutral default."""
        assert Tone.NEUTRAL.value == "neutral"

    def test_provider_type_values(self) -> None:
        """Provider types cover all backends."""
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.OLLAMA.value == "ollama"


class TestGuardrailConfig:
    """Test GuardrailConfig defaults."""

    def test_defaults(self) -> None:
        """Default guardrail config matches spec."""
        config = GuardrailConfig()
        assert config.pii_scan is True
        assert config.token_limit == 4000
        assert config.no_code is False


class TestPromptRequest:
    """Test PromptRequest model."""

    def test_minimal_request(self, anthropic_provider_config) -> None:
        """PromptRequest requires role, user_message, and provider_config."""
        req = PromptRequest(
            role=Role.SENIOR_DEV,
            user_message="Hello",
            provider_config=anthropic_provider_config,
        )
        assert req.tone == Tone.NEUTRAL
        assert req.output_format == OutputFormat.PLAIN_TEXT

    def test_missing_user_message_raises(self, anthropic_provider_config) -> None:
        """user_message is required."""
        with pytest.raises(ValidationError):
            PromptRequest(
                role=Role.SENIOR_DEV,
                provider_config=anthropic_provider_config,
            )


class TestRunResult:
    """Test RunResult model."""

    def test_run_result_structure(self, sample_run_result) -> None:
        """RunResult has all required fields."""
        assert sample_run_result.score == 85
        assert len(sample_run_result.score_breakdown) == 6


class TestSavedPrompt:
    """Test SavedPrompt model."""

    def test_saved_prompt_tags_default(self, sample_run_result) -> None:
        """Tags default to empty list."""
        saved = SavedPrompt(
            id="test",
            name="Test",
            run_result=sample_run_result,
            saved_at="2024-01-01T00:00:00Z",
        )
        assert saved.tags == []
