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
from pathlib import Path

from src.api.router import router
from src.config import settings

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

# Serve UI static files
ui_dir = Path(__file__).resolve().parent.parent / "ui"
if ui_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")
