from __future__ import annotations

import hashlib
import io
import json
import secrets
from datetime import timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from .config import settings
from .database import db
from .factory_policy import FINAL_STATUSES, PENDING_STATUSES, can_approve, online, utcnow


class MotorSync(BaseModel):
    boot_id: str = Field(min_length=8, max_length=100)
    state: str = Field(max_length=60)
    motor_on: bool
    calibrated: bool
    sensor_valid: bool
    area_clear: bool
    baseline_mm: float | None = None
    distance_mm: float | None = None
    event_id: str | None = Field(default=None, max_length=160)
    completed_event_id: str | None = Field(default=None, max_length=160)
    ack_command_id: UUID | None = None
    ack_status: Literal["applied", "rejected"] | None = None
    ack_reason: str | None = Field(default=None, max_length=500)
    firmware_version: str | None = Field(default=None, max_length=80)


class CameraPoll(BaseModel):
    boot_id: str = Field(min_length=8, max_length=100)
    ready: bool
    firmware_version: str | None = Field(default=None, max_length=80)
    error: str | None = Field(default=None, max_length=500)


class CaptureFailure(BaseModel):
    boot_id: str = Field(min_length=8, max_length=100)
    lease_token: str = Field(max_length=100)
    reason: str = Field(min_length=1, max_length=500)


class CommandInput(BaseModel):
    action: Literal["calibrate", "start", "stop"]


def authenticate(role: str, authorization: str | None):
    configured = settings.motor_api_token if role == "motor" else settings.camera_api_token
    if not configured or not authorization or not secrets.compare_digest(authorization, f"Bearer {configured}"):
        raise HTTPException(401, "Credencial do dispositivo inválida ou não configurada.")


def require_motor(authorization: str | None = Header(default=None)):
    authenticate("motor", authorization)


def require_camera(authorization: str | None = Header(default=None)):
    authenticate("camera", authorization)


def _finish(conn, cycle, status, reason, component_id=None, component_name=None, confidence=None):
    conn.execute("""UPDATE factory_cycles SET status=%s, reason=%s, component_id=%s,
        component_name=%s, confidence=%s WHERE id=%s""",
        (status, reason, component_id, component_name, confidence, cycle["id"]))
    conn.execute("""UPDATE recognition_events SET status=%s, detected_name=%s, confidence=%s,
        component_id=%s WHERE id=%s""", (status if status != "cancelled" else "error",
        component_name or reason, confidence, component_id, cycle["recognition_event_id"]))


def _expire(conn):
    # Serializar apenas as transações curtas do protocolo, nunca a inferência.
    # Evita inversões de locks entre comandos, boots, leases e expirações.
    conn.execute("SELECT pg_advisory_xact_lock(681923004)")
    conn.execute("UPDATE factory_commands SET status='expired' WHERE status='pending' AND expires_at<=clock_timestamp()")
    rows = conn.execute("""SELECT * FROM factory_cycles WHERE status IN ('awaiting_capture','processing')
        AND deadline<=clock_timestamp()""").fetchall()
    for cycle in rows:
        # Mesma ordem de bloqueio do sync e do worker: motor antes do ciclo.
        conn.execute("SELECT id FROM factory_devices WHERE id=%s FOR UPDATE", (cycle["device_id"],))
        current = conn.execute("SELECT * FROM factory_cycles WHERE id=%s FOR UPDATE", (cycle["id"],)).fetchone()
        if current["status"] in PENDING_STATUSES and current["deadline"] <= utcnow():
            _finish(conn, current, "error", "Prazo de captura/análise expirado; conferência necessária")


def _device(conn, device_id):
    return conn.execute("SELECT * FROM factory_devices WHERE id=%s", (device_id,)).fetchone()


