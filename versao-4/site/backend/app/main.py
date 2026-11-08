"""Composição da aplicação; regras ficam nos módulos internos e núcleo da fábrica."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import PROJECT_ROOT, settings, validate_production_settings
from .database import db
from .factory import build_router
from .modules import auth, catalog, pages, status


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    db.open()
    auth.seed_admin()
    try:
        yield
    finally:
        db.close()


app = FastAPI(title="Mini Fábrica Inteligente", version="0.4.0", lifespan=lifespan,
              docs_url="/api/docs", redoc_url=None)
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "frontend" / "assets"), name="assets")
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(status.router)
app.include_router(build_router(auth.current_user))
