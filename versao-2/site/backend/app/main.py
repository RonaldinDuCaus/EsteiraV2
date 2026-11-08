from __future__ import annotations

import io
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

from .config import PROJECT_ROOT, settings, validate_production_settings
from .database import db
from .security import create_session, hash_password, read_session, verify_password


FRONTEND_DIR = PROJECT_ROOT / "frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"
settings.upload_dir.mkdir(parents=True, exist_ok=True)


def image_url(filename: str | None) -> str | None:
    return f"/uploads/{filename}" if filename else None


def validate_image(data: bytes) -> str:
    if not data:
        raise HTTPException(400, "A imagem está vazia.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"A imagem ultrapassa {settings.max_upload_mb} MB.")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            image_format = (image.format or "JPEG").lower()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "O arquivo enviado não é uma imagem válida.")
    return {"jpeg": "jpg", "png": "png", "webp": "webp"}.get(image_format, "jpg")


def save_image(data: bytes, extension: str) -> str:
    filename = f"{uuid4().hex}.{extension}"
    (settings.upload_dir / filename).write_bytes(data)
    return filename


def seed_admin() -> None:
    with db.connection() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE username = %s", (settings.admin_username,)
        ).fetchone()
        if not user:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (settings.admin_username, hash_password(settings.admin_password)),
            )


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    db.open()
    seed_admin()
    yield
    db.close()


app = FastAPI(
    title="Mini Fábrica Inteligente",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


class LoginInput(BaseModel):
    username: str
    password: str


class EventInput(BaseModel):
    component_id: int | None = None
    detected_name: str | None = None
    confidence: float | None = None
    status: str = "recognized"
    image_filename: str | None = None
    device_id: str | None = None


def current_user(request: Request) -> dict:
    token = request.cookies.get("minifabrica_session")
    user_id = read_session(token or "", settings.session_secret)
    if not user_id:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    with db.connection() as conn:
        user = conn.execute(
            "SELECT id, username FROM users WHERE id = %s AND active = TRUE", (user_id,)
        ).fetchone()
    if not user:
        raise HTTPException(401, "Usuário não encontrado.")
    return user


def require_device(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.device_api_token}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(401, "Token do dispositivo inválido.")


@app.get("/", include_in_schema=False)
def site() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(ASSETS_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/uploads/{filename}", include_in_schema=False)
def protected_upload(filename: str, _: dict = Depends(current_user)) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(400, "Nome de arquivo inválido.")
    target = settings.upload_dir / filename
    if not target.is_file():
        raise HTTPException(404, "Imagem não encontrada.")
    return FileResponse(target)


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "service": "minifabrica"}


@app.post("/api/v1/auth/login")
def login(payload: LoginInput, response: Response) -> dict:
    with db.connection() as conn:
        user = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = %s AND active = TRUE",
            (payload.username.strip(),),
        ).fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Usuário ou senha incorretos.")
    response.set_cookie(
        "minifabrica_session",
        create_session(user["id"], settings.session_secret),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=12 * 3600,
    )
    return {"id": user["id"], "username": user["username"]}


