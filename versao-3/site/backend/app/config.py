import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
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
    max_image_pixels: int = int(os.getenv("MAX_IMAGE_PIXELS", "12000000"))
    motor_api_token: str = os.getenv("MOTOR_API_TOKEN", "")
    camera_api_token: str = os.getenv("CAMERA_API_TOKEN", "")
    motor_device_id: str = os.getenv("MOTOR_DEVICE_ID", "esteira-01")
    camera_device_id: str = os.getenv("CAMERA_DEVICE_ID", "camera-01")
    device_online_seconds: int = int(os.getenv("DEVICE_ONLINE_SECONDS", "5"))
    command_ttl_seconds: int = int(os.getenv("COMMAND_TTL_SECONDS", "10"))
    capture_lease_seconds: int = int(os.getenv("CAPTURE_LEASE_SECONDS", "20"))
    cycle_timeout_seconds: int = int(os.getenv("CYCLE_TIMEOUT_SECONDS", "60"))
    yolo_model_path: Path = Path(os.getenv("YOLO_MODEL_PATH", PROJECT_ROOT / "models" / "best.pt"))
    yolo_class_map_path: Path = Path(os.getenv("YOLO_CLASS_MAP_PATH", PROJECT_ROOT / "models" / "classes.json"))
    yolo_device: str = os.getenv("YOLO_DEVICE", "cpu")
    yolo_confidence: float = float(os.getenv("YOLO_CONFIDENCE", "0.80"))
    yolo_image_size: int = int(os.getenv("YOLO_IMAGE_SIZE", "640"))


settings = Settings()


def validate_production_settings() -> None:
    if settings.app_env != "production":
        return
    secrets_to_check = {
        "ADMIN_PASSWORD": settings.admin_password,
        "SESSION_SECRET": settings.session_secret,
        "MOTOR_API_TOKEN": settings.motor_api_token,
        "CAMERA_API_TOKEN": settings.camera_api_token,
    }
    invalid = [name for name, value in secrets_to_check.items() if len(value) < 16 or "altere" in value or "troque" in value]
    if invalid:
        raise RuntimeError(f"Configurações inseguras no .env: {', '.join(invalid)}")
    if settings.motor_api_token == settings.camera_api_token:
        raise RuntimeError("Use credenciais distintas para motor e câmera.")
