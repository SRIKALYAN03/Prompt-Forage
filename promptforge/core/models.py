"""Pydantic models for the PromptForge application."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Audience role for system prompt tailoring."""

    SENIOR_DEV = "senior_dev"
    JUNIOR_DEV = "junior_dev"
    PRODUCT_MANAGER = "product_manager"
    EXECUTIVE = "executive"
    DATA_SCIENTIST = "data_scientist"
    TEACHER = "teacher"
    DEVOPS = "devops"
    CUSTOM = "custom"


class Tone(str, Enum):
    """Communication tone for responses."""

    NEUTRAL = "neutral"
    FORMAL = "formal"
    FRIENDLY = "friendly"
    TECHNICAL = "technical"
    CONCISE = "concise"
    CREATIVE = "creative"


class OutputFormat(str, Enum):
    """Desired output structure."""

    PLAIN_TEXT = "plain_text"
    BULLET_POINTS = "bullet_points"
    NUMBERED_LIST = "numbered_list"
    JSON = "json"
    MARKDOWN = "markdown"
    TABLE = "table"


class ProviderType(str, Enum):
    """Supported LLM provider backends."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    COMPAT = "compat"


class GuardrailConfig(BaseModel):
    """Configuration for active guardrails on a prompt run."""

    pii_scan: bool = True
    injection_detect: bool = True
    token_limit: int = 4000
    hallucination_guard: bool = True
    pii_output_scan: bool = True
    bypass_detect: bool = True
    no_code: bool = False


class ProviderConfig(BaseModel):
    """LLM provider connection configuration."""

    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str


class PromptRequest(BaseModel):
    """Incoming request to run a prompt through the pipeline."""

    role: Role
    custom_role: Optional[str] = None
    tone: Tone = Tone.NEUTRAL
    output_format: OutputFormat = OutputFormat.PLAIN_TEXT
    context: Optional[str] = None
    user_message: str
    guardrail_config: GuardrailConfig = Field(default_factory=GuardrailConfig)
    provider_config: ProviderConfig
    regenerate: bool = False


class GuardrailViolation(BaseModel):
    """A single guardrail violation detected during input or output checks."""

    guardrail_id: str
    severity: str  # "warn" | "block" | "info"
    message: str
    detected_values: Optional[List[str]] = None


class ScoreBreakdown(BaseModel):
    """Individual scoring check result."""

    check: str
    points: int
    passed: bool


class RunResult(BaseModel):
    """Complete result of a prompt run."""

    id: str
    system_prompt: str
    user_message: str
    response: str
    score: int
    score_breakdown: List[ScoreBreakdown]
    input_violations: List[GuardrailViolation]
    output_violations: List[GuardrailViolation]
    provider: str
    model: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    latency_ms: int
    timestamp: str
    role: str
    tone: str
    output_format: str


class SavedPrompt(BaseModel):
    """A persisted prompt run with metadata."""

    id: str
    name: Optional[str]
    run_result: RunResult
    tags: List[str] = Field(default_factory=list)
    saved_at: str
