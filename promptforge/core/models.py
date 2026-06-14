"""Pydantic models for the PromptForge application."""

from enum import Enum
from typing import Any, Dict, List, Optional

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
    # Phase 4 additions
    custom_pii_patterns: List[str] = Field(default_factory=list)
    blocked_topics: List[str] = Field(default_factory=list)
    json_schema: Optional[Dict[str, Any]] = None
    semantic_injection: bool = False
    validate_json_output: bool = False


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
    name: Optional[str] = None
    run_result: RunResult
    tags: List[str] = Field(default_factory=list)
    saved_at: str
    # Phase 1: version tracking
    version: int = 1
    parent_id: Optional[str] = None
    author: Optional[str] = None


# ── Phase 2: Collaboration models ────────────────────────────────────────────

class Comment(BaseModel):
    """A comment attached to a saved prompt run."""

    id: str
    run_id: str
    text: str
    author: Optional[str] = None
    created_at: str


class PromptTemplate(BaseModel):
    """A reusable prompt template with variable placeholders."""

    id: str
    name: str
    template: str
    variables: List[str] = Field(default_factory=list)
    created_at: str


class Project(BaseModel):
    """A named collection of saved prompts."""

    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    prompt_ids: List[str] = Field(default_factory=list)
    created_at: str


# ── Phase 2: Workflow models ──────────────────────────────────────────────────

class BatchItem(BaseModel):
    """A single item in a batch comparison request."""

    provider_config: ProviderConfig
    label: Optional[str] = None


class BatchRequest(BaseModel):
    """Run the same prompt against multiple providers for comparison."""

    prompt_request: PromptRequest
    providers: List[BatchItem]


class ChainStep(BaseModel):
    """A single step in a prompt chain."""

    user_message: str
    guardrail_config: GuardrailConfig = Field(default_factory=GuardrailConfig)
    provider_config: ProviderConfig


class ChainRequest(BaseModel):
    """Sequential chain of prompts where each step can use the previous output."""

    steps: List[ChainStep]
    role: Role = Role.SENIOR_DEV
    tone: Tone = Tone.NEUTRAL
    output_format: OutputFormat = OutputFormat.PLAIN_TEXT
