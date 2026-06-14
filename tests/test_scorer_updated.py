"""Tests for Phase 4 scorer improvements: warn penalty + citation bonus."""
from promptforge.core.models import (
    GuardrailViolation, OutputFormat, Role, Tone,
)
from promptforge.core.scorer import score_run


SYS = "You are a senior software engineer. Use technical language. Format as plain text."
GOOD_RESPONSE = " ".join(["word"] * 20)


def _violation(severity: str, gid: str = "test") -> GuardrailViolation:
    return GuardrailViolation(
        guardrail_id=gid, severity=severity, message="test violation"
    )


def test_warn_penalty_reduces_score():
    warns = [_violation("warn") for _ in range(2)]
    score, _ = score_run(
        system_prompt=SYS, response=GOOD_RESPONSE,
        output_violations=warns,
        role=Role.SENIOR_DEV, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    score_clean, _ = score_run(
        system_prompt=SYS, response=GOOD_RESPONSE,
        output_violations=[],
        role=Role.SENIOR_DEV, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    assert score < score_clean


def test_citation_bonus_applied():
    response_with_citation = GOOD_RESPONSE + " According to source: Wikipedia, this is correct."
    score_cite, _ = score_run(
        system_prompt=SYS, response=response_with_citation,
        output_violations=[],
        role=Role.SENIOR_DEV, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    score_no_cite, _ = score_run(
        system_prompt=SYS, response=GOOD_RESPONSE,
        output_violations=[],
        role=Role.SENIOR_DEV, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    assert score_cite >= score_no_cite


def test_block_violation_reduces_more_than_warn():
    block_v = [_violation("block")]
    warn_v = [_violation("warn")]
    score_block, _ = score_run(
        system_prompt=SYS, response=GOOD_RESPONSE,
        output_violations=block_v,
        role=Role.SENIOR_DEV, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    score_warn, _ = score_run(
        system_prompt=SYS, response=GOOD_RESPONSE,
        output_violations=warn_v,
        role=Role.SENIOR_DEV, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    assert score_warn >= score_block


def test_score_capped_at_100():
    response = GOOD_RESPONSE + " source: Wikipedia"
    score, _ = score_run(
        system_prompt=SYS, response=response,
        output_violations=[],
        role=Role.SENIOR_DEV, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    assert score <= 100


def test_score_floor_zero():
    blocks = [_violation("block") for _ in range(10)]
    score, _ = score_run(
        system_prompt="", response="",
        output_violations=blocks,
        role=Role.CUSTOM, tone=Tone.NEUTRAL, output_format=OutputFormat.PLAIN_TEXT,
    )
    assert score >= 0
