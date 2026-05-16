from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet

from aac_backend.config import get_settings


def encrypt_secret_payload(payload: dict[str, Any]) -> str:
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(plaintext).decode("utf-8")


def decrypt_secret_payload(encrypted_payload: str) -> dict[str, Any]:
    plaintext = _fernet().decrypt(encrypted_payload.encode("utf-8"))
    value = json.loads(plaintext.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("secret payload is not an object")
    return value


def _fernet() -> Fernet:
    settings = get_settings()
    configured = settings.secret_encryption_key
    if configured:
        return Fernet(_normalise_key(configured))
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest())
    return Fernet(derived)


def _normalise_key(value: str) -> bytes:
    raw = value.encode("utf-8")
    try:
        Fernet(raw)
    except Exception:
        return base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return raw
