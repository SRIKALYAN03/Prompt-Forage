# PromptForge

Open-source prompt engineering studio with guardrails, multi-provider LLM support, and a FastAPI backend.

## Features

- **Prompt Engineering** — role-aware system prompts, tone/format selection, document context ingestion
- **Guardrails** — PII scanning, injection detection, token limiting, hallucination reduction, output validation
- **Multi-Provider** — Anthropic Claude, OpenAI GPT, local Ollama, OpenAI-compatible endpoints
- **Storage** — local JSON/YAML files and GitHub Gist export

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
pip install -e .
cp .env.example .env         # add your API keys
make run
```

Open http://localhost:8000

## Docker

Run everything in a container (no local Python/venv required):

```bash
cp .env.example .env          # add API keys (optional for Ollama-only)
docker compose up --build
```

Open http://localhost:8000

**With Ollama in Docker** (local LLM, no cloud API keys):

```bash
# In .env set:
#   OLLAMA_BASE_URL=http://ollama:11434
docker compose --profile ollama up --build
```

Pull a model inside the Ollama container:

```bash
docker exec -it promptforge-ollama ollama pull llama3.2
```

**Development with hot reload:**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Command | What it runs |
|---------|----------------|
| `docker compose up --build` | PromptForge only |
| `docker compose --profile ollama up` | PromptForge + Ollama |
| `docker build -t promptforge .` | Build image manually |

Saved prompts persist in the Docker volume `promptforge-data`.

## Run Tests

```bash
pytest tests/ -v --cov=promptforge --cov-fail-under=80
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/run` | Run full prompt pipeline |
| POST | `/api/upload` | Upload document/image for context |
| POST | `/api/save/local` | Save run to local storage |
| POST | `/api/save/gist` | Save run to GitHub Gist |
| GET | `/api/history` | List saved prompts |
| GET | `/api/providers/ollama/models` | List Ollama models |

## License

MIT — see [LICENSE](LICENSE)
