# PromptForge 🔥

> A self-hosted, open-source prompt engineering studio — build, test, evaluate, and version your AI prompts with a full guardrail pipeline, multi-provider support, and a clean browser UI.

![Version](https://img.shields.io/badge/version-0.2.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Tests](https://img.shields.io/badge/tests-197%20passed-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-80.93%25-brightgreen)

---

## What is PromptForge?

PromptForge is a local-first prompt engineering platform that lets you:

- **Design** prompts tailored to specific roles, tones, and output formats
- **Evaluate** every response with an automated 0–100 quality scorer
- **Protect** inputs and outputs through a layered guardrail pipeline
- **Track** prompt versions and compare them over time
- **Collaborate** with comments, templates, projects, and shareable links
- **Run locally** using Ollama — no API keys needed

Built with **FastAPI + Pydantic v2** on the backend and a zero-dependency vanilla JS frontend. Fully async, fully typed.

---

## Features

### Phase 1 — Core Engine + UX
- Role-based system prompt builder (Senior Dev, Executive, Teacher, and more)
- Tone and output format controls (Formal, Technical, Friendly · JSON, Markdown, Table)
- Live token counter with debounced estimation
- 0–100 quality scorer with 6-check breakdown
- Dark/light theme toggle
- Prompt history sidebar

### Phase 2 — Workflow
- **Batch comparisons** — run the same prompt across multiple providers/models side by side
- **Prompt chains** — sequential steps where `{{previous_output}}` pipes between them
- **Templates** — reusable prompts with `{{variable}}` placeholders
- **Projects** — named collections of saved prompts

### Phase 3 — Collaboration
- **Comments** — annotate any saved run
- **Share links** — read-only snapshots via `/api/share/{id}`
- **Version tracking** — auto-increments version when same prompt name is saved again
- **Diff view** — compare any two saved versions field by field
- **Webhooks** — fire-and-forget POST on every completed run

### Phase 4 — Safety & Validation
- PII scanner (API keys, emails, SSNs, credit cards) — blocks or warns
- Prompt injection detection (regex + semantic heuristics)
- Semantic injection guard — catches paraphrase-style jailbreaks
- Content policy — configurable topic blocklist
- JSON schema output validation — verify required fields in LLM JSON responses
- Guardrail introspection API — list all active guards with metadata

---

## Quick Start

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) (for local LLM, no API key needed)
- Git

### 1. Clone the repo

```bash
git clone https://github.com/SRIKALYAN03/Prompt-Forage.git
cd Prompt-Forage
```

### 2. Install dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env to add API keys for Anthropic/OpenAI if needed
# Ollama works with no keys at all
```

### 4. Pull an Ollama model

```bash
ollama pull llama3.2
```

### 5. Start the server

```bash
uvicorn promptforge.main:app --reload --port 8000
```

### 6. Open the UI

Navigate to **http://localhost:8000** in your browser.

---

## Providers

| Provider | Requires | Notes |
|---|---|---|
| **Ollama** (default) | Local Ollama install | `ollama pull llama3.2` — no API key |
| **Anthropic** | `ANTHROPIC_API_KEY` in `.env` | Claude models |
| **OpenAI** | `OPENAI_API_KEY` in `.env` | GPT models |
| **OpenAI-compat** | Custom endpoint URL + key | Any OpenAI-compatible API |

---

## Configuration

All settings load from `.env` or environment variables:

```env
# Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# Storage
LOCAL_STORAGE_PATH=./prompts

# Collaboration
WEBHOOK_URL=https://your-webhook.com/notify

# GitHub Gist (for cloud saves)
GITHUB_TOKEN=ghp_...
```

---

## API Reference

### Core

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/run` | Run a prompt through the full pipeline |
| `POST` | `/api/estimate` | Estimate token count |
| `GET` | `/health` | Health check — returns version |

