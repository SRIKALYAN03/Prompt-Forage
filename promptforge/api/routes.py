"""FastAPI route handlers for PromptForge."""

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from promptforge.api.schemas import (
    CommentRequest,
    EstimateRequest,
    EstimateResponse,
    GuardrailInfo,
    ProjectCreateRequest,
    SaveGistRequest,
    SaveLocalRequest,
    TemplateCreateRequest,
    UploadResponse,
)
from promptforge.config import Settings, get_settings
from promptforge.core.context_extractor import extract_context
from promptforge.core.models import (
    BatchRequest,
    ChainRequest,
    Comment,
    Project,
    PromptRequest,
    PromptTemplate,
    RunResult,
    SavedPrompt,
)
from promptforge.core.prompt_builder import build_system_prompt
from promptforge.core.scorer import score_run
from promptforge.guardrails.orchestrator import GuardrailOrchestrator
from promptforge.guardrails.token_limiter import estimate_tokens
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


# ── Core run pipeline ─────────────────────────────────────────────────────────

@router.post("/api/run", response_model=RunResult)
async def run_prompt(
    request: PromptRequest,
    settings: Settings = Depends(get_settings),
) -> RunResult:
    """Run the full prompt pipeline."""
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

    result = RunResult(
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

    # Fire-and-forget webhook (Phase 3)
    if settings.webhook_url:
        import asyncio

        webhook_url = settings.webhook_url

        async def _fire_webhook() -> None:
            try:
                async with httpx.AsyncClient(timeout=5.0) as wh_client:
                    await wh_client.post(
                        webhook_url,
                        json={
                            "event": "run_complete",
                            "run_id": result.id,
                            "score": result.score,
                            "provider": result.provider,
                            "model": result.model,
                        },
                    )
            except Exception:
                pass

        asyncio.create_task(_fire_webhook())

    return result


# ── Storage ────────────────────────────────────────────────────────────────────

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
        author=body.author,
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
) -> List[Dict[str, Any]]:
    """Return list of saved prompts from local storage."""
    return await storage.list_local()


# ── Phase 1: Versioning + Diff ─────────────────────────────────────────────────

