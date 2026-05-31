"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from promptforge.api.routes import router
from promptforge.config import get_settings

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="PromptForge",
    description="Open-source prompt engineering studio with guardrails",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if FRONTEND_DIR.exists():
    static_dir = FRONTEND_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    templates = Jinja2Templates(directory=str(FRONTEND_DIR))


@app.get("/")
async def serve_frontend(request: Request):
    """Serve the main frontend HTML page."""
    if not FRONTEND_DIR.exists():
        return {"message": "PromptForge API is running. Frontend not found."}
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "promptforge.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
