# PromptForge — production image
FROM python:3.11-slim

WORKDIR /app

# Runtime libs for PyMuPDF / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt setup.py ./
COPY promptforge/ ./promptforge/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e .

# Frontend static assets
COPY frontend/ ./frontend/

# Persistent prompt storage inside container
RUN mkdir -p /app/prompts

ENV HOST=0.0.0.0 \
    PORT=8000 \
    LOCAL_STORAGE_PATH=/app/prompts

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "promptforge.main:app", "--host", "0.0.0.0", "--port", "8000"]
