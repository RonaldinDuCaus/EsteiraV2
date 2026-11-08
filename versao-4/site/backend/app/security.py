import base64
import hashlib
import hmac
import os
import time


PBKDF2_ITERATIONS = 240_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(user_id: int, secret: str, hours: int = 12) -> str:
    payload = f"{user_id}:{int(time.time()) + hours * 3600}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()
    return token.rstrip("=")


def read_session(token: str, secret: str) -> int | None:
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode()).decode()
        user_id, expires, signature = decoded.split(":", 2)
        payload = f"{user_id}:{expires}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires) < int(time.time()):
            return None
        return int(user_id)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
