from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.app import config, main
from backend.app.modules import auth, pages, status


def test_public_home_and_panel_shell_do_not_read_private_operational_data(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<h1>Homepage pública</h1>", encoding="utf-8")
    (tmp_path / "painel.html").write_text('<form id="login-form">Entrar</form>', encoding="utf-8")
    monkeypatch.setattr(pages, "FRONTEND_DIR", tmp_path)
    monkeypatch.setattr(status, "factory_status", lambda: pytest.fail("Homepage não pode consultar telemetria"))
    client = TestClient(main.app)
    assert "Homepage pública" in client.get("/").text
    assert 'id="login-form"' in client.get("/painel").text
    assert client.get("/painel/").status_code == 200
    assert client.get("/api/v1/factory/status").status_code == 401
    assert client.get("/api/v1/dashboard").status_code == 401


def test_public_info_is_explicitly_allowlisted_and_never_contains_secrets(monkeypatch):
    configured = replace(status.settings, motor_api_token="private-motor-token-test", camera_api_token="private-camera-token-test",
                         session_secret="private-session-test", admin_password="private-admin-test")
    monkeypatch.setattr(status, "settings", configured)
    response = TestClient(main.app).get("/api/v1/public/info")
    assert response.status_code == 200
    assert set(response.json()) == {"name", "description", "public_base_url", "panel_path", "version"}
    assert "private-" not in response.text


def test_legacy_result_fabrication_endpoints_are_gone():
    client = TestClient(main.app)
    assert client.post("/api/v1/events", json={"status": "recognized", "component_id": 1}).status_code == 410
    assert client.post("/api/v1/captures", content=b"fake").status_code == 410


def test_no_configured_session_cannot_login_or_seed_default_admin(monkeypatch):
    monkeypatch.setattr(auth, "settings", replace(auth.settings, session_secret="", admin_password=""))
    monkeypatch.setattr(auth, "db", None)
    auth.seed_admin()  # Precisa retornar antes de acessar banco/criar conta padrão.
    assert TestClient(main.app).post("/api/v1/auth/login", json={"username": "admin", "password": "admin"}).status_code == 503


def test_production_requires_https_cookie_and_distinct_nonempty_credentials(monkeypatch):
    good = replace(config.settings, app_env="production", public_base_url="https://minifabrica.kronux.com.br",
                   admin_password="a" * 24, session_secret="b" * 32, motor_api_token="c" * 32,
                   camera_api_token="d" * 32, cookie_secure=True)
    monkeypatch.setattr(config, "settings", good)
    config.validate_production_settings()
    for changes in ({"admin_password": ""}, {"motor_api_token": ""}, {"session_secret": ""},
                    {"cookie_secure": False}, {"public_base_url": "http://minifabrica.kronux.com.br"},
                    {"camera_api_token": good.motor_api_token}):
        monkeypatch.setattr(config, "settings", replace(good, **changes))
        with pytest.raises(RuntimeError):
            config.validate_production_settings()
