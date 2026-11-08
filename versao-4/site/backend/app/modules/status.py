from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..database import db
from ..factory import factory_status
from .auth import current_user
from .images import image_url

router = APIRouter(tags=["Painel e módulos"])


@router.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "minifabrica", "version": "0.4.0"}


@router.get("/api/v1/public/info")
def public_info():
    return {"name": "Mini Fábrica Inteligente", "description": "Identificação de componentes eletrônicos com esteira e visão computacional.",
            "public_base_url": settings.public_base_url, "panel_path": "/painel", "version": "0.4.0"}


@router.get("/api/v1/system/modules", dependencies=[Depends(current_user)])
def modules():
    return {"modules": [
        {"id": "auth", "name": "Acesso administrativo", "enabled": True},
        {"id": "catalog", "name": "Catálogo e referências", "enabled": True},
        {"id": "history", "name": "Histórico", "enabled": True},
        {"id": "factory", "name": "Esteira e captura", "enabled": True},
        {"id": "recognition", "name": "Reconhecimento YOLOv8", "enabled": True},
    ]}


@router.get("/api/v1/recognition/status", dependencies=[Depends(current_user)])
def recognition_status():
    return {"ai": factory_status()["ai"], "requires_trained_model": True, "automatic_training": False}


@router.get("/api/v1/dashboard", dependencies=[Depends(current_user)])
def dashboard():
    with db.connection() as conn:
        summary = conn.execute("""SELECT
            (SELECT COUNT(*) FROM components WHERE active=TRUE) AS active_components,
            (SELECT COUNT(*) FROM factory_cycles WHERE status IN ('recognized','unknown')
             AND (created_at AT TIME ZONE 'America/Sao_Paulo')::date=(NOW() AT TIME ZONE 'America/Sao_Paulo')::date) AS events_today,
            (SELECT COUNT(*) FROM factory_cycles WHERE status='unknown'
             AND (created_at AT TIME ZONE 'America/Sao_Paulo')::date=(NOW() AT TIME ZONE 'America/Sao_Paulo')::date) AS unknown_today""").fetchone()
        latest = conn.execute("""SELECT id,detected_name,confidence,status,image_filename,device_id,created_at
            FROM recognition_events ORDER BY created_at DESC LIMIT 1""").fetchone()
    if latest:
        latest = dict(latest)
        latest["image_url"] = image_url(latest.pop("image_filename"))
    factory = factory_status()
    return {"summary": summary, "latest": latest,
            "devices": {"esp32": "online" if factory["motor"]["online"] else "offline",
                        "camera": "online" if factory["camera"]["online"] else "offline"}}


@router.post("/api/v1/events", status_code=410)
def blocked_legacy_event():
    raise HTTPException(410, "Resultados são produzidos apenas pelo worker; use o protocolo de eventos físicos.")


@router.post("/api/v1/captures", status_code=410)
def blocked_legacy_capture():
    raise HTTPException(410, "Envie a imagem ao pedido reservado em /api/v1/devices/camera/captures/{id}.")
