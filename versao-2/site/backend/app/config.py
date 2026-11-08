import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://minifabrica:minifabrica@localhost:5432/minifabrica",
    )
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "altere-esta-senha")
    session_secret: str = os.getenv("SESSION_SECRET", "altere-este-segredo")
    device_api_token: str = os.getenv("DEVICE_API_TOKEN", "altere-este-token")
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", PROJECT_ROOT / "data" / "uploads"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "8"))


settings = Settings()


def validate_production_settings() -> None:
    if settings.app_env != "production":
        return
    secrets_to_check = {
        "ADMIN_PASSWORD": settings.admin_password,
        "SESSION_SECRET": settings.session_secret,
        "DEVICE_API_TOKEN": settings.device_api_token,
    }
    invalid = [name for name, value in secrets_to_check.items() if len(value) < 16 or "altere" in value or "troque" in value]
    if invalid:
        raise RuntimeError(f"Configurações inseguras no .env: {', '.join(invalid)}")