def _register(conn, device_id, role, boot_id, telemetry):
    old = conn.execute("SELECT * FROM factory_devices WHERE id=%s FOR UPDATE", (device_id,)).fetchone()
    recorded_boot = conn.execute("SELECT * FROM factory_device_boots WHERE device_id=%s AND boot_id=%s", (device_id, boot_id)).fetchone()
    if recorded_boot and recorded_boot["retired_at"]:
        raise HTTPException(409, "Inicialização aposentada; reinicie o dispositivo para uma nova sessão")
    if old and old["boot_id"] != boot_id:
        conn.execute("UPDATE factory_device_boots SET retired_at=clock_timestamp() WHERE device_id=%s AND boot_id=%s", (device_id, old["boot_id"]))
        conn.execute("UPDATE factory_commands SET status='superseded' WHERE device_id=%s AND status='pending'", (device_id,))
        if role == "motor":
            cycles = conn.execute("SELECT * FROM factory_cycles WHERE device_id=%s AND completed=FALSE FOR UPDATE", (device_id,)).fetchall()
            for cycle in cycles:
                if cycle["status"] in PENDING_STATUSES:
                    _finish(conn, cycle, "cancelled", "Inicialização do motor mudou; autorização anterior revogada")
                conn.execute("UPDATE factory_cycles SET completed=TRUE WHERE id=%s", (cycle["id"],))
        else:
            # Uma captura reservada em outro boot não pode ser recebida pelo boot novo.
            cycles = conn.execute("""SELECT * FROM factory_cycles WHERE camera_boot_id=%s
                AND status='awaiting_capture' FOR UPDATE""", (old["boot_id"],)).fetchall()
            for cycle in cycles:
                _finish(conn, cycle, "error", "Câmera reiniciou durante a captura")
        conn.execute("UPDATE factory_devices SET authorized=FALSE,last_ack_id=NULL WHERE id=%s", (device_id,))
    conn.execute("INSERT INTO factory_device_boots(device_id,boot_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (device_id, boot_id))
    conn.execute("""INSERT INTO factory_devices(id,role,boot_id,last_seen,telemetry)
        VALUES (%s,%s,%s,clock_timestamp(),%s::jsonb) ON CONFLICT(id) DO UPDATE SET
        boot_id=EXCLUDED.boot_id,last_seen=clock_timestamp(),telemetry=EXCLUDED.telemetry""",
        (device_id, role, boot_id, json.dumps(telemetry)))
    return _device(conn, device_id)


def _event_json(cycle, motor):
    if not cycle:
        return None
    return {"id": str(cycle["id"]), "event_id": cycle["event_id"], "boot_id": cycle["boot_id"],
            "status": cycle["status"], "approved": can_approve(cycle, motor),
            "reason": cycle["reason"], "component_id": cycle["component_id"],
            "component_name": cycle["component_name"], "confidence": cycle["confidence"],
            "image_url": f"/uploads/{cycle['image_filename']}" if cycle["image_filename"] else None,
            "created_at": cycle["created_at"]}


def _command_json(command):
    if not command:
        return None
    result = dict(command)
    result["id"] = str(result["id"])
    return result


def _conditions(conn, motor):
    telemetry = (motor or {}).get("telemetry", {})
    fresh = online(motor, settings.device_online_seconds)
    pending = conn.execute("""SELECT id FROM factory_cycles WHERE device_id=%s AND completed=FALSE
        AND status IN ('awaiting_capture','processing') LIMIT 1""", (settings.motor_device_id,)).fetchone()
    unresolved = conn.execute("SELECT id FROM factory_cycles WHERE device_id=%s AND completed=FALSE LIMIT 1",
                              (settings.motor_device_id,)).fetchone()
    inactive_states = {"disabled", "ready", "review", "fault"}
    stopped = fresh and telemetry.get("sensor_valid") and not telemetry.get("motor_on") and telemetry.get("state") in inactive_states
    safe = stopped and telemetry.get("area_clear")
    camera = _device(conn, settings.camera_device_id)
    ai = conn.execute("SELECT * FROM factory_worker_health WHERE id=1").fetchone()
    ai_ready = bool(ai and ai["status"] == "ready" and (utcnow() - ai["last_seen"]).total_seconds() <= 10)
    capture_ready = online(camera, settings.device_online_seconds) and camera["telemetry"].get("ready")
    can_calibrate = stopped and not pending and (not telemetry.get("calibrated") or telemetry.get("area_clear"))
    return bool(can_calibrate), bool(safe and telemetry.get("calibrated") and not unresolved and ai_ready and capture_ready)


def factory_status():
    with db.connection() as conn:
        _expire(conn)
        motor = _device(conn, settings.motor_device_id)
        camera = _device(conn, settings.camera_device_id)
        command = conn.execute("SELECT * FROM factory_commands WHERE device_id=%s ORDER BY created_at DESC LIMIT 1",
                               (settings.motor_device_id,)).fetchone()
        event = conn.execute("SELECT * FROM factory_cycles WHERE device_id=%s ORDER BY created_at DESC LIMIT 1",
                             (settings.motor_device_id,)).fetchone()
        worker = conn.execute("SELECT * FROM factory_worker_health WHERE id=1").fetchone()
        can_calibrate, can_start = _conditions(conn, motor)
    def serialize_device(device):
        return {"online": online(device, settings.device_online_seconds), "boot_id": device["boot_id"] if device else None,
                "last_seen": device["last_seen"] if device else None, "authorized": bool(device and device["authorized"]),
                "telemetry": device["telemetry"] if device else {}}
    return {"motor": serialize_device(motor), "camera": serialize_device(camera), "command": _command_json(command),
            "event": _event_json(event, motor), "can_calibrate": can_calibrate, "can_start": can_start,
            "ai": {"online": bool(worker and (utcnow()-worker["last_seen"]).total_seconds() <= 10),
                   "status": worker["status"] if worker else "awaiting", "reason": worker["reason"] if worker else "Worker ainda não iniciou",
                   "last_seen": worker["last_seen"] if worker else None, "model_path": str(settings.yolo_model_path)}}


def queue_command(action):
    with db.connection() as conn:
        _expire(conn)
        motor = conn.execute("SELECT * FROM factory_devices WHERE id=%s FOR UPDATE", (settings.motor_device_id,)).fetchone()
        can_calibrate, can_start = _conditions(conn, motor)
        if action == "calibrate" and not can_calibrate:
            raise HTTPException(409, "Calibração exige placa online, motor parado, área livre e nenhuma captura/análise pendente.")
        if action == "start" and not can_start:
            raise HTTPException(409, "Início exige calibração, área livre, câmera e IA prontas e nenhum evento pendente.")
        conn.execute("UPDATE factory_commands SET status='superseded' WHERE device_id=%s AND status='pending'", (settings.motor_device_id,))
        if action in {"stop", "calibrate"}:
            conn.execute("UPDATE factory_devices SET authorized=FALSE WHERE id=%s", (settings.motor_device_id,))
        if action == "stop":
            rows = conn.execute("SELECT * FROM factory_cycles WHERE device_id=%s AND completed=FALSE FOR UPDATE", (settings.motor_device_id,)).fetchall()
            for cycle in rows:
                if cycle["status"] in PENDING_STATUSES:
                    _finish(conn, cycle, "cancelled", "Parada solicitada pelo operador")
                conn.execute("UPDATE factory_cycles SET completed=TRUE WHERE id=%s", (cycle["id"],))
        command = conn.execute("""INSERT INTO factory_commands(id,device_id,boot_id,action,expires_at)
            VALUES (%s,%s,%s,%s,%s) RETURNING *""", (uuid4(), settings.motor_device_id,
            motor["boot_id"] if motor else "", action, utcnow()+timedelta(seconds=settings.command_ttl_seconds))).fetchone()
    return {"requested": True, "command": _command_json(command)}


def sync_motor(payload: MotorSync):
    now = utcnow()
    acknowledged_complete = None
    with db.connection() as conn:
        _expire(conn)
        now = utcnow()
        previous = _device(conn, settings.motor_device_id)
        previous_fault = bool(previous and previous["boot_id"] == payload.boot_id and "fault" in previous["telemetry"].get("state", "").lower())
        motor = _register(conn, settings.motor_device_id, "motor", payload.boot_id, payload.model_dump(mode="json"))
        if "fault" in payload.state.lower():
            conn.execute("UPDATE factory_devices SET authorized=FALSE WHERE id=%s", (settings.motor_device_id,))
            if not previous_fault:
                conn.execute("""UPDATE factory_commands SET status='superseded',ack_reason='Falha local revogou comando pendente'
                    WHERE device_id=%s AND status='pending' AND action IN ('start','calibrate')""", (settings.motor_device_id,))
        if payload.ack_command_id and payload.ack_status:
            command = conn.execute("SELECT * FROM factory_commands WHERE id=%s FOR UPDATE", (payload.ack_command_id,)).fetchone()
            if command and command["device_id"] == settings.motor_device_id and command["boot_id"] == payload.boot_id:
                # Confirmar o recebimento mesmo de ACK tardio: firmware vê authorized=false e para.
                conn.execute("UPDATE factory_devices SET last_ack_id=%s WHERE id=%s", (command["id"], settings.motor_device_id))
                if command["status"] == "pending" and command["expires_at"] > now:
                    accepted = payload.ack_status == "applied"
                    conn.execute("UPDATE factory_commands SET status=%s,ack_reason=%s WHERE id=%s",
                                 (payload.ack_status, payload.ack_reason, command["id"]))
                    if command["action"] == "start":
                        conn.execute("UPDATE factory_devices SET authorized=%s WHERE id=%s", (accepted, settings.motor_device_id))
                    elif accepted and command["action"] == "calibrate":
                        # O firmware só aceita calibrar com peça removida e fora de análise.
                        conn.execute("""UPDATE factory_cycles SET completed=TRUE WHERE device_id=%s AND boot_id=%s
                            AND status IN ('recognized','unknown','error','cancelled')""", (settings.motor_device_id, payload.boot_id))
        motor = _device(conn, settings.motor_device_id)
        if payload.completed_event_id:
            cycle = conn.execute("SELECT * FROM factory_cycles WHERE device_id=%s AND boot_id=%s AND event_id=%s FOR UPDATE",
                                 (settings.motor_device_id, payload.boot_id, payload.completed_event_id)).fetchone()
            if cycle and cycle["status"] in FINAL_STATUSES and payload.area_clear:
                conn.execute("UPDATE factory_cycles SET completed=TRUE WHERE id=%s", (cycle["id"],))
                acknowledged_complete = payload.completed_event_id
        cycle = None
        if payload.event_id:
            cycle = conn.execute("SELECT * FROM factory_cycles WHERE device_id=%s AND boot_id=%s AND event_id=%s FOR UPDATE",
                                 (settings.motor_device_id, payload.boot_id, payload.event_id)).fetchone()
            if not cycle:
                other = conn.execute("SELECT id FROM factory_cycles WHERE device_id=%s AND completed=FALSE LIMIT 1", (settings.motor_device_id,)).fetchone()
                blocked = not motor["authorized"] or payload.motor_on or not payload.sensor_valid or other
                reason = "Evento recebido sem condições de captura; não autoriza movimento" if blocked else None
                event = conn.execute("""INSERT INTO recognition_events(status,detected_name,device_id)
                    VALUES (%s,%s,%s) RETURNING id""", ("error" if blocked else "pending",
                    reason or "Aguardando captura", settings.motor_device_id)).fetchone()
                cycle = conn.execute("""INSERT INTO factory_cycles(id,device_id,boot_id,event_id,recognition_event_id,deadline,status,reason,completed)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""", (uuid4(), settings.motor_device_id, payload.boot_id,
                    payload.event_id, event["id"], now+timedelta(seconds=settings.cycle_timeout_seconds),
                    "cancelled" if blocked else "awaiting_capture", reason, bool(other))).fetchone()
        pending_command = conn.execute("""SELECT * FROM factory_commands WHERE device_id=%s AND boot_id=%s
            AND status='pending' AND expires_at>clock_timestamp() ORDER BY created_at DESC LIMIT 1""",
            (settings.motor_device_id, payload.boot_id)).fetchone()
        return {"server_time": utcnow(), "boot_id": payload.boot_id, "authorized": bool(motor["authorized"]), "command": _command_json(pending_command),
                "event": _event_json(cycle, motor), "completed_event_id": acknowledged_complete,
                "acknowledged_command_id": str(motor["last_ack_id"]) if motor["last_ack_id"] else None}


def poll_camera(payload: CameraPoll):
    now = utcnow()
    with db.connection() as conn:
        _expire(conn)
        now = utcnow()
        _register(conn, settings.camera_device_id, "camera", payload.boot_id, payload.model_dump())
        if not payload.ready:
            return {"capture": None, "server_time": utcnow()}
        # Um único slot por câmera, bloqueado no banco inclusive entre processos da API.
        conn.execute("SELECT id FROM factory_devices WHERE id=%s FOR UPDATE", (settings.camera_device_id,))
        expired = conn.execute("""SELECT * FROM factory_cycles WHERE status='awaiting_capture'
            AND lease_expires_at<=clock_timestamp() FOR UPDATE""").fetchall()
        for cycle in expired:
            _finish(conn, cycle, "error", "Reserva de captura expirou")
        cycle = conn.execute("""SELECT * FROM factory_cycles WHERE status='awaiting_capture'
            AND (lease_token IS NULL OR camera_boot_id=%s) AND deadline>clock_timestamp()
            ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED""", (payload.boot_id,)).fetchone()
        if not cycle:
            return {"capture": None, "server_time": utcnow()}
        if not cycle["lease_token"]:
            cycle = conn.execute("""UPDATE factory_cycles SET lease_token=%s,camera_boot_id=%s,lease_expires_at=%s
                WHERE id=%s RETURNING *""", (secrets.token_urlsafe(24), payload.boot_id,
                min(cycle["deadline"], now+timedelta(seconds=settings.capture_lease_seconds)), cycle["id"])).fetchone()
        return {"server_time": utcnow(), "capture": {"id": str(cycle["id"]), "event_id": str(cycle["id"]),
                "motor_boot_id": cycle["boot_id"], "lease_token": cycle["lease_token"], "expires_at": cycle["lease_expires_at"]}}


def _check_lease(cycle, boot_id, lease):
    if not cycle:
        raise HTTPException(404, "Pedido de captura não encontrado")
    if cycle["camera_boot_id"] != boot_id or not cycle["lease_token"] or not secrets.compare_digest(cycle["lease_token"], lease):
        raise HTTPException(409, "Reserva não pertence a esta captura/inicialização")


def accept_capture(capture_id, boot_id, lease, data):
    if not data or len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Imagem vazia ou acima do limite")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "JPEG" or image.width * image.height > settings.max_image_pixels:
                raise HTTPException(400, "Captura deve ser JPEG dentro do limite de resolução")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(400, "Imagem JPEG inválida")
    digest = hashlib.sha256(data).hexdigest()
    saved = None
    try:
        with db.connection() as conn:
            _expire(conn)
            cycle = conn.execute("SELECT * FROM factory_cycles WHERE id=%s FOR UPDATE", (capture_id,)).fetchone()
            _check_lease(cycle, boot_id, lease)
            conn.execute("UPDATE factory_devices SET last_seen=clock_timestamp() WHERE id=%s AND boot_id=%s", (settings.camera_device_id, boot_id))
            if cycle["image_sha256"]:
                if cycle["image_sha256"] != digest:
                    raise HTTPException(409, "Reenvio de captura com bytes diferentes")
                return {"event_id": str(cycle["id"]), "status": cycle["status"], "duplicate": True}
            if cycle["status"] != "awaiting_capture" or cycle["completed"] or cycle["deadline"] <= utcnow() or cycle["lease_expires_at"] <= utcnow():
                raise HTTPException(410, "Pedido cancelado ou expirado")
            filename = f"{cycle['id']}.jpg"
            saved = settings.upload_dir / filename
            saved.write_bytes(data)
            conn.execute("""UPDATE factory_cycles SET image_filename=%s,image_sha256=%s,status='processing',reason=NULL
                WHERE id=%s""", (filename, digest, capture_id))
            conn.execute("UPDATE recognition_events SET image_filename=%s,detected_name='Análise YOLO pendente' WHERE id=%s",
                         (filename, cycle["recognition_event_id"]))
        return {"event_id": str(capture_id), "status": "processing", "duplicate": False}
    except Exception:
        if saved:
            saved.unlink(missing_ok=True)
        raise


def fail_capture(capture_id, payload):
    with db.connection() as conn:
        _expire(conn)
        cycle = conn.execute("SELECT * FROM factory_cycles WHERE id=%s FOR UPDATE", (capture_id,)).fetchone()
        _check_lease(cycle, payload.boot_id, payload.lease_token)
        conn.execute("UPDATE factory_devices SET last_seen=clock_timestamp() WHERE id=%s AND boot_id=%s", (settings.camera_device_id, payload.boot_id))
        if cycle["status"] == "awaiting_capture":
            _finish(conn, cycle, "error", f"Falha da câmera: {payload.reason}")
    return {"ok": True}


def build_router(current_user):
    router = APIRouter()

    @router.get("/api/v1/factory/status", dependencies=[Depends(current_user)])
    def status_route():
        return factory_status()

    @router.post("/api/v1/factory/commands", status_code=202, dependencies=[Depends(current_user)])
    def command_route(payload: CommandInput, request: Request):
        # Cookie SameSite + restrição de Origin, quando o navegador o fornece.
        origin = request.headers.get("origin")
        expected_origin = settings.public_base_url or str(request.base_url).rstrip("/")
        if origin and origin.rstrip("/") != expected_origin:
            raise HTTPException(403, "Origem administrativa inválida")
        return queue_command(payload.action)

    @router.post("/api/v1/devices/motor/sync", dependencies=[Depends(require_motor)])
    def motor_route(payload: MotorSync):
        return sync_motor(payload)

    @router.post("/api/v1/devices/camera/poll", dependencies=[Depends(require_camera)])
    def camera_route(payload: CameraPoll):
        return poll_camera(payload)

    @router.post("/api/v1/devices/camera/captures/{capture_id}", status_code=202, dependencies=[Depends(require_camera)])
    async def capture_route(capture_id: UUID, request: Request,
                            x_capture_lease: str = Header(...), x_camera_boot_id: str = Header(...)):
        length = request.headers.get("content-length")
        if length:
            if not length.isdigit():
                raise HTTPException(400, "Content-Length inválido")
            if int(length) > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(413, "Imagem acima do limite")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                raise HTTPException(413, "Imagem acima do limite")
            chunks.append(chunk)
        return accept_capture(capture_id, x_camera_boot_id, x_capture_lease, b"".join(chunks))

    @router.post("/api/v1/devices/camera/captures/{capture_id}/failure", dependencies=[Depends(require_camera)])
    def failure_route(capture_id: UUID, payload: CaptureFailure):
        return fail_capture(capture_id, payload)

    return router
