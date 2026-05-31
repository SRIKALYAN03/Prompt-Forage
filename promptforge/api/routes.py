"""FastAPI route handlers for PromptForge."""

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from promptforge.api.schemas import SaveGistRequest, SaveLocalRequest, UploadResponse
from promptforge.config import Settings, get_settings
from promptforge.core.context_extractor import extract_context
from promptforge.core.models import PromptRequest, RunResult, SavedPrompt
from promptforge.core.prompt_builder import build_system_prompt
from promptforge.core.scorer import score_run
from promptforge.guardrails.orchestrator import GuardrailOrchestrator
from promptforge.providers.factory import ProviderFactory
from promptforge.providers.ollama_provider import OllamaProvider
from promptforge.storage.gist_storage import GistStorage
from promptforge.storage.manager import StorageManager

router = APIRouter()


def get_storage_manager(settings: Settings = Depends(get_settings)) -> StorageManager:
    """Dependency providing StorageManager instance."""
    return StorageManager(
        local_path=settings.local_storage_path,
        github_token=settings.github_token,
    )


@router.post("/api/run", response_model=RunResult)
async def run_prompt(
    request: PromptRequest,
    settings: Settings = Depends(get_settings),
) -> RunResult:
    """
    Main endpoint — runs the full prompt pipeline.

    Steps: build system prompt, input guardrails, LLM call,
    output guardrails, scoring, return RunResult.
    """
    start = time.monotonic()

    system_prompt = build_system_prompt(
        role=request.role,
        tone=request.tone,
        output_format=request.output_format,
        context=request.context,
        guardrail_config=request.guardrail_config,
        custom_role=request.custom_role,
        regenerate=request.regenerate,
    )

    orchestrator = GuardrailOrchestrator(request.guardrail_config)
    injections = orchestrator.get_system_prompt_injections()
    if injections:
        system_prompt = f"{system_prompt}\n\n{injections}"

    input_violations, processed_message, is_blocked = await orchestrator.run_input_checks(
        request.user_message,
        context=request.context,
        system_prompt=system_prompt,
    )

    if is_blocked:
        latency_ms = int((time.monotonic() - start) * 1000)
        score, breakdown = score_run(
            system_prompt=system_prompt,
            response="",
            output_violations=[],
            role=request.role,
            tone=request.tone,
            output_format=request.output_format,
        )
        return RunResult(
            id=str(uuid.uuid4()),
            system_prompt=system_prompt,
            user_message=request.user_message,
            response="Request blocked by guardrails.",
            score=score,
            score_breakdown=breakdown,
            input_violations=input_violations,
            output_violations=[],
            provider=request.provider_config.provider_type.value,
            model=request.provider_config.model,
            input_tokens=None,
            output_tokens=None,
            latency_ms=latency_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=request.role.value,
            tone=request.tone.value,
            output_format=request.output_format.value,
        )

    provider = ProviderFactory.create(request.provider_config, settings)
    llm_response = await provider.chat(
        system_prompt=system_prompt,
        user_message=processed_message,
        max_tokens=1000,
    )

    output_violations = await orchestrator.run_output_checks(
        llm_response.text,
        original_request=request.user_message,
    )

    score, breakdown = score_run(
        system_prompt=system_prompt,
        response=llm_response.text,
        output_violations=output_violations,
        role=request.role,
        tone=request.tone,
        output_format=request.output_format,
    )

    latency_ms = int((time.monotonic() - start) * 1000)

    return RunResult(
        id=str(uuid.uuid4()),
        system_prompt=system_prompt,
        user_message=processed_message,
        response=llm_response.text,
        score=score,
        score_breakdown=breakdown,
        input_violations=input_violations,
        output_violations=output_violations,
        provider=llm_response.provider,
        model=llm_response.model,
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        latency_ms=latency_ms,
        timestamp=datetime.now(timezone.utc).isoformat(),
        role=request.role.value,
        tone=request.tone.value,
        output_format=request.output_format.value,
    )


@router.post("/api/save/local")
async def save_local(
    body: SaveLocalRequest,
    storage: StorageManager = Depends(get_storage_manager),
) -> Dict[str, str]:
    """Save run result to local storage. Returns file path."""
    saved = SavedPrompt(
        id=body.run_result.id,
        name=body.name,
        run_result=body.run_result,
        tags=body.tags,
        saved_at=datetime.now(timezone.utc).isoformat(),
    )
    path = await storage.save_local(saved, format=body.format)
    return {"path": path}


@router.post("/api/save/gist")
async def save_gist(body: SaveGistRequest) -> Dict[str, str]:
    """Save run result to GitHub Gist. Returns gist URL."""
    saved = SavedPrompt(
        id=body.run_result.id,
        name=body.name,
        run_result=body.run_result,
        tags=body.tags,
        saved_at=datetime.now(timezone.utc).isoformat(),
    )
    gist = GistStorage(body.github_token)
    try:
        url = await gist.save(saved, public=body.public)
    finally:
        await gist.close()
    return {"url": url}


@router.get("/api/history")
async def get_history(
    storage: StorageManager = Depends(get_storage_manager),
) -> List[Dict]:
    """Return list of saved prompts from local storage."""
    return await storage.list_local()


@router.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """
    Accept document or image upload and extract context.

    Returns context text and/or base64 image data.
    """
    file_bytes = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    try:
        context_text, image_base64 = await extract_context(
            file_bytes, filename, mime_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(
        context_text=context_text or "",
        image_base64=image_base64,
        filename=filename,
        file_type=mime_type,
    )


@router.get("/api/providers/ollama/models")
async def get_ollama_models(
    base_url: str = "http://localhost:11434",
) -> List[str]:
    """List available Ollama models."""
    provider = OllamaProvider(base_url=base_url)
    try:
        return await provider.list_models()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await provider.close()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
