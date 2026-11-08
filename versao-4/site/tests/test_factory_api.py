"""Testes de contrato/autorização sem acessar PostgreSQL ou equipamentos."""
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app import factory


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(factory, "settings", replace(factory.settings, motor_api_token="motor-test-token", camera_api_token="camera-test-token"))
    app = FastAPI()

    def admin():
        return {"id": 1}

    app.include_router(factory.build_router(admin))
    return TestClient(app)


def motor_payload():
    return {"boot_id": "boot-test-0001", "state": "disabled", "motor_on": False, "calibrated": False,
            "sensor_valid": True, "area_clear": True}


def test_motor_and_camera_tokens_are_separate(client, monkeypatch):
    monkeypatch.setattr(factory, "sync_motor", lambda payload: {"boot_id": payload.boot_id, "command": None, "event": None})
    assert client.post("/api/v1/devices/motor/sync", json=motor_payload()).status_code == 401
    assert client.post("/api/v1/devices/motor/sync", headers={"Authorization": "Bearer camera-test-token"}, json=motor_payload()).status_code == 401
    response = client.post("/api/v1/devices/motor/sync", headers={"Authorization": "Bearer motor-test-token"}, json=motor_payload())
    assert response.status_code == 200
    assert response.json()["boot_id"] == "boot-test-0001"


def test_camera_not_ready_is_passed_without_claiming_from_wrong_role(client, monkeypatch):
    seen = []
    monkeypatch.setattr(factory, "poll_camera", lambda payload: seen.append(payload.ready) or {"capture": None})
    headers = {"Authorization": "Bearer camera-test-token"}
    assert client.post("/api/v1/devices/camera/poll", headers=headers, json={"boot_id": "camera-boot", "ready": False}).json() == {"capture": None}
    assert seen == [False]


def test_admin_command_action_validation_and_cross_origin(client, monkeypatch):
    monkeypatch.setattr(factory, "queue_command", lambda action: {"requested": True, "command": {"action": action}})
    assert client.post("/api/v1/factory/commands", json={"action": "approve"}).status_code == 422
    assert client.post("/api/v1/factory/commands", headers={"Origin": "https://foreign.example"}, json={"action": "start"}).status_code == 403
    assert client.post("/api/v1/factory/commands", json={"action": "stop"}).json()["command"]["action"] == "stop"


def test_camera_upload_requires_lease_and_boot_headers(client, monkeypatch):
    headers = {"Authorization": "Bearer camera-test-token"}
    url = f"/api/v1/devices/camera/captures/{uuid4()}"
    assert client.post(url, headers=headers, content=b"image").status_code == 422
    monkeypatch.setattr(factory, "accept_capture", lambda *args: {"event_id": str(args[0]), "status": "processing", "duplicate": False})
    headers.update({"X-Capture-Lease": "lease", "X-Camera-Boot-ID": "camera-boot"})
    assert client.post(url, headers=headers, content=b"image").status_code == 202


def test_public_https_origin_behind_local_proxy(client, monkeypatch):
    monkeypatch.setattr(factory, "settings", replace(factory.settings, public_base_url="https://painel.example"))
    monkeypatch.setattr(factory, "queue_command", lambda action: {"requested": True})
    url = "/api/v1/factory/commands"
    assert client.post(url, headers={"Origin": "https://painel.example"}, json={"action": "stop"}).status_code == 202
    assert client.post(url, headers={"Origin": "http://testserver"}, json={"action": "start"}).status_code == 403