@app.post("/api/v1/auth/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("minifabrica_session")
    return {"ok": True}


@app.get("/api/v1/auth/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user


@app.get("/api/v1/dashboard")
def dashboard(_: dict = Depends(current_user)) -> dict:
    with db.connection() as conn:
        summary = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM components WHERE active = TRUE) AS active_components,
                (SELECT COUNT(*) FROM recognition_events WHERE created_at::date = CURRENT_DATE) AS events_today,
                (SELECT COUNT(*) FROM recognition_events WHERE status = 'unknown' AND created_at::date = CURRENT_DATE) AS unknown_today
            """
        ).fetchone()
        latest = conn.execute(
            """
            SELECT id, detected_name, confidence, status, image_filename, device_id, created_at
            FROM recognition_events ORDER BY created_at DESC LIMIT 1
            """
        ).fetchone()
    if latest:
        latest = dict(latest)
        latest["image_url"] = image_url(latest.pop("image_filename"))
    return {
        "summary": summary,
        "latest": latest,
        "devices": {"esp32": "awaiting", "camera": "awaiting"},
    }


@app.get("/api/v1/components")
def list_components(_: dict = Depends(current_user)) -> list[dict]:
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.category, c.code, c.active, c.created_at,
                   (SELECT ci.filename FROM component_images ci WHERE ci.component_id = c.id ORDER BY ci.id LIMIT 1) AS image_filename,
                   (SELECT COUNT(*) FROM component_images ci WHERE ci.component_id = c.id) AS image_count
            FROM components c ORDER BY c.created_at DESC
            """
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["image_url"] = image_url(item.pop("image_filename"))
        result.append(item)
    return result


@app.post("/api/v1/components", status_code=201)
async def create_component(
    name: str = Form(...),
    category: str = Form(""),
    code: str = Form(""),
    images: list[UploadFile] = File(...),
    _: dict = Depends(current_user),
) -> dict:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(400, "Informe o nome do componente.")
    if not images or len(images) > 10:
        raise HTTPException(400, "Envie entre 1 e 10 imagens.")

    saved: list[tuple[str, str | None, str | None]] = []
    try:
        for upload in images:
            data = await upload.read()
            extension = validate_image(data)
            filename = save_image(data, extension)
            saved.append((filename, upload.filename, upload.content_type))

        with db.connection() as conn:
            component = conn.execute(
                "INSERT INTO components (name, category, code) VALUES (%s, %s, %s) RETURNING id, name",
                (clean_name, category.strip() or None, code.strip() or None),
            ).fetchone()
            for filename, original_name, content_type in saved:
                conn.execute(
                    """
                    INSERT INTO component_images (component_id, filename, original_name, content_type)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (component["id"], filename, original_name, content_type),
                )
        return {"id": component["id"], "name": component["name"], "images": len(saved)}
    except Exception:
        for filename, _, _ in saved:
            (settings.upload_dir / filename).unlink(missing_ok=True)
        raise


@app.patch("/api/v1/components/{component_id}/status")
def change_component_status(
    component_id: int,
    active: bool,
    _: dict = Depends(current_user),
) -> dict:
    with db.connection() as conn:
        row = conn.execute(
            "UPDATE components SET active = %s WHERE id = %s RETURNING id, active",
            (active, component_id),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Componente não encontrado.")
    return row


@app.get("/api/v1/events")
def list_events(limit: int = 50, _: dict = Depends(current_user)) -> list[dict]:
    safe_limit = min(max(limit, 1), 200)
    with db.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, component_id, detected_name, confidence, status, image_filename, device_id, created_at
            FROM recognition_events ORDER BY created_at DESC LIMIT %s
            """,
            (safe_limit,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["image_url"] = image_url(item.pop("image_filename"))
        result.append(item)
    return result


@app.post("/api/v1/events", status_code=201, dependencies=[Depends(require_device)])
def create_event(payload: EventInput) -> dict:
    with db.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO recognition_events
                (component_id, detected_name, confidence, status, image_filename, device_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (
                payload.component_id,
                payload.detected_name,
                payload.confidence,
                payload.status,
                payload.image_filename,
                payload.device_id,
            ),
        ).fetchone()
    return row


@app.post("/api/v1/captures", status_code=202, dependencies=[Depends(require_device)])
async def receive_capture(request: Request, x_device_id: str = Header(default="esp32-cam")) -> dict:
    data = await request.body()
    extension = validate_image(data)
    filename = save_image(data, extension)
    with db.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO recognition_events (detected_name, status, image_filename, device_id)
            VALUES ('Processamento pendente', 'pending', %s, %s)
            RETURNING id, created_at
            """,
            (filename, x_device_id),
        ).fetchone()
    return {"event_id": row["id"], "status": "pending", "created_at": row["created_at"]}
