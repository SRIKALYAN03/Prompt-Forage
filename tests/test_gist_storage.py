# tests/test_gist_storage.py
"""Tests for promptforge.storage.gist_storage."""

import pytest
import respx
import httpx

from promptforge.storage.base import AuthError, StorageError
from promptforge.storage.gist_storage import GIST_API_URL, GistStorage


class TestGistStorage:
    """Test GitHub Gist storage with mocked HTTP."""

    @pytest.fixture
    def gist_storage(self):
        """Create GistStorage with test token."""
        return GistStorage("ghp_testtoken")

    @pytest.mark.asyncio
    @respx.mock
    async def test_save_returns_gist_url(self, gist_storage, sample_saved_prompt) -> None:
        """Save returns gist HTML URL."""
        respx.post(GIST_API_URL).mock(
            return_value=httpx.Response(
                201,
                json={"html_url": "https://gist.github.com/test/abc123", "id": "abc123"},
            )
        )
        url = await gist_storage.save(sample_saved_prompt)
        assert "gist.github.com" in url
        await gist_storage.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_load_parses_gist(self, gist_storage, sample_saved_prompt) -> None:
        """Load parses gist file content."""
        content = sample_saved_prompt.model_dump_json()
        respx.get(f"{GIST_API_URL}/abc123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "files": {
                        "prompt.json": {"content": content},
                    }
                },
            )
        )
        loaded = await gist_storage.load("abc123")
        assert loaded is not None
        assert loaded.id == sample_saved_prompt.id
        await gist_storage.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_invalid_token_raises_auth_error(
        self, gist_storage, sample_saved_prompt
    ) -> None:
        """401 response raises AuthError."""
        respx.post(GIST_API_URL).mock(return_value=httpx.Response(401))
        with pytest.raises(AuthError):
            await gist_storage.save(sample_saved_prompt)
        await gist_storage.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_network_error_raises_storage_error(
        self, gist_storage, sample_saved_prompt
    ) -> None:
        """Network failure raises StorageError."""
        respx.post(GIST_API_URL).mock(side_effect=httpx.ConnectError("Connection refused"))
        with pytest.raises(StorageError):
            await gist_storage.save(sample_saved_prompt)
        await gist_storage.close()
