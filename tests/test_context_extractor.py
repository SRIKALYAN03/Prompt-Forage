# tests/test_context_extractor.py
"""Tests for promptforge.core.context_extractor."""

import pytest

from promptforge.core.context_extractor import (
    MAX_CONTEXT_CHARS,
    _FITZ_AVAILABLE,
    extract_context,
    extract_from_docx,
    extract_from_image,
    extract_from_pdf,
    extract_from_txt,
)

pytestmark_pdf = pytest.mark.skipif(
    not _FITZ_AVAILABLE, reason="PyMuPDF not available on this system"
)


class TestPDFExtraction:
    """Test PDF text extraction."""

    @pytestmark_pdf
    @pytest.mark.asyncio
    async def test_pdf_returns_non_empty(self, sample_pdf_bytes) -> None:
        """PDF extraction returns non-empty string."""
        text = await extract_from_pdf(sample_pdf_bytes)
        assert text
        assert "Sample PDF" in text or len(text) > 0

    @pytest.mark.asyncio
    async def test_empty_pdf_raises(self) -> None:
        """Empty PDF bytes raises ValueError."""
        with pytest.raises(ValueError):
            await extract_from_pdf(b"")


class TestDOCXExtraction:
    """Test DOCX text extraction."""

    @pytest.mark.asyncio
    async def test_docx_extraction(self) -> None:
        """DOCX extraction from minimal docx bytes."""
        import io

        from docx import Document

        doc = Document()
        doc.add_paragraph("Hello from DOCX test document.")
        buffer = io.BytesIO()
        doc.save(buffer)
        text = await extract_from_docx(buffer.getvalue())
        assert "Hello from DOCX" in text


class TestTXTExtraction:
    """Test plain text extraction."""

    @pytest.mark.asyncio
    async def test_txt_extraction(self, sample_txt_bytes) -> None:
        """TXT extraction decodes bytes correctly."""
        text = await extract_from_txt(sample_txt_bytes)
        assert "machine learning" in text


class TestImageExtraction:
    """Test image base64 extraction."""

    @pytest.mark.asyncio
    async def test_image_returns_base64(self) -> None:
        """Image extraction returns base64 data URI."""
        import io

        from PIL import Image

        img = Image.new("RGB", (10, 10), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        result = await extract_from_image(buffer.getvalue(), "image/png")
        assert result.startswith("data:image/png;base64,")


class TestExtractContext:
    """Test main extract_context dispatcher."""

    @pytestmark_pdf
    @pytest.mark.asyncio
    async def test_pdf_dispatch(self, sample_pdf_bytes) -> None:
        """PDF files route to PDF extractor."""
        text, image = await extract_context(sample_pdf_bytes, "doc.pdf", "application/pdf")
        assert text
        assert image is None

    @pytest.mark.asyncio
    async def test_txt_dispatch(self, sample_txt_bytes) -> None:
        """TXT files route to text extractor."""
        text, image = await extract_context(sample_txt_bytes, "doc.txt", "text/plain")
        assert "machine learning" in text
        assert image is None

    @pytest.mark.asyncio
    async def test_unsupported_format_raises(self) -> None:
        """Unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported"):
            await extract_context(b"data", "file.xyz", "application/xyz")

    @pytest.mark.asyncio
    async def test_empty_file_raises(self) -> None:
        """Empty file raises ValueError."""
        with pytest.raises(ValueError):
            await extract_context(b"", "empty.txt", "text/plain")

    @pytest.mark.asyncio
    async def test_max_length_truncation(self) -> None:
        """Text is truncated at MAX_CONTEXT_CHARS."""
        long_text = "A" * (MAX_CONTEXT_CHARS + 500)
        text = await extract_from_txt(long_text.encode())
        assert len(text) <= MAX_CONTEXT_CHARS
