# tests/test_scorer.py
"""Tests for promptforge.core.scorer."""


from promptforge.core.models import (
    GuardrailViolation,
    OutputFormat,
    Role,
    Tone,
)
from promptforge.core.scorer import score_run


class TestScoreRun:
    """Test prompt run scoring."""

    def test_perfect_run_scores_high(self) -> None:
        """Well-formed run scores near 100."""
        system_prompt = (
            "You are a senior software engineer. "
            "Use formal tone. Format as bullet points."
        )
        response = (
            "- JWT consists of header, payload, and signature.\n"
            "- The server signs tokens with a secret key.\n"
            "- Clients send tokens in Authorization header.\n"
            "- Tokens should have expiration times.\n"
            "- Always use HTTPS in production."
        )
        score, breakdown = score_run(
            system_prompt=system_prompt,
            response=response,
            output_violations=[],
            role=Role.SENIOR_DEV,
            tone=Tone.FORMAL,
            output_format=OutputFormat.BULLET_POINTS,
        )
        assert score >= 80

    def test_short_response_reduces_score(self) -> None:
        """Very short response reduces response_length points."""
        score, breakdown = score_run(
            system_prompt="You are a senior software engineer with formal tone.",
            response="Yes.",
            output_violations=[],
            role=Role.SENIOR_DEV,
            tone=Tone.FORMAL,
            output_format=OutputFormat.PLAIN_TEXT,
        )
        length_check = next(b for b in breakdown if b.check == "response_length")
        assert length_check.passed is False

    def test_violations_reduce_score(self) -> None:
        """Output violations reduce no_violations score."""
        violations = [
            GuardrailViolation(
                guardrail_id="output_validator",
                severity="block",
                message="Bypass detected",
            )
        ]
        score_with, _ = score_run(
            system_prompt="You are a senior software engineer.",
            response="A long enough response with multiple words here for length.",
            output_violations=violations,
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
        )
        score_without, _ = score_run(
            system_prompt="You are a senior software engineer.",
            response="A long enough response with multiple words here for length.",
            output_violations=[],
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
        )
        assert score_with < score_without

    def test_score_never_exceeds_100(self) -> None:
        """Score is capped at 100."""
        score, _ = score_run(
            system_prompt="You are a senior software engineer with formal tone bullet points.",
            response="- " + "word " * 100,
            output_violations=[],
            role=Role.SENIOR_DEV,
            tone=Tone.FORMAL,
            output_format=OutputFormat.BULLET_POINTS,
        )
        assert score <= 100

    def test_score_never_below_0(self) -> None:
        """Score is floored at 0."""
        violations = [
            GuardrailViolation(guardrail_id="x", severity="block", message="a"),
            GuardrailViolation(guardrail_id="y", severity="block", message="b"),
            GuardrailViolation(guardrail_id="z", severity="block", message="c"),
        ]
        score, _ = score_run(
            system_prompt="",
            response="No",
            output_violations=violations,
            role=Role.SENIOR_DEV,
            tone=Tone.NEUTRAL,
            output_format=OutputFormat.PLAIN_TEXT,
        )
        assert score >= 0