@router.get("/api/history/{prompt_id}/versions")
async def get_versions(
    prompt_id: str,
    storage: StorageManager = Depends(get_storage_manager),
) -> List[Dict[str, Any]]:
    """Return all versions of the prompt with the same name as prompt_id."""
    prompt = await storage.load_local(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    if not prompt.name:
        return [{"id": prompt.id, "version": prompt.version, "saved_at": prompt.saved_at}]
    return await storage.get_versions(prompt.name)


@router.get("/api/history/{id1}/diff")
async def diff_prompts(
    id1: str,
    compare: str,
    storage: StorageManager = Depends(get_storage_manager),
) -> List[Dict[str, str]]:
    """Return field-level diff between two saved prompts."""
    a = await storage.load_local(id1)
    b = await storage.load_local(compare)
    if not a or not b:
        raise HTTPException(status_code=404, detail="One or both prompts not found")
    results: List[Dict[str, str]] = []
    for field in ["system_prompt", "user_message", "response"]:
        va = str(getattr(a.run_result, field, ""))
        vb = str(getattr(b.run_result, field, ""))
        if va != vb:
            results.append({"field": field, "before": va, "after": vb})
    results.append(
        {
            "field": "score",
            "before": str(a.run_result.score),
            "after": str(b.run_result.score),
        }
    )
    return results


# ── Phase 1: Token estimate ────────────────────────────────────────────────────

@router.post("/api/estimate", response_model=EstimateResponse)
async def estimate_tokens_endpoint(body: EstimateRequest) -> EstimateResponse:
    """Estimate token count for the given text."""
    total = estimate_tokens(body.text)
    if body.context:
        total += estimate_tokens(body.context)
    if body.system_prompt:
        total += estimate_tokens(body.system_prompt)
    return EstimateResponse(estimated_tokens=total)


# ── Phase 1/3: Comments ────────────────────────────────────────────────────────

@router.post("/api/history/{run_id}/comments")
async def add_comment(
    run_id: str,
    body: CommentRequest,
    storage: StorageManager = Depends(get_storage_manager),
) -> Dict[str, str]:
    """Add a comment to a run result."""
    comment = Comment(
        id=str(uuid.uuid4()),
        run_id=run_id,
        author=body.author,
        text=body.text,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    path = await storage.save_comment(comment)
    return {"id": comment.id, "path": path}


@router.get("/api/history/{run_id}/comments")
async def get_comments(
    run_id: str,
    storage: StorageManager = Depends(get_storage_manager),
) -> List[Dict[str, Any]]:
    """Return all comments for a run result."""
    comments = await storage.list_comments(run_id)
    return [c.model_dump() for c in comments]


# ── Phase 2: Batch ─────────────────────────────────────────────────────────────

@router.post("/api/batch")
async def run_batch(
    request: BatchRequest,
    settings: Settings = Depends(get_settings),
) -> List[Dict[str, Any]]:
    """Run the same prompt against multiple providers and return a comparison."""
    results: List[Dict[str, Any]] = []
    pr = request.prompt_request
    for item in request.providers:
        label = item.label or f"{item.provider_config.provider_type.value}/{item.provider_config.model}"
        try:
            system_prompt = build_system_prompt(
                role=pr.role,
                tone=pr.tone,
                output_format=pr.output_format,
                context=pr.context,
                guardrail_config=pr.guardrail_config,
                custom_role=pr.custom_role,
            )
            orchestrator = GuardrailOrchestrator(pr.guardrail_config)
            input_violations, processed_message, is_blocked = await orchestrator.run_input_checks(
                pr.user_message, context=pr.context, system_prompt=system_prompt
            )
            if is_blocked:
                results.append({"label": label, "error": "blocked by guardrails", "score": 0})
                continue
            provider = ProviderFactory.create(item.provider_config, settings)
            llm_response = await provider.chat(
                system_prompt=system_prompt,
                user_message=processed_message,
                max_tokens=1000,
            )
            output_violations = await orchestrator.run_output_checks(
                llm_response.text, original_request=pr.user_message
            )
            score, breakdown = score_run(
                system_prompt=system_prompt,
                response=llm_response.text,
                output_violations=output_violations,
                role=pr.role,
                tone=pr.tone,
                output_format=pr.output_format,
            )
            results.append({
                "label": label,
                "response": llm_response.text,
                "score": score,
                "provider": llm_response.provider,
                "model": llm_response.model,
                "input_violations": [v.model_dump() for v in input_violations],
                "output_violations": [v.model_dump() for v in output_violations],
            })
        except Exception as exc:
            results.append({"label": label, "error": str(exc), "score": 0})
    return results


# ── Phase 2: Chain ─────────────────────────────────────────────────────────────

@router.post("/api/chain")
async def run_chain(
    request: ChainRequest,
    settings: Settings = Depends(get_settings),
) -> List[Dict[str, Any]]:
    """Run a sequential prompt chain, piping output between steps."""
    results: List[Dict[str, Any]] = []
    previous_output = ""
    for i, step in enumerate(request.steps):
        user_msg = step.user_message.replace("{{previous_output}}", previous_output)
        system_prompt = build_system_prompt(
            role=request.role,
            tone=request.tone,
            output_format=request.output_format,
            context=None,
            guardrail_config=step.guardrail_config,
        )
        orchestrator = GuardrailOrchestrator(step.guardrail_config)
        input_violations, processed_message, is_blocked = await orchestrator.run_input_checks(
            user_msg, context=None, system_prompt=system_prompt
        )
        if is_blocked:
            results.append({"step": i + 1, "error": "blocked by guardrails", "response": ""})
            break
        try:
            provider = ProviderFactory.create(step.provider_config, settings)
            llm_response = await provider.chat(
                system_prompt=system_prompt,
                user_message=processed_message,
                max_tokens=1000,
            )
        except Exception as exc:
            results.append({"step": i + 1, "error": str(exc), "response": ""})
            break
        previous_output = llm_response.text
        results.append({
            "step": i + 1,
            "response": llm_response.text,
            "provider": llm_response.provider,
            "model": llm_response.model,
        })
    return results


# ── Phase 2: Templates ─────────────────────────────────────────────────────────

@router.post("/api/templates")
async def create_template(
    body: TemplateCreateRequest,
    storage: StorageManager = Depends(get_storage_manager),
) -> Dict[str, Any]:
    """Create a reusable prompt template."""
    variables = list(set(re.findall(r"\{\{(\w+)\}\}", body.template)))
    template = PromptTemplate(
        id=str(uuid.uuid4()),
        name=body.name,
        template=body.template,
        variables=variables,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    path = await storage.save_template(template)
    return {"id": template.id, "name": template.name, "variables": template.variables, "path": path}


@router.get("/api/templates")
async def list_templates(
    storage: StorageManager = Depends(get_storage_manager),
) -> List[Dict[str, Any]]:
    """List all saved templates."""
    return await storage.list_templates()


@router.get("/api/templates/{template_id}")
async def get_template(
    template_id: str,
    storage: StorageManager = Depends(get_storage_manager),
) -> Dict[str, Any]:
    """Get a template by ID."""
    t = await storage.load_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t.model_dump()


# ── Phase 2: Projects ──────────────────────────────────────────────────────────

@router.post("/api/projects")
async def create_project(
    body: ProjectCreateRequest,
    storage: StorageManager = Depends(get_storage_manager),
) -> Dict[str, Any]:
    """Create a new project."""
    project = Project(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        tags=body.tags,
        prompt_ids=[],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    path = await storage.save_project(project)
    return {"id": project.id, "name": project.name, "path": path}


@router.get("/api/projects")
async def list_projects(
    storage: StorageManager = Depends(get_storage_manager),
) -> List[Dict[str, Any]]:
    """List all projects."""
    return await storage.list_projects()


# ── Phase 3: Share ─────────────────────────────────────────────────────────────

@router.get("/api/share/{prompt_id}")
async def share_prompt(
    prompt_id: str,
    storage: StorageManager = Depends(get_storage_manager),
) -> Dict[str, Any]:
    """Return a read-only shareable snapshot of a saved prompt."""
    prompt = await storage.load_local(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {
        "id": prompt.id,
        "name": prompt.name,
        "score": prompt.run_result.score,
        "role": prompt.run_result.role,
        "response": prompt.run_result.response,
        "saved_at": prompt.saved_at,
        "tags": prompt.tags,
        "version": prompt.version,
        "author": prompt.author,
    }


# ── Phase 4: Guardrail introspection ──────────────────────────────────────────

@router.get("/api/guardrails", response_model=List[GuardrailInfo])
async def list_guardrails() -> List[GuardrailInfo]:
    """Return metadata for all available guardrails."""
    return [
        GuardrailInfo(id="pii_scanner", description="Detects PII and API key leakage", phase="input+output", default=True),
        GuardrailInfo(id="injection_guard", description="Detects prompt injection and jailbreak attempts", phase="input", default=True),
        GuardrailInfo(id="token_limiter", description="Truncates input to fit token budget", phase="input", default=True),
        GuardrailInfo(id="hallucination_guard", description="Flags potential hallucination signals in output", phase="output", default=True),
        GuardrailInfo(id="output_validator", description="Detects bypass language in model output", phase="output", default=True),
        GuardrailInfo(id="semantic_injection", description="Heuristic semantic/paraphrase injection detection", phase="input", default=False),
        GuardrailInfo(id="content_policy", description="Configurable topic blocklist", phase="input", default=False),
        GuardrailInfo(id="schema_validator", description="JSON schema output validation", phase="output", default=False),
    ]


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """Accept document or image upload and extract context."""
    file_bytes = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    try:
        context_text, image_base64 = await extract_context(file_bytes, filename, mime_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return UploadResponse(
        context_text=context_text or "",
        image_base64=image_base64,
        filename=filename,
        file_type=mime_type,
    )


# ── Ollama model list ──────────────────────────────────────────────────────────

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


# ── Health ─────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.0"}
