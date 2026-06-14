"""Tests for new storage features: comments, templates, projects."""
import pytest
from datetime import datetime, timezone
from promptforge.core.models import (
    Comment, PromptTemplate, Project, RunResult, ScoreBreakdown
)
from promptforge.storage.local_storage import LocalStorage


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_run(rid: str) -> RunResult:
    return RunResult(
        id=rid, system_prompt="sys", user_message="hi", response="hello world ok",
        score=70, score_breakdown=[ScoreBreakdown(check="has_role", points=20, passed=True)],
        input_violations=[], output_violations=[], provider="ollama", model="llama3.2",
        input_tokens=5, output_tokens=10, latency_ms=50, timestamp=_now(),
        role="senior_dev", tone="neutral", output_format="plain_text",
    )


# ── Comments ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_list_comments(tmp_path):
    storage = LocalStorage(str(tmp_path))
    c1 = Comment(id="c1", run_id="run-1", author="Alice", text="Nice!", created_at=_now())
    c2 = Comment(id="c2", run_id="run-1", author="Bob",   text="Agreed!", created_at=_now())
    await storage.save_comment(c1)
    await storage.save_comment(c2)
    comments = await storage.list_comments("run-1")
    assert len(comments) == 2
    texts = {c.text for c in comments}
    assert "Nice!" in texts
    assert "Agreed!" in texts


@pytest.mark.asyncio
async def test_list_comments_empty(tmp_path):
    storage = LocalStorage(str(tmp_path))
    result = await storage.list_comments("nonexistent-run")
    assert result == []


@pytest.mark.asyncio
async def test_comment_isolation_by_run_id(tmp_path):
    storage = LocalStorage(str(tmp_path))
    c_a = Comment(id="ca", run_id="run-A", author=None, text="For A", created_at=_now())
    c_b = Comment(id="cb", run_id="run-B", author=None, text="For B", created_at=_now())
    await storage.save_comment(c_a)
    await storage.save_comment(c_b)
    comments_a = await storage.list_comments("run-A")
    assert len(comments_a) == 1
    assert comments_a[0].text == "For A"


# ── Templates ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_load_template(tmp_path):
    storage = LocalStorage(str(tmp_path))
    t = PromptTemplate(
        id="t1", name="Test Template",
        template="Explain {{topic}} to a {{audience}}.",
        variables=["topic", "audience"],
        created_at=_now(),
    )
    path = await storage.save_template(t)
    assert path
    loaded = await storage.load_template("t1")
    assert loaded is not None
    assert loaded.name == "Test Template"
    assert "topic" in loaded.variables


@pytest.mark.asyncio
async def test_load_template_not_found(tmp_path):
    storage = LocalStorage(str(tmp_path))
    result = await storage.load_template("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_templates(tmp_path):
    storage = LocalStorage(str(tmp_path))
    for i in range(3):
        t = PromptTemplate(
            id=f"t{i}", name=f"Template {i}", template=f"Do {{{{x}}}} number {i}",
            variables=["x"], created_at=_now()
        )
        await storage.save_template(t)
    items = await storage.list_templates()
    assert len(items) == 3


# ── Projects ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_and_load_project(tmp_path):
    storage = LocalStorage(str(tmp_path))
    p = Project(
        id="p1", name="My Project", description="desc", tags=["ai"],
        prompt_ids=["r1", "r2"], created_at=_now()
    )
    await storage.save_project(p)
    loaded = await storage.load_project("p1")
    assert loaded is not None
    assert loaded.name == "My Project"
    assert len(loaded.prompt_ids) == 2


@pytest.mark.asyncio
async def test_load_project_not_found(tmp_path):
    storage = LocalStorage(str(tmp_path))
    result = await storage.load_project("nope")
    assert result is None


@pytest.mark.asyncio
async def test_list_projects(tmp_path):
    storage = LocalStorage(str(tmp_path))
    for i in range(2):
        p = Project(
            id=f"proj{i}", name=f"Project {i}", description=None,
            tags=[], prompt_ids=[], created_at=_now()
        )
        await storage.save_project(p)
    items = await storage.list_projects()
    assert len(items) == 2
    assert all("name" in item for item in items)
