"""Integração PostgreSQL real, opt-in e restrita a banco cujo nome termina em _test.

FACTORY_TEST_DATABASE_URL=postgresql://.../minifabrica_v3_test python -m pytest tests/test_factory_postgres.py
O banco dedicado é limpo entre ensaios; nunca apontar para uma instalação real.
YOLO é substituído apenas no ponto de resultado: inferência real requer pesos do usuário.
"""
from dataclasses import replace
from datetime import timedelta
from io import BytesIO
import os
from urllib.parse import urlparse

import pytest
from PIL import Image
from fastapi import HTTPException

from backend.app import database, factory, yolo_worker
from backend.app.factory import CameraPoll, MotorSync
from backend.app.factory_policy import utcnow


@pytest.fixture
def pg(monkeypatch, tmp_path):
    url = os.getenv("FACTORY_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina FACTORY_TEST_DATABASE_URL para integração PostgreSQL real")
    if not urlparse(url).path.rstrip("/").endswith("_test"):
        pytest.fail("Banco de integração precisa ter nome terminado em _test")
    config = replace(factory.settings, database_url=url, upload_dir=tmp_path,
                     motor_device_id="test-motor", camera_device_id="test-camera")
    monkeypatch.setattr(database, "settings", config)
    test_db = database.Database()
    test_db.open()
    monkeypatch.setattr(factory, "db", test_db)
    monkeypatch.setattr(factory, "settings", config)
    monkeypatch.setattr(yolo_worker, "db", test_db)
    monkeypatch.setattr(yolo_worker, "settings", config)
    with test_db.connection() as conn:
        conn.execute("TRUNCATE factory_commands,factory_cycles,factory_devices,factory_device_boots,factory_worker_health,recognition_events,component_images,components,users RESTART IDENTITY CASCADE")
        conn.execute("INSERT INTO components(name) VALUES ('Capacitor')")
        conn.execute("INSERT INTO factory_worker_health(id,status,model_path) VALUES (1,'ready','test-only.pt')")
    factory.poll_camera(CameraPoll(boot_id="camera-boot-A", ready=True))
    yield test_db
    test_db.close()


def payload(**changes):
    data = dict(boot_id="motor-boot-A", state="disabled", motor_on=False, calibrated=False,
                sensor_valid=True, area_clear=False, distance_mm=96.2, baseline_mm=None)
    data.update(changes)
    return MotorSync(**data)


def enable_cycle():
    factory.sync_motor(payload())
    command = factory.queue_command("calibrate")["command"]
    factory.sync_motor(payload(calibrated=True, baseline_mm=96.2, area_clear=True,
                               ack_command_id=command["id"], ack_status="applied"))
    start = factory.queue_command("start")["command"]
    response = factory.sync_motor(payload(calibrated=True, baseline_mm=96.2, area_clear=True,
                                         state="moving", motor_on=True,
                                         ack_command_id=start["id"], ack_status="applied"))
    assert response["authorized"]


def create_cycle():
    return factory.sync_motor(payload(calibrated=True, baseline_mm=96.2,
                                      event_id="motor-boot-A-1", state="awaiting_analysis",
                                      distance_mm=60.0))["event"]


def photo_bytes(color="red"):
    output = BytesIO()
    Image.new("RGB", (64, 48), color).save(output, format="JPEG")
    return output.getvalue()


def reserve_and_upload():
    capture = factory.poll_camera(CameraPoll(boot_id="camera-boot-A", ready=True))["capture"]
    result = factory.accept_capture(capture["id"], "camera-boot-A", capture["lease_token"], photo_bytes())
    assert result["status"] == "processing"
    return capture


def recognized():
    return {"status": "recognized", "reason": "Teste com saída simulada do detector",
            "component_id": 1, "component_name": "Capacitor", "confidence": 0.95}


def test_first_calibration_does_not_require_baseline_or_area_clear(pg):
    factory.sync_motor(payload())
    status = factory.factory_status()
    assert status["can_calibrate"]
    assert not status["can_start"]
    assert factory.queue_command("calibrate")["requested"]


def test_full_cycle_idempotence_and_matching_release(pg):
    enable_cycle()
    event = create_cycle()
    assert not event["approved"]
    assert create_cycle()["id"] == event["id"]
    capture = reserve_and_upload()
    duplicate = factory.accept_capture(capture["id"], "camera-boot-A", capture["lease_token"], photo_bytes())
    assert duplicate["duplicate"]
    with pytest.raises(HTTPException) as exc:
        factory.accept_capture(capture["id"], "camera-boot-A", capture["lease_token"], photo_bytes("blue"))
    assert exc.value.status_code == 409
    with pg.connection() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM recognition_events").fetchone()["n"] == 1
        assert conn.execute("SELECT COUNT(*) AS n FROM factory_cycles").fetchone()["n"] == 1
    job = yolo_worker.claim_job()
    assert yolo_worker.finish_job(job, recognized())
    response = factory.sync_motor(payload(calibrated=True, baseline_mm=96.2,
                                          event_id="motor-boot-A-1", state="awaiting_analysis", distance_mm=60))
    assert response["event"]["approved"]
    assert response["event"]["event_id"] == "motor-boot-A-1"
    completed = factory.sync_motor(payload(calibrated=True, baseline_mm=96.2, area_clear=True,
                                           event_id="motor-boot-A-1", completed_event_id="motor-boot-A-1", state="completing"))
    assert completed["completed_event_id"] == "motor-boot-A-1"
    assert not completed["event"]["approved"]
    assert not yolo_worker.finish_job(job, recognized())


