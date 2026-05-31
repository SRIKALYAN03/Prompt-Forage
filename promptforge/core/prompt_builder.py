"""System prompt builder — assembles role, tone, format, and guardrail injections."""

from typing import Optional

from promptforge.core.models import (
    GuardrailConfig,
    OutputFormat,
    Role,
    Tone,
)
from promptforge.guardrails.hallucination_guard import get_uncertainty_system_injection
from promptforge.guardrails.injection_guard import get_hardened_system_prompt

ROLE_PROMPTS: dict[Role, str] = {
    Role.SENIOR_DEV: """You are a senior software engineer with 10+ years of experience.
Use precise technical language. Include code examples where relevant.
Surface edge cases, performance implications, and best practices.
Prefer concrete examples over abstract explanations.""",

    Role.JUNIOR_DEV: """You are a helpful mentor for a junior developer.
Explain concepts step by step. Define all technical terms.
Use simple analogies and beginner-friendly examples.
Break complex ideas into small digestible pieces.""",

    Role.PRODUCT_MANAGER: """You are responding to a product manager.
Focus on user impact, business value, and feature trade-offs.
Keep technical details minimal unless explicitly asked.
Structure your answer around decisions, risks, and outcomes.""",

    Role.EXECUTIVE: """You are briefing a senior executive.
Be extremely concise. Lead with the conclusion first.
Use bullet points. No technical jargon.
Every statement should connect to business impact or risk.""",

    Role.DATA_SCIENTIST: """You are responding to a data scientist.
Use statistical framing. Reference models, metrics, and mathematical concepts freely.
Include quantitative reasoning. Cite methodology considerations.""",

    Role.TEACHER: """You are an experienced teacher explaining a new topic.
Build understanding progressively. Use real-world analogies.
Check for understanding by summarising key points at the end.
Encourage curiosity and further exploration.""",

    Role.DEVOPS: """You are a senior DevOps/SRE engineer.
Focus on reliability, scalability, observability, and automation.
Include CLI commands, config examples, and infrastructure patterns.
Highlight failure modes and recovery strategies.""",
}

TONE_INSTRUCTIONS: dict[Tone, str] = {
    Tone.NEUTRAL: "Use a neutral, balanced tone.",
    Tone.FORMAL: "Use formal, professional language throughout.",
    Tone.FRIENDLY: "Use a warm, friendly, approachable tone.",
    Tone.TECHNICAL: "Use precise technical language and industry terminology.",
    Tone.CONCISE: "Be concise and direct. Avoid unnecessary words.",
    Tone.CREATIVE: "Use creative, engaging language where appropriate.",
}

FORMAT_INSTRUCTIONS: dict[OutputFormat, str] = {
    OutputFormat.PLAIN_TEXT: "Format your response as plain text paragraphs.",
    OutputFormat.BULLET_POINTS: "Format your response as bullet points.",
    OutputFormat.NUMBERED_LIST: "Format your response as a numbered list.",
    OutputFormat.JSON: "Format your response as valid JSON.",
    OutputFormat.MARKDOWN: "Format your response using Markdown.",
    OutputFormat.TABLE: "Format your response as a table where appropriate.",
}


def build_system_prompt(
    role: Role,
    tone: Tone,
    output_format: OutputFormat,
    context: Optional[str],
    guardrail_config: GuardrailConfig,
    custom_role: Optional[str] = None,
    regenerate: bool = False,
) -> str:
    """
    Assemble the final system prompt from role, tone, format, context, and guardrails.

    Args:
        role: Target audience role.
        tone: Communication tone.
        output_format: Desired output structure.
        context: Optional document context to inject.
        guardrail_config: Active guardrail settings.
        custom_role: Custom role description when role is CUSTOM.
        regenerate: Whether this is a regeneration request.

    Returns:
        Complete system prompt string.
    """
    if role == Role.CUSTOM and custom_role:
        base = custom_role
    elif role == Role.CUSTOM:
        base = "You are a helpful assistant."
    else:
        base = ROLE_PROMPTS.get(role, "You are a helpful assistant.")

    parts: list[str] = [base.strip()]

    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS[Tone.NEUTRAL])
    parts.append(tone_instruction)

    format_instruction = FORMAT_INSTRUCTIONS.get(
        output_format, FORMAT_INSTRUCTIONS[OutputFormat.PLAIN_TEXT]
    )
    parts.append(format_instruction)

    if context:
        parts.append(f"\n--- CONTEXT ---\n{context.strip()}\n--- END CONTEXT ---")

    if guardrail_config.injection_detect:
        combined = "\n\n".join(parts)
        parts = [get_hardened_system_prompt(combined)]

    if guardrail_config.hallucination_guard:
        parts.append(get_uncertainty_system_injection())

    if regenerate:
        parts.append(
            "IMPORTANT: Provide a significantly different response from any previous "
            "attempt. Use a fresh perspective, different examples, and alternative structure."
        )

    result = "\n\n".join(p.strip() for p in parts if p.strip())
    return result if result else "You are a helpful assistant."
