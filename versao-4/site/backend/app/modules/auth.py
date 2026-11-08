from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..config import settings
from ..database import db
from ..security import create_session, hash_password, read_session, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["Acesso administrativo"])


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=512)


def same_origin(request: Request):
    origin = request.headers.get("origin")
    expected = settings.public_base_url or str(request.base_url).rstrip("/")
    if origin and origin.rstrip("/") != expected:
        raise HTTPException(403, "Origem administrativa inválida.")


def current_user(request: Request) -> dict:
    token = request.cookies.get("minifabrica_session")
    user_id = read_session(token or "", settings.session_secret) if settings.session_secret else None
    if not user_id:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    with db.connection() as conn:
        user = conn.execute("SELECT id,username FROM users WHERE id=%s AND active=TRUE", (user_id,)).fetchone()
    if not user:
        raise HTTPException(401, "Sessão inválida ou expirada.")
    return user


def seed_admin():
    if not settings.admin_password or not settings.session_secret:
        return
    with db.connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE username=%s", (settings.admin_username,)).fetchone()
        if not user:
            conn.execute("INSERT INTO users(username,password_hash) VALUES (%s,%s)",
                         (settings.admin_username, hash_password(settings.admin_password)))


@router.post("/login", dependencies=[Depends(same_origin)])
def login(payload: LoginInput, response: Response):
    if not settings.session_secret:
        raise HTTPException(503, "Acesso administrativo ainda não configurado.")
    with db.connection() as conn:
        user = conn.execute("SELECT id,username,password_hash FROM users WHERE username=%s AND active=TRUE",
                            (payload.username.strip(),)).fetchone()
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(401, "Usuário ou senha incorretos.")
    response.set_cookie("minifabrica_session", create_session(user["id"], settings.session_secret),
                        httponly=True, secure=settings.cookie_secure, samesite="lax", max_age=12 * 3600)
    return {"id": user["id"], "username": user["username"]}


@router.post("/logout", dependencies=[Depends(same_origin)])
def logout(response: Response):
    response.delete_cookie("minifabrica_session", secure=settings.cookie_secure, httponly=True, samesite="lax")
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