def test_stop_revokes_permission_and_late_inference_is_discarded(pg):
    enable_cycle()
    create_cycle()
    reserve_and_upload()
    job = yolo_worker.claim_job()
    factory.queue_command("stop")
    assert not yolo_worker.finish_job(job, recognized())
    response = create_cycle()
    assert response["status"] == "cancelled"
    assert not response["approved"]


def test_reboot_retires_old_boot_and_old_packets_cannot_reactivate_it(pg):
    enable_cycle()
    create_cycle()
    response = factory.sync_motor(payload(boot_id="motor-boot-B"))
    assert not response["authorized"]
    with pytest.raises(HTTPException) as exc:
        factory.sync_motor(payload())
    assert exc.value.status_code == 409


def test_expired_command_ack_is_received_but_never_authorizes(pg):
    factory.sync_motor(payload(calibrated=True, area_clear=True, baseline_mm=96.2))
    command = factory.queue_command("start")["command"]
    with pg.connection() as conn:
        conn.execute("UPDATE factory_commands SET expires_at=NOW()-INTERVAL '1 second' WHERE id=%s", (command["id"],))
    response = factory.sync_motor(payload(calibrated=True, area_clear=True, baseline_mm=96.2,
                                          ack_command_id=command["id"], ack_status="applied"))
    assert response["acknowledged_command_id"] == command["id"]
    assert not response["authorized"]


def test_expired_analysis_does_not_approve_and_unknown_cannot_be_started_over(pg):
    enable_cycle()
    create_cycle()
    reserve_and_upload()
    job = yolo_worker.claim_job()
    with pg.connection() as conn:
        conn.execute("UPDATE factory_cycles SET deadline=NOW()-INTERVAL '1 second' WHERE id=%s", (job["id"],))
    assert not yolo_worker.finish_job(job, recognized())
    event = create_cycle()
    assert event["status"] == "error"
    assert not event["approved"]
    factory.sync_motor(payload(calibrated=True, area_clear=True, baseline_mm=96.2, state="review"))
    with pytest.raises(HTTPException):
        factory.queue_command("start")


def test_inactive_component_at_finish_is_unknown(pg):
    enable_cycle()
    create_cycle()
    reserve_and_upload()
    job = yolo_worker.claim_job()
    with pg.connection() as conn:
        conn.execute("UPDATE components SET active=FALSE WHERE id=1")
    assert yolo_worker.finish_job(job, recognized())
    event = create_cycle()
    assert event["status"] == "unknown"
    assert not event["approved"]


def test_camera_failure_and_not_ready_never_produce_approval(pg):
    enable_cycle()
    create_cycle()
    assert factory.poll_camera(CameraPoll(boot_id="camera-boot-A", ready=False))["capture"] is None
    capture = factory.poll_camera(CameraPoll(boot_id="camera-boot-A", ready=True))["capture"]
    factory.fail_capture(capture["id"], factory.CaptureFailure(boot_id="camera-boot-A", lease_token=capture["lease_token"], reason="Sem framebuffer"))
    assert create_cycle()["status"] == "error"
    assert not create_cycle()["approved"]


def test_fault_before_first_event_registration_still_receives_stop_and_can_recover(pg):
    enable_cycle()
    response = factory.sync_motor(payload(state="fault", event_id="motor-boot-A-1", sensor_valid=False))
    assert response["event"]["status"] == "cancelled"
    assert not response["event"]["approved"]
    assert not response["authorized"]
    assert factory.sync_motor(payload(state="fault", event_id="motor-boot-A-1", sensor_valid=False))["event"]["id"] == response["event"]["id"]
    stop = factory.queue_command("stop")["command"]
    response = factory.sync_motor(payload(state="fault", event_id="motor-boot-A-1"))
    assert response["command"]["id"] == stop["id"]


def test_conflicting_new_event_is_terminal_without_interrupting_sync(pg):
    enable_cycle()
    first = create_cycle()
    response = factory.sync_motor(payload(calibrated=True, event_id="motor-boot-A-2", state="awaiting_analysis", distance_mm=60))
    assert response["event"]["status"] == "cancelled"
    assert not response["event"]["approved"]
    with pg.connection() as conn:
        open_cycles = conn.execute("SELECT id FROM factory_cycles WHERE completed=FALSE").fetchall()
    assert len(open_cycles) == 1
    assert str(open_cycles[0]["id"]) == first["id"]


