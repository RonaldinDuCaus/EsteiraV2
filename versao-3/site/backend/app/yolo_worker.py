"""Processo separado: python -m backend.app.yolo_worker.

Nenhum peso genérico é baixado automaticamente. Somente modelo local treinado,
mapa explícito e componente ativo podem resultar em reconhecimento.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from uuid import uuid4

from .config import settings, validate_production_settings
from .database import db
from .factory import _expire, _finish
from .factory_policy import choose_detection, utcnow


logger = logging.getLogger("minifabrica.yolo")


class YoloRecognizer:
    def __init__(self):
        if not settings.yolo_model_path.is_file():
            raise RuntimeError("Modelo YOLOv8 local não encontrado; instalar best.pt treinado")
        if not settings.yolo_class_map_path.is_file():
            raise RuntimeError("Mapa de classes YOLO não encontrado")
        mapping = json.loads(settings.yolo_class_map_path.read_text(encoding="utf-8"))
        if not isinstance(mapping, dict) or not mapping or any(not isinstance(k, str) or not isinstance(v, int) or isinstance(v, bool) or v < 1 for k, v in mapping.items()):
            raise RuntimeError("Mapa deve ser objeto JSON não vazio: nome da classe -> ID inteiro do componente")
        if not 0 < settings.yolo_confidence <= 1:
            raise RuntimeError("YOLO_CONFIDENCE deve estar entre 0 e 1")
        from ultralytics import YOLO  # Dependências pesadas ficam fora do processo da API.
        self.model = YOLO(str(settings.yolo_model_path))
        if self.model.task != "detect":
            raise RuntimeError("Esta versão exige um modelo de detecção YOLOv8, não classificação/segmentação")
        self.class_map = mapping
        if not set(mapping).issubset(set(self.model.names.values())):
            raise RuntimeError("Mapa contém classes ausentes no modelo treinado")

    def infer(self, path, active_components):
        results = self.model.predict(source=str(path), device=settings.yolo_device,
                                     imgsz=settings.yolo_image_size, conf=0.05, verbose=False, save=False)
        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                detections.append({"class_name": result.names[int(box.cls.item())], "confidence": float(box.conf.item())})
        return choose_detection(detections, self.class_map, active_components, settings.yolo_confidence)


def claim_job():
    with db.connection() as conn:
        _expire(conn)
        row = conn.execute("""SELECT * FROM factory_cycles WHERE status='processing' AND worker_token IS NULL
            AND completed=FALSE AND deadline>clock_timestamp() ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
        if not row:
            return None
        return conn.execute("UPDATE factory_cycles SET worker_token=%s WHERE id=%s RETURNING *", (str(uuid4()), row["id"])).fetchone()


def finish_job(job, result):
    with db.connection() as conn:
        _expire(conn)
        motor = conn.execute("SELECT * FROM factory_devices WHERE id=%s FOR UPDATE", (job["device_id"],)).fetchone()
        cycle = conn.execute("SELECT * FROM factory_cycles WHERE id=%s FOR UPDATE", (job["id"],)).fetchone()
        if not cycle or cycle["status"] != "processing" or cycle["completed"] or cycle["worker_token"] != job["worker_token"] or cycle["deadline"] <= utcnow():
            return False
        if not motor or motor["boot_id"] != cycle["boot_id"] or not motor["authorized"]:
            _finish(conn, cycle, "cancelled", "Autorização/boot mudou durante a análise")
            return False
        if result["status"] == "recognized":
            component = conn.execute("SELECT id,name FROM components WHERE id=%s AND active=TRUE", (result["component_id"],)).fetchone()
            if not component:
                result = {"status": "unknown", "reason": "Componente desativado ou removido durante análise"}
            else:
                result["component_name"] = component["name"]
        _finish(conn, cycle, result["status"], result["reason"], result.get("component_id"),
                result.get("component_name"), result.get("confidence"))
        return True


def heartbeat(stop, state):
    while not stop.is_set():
        try:
            with db.connection() as conn:
                conn.execute("""INSERT INTO factory_worker_health(id,last_seen,status,reason,model_path)
                    VALUES (1,clock_timestamp(),%s,%s,%s) ON CONFLICT(id) DO UPDATE SET
                    last_seen=clock_timestamp(),status=EXCLUDED.status,reason=EXCLUDED.reason,model_path=EXCLUDED.model_path""",
                    (state["status"], state["reason"], str(settings.yolo_model_path)))
                _expire(conn)
        except Exception:
            logger.exception("Falha no heartbeat do worker")
        stop.wait(2)


def main():
    logging.basicConfig(level=logging.INFO)
    validate_production_settings()
    db.open()
    state = {"status": "error", "reason": "Carregando modelo local"}
    stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(stop, state), daemon=True)
    thread.start()
    recognizer = None
    try:
        try:
            recognizer = YoloRecognizer()
            state.update(status="ready", reason=None)
        except Exception as exc:
            state.update(status="error", reason=str(exc)[:500])
            logger.error("YOLO indisponível: %s", exc)
        while True:
            try:
                job = claim_job()
                if not job:
                    time.sleep(0.4)
                    continue
                if recognizer is None:
                    result = {"status": "error", "reason": state["reason"] or "Modelo indisponível"}
                else:
                    with db.connection() as conn:
                        rows = conn.execute("SELECT id,name FROM components WHERE active=TRUE").fetchall()
                    components = {row["id"]: row for row in rows}
                    try:
                        result = recognizer.infer(settings.upload_dir / job["image_filename"], components)
                    except Exception as exc:
                        logger.exception("Falha na inferência")
                        result = {"status": "error", "reason": f"Falha técnica da análise: {type(exc).__name__}"}
                finish_job(job, result)
            except Exception:
                logger.exception("Erro no ciclo do worker; evento permanece sujeito ao timeout")
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        thread.join(timeout=3)
        db.close()


if __name__ == "__main__":
    main()
