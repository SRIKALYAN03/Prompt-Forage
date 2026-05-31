# tests/test_api_routes.py
"""Tests for promptforge.api.routes."""

import pytest
from unittest.mock import AsyncMock, patch


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_200(self, test_client) -> None:
        """GET /health returns 200 with status ok."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


class TestRunEndpoint:
    """Test /api/run endpoint."""

    @pytest.mark.asyncio
    async def test_run_returns_run_result_shape(
        self, async_test_client, basic_prompt_request, mock_llm_response
    ) -> None:
        """POST /api/run returns RunResult shape."""
        mock_provider = AsyncMock()
        mock_provider.chat = AsyncMock(return_value=mock_llm_response)
        mock_provider.provider_name = "anthropic"

        with patch(
            "promptforge.api.routes.ProviderFactory.create",
            return_value=mock_provider,
        ):
            payload = basic_prompt_request.model_dump()
            payload["provider_config"]["provider_type"] = "anthropic"
            response = await async_test_client.post("/api/run", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "response" in data
        assert "score" in data
        assert "system_prompt" in data

    @pytest.mark.asyncio
    async def test_run_missing_provider_returns_422(self, async_test_client) -> None:
        """Invalid request body returns 422."""
        response = await async_test_client.post("/api/run", json={"user_message": "hi"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_run_with_injection_returns_violations(
        self, async_test_client, injection_attempt_request
    ) -> None:
        """Injection in input returns violations and blocked response."""
        payload = injection_attempt_request.model_dump()
        payload["provider_config"]["provider_type"] = "anthropic"
        response = await async_test_client.post("/api/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["input_violations"]) > 0
        assert "blocked" in data["response"].lower()

    @pytest.mark.asyncio
    async def test_run_with_pii_returns_warnings(
        self, async_test_client, pii_in_input_request
    ) -> None:
        """PII in input returns warn violations."""
        payload = pii_in_input_request.model_dump()
        payload["provider_config"]["provider_type"] = "anthropic"
        response = await async_test_client.post("/api/run", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["input_violations"]) > 0


class TestUploadEndpoint:
    """Test /api/upload endpoint."""

    def test_upload_accepts_pdf(self, test_client, sample_pdf_bytes) -> None:
        """POST /api/upload accepts PDF files."""
        response = test_client.post(
            "/api/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"

    def test_upload_accepts_txt(self, test_client, sample_txt_bytes) -> None:
        """POST /api/upload accepts text files."""
        response = test_client.post(
            "/api/upload",
            files={"file": ("test.txt", sample_txt_bytes, "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "machine learning" in data["context_text"]

    def test_upload_accepts_image(self, test_client) -> None:
        """POST /api/upload accepts image files."""
        from PIL import Image
        import io

        img = Image.new("RGB", (10, 10), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        response = test_client.post(
            "/api/upload",
            files={"file": ("test.png", buffer.getvalue(), "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["image_base64"] is not None


class TestHistoryEndpoint:
    """Test /api/history endpoint."""

    def test_history_returns_list(self, test_client) -> None:
        """GET /api/history returns a list."""
        response = test_client.get("/api/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
