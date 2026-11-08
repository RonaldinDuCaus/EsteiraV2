from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..config import PROJECT_ROOT
from .auth import current_user
from .images import image_path

FRONTEND_DIR = PROJECT_ROOT / "frontend"
router = APIRouter(tags=["Páginas"])


@router.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/painel", include_in_schema=False)
@router.get("/painel/", include_in_schema=False)
def panel():
    # Shell de login sem injeção de telemetria; as APIs exigem sessão.
    return FileResponse(FRONTEND_DIR / "painel.html")


@router.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse(FRONTEND_DIR / "assets" / "favicon.svg", media_type="image/svg+xml")


@router.get("/uploads/{filename}", include_in_schema=False, dependencies=[Depends(current_user)])
def protected_upload(filename: str):
    return FileResponse(image_path(filename))