### Storage & History

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/save/local` | Save run to local JSON/YAML |
| `POST` | `/api/save/gist` | Save run to GitHub Gist |
| `GET` | `/api/history` | List all saved prompts |
| `GET` | `/api/history/{id}/versions` | Get full version chain |
| `GET` | `/api/history/{id1}/diff?compare={id2}` | Diff two saved prompts |
| `GET` | `/api/share/{id}` | Read-only shareable snapshot |

### Collaboration

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/history/{run_id}/comments` | Add a comment to a run |
| `GET` | `/api/history/{run_id}/comments` | List comments |
| `POST` | `/api/templates` | Create a reusable template |
| `GET` | `/api/templates` | List all templates |
| `POST` | `/api/projects` | Create a project |
| `GET` | `/api/projects` | List all projects |

### Workflow

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/batch` | Run prompt across multiple providers |
| `POST` | `/api/chain` | Sequential prompt chain with output piping |

### Safety

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/guardrails` | List all guardrails with metadata |

---

## Guardrail Pipeline

```
INPUT
  │
  ├─ Custom PII patterns      (opt-in)
  ├─ PII scanner              (API keys, emails, SSNs — default ON)
  ├─ Injection guard          (regex patterns — default ON)
  ├─ Semantic injection guard (paraphrase jailbreaks — opt-in)
  ├─ Content policy           (topic blocklist — opt-in)
  └─ Token limiter            (truncates to budget — default ON)
         │
        LLM
         │
OUTPUT
  ├─ PII output scan          (default ON)
  ├─ Bypass detector          (default ON)
  ├─ Hallucination guard      (default ON)
  └─ JSON schema validator    (opt-in)
```

---

## Running Tests

```bash
# Full suite with coverage
pytest tests/ -v --cov=promptforge --cov-report=term-missing --cov-fail-under=80

# Lint
ruff check promptforge/ tests/ --fix --ignore E501

# Type check
mypy promptforge/ --ignore-missing-imports
```

**Current:** 197 passed · 3 skipped · 0 failed · **80.93% coverage**

---

## Project Structure

```
Prompt-Forage/
├── promptforge/
│   ├── api/
│   │   ├── routes.py              # All 22 API endpoints
│   │   └── schemas.py             # Request/response schemas
│   ├── core/
│   │   ├── models.py              # Pydantic models
│   │   ├── prompt_builder.py      # System prompt generator
│   │   ├── scorer.py              # 0-100 quality scorer
│   │   └── context_extractor.py   # File upload handler
│   ├── guardrails/
│   │   ├── orchestrator.py        # Pipeline coordinator
│   │   ├── pii_scanner.py
│   │   ├── injection_guard.py
│   │   ├── semantic_injection.py  # Phase 4
│   │   ├── content_policy.py      # Phase 4
│   │   ├── schema_validator.py    # Phase 4
│   │   ├── hallucination_guard.py
│   │   └── token_limiter.py
│   ├── providers/
│   │   ├── ollama_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   └── factory.py
│   ├── storage/
│   │   ├── local_storage.py       # JSON/YAML + versions + comments
│   │   ├── gist_storage.py        # GitHub Gist
│   │   └── manager.py
│   └── config.py
├── frontend/
│   ├── index.html
│   └── static/
│       ├── app.js
│       └── style.css
├── tests/                         # 22 test files, 197 tests
├── requirements.txt
├── requirements-dev.txt
└── pytest.ini
```

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Add your changes with tests
4. Run checks: `pytest && ruff check . && mypy promptforge/`
5. Open a pull request

All PRs welcome — bug fixes, new guardrails, new providers, UI improvements.

---

## Roadmap (v0.3.0)

- [ ] Cursor prompt generator mode
- [ ] Multi-turn conversation support
- [ ] Prompt marketplace / community templates
- [ ] RAG context injection from local documents
- [ ] Analytics dashboard (score trends over time)
- [ ] Docker one-command setup

---

## License

MIT — free to use, modify, and distribute.

---

Built with ❤️ by [SRIKALYAN03](https://github.com/SRIKALYAN03)
