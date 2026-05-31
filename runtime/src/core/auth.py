from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

from src.config import settings

SESSION_COOKIE_NAME = "fast_harness_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60


def authenticate_user(user_id: str, password: str) -> dict | None:
    try:
        user = settings.get_user(user_id)
    except ValueError:
        return None
    if not hmac.compare_digest(str(user.get("password", "")), password):
        return None
    return user


def create_session_token(user_id: str, now: int | None = None) -> str:
    issued_at = int(now or time.time())
    payload = {
        "user_id": user_id,
        "exp": issued_at + SESSION_TTL_SECONDS,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = _b64encode(payload_json)
    signature = _sign(encoded_payload.encode("ascii"))
    return f"{encoded_payload}.{signature}"


def verify_session_token(token: str | None, now: int | None = None) -> str | None:
    if not token or "." not in token:
        return None
    encoded_payload, signature = token.rsplit(".", 1)
    expected = _sign(encoded_payload.encode("ascii"))
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(encoded_payload))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(now or time.time()):
        return None
    user_id = str(payload.get("user_id", "")).strip()
    if not user_id:
        return None
    try:
        settings.get_user(user_id)
    except ValueError:
        return None
    return user_id


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "role": user.get("role", "member"),
        "enabled": bool(user.get("enabled", True)),
    }


def auth_secret() -> bytes:
    env_secret = getattr(settings, "auth_secret", "")
    if env_secret:
        return env_secret.encode("utf-8")

    seed = (
        str(Path(settings.workspace_root).resolve())
        + "|"
        + "|".join(f"{user['id']}:{user.get('password', '')}" for user in settings.enabled_users)
    )
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _sign(data: bytes) -> str:
    return _b64encode(hmac.new(auth_secret(), data, hashlib.sha256).digest())


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
