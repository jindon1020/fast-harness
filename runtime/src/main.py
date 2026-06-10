"""
fast-harness runtime — Claude Code Agent SDK service.

Start with:
    uvicorn src.main:app --reload
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse, JSONResponse, FileResponse
from pathlib import Path

from src.api.router import router
from src.config import settings
from src.core.auth import SESSION_COOKIE_NAME, verify_session_token

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("fast-harness runtime starting on %s:%s", settings.host, settings.port)
    harness_path = settings.resolved_harness_path
    if harness_path.exists():
        logger.info("Harness plugin loaded from: %s", harness_path)
    else:
        logger.warning("Harness plugin path NOT found: %s", harness_path)
    logger.info("Workspace root: %s", settings.workspace_root)
    yield
    logger.info("fast-harness runtime shutting down")


app = FastAPI(
    title="fast-harness runtime",
    description="Claude Code Agent SDK 服务化运行时 — 集成了 fast-harness 的 command/subagent/skill 能力",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.middleware("http")
async def require_login(request, call_next):
    path = request.url.path
    if _is_public_path(path):
        return await call_next(request)

    user_id = verify_session_token(request.cookies.get(SESSION_COOKIE_NAME))
    if not user_id:
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)
        return RedirectResponse(url="/login", status_code=303)

    if _is_reporter_user(user_id):
        if path.startswith("/api/") and not _is_reporter_api_path(path):
            return JSONResponse({"detail": "Reporter role can only access bug-fix workflows"}, status_code=403)
        if not path.startswith("/api/") and not _is_reporter_page_path(path):
            return RedirectResponse(url="/bug-fix", status_code=303)

    headers = [
        (key, value)
        for key, value in request.scope.get("headers", [])
        if key.lower() != b"x-user-id"
    ]
    headers.append((b"x-user-id", user_id.encode("utf-8")))
    request.scope["headers"] = headers
    return await call_next(request)


def _is_public_path(path: str) -> bool:
    return (
        path in {"/login", "/login.html", "/api/login", "/api/logout", "/api/healthz"}
        or path.startswith("/api/users")
    )


def _is_reporter_user(user_id: str) -> bool:
    try:
        return settings.is_reporter(user_id)
    except ValueError:
        return False


def _is_reporter_page_path(path: str) -> bool:
    return path in {"/bug-fix", "/bug-fix/"} or path.startswith("/bug-fix/")


def _is_reporter_api_path(path: str) -> bool:
    if path in {"/api/me", "/api/logout"}:
        return True
    if path.startswith("/api/users") or path.startswith("/api/repositories"):
        return True
    if path.startswith("/api/bug-pipelines"):
        return True
    if path.startswith("/api/sessions/"):
        return True
    return False


@app.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse(Path(__file__).resolve().parent.parent / "ui" / "login.html")


@app.get("/bug-fix", include_in_schema=False)
async def bug_fix_page():
    return FileResponse(Path(__file__).resolve().parent.parent / "ui" / "bug-fix" / "index.html")

# Serve UI static files
ui_dir = Path(__file__).resolve().parent.parent / "ui"
if ui_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")
