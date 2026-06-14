"""Tests for prompt versioning and version chain in LocalStorage."""
import pytest
from promptforge.core.models import SavedPrompt, RunResult, ScoreBreakdown
from promptforge.storage.local_storage import LocalStorage
from datetime import datetime, timezone


def _make_run_result(run_id: str) -> RunResult:
    return RunResult(
        id=run_id,
        system_prompt="You are helpful.",
        user_message="Hello",
        response="Hi there!",
        score=80,
        score_breakdown=[ScoreBreakdown(check="has_role", points=20, passed=True)],
        input_violations=[],
        output_violations=[],
        provider="ollama",
        model="llama3.2",
        input_tokens=10,
        output_tokens=20,
        latency_ms=100,
        timestamp=datetime.now(timezone.utc).isoformat(),
        role="senior_dev",
        tone="neutral",
        output_format="plain_text",
    )


def _make_saved_prompt(prompt_id: str, name: str = "test-prompt") -> SavedPrompt:
    return SavedPrompt(
        id=prompt_id,
        name=name,
        run_result=_make_run_result(prompt_id),
        saved_at=datetime.now(timezone.utc).isoformat(),
    )


@pytest.mark.asyncio
async def test_saved_prompt_default_version():
    p = _make_saved_prompt("id-1")
    assert p.version == 1
    assert p.parent_id is None
    assert p.author is None


@pytest.mark.asyncio
async def test_version_chain(tmp_path):
    storage = LocalStorage(str(tmp_path))
    p1 = _make_saved_prompt("v1-id", "my-prompt")
    await storage.save(p1)

    p2 = _make_saved_prompt("v2-id", "my-prompt")
    await storage.save(p2)

    loaded = await storage.load("v2-id")
    assert loaded is not None
    assert loaded.version == 2
    assert loaded.parent_id == "v1-id"


@pytest.mark.asyncio
async def test_get_versions(tmp_path):
    storage = LocalStorage(str(tmp_path))
    for i in range(3):
        p = _make_saved_prompt(f"vid-{i}", "versioned-prompt")
        await storage.save(p)

    versions = await storage.get_versions("versioned-prompt")
    assert len(versions) == 3
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    assert versions[2]["version"] == 3


@pytest.mark.asyncio
async def test_list_all_includes_version(tmp_path):
    storage = LocalStorage(str(tmp_path))
    p = _make_saved_prompt("list-id", "list-prompt")
    await storage.save(p)

    items = await storage.list_all()
    assert len(items) == 1
    assert "version" in items[0]
    assert items[0]["version"] == 1


@pytest.mark.asyncio
async def test_author_field(tmp_path):
    storage = LocalStorage(str(tmp_path))
    p = _make_saved_prompt("auth-id", "author-prompt")
    p = p.model_copy(update={"author": "Mini"})
    await storage.save(p)

    loaded = await storage.load("auth-id")
    assert loaded is not None
    assert loaded.author == "Mini"
