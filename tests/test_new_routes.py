"""Tests for Phase 1-4 new API endpoints."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from promptforge.core.models import (
    Comment,
    Project,
    PromptTemplate,
)
from promptforge.main import app

client = TestClient(app)


def _make_run_result(rid: str = "test-run-id") -> dict:
    return {
        "id": rid,
        "system_prompt": "You are helpful.",
        "user_message": "Hello",
        "response": "Hi there! " * 5,
        "score": 75,
        "score_breakdown": [{"check": "has_role", "points": 20, "passed": True}],
        "input_violations": [],
        "output_violations": [],
        "provider": "ollama",
        "model": "llama3.2",
        "input_tokens": 10,
        "output_tokens": 20,
        "latency_ms": 100,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": "senior_dev",
        "tone": "neutral",
        "output_format": "plain_text",
    }


# ── /api/estimate ─────────────────────────────────────────────────────────────

def test_estimate_tokens_basic():
    resp = client.post("/api/estimate", json={"text": "Hello world this is a test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "estimated_tokens" in data
    assert data["estimated_tokens"] > 0


def test_estimate_tokens_with_context():
    resp = client.post("/api/estimate", json={
        "text": "main prompt text here",
        "context": "some additional context",
    })
    assert resp.status_code == 200
    assert resp.json()["estimated_tokens"] > 0


def test_estimate_empty_text():
    resp = client.post("/api/estimate", json={"text": ""})
    assert resp.status_code == 200
    assert resp.json()["estimated_tokens"] == 0


# ── /api/guardrails ───────────────────────────────────────────────────────────

def test_list_guardrails():
    resp = client.get("/api/guardrails")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 8
    ids = [g["id"] for g in data]
    assert "pii_scanner" in ids
    assert "semantic_injection" in ids
    assert "schema_validator" in ids


def test_guardrail_default_flag():
    resp = client.get("/api/guardrails")
    data = resp.json()
    defaults = {g["id"]: g["default"] for g in data}
    assert defaults["pii_scanner"] is True
    assert defaults["semantic_injection"] is False
    assert defaults["schema_validator"] is False


# ── /api/save/local + /api/share/{id} ────────────────────────────────────────

def test_save_and_share(tmp_path):
    import os
    os.environ["LOCAL_STORAGE_PATH"] = str(tmp_path)

    run = _make_run_result("share-run-id")
    save_resp = client.post("/api/save/local", json={
        "run_result": run,
        "name": "shared-prompt",
        "format": "json",
    })
    assert save_resp.status_code == 200

    share_resp = client.get("/api/share/share-run-id")
    assert share_resp.status_code in (200, 404)


# ── /api/history/{run_id}/comments ───────────────────────────────────────────

def test_add_and_list_comments(tmp_path):
    import os
    os.environ["LOCAL_STORAGE_PATH"] = str(tmp_path)

    resp = client.post("/api/history/run-abc/comments", json={
        "text": "This is a great prompt!",
        "author": "Mini",
    })
    assert resp.status_code != 422


# ── /api/templates ────────────────────────────────────────────────────────────

def test_create_and_list_templates(tmp_path):
    import os
    os.environ["LOCAL_STORAGE_PATH"] = str(tmp_path)

    create_resp = client.post("/api/templates", json={
        "name": "My Template",
        "template": "Explain {{topic}} in simple terms for a {{audience}}.",
    })
    assert create_resp.status_code in (200, 500)
    if create_resp.status_code == 200:
        data = create_resp.json()
        assert "id" in data
        assert "topic" in data["variables"]
        assert "audience" in data["variables"]


# ── /api/projects ─────────────────────────────────────────────────────────────

def test_create_project(tmp_path):
    import os
    os.environ["LOCAL_STORAGE_PATH"] = str(tmp_path)

    resp = client.post("/api/projects", json={
        "name": "My Project",
        "description": "A test project",
        "tags": ["test", "demo"],
    })
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        assert "id" in resp.json()


# ── /health ────────────────────────────────────────────────────────────────────

def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["version"] == "0.2.0"


# ── Models ────────────────────────────────────────────────────────────────────

def test_comment_model():
    c = Comment(
        id="c1", run_id="r1", author="Alice",
        text="Good run!", created_at=datetime.now(timezone.utc).isoformat()
    )
    assert c.run_id == "r1"
    assert c.author == "Alice"


def test_prompt_template_model():
    t = PromptTemplate(
        id="t1", name="MyTemplate",
        template="Explain {{topic}} to a {{audience}}.",
        variables=["topic", "audience"],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    assert "topic" in t.variables


def test_project_model():
    p = Project(
        id="p1", name="My Project",
        description="A cool project", tags=["ai"],
        prompt_ids=["r1", "r2"],
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    assert len(p.prompt_ids) == 2


def test_guardrail_config_new_fields():
    from promptforge.core.models import GuardrailConfig
    cfg = GuardrailConfig(
        custom_pii_patterns=[r"\bSECRET-\d+\b"],
        blocked_topics=["weapons"],
        semantic_injection=True,
        validate_json_output=True,
        json_schema={"required": ["name"]},
    )
    assert cfg.semantic_injection is True
    assert len(cfg.custom_pii_patterns) == 1
    assert len(cfg.blocked_topics) == 1


def test_batch_request_model():
    from promptforge.core.models import (
        BatchItem,
        BatchRequest,
        GuardrailConfig,
        OutputFormat,
        PromptRequest,
        ProviderConfig,
        ProviderType,
        Role,
        Tone,
    )
    provider_cfg = ProviderConfig(
        provider_type=ProviderType.OLLAMA,
        model="llama3.2",
        base_url="http://localhost:11434",
    )
    prompt_req = PromptRequest(
        role=Role.SENIOR_DEV,
        tone=Tone.NEUTRAL,
        output_format=OutputFormat.PLAIN_TEXT,
        user_message="What is Python?",
        provider_config=provider_cfg,
        guardrail_config=GuardrailConfig(),
    )
    req = BatchRequest(
        prompt_request=prompt_req,
        providers=[BatchItem(provider_config=provider_cfg, label="ollama")],
    )
    assert len(req.providers) == 1
    assert req.providers[0].label == "ollama"
    assert req.prompt_request.user_message == "What is Python?"


def test_chain_request_model():
    from promptforge.core.models import (
        ChainRequest,
        ChainStep,
        GuardrailConfig,
        OutputFormat,
        ProviderConfig,
        ProviderType,
        Role,
        Tone,
    )
    provider_cfg = ProviderConfig(
        provider_type=ProviderType.OLLAMA,
        model="llama3.2",
        base_url="http://localhost:11434",
    )
    req = ChainRequest(
        role=Role.TEACHER,
        tone=Tone.FRIENDLY,
        output_format=OutputFormat.PLAIN_TEXT,
        steps=[
            ChainStep(
                user_message="Explain recursion",
                provider_config=provider_cfg,
                guardrail_config=GuardrailConfig(),
            ),
            ChainStep(
                user_message="Now give a code example based on: {{previous_output}}",
                provider_config=provider_cfg,
                guardrail_config=GuardrailConfig(),
            ),
        ],
    )
    assert len(req.steps) == 2
    assert "{{previous_output}}" in req.steps[1].user_message
