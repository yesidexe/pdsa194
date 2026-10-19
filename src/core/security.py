"""Utilidades de seguridad locales: PIN de elector y contraseña de administrador.

Se usan únicamente funciones de la biblioteca estándar para no añadir
dependencias en esta etapa. Para un despliegue real se recomienda Argon2id,
gestión de secretos y TLS.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Optional

_PIN_SALT = "e-voting-local-pin-v1"
_PASSWORD_ITERATIONS = 260_000


def hash_pin(pin: str) -> str:
    """Deriva una huella del PIN de demostración.

    El PIN es de 4 dígitos y se usa solo en el simulador local. En un sistema
    real se debe usar un secreto más fuerte y un KDF con sal por usuario.
    """
    payload = f"{_PIN_SALT}:{str(pin).strip()}".encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", payload, _PIN_SALT.encode("utf-8"), 120_000).hex()


def verify_pin(pin: str, stored_hash: Optional[str]) -> bool:
    """Compara en tiempo constante el PIN recibido con la huella almacenada."""
    if not stored_hash:
        return False
    return hmac.compare_digest(hash_pin(pin), str(stored_hash))


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Devuelve `salt$hash` con PBKDF2-SHA256 para la cuenta administradora."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt.encode("utf-8"),
        _PASSWORD_ITERATIONS,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: Optional[str]) -> bool:
    """Verifica una contraseña administradora contra el formato `salt$hash`."""
    if not stored_hash or "$" not in stored_hash:
        return False
    salt, expected = stored_hash.split("$", 1)
    candidate = hash_password(password, salt=salt).split("$", 1)[1]
    return hmac.compare_digest(candidate, expected)
