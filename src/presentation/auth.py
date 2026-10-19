"""Autenticación local del administrador.

La cuenta es única y se configura por variables de entorno (``ADMIN_USER`` y
``ADMIN_PASSWORD`` o ``ADMIN_PASSWORD_HASH``). La sesión se firma con HMAC y se
guarda en una cookie ``HttpOnly``; el JavaScript del panel no ve el token.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from src.core.settings import (
    ADMIN_PASSWORD,
    ADMIN_PASSWORD_HASH,
    ADMIN_USER,
    SECRET_KEY,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
)
from src.core.security import verify_password
from src.modules.security.access_proxy import UserRole, UserSession


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload: str) -> str:
    return _b64encode(hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest())


def create_session_token() -> str:
    """Crea un token firmado con vencimiento."""
    expires_at = int(time.time()) + SESSION_MAX_AGE_SECONDS
    payload = f"admin:{expires_at}"
    return f"{_b64encode(payload.encode('utf-8'))}.{_sign(payload)}"


def verify_session_token(token: Optional[str]) -> bool:
    """Verifica firma y vencimiento de la cookie de administrador."""
    if not token or "." not in token:
        return False
    encoded_payload, signature = token.split(".", 1)
    try:
        payload = _b64decode(encoded_payload).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    if not hmac.compare_digest(_sign(payload), signature):
        return False
    try:
        prefix, expires_raw = payload.split(":", 1)
        return prefix == "admin" and int(expires_raw) >= int(time.time())
    except (ValueError, IndexError):
        return False


def verify_admin_credentials(username: str, password: str) -> bool:
    """Comprueba usuario y contraseña de la cuenta administradora."""
    if not hmac.compare_digest(str(username).strip(), ADMIN_USER):
        return False
    if ADMIN_PASSWORD_HASH:
        return verify_password(str(password), ADMIN_PASSWORD_HASH)
    return hmac.compare_digest(str(password), ADMIN_PASSWORD)


def is_admin_request(request: Request) -> bool:
    """Indica si la petición trae una cookie de administrador válida."""
    return verify_session_token(request.cookies.get(SESSION_COOKIE_NAME))


def require_admin_session(request: Request) -> UserSession:
    """Dependencia de FastAPI para endpoints exclusivos del administrador."""
    if not is_admin_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere iniciar sesión como administrador.",
        )
    return UserSession(
        user_id=ADMIN_USER,
        role=UserRole.ADMINISTRADOR,
        session_token="cookie-session",
    )
