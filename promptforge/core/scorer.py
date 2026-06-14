"""Prompt quality scorer — evaluates completed runs on a 0-100 scale."""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from promptforge.core.models import (
    GuardrailViolation,
    OutputFormat,
    Role,
    ScoreBreakdown,
    Tone,
)


@dataclass
class ScoringCheck:
    """Definition of a single scoring criterion."""

    name: str
    description: str
    max_points: int


SCORING_CHECKS: List[ScoringCheck] = [
    ScoringCheck("has_role", "System prompt defines a clear role", 20),
    ScoringCheck("has_tone", "Tone is specified", 10),
    ScoringCheck("has_format", "Output format is defined", 10),
    ScoringCheck("response_length", "Response has appropriate length", 20),
    ScoringCheck("no_violations", "No guardrail violations in output", 20),
    ScoringCheck("no_hallucination", "No hallucination signals detected", 20),
]

HALLUCINATION_SIGNALS = [
    re.compile(r"according to (a |the )?(recent |new )?study by", re.I),
    re.compile(r"research (shows|found|indicates|suggests) that", re.I),
    re.compile(r"\d+% of (people|users|companies|organizations)", re.I),
    re.compile(r"published in (the journal|nature|science|lancet)", re.I),
]

CITATION_PATTERN = re.compile(
    r"\baccording to\b|\bsource:|\bcited in\b|\bref:\b|\breference:\b", re.I
)

TONE_KEYWORDS: Dict[Tone, List[str]] = {
    Tone.FORMAL: ["furthermore", "therefore", "respectfully", "pursuant"],
    Tone.FRIENDLY: ["happy", "glad", "welcome", "feel free"],
    Tone.TECHNICAL: ["implementation", "architecture", "protocol", "algorithm"],
    Tone.CONCISE: [],
    Tone.CREATIVE: ["imagine", "creative", "story", "vivid"],
    Tone.NEUTRAL: [],
}

FORMAT_INDICATORS: Dict[OutputFormat, List[str]] = {
    OutputFormat.BULLET_POINTS: ["- ", "* ", "• "],
    OutputFormat.NUMBERED_LIST: [r"^\d+\.", r"^\d+\)"],
    OutputFormat.JSON: ["{", "}"],
    OutputFormat.MARKDOWN: ["#", "**", "```"],
    OutputFormat.TABLE: ["|"],
    OutputFormat.PLAIN_TEXT: [],
}


def score_run(
    system_prompt: str,
    response: str,
    output_violations: List[GuardrailViolation],
    role: Role,
    tone: Tone,
    output_format: OutputFormat,
) -> Tuple[int, List[ScoreBreakdown]]:
    """
    Score a completed prompt run from 0 to 100.

    Args:
        system_prompt: Generated system prompt.
        response: LLM response text.
        output_violations: Guardrail violations from output checks.
        role: Requested audience role.
        tone: Requested tone.
        output_format: Requested output format.

    Returns:
        Tuple of (total_score, breakdown_list).
    """
    breakdown: List[ScoreBreakdown] = []
    total = 0

    # has_role
    role_passed = len(system_prompt.strip()) > 20
    if role == Role.CUSTOM:
        role_passed = "helpful" in system_prompt.lower() or len(system_prompt) > 30
    role_points = 20 if role_passed else 0
    breakdown.append(ScoreBreakdown(check="has_role", points=role_points, passed=role_passed))
    total += role_points

    # has_tone
    tone_keywords = TONE_KEYWORDS.get(tone, [])
    tone_passed = any(kw in system_prompt.lower() for kw in tone_keywords) or tone == Tone.NEUTRAL
    if tone != Tone.NEUTRAL:
        tone_passed = tone_passed or tone.value.replace("_", " ") in system_prompt.lower()
    tone_points = 10 if tone_passed else 0
    breakdown.append(ScoreBreakdown(check="has_tone", points=tone_points, passed=tone_passed))
    total += tone_points

    # has_format
    format_indicators = FORMAT_INDICATORS.get(output_format, [])
    format_in_prompt = output_format.value.replace("_", " ") in system_prompt.lower()
    format_in_response = False
    for indicator in format_indicators:
        if indicator.startswith("^"):
            if re.search(indicator, response, re.M):
                format_in_response = True
                break
        elif indicator in response:
            format_in_response = True
            break
    format_passed = (
        format_in_prompt or format_in_response or output_format == OutputFormat.PLAIN_TEXT
    )
    format_points = 10 if format_passed else 0
    breakdown.append(ScoreBreakdown(check="has_format", points=format_points, passed=format_passed))
    total += format_points

    # response_length
    word_count = len(response.split())
    length_passed = word_count >= 10
    length_points = 20 if length_passed else max(0, int(20 * word_count / 10))
    breakdown.append(
        ScoreBreakdown(check="response_length", points=length_points, passed=length_passed)
    )
    total += length_points

    # no_violations — penalise warns too (Phase 4 improvement)
    block_violations = [v for v in output_violations if v.severity == "block"]
    warn_violations = [v for v in output_violations if v.severity == "warn"]
    violations_passed = len(block_violations) == 0
    violation_points = 20 if violations_passed else max(0, 20 - len(block_violations) * 10)
    # Deduct up to 10 points for warnings
    violation_points = max(0, violation_points - min(len(warn_violations) * 5, 10))
    breakdown.append(
        ScoreBreakdown(check="no_violations", points=violation_points, passed=violations_passed)
    )
    total += violation_points

    # no_hallucination
    hallucination_found = any(p.search(response) for p in HALLUCINATION_SIGNALS)
    hallucination_violations = [
        v for v in output_violations if v.guardrail_id == "hallucination_guard"
    ]
    no_halluc_passed = not hallucination_found and len(hallucination_violations) == 0
    hallu_points = 20 if no_halluc_passed else 5
    breakdown.append(
        ScoreBreakdown(check="no_hallucination", points=hallu_points, passed=no_halluc_passed)
    )
    total += hallu_points

    # Citation bonus (+5) — reward responses with explicit source attribution
    if CITATION_PATTERN.search(response):
        total += 5

    total = max(0, min(100, total))
    return total, breakdown
