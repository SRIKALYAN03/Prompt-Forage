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
    image_base64: Optional[str]
    filename: str
    file_type: str
