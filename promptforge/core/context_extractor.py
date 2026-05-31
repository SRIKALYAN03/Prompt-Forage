"""Extract text context from uploaded documents and images."""

import asyncio
import base64
import io
from typing import Optional, Tuple

import fitz
from docx import Document
from PIL import Image

MAX_CONTEXT_CHARS = 3000


async def extract_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from PDF bytes using PyMuPDF.

    Args:
        file_bytes: Raw PDF file content.

    Returns:
        Extracted text, truncated to MAX_CONTEXT_CHARS.
    """
    if not file_bytes:
        raise ValueError("Empty file provided")

    def _extract() -> str:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_parts: list[str] = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts).strip()

    text = await asyncio.to_thread(_extract)
    if not text:
        raise ValueError("No text could be extracted from PDF")
    return text[:MAX_CONTEXT_CHARS]


async def extract_from_docx(file_bytes: bytes) -> str:
    """
    Extract text from .docx bytes using python-docx.

    Args:
        file_bytes: Raw DOCX file content.

    Returns:
        Extracted text, truncated to MAX_CONTEXT_CHARS.
    """
    if not file_bytes:
        raise ValueError("Empty file provided")

    def _extract() -> str:
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()

    text = await asyncio.to_thread(_extract)
    if not text:
        raise ValueError("No text could be extracted from DOCX")
    return text[:MAX_CONTEXT_CHARS]


async def extract_from_txt(file_bytes: bytes) -> str:
    """
    Decode plain text file bytes.

    Args:
        file_bytes: Raw text file content.

    Returns:
        Decoded text, truncated to MAX_CONTEXT_CHARS.
    """
    if not file_bytes:
        raise ValueError("Empty file provided")

    text = file_bytes.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("Empty text file")
    return text[:MAX_CONTEXT_CHARS]


async def extract_from_image(file_bytes: bytes, mime_type: str) -> str:
    """
    Return base64-encoded image string for vision models.

    Also extracts basic metadata (dimensions, format).

    Args:
        file_bytes: Raw image file content.
        mime_type: MIME type of the image.

    Returns:
        Base64-encoded image data URI string.
    """
    if not file_bytes:
        raise ValueError("Empty file provided")

    def _process() -> str:
        img = Image.open(io.BytesIO(file_bytes))
        width, height = img.size
        fmt = img.format or "unknown"
        encoded = base64.b64encode(file_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}|{width}x{height}|{fmt}"

    return await asyncio.to_thread(_process)


async def extract_context(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> Tuple[str, Optional[str]]:
    """
    Main dispatcher for file context extraction.

    Routes to the correct extractor based on mime_type and filename extension.

    Args:
        file_bytes: Raw file content.
        filename: Original filename.
        mime_type: MIME type of the file.

    Returns:
        Tuple of (text_context, image_base64_or_none).

    Raises:
        ValueError: If file is empty or format is unsupported.
    """
    if not file_bytes:
        raise ValueError("Empty file provided")

    lower_name = filename.lower()
    lower_mime = mime_type.lower()

    if lower_mime == "application/pdf" or lower_name.endswith(".pdf"):
        text = await extract_from_pdf(file_bytes)
        return text, None

    if (
        lower_mime
        in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        )
        or lower_name.endswith(".docx")
    ):
        text = await extract_from_docx(file_bytes)
        return text, None

    if lower_mime.startswith("text/") or lower_name.endswith(".txt"):
        text = await extract_from_txt(file_bytes)
        return text, None

    if lower_mime.startswith("image/"):
        image_data = await extract_from_image(file_bytes, mime_type)
        return "", image_data

    raise ValueError(f"Unsupported file format: {mime_type} ({filename})")
