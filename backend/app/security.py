import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import settings

PBKDF2_ITERATIONS = 120_000


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        iterations_text, salt_text, digest_text = stored_hash.split("$", 2)
        iterations = int(iterations_text)
        salt = _b64url_decode(salt_text)
        expected_digest = _b64url_decode(digest_text)
    except (TypeError, ValueError):
        return False

    candidate_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate_digest, expected_digest)


def create_access_token(*, subject: str, username: str, role: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": int(expires_at.timestamp()),
    }

    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    signature = hmac.new(
        settings.app_secret_key.encode("utf-8"), payload_segment.encode("ascii"), hashlib.sha256
    ).digest()
    return f"{payload_segment}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = hmac.new(
        settings.app_secret_key.encode("utf-8"), payload_segment.encode("ascii"), hashlib.sha256
    ).digest()

    try:
        provided_signature = _b64url_decode(signature_segment)
    except Exception:
        return None

    if not hmac.compare_digest(expected_signature, provided_signature):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_segment))
    except Exception:
        return None

    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None

    if datetime.now(UTC).timestamp() > exp:
        return None

    return payload