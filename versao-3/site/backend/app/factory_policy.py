"""Regras pequenas usadas tanto no protocolo quanto nos testes sem hardware."""
from datetime import datetime, timezone
from math import isfinite


FINAL_STATUSES = {"recognized", "unknown", "error", "cancelled"}
PENDING_STATUSES = {"awaiting_capture", "processing"}


def utcnow():
    return datetime.now(timezone.utc)


def online(device, seconds, now=None):
    if not device or not device.get("last_seen"):
        return False
    return ((now or utcnow()) - device["last_seen"]).total_seconds() <= seconds


def can_approve(cycle, device, now=None):
    """Uma autorização vale exclusivamente para o evento e boot que a originaram."""
    return bool(
        cycle and device and device.get("authorized")
        and cycle["status"] == "recognized" and not cycle.get("completed")
        and cycle["boot_id"] == device["boot_id"]
        and cycle["device_id"] == device["id"]
        and cycle["deadline"] > (now or utcnow())
    )


def choose_detection(detections, class_map, active_components, threshold):
    """Uma peça por captura: múltiplas caixas são ambiguidade, nunca aprovação."""
    if len(detections) != 1:
        return {"status": "unknown", "reason": "Nenhuma peça detectada" if not detections else "Mais de uma detecção; conferir a peça"}
    detection = detections[0]
    confidence = float(detection["confidence"])
    if not isfinite(confidence) or not 0 <= confidence <= 1:
        return {"status": "error", "reason": "Score YOLO inválido"}
    if confidence < threshold:
        return {"status": "unknown", "reason": "Score YOLO abaixo do limiar", "confidence": confidence}
    component_id = class_map.get(detection["class_name"])
    component = active_components.get(component_id)
    if not component:
        return {"status": "unknown", "reason": "Classe sem componente ativo associado", "confidence": confidence}
    return {"status": "recognized", "reason": "Classe treinada associada a componente ativo", "component_id": component_id,
            "component_name": component["name"], "confidence": confidence}
