"""API request/response schemas."""

from typing import List, Optional

from pydantic import BaseModel, Field

from promptforge.core.models import RunResult


class SaveLocalRequest(BaseModel):
    """Request body for local save endpoint."""

    run_result: RunResult
    name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    format: str = "json"
    author: Optional[str] = None


class SaveGistRequest(BaseModel):
    """Request body for gist save endpoint."""

    run_result: RunResult
    github_token: str
    name: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    public: bool = False


class UploadResponse(BaseModel):
    """Response from file upload endpoint."""

    context_text: str
    image_base64: Optional[str] = None
    filename: str
    file_type: str


class EstimateRequest(BaseModel):
    """Request body for token estimate endpoint."""

    text: str
    context: Optional[str] = None
    system_prompt: Optional[str] = None


class EstimateResponse(BaseModel):
    """Response from token estimate endpoint."""

    estimated_tokens: int


class CommentRequest(BaseModel):
    """Request body for adding a comment to a run."""

    text: str
    author: Optional[str] = None


class ProjectCreateRequest(BaseModel):
    """Request body for creating a project."""

    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class TemplateCreateRequest(BaseModel):
    """Request body for creating a prompt template."""

    name: str
    template: str


class GuardrailInfo(BaseModel):
    """Metadata about a single guardrail."""

    id: str
    description: str
    phase: str
    default: bool
