# tests/test_local_storage.py
"""Tests for promptforge.storage.local_storage."""

import pytest

from promptforge.storage.local_storage import LocalStorage


class TestLocalStorage:
    """Test local JSON/YAML storage."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create LocalStorage in temp directory."""
        return LocalStorage(str(tmp_path / "prompts"))

    @pytest.mark.asyncio
    async def test_save_creates_file(self, storage, sample_saved_prompt) -> None:
        """Save creates a file on disk."""
        path = await storage.save(sample_saved_prompt)
        assert path.endswith(".json")

    @pytest.mark.asyncio
    async def test_load_returns_correct_data(self, storage, sample_saved_prompt) -> None:
        """Load returns the saved prompt."""
        await storage.save(sample_saved_prompt)
        loaded = await storage.load(sample_saved_prompt.id)
        assert loaded is not None
        assert loaded.id == sample_saved_prompt.id
        assert loaded.name == sample_saved_prompt.name

    @pytest.mark.asyncio
    async def test_load_nonexistent_returns_none(self, storage) -> None:
        """Load returns None for missing ID."""
        result = await storage.load("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all_returns_correct_count(self, storage, sample_saved_prompt) -> None:
        """List returns all saved prompts."""
        await storage.save(sample_saved_prompt)
        items = await storage.list_all()
        assert len(items) == 1
        assert items[0]["id"] == sample_saved_prompt.id

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, storage, sample_saved_prompt) -> None:
        """Delete removes the prompt file."""
        await storage.save(sample_saved_prompt)
        deleted = await storage.delete(sample_saved_prompt.id)
        assert deleted is True
        assert await storage.load(sample_saved_prompt.id) is None

    @pytest.mark.asyncio
    async def test_yaml_round_trip(self, storage, sample_saved_prompt) -> None:
        """YAML save and load round-trips correctly."""
        path = await storage.save(sample_saved_prompt, format="yaml")
        assert path.endswith(".yaml")
        loaded = await storage.load(sample_saved_prompt.id)
        assert loaded is not None
        assert loaded.run_result.score == sample_saved_prompt.run_result.score