def test_real_admin_session_and_dashboard_commands(pg, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import main
    from backend.app.modules import auth, catalog, status, images
    config = replace(factory.settings, admin_username="factory-test-admin", admin_password="test-admin-password",
                     session_secret="test-session-secret-only", cookie_secure=False)
    for module in (auth, catalog, status, images):
        monkeypatch.setattr(module, "settings", config)
        if hasattr(module, "db"):
            monkeypatch.setattr(module, "db", pg)
    auth.seed_admin()
    client = TestClient(main.app)
    assert client.get("/api/v1/factory/status").status_code == 401
    assert client.post("/api/v1/factory/commands", json={"action": "stop"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": config.admin_username, "password": "wrong"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": config.admin_username, "password": config.admin_password}).status_code == 200
    factory.sync_motor(payload())
    status = client.get("/api/v1/factory/status")
    assert status.status_code == 200
    assert status.json()["can_calibrate"]
    command = client.post("/api/v1/factory/commands", json={"action": "calibrate"})
    assert command.status_code == 202
    assert command.json()["command"]["status"] == "pending"
    assert client.get("/api/v1/dashboard").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/factory/status").status_code == 401


def test_stopping_after_recognition_revokes_release_without_erasing_classification(pg):
    enable_cycle()
    create_cycle()
    reserve_and_upload()
    job = yolo_worker.claim_job()
    assert yolo_worker.finish_job(job, recognized())
    factory.queue_command("stop")
    event = create_cycle()
    assert event["status"] == "recognized"
    assert not event["approved"]


@pytest.fixture
def admin_client(pg, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import main
    from backend.app.modules import auth, catalog, status, images
    config = replace(factory.settings, admin_username="factory-test-admin", admin_password="test-admin-password",
                     session_secret="test-session-secret-only", cookie_secure=False)
    for module in (auth, catalog, status, images):
        monkeypatch.setattr(module, "settings", config)
        if hasattr(module, "db"):
            monkeypatch.setattr(module, "db", pg)
    auth.seed_admin()
    client = TestClient(main.app)
    login = client.post("/api/v1/auth/login", json={"username": config.admin_username, "password": config.admin_password})
    assert login.status_code == 200
    return client


def test_catalog_reference_upload_inactivation_and_protected_photo(admin_client):
    client = admin_client
    created = client.post("/api/v1/components", data={"name": "Resistor cadastrado", "code": "1k"},
                          files={"images": ("resistor.jpg", photo_bytes(), "image/jpeg")})
    assert created.status_code == 201
    component_id = created.json()["id"]
    catalog = client.get("/api/v1/components").json()
    component = next(item for item in catalog if item["id"] == component_id)
    assert component["image_count"] == 1
    assert component["active"]
    assert client.get(component["image_url"]).status_code == 200
    assert client.patch(f"/api/v1/components/{component_id}/status?active=false").status_code == 200
    assert not next(item for item in client.get("/api/v1/components").json() if item["id"] == component_id)["active"]
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get(component["image_url"]).status_code == 401
    assert client.get("/api/v1/components").status_code == 401


def test_invalid_reference_does_not_create_component_or_file(admin_client, pg):
    before_files = set(factory.settings.upload_dir.iterdir())
    response = admin_client.post("/api/v1/components", data={"name": "Invalid"},
                                 files={"images": ("fake.jpg", b"not-an-image", "image/jpeg")})
    assert response.status_code == 400
    with pg.connection() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM components WHERE name='Invalid'").fetchone()["n"] == 0
    assert set(factory.settings.upload_dir.iterdir()) == before_files


def test_inactive_user_cannot_keep_using_existing_session(admin_client, pg):
    with pg.connection() as conn:
        conn.execute("UPDATE users SET active=FALSE WHERE username='factory-test-admin'")
    assert admin_client.get("/api/v1/system/modules").status_code == 401
    assert admin_client.get("/api/v1/events").status_code == 401


def test_internal_modules_and_recognition_status_are_authenticated(admin_client):
    response = admin_client.get("/api/v1/system/modules")
    assert {module["id"] for module in response.json()["modules"]} == {"auth", "catalog", "history", "factory", "recognition"}
    assert admin_client.get("/api/v1/recognition/status").json()["automatic_training"] is False
    assert admin_client.post("/api/v1/auth/logout").status_code == 200
    assert admin_client.get("/api/v1/system/modules").status_code == 401
    assert admin_client.get("/api/v1/recognition/status").status_code == 401


def test_foreign_origin_cannot_modify_catalog_or_log_out(admin_client):
    headers = {"Origin": "https://foreign.example"}
    assert admin_client.post("/api/v1/auth/logout", headers=headers).status_code == 403
    assert admin_client.patch("/api/v1/components/1/status?active=false", headers=headers).status_code == 403
    assert admin_client.get("/api/v1/auth/me").status_code == 200
