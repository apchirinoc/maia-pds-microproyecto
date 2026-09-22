"""Emisión y verificación de tokens de acceso."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, Exception):  # noqa: B014 - argon2 agrupa varias
        return False


def create_access_token(subject: str, *, claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expira,
        "iat": datetime.now(timezone.utc),
        **(claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
