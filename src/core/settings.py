"""Configuración de entorno para la ejecución local de la plataforma.

Este módulo centraliza los valores que dependen del entorno (credenciales del
administrador, clave de firma de sesiones, base de datos y opciones de arranque).
La aplicación está pensada para ejecutarse en local con:

    python3 -m src.main

No se requieren variables de entorno obligatorias para la demo: si no existe un
archivo `.env`, se usan valores locales seguros por defecto. En un despliegue
real, todos estos valores deben venir de un gestor de secretos.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Carga un archivo .env sencillo sin dependencias externas.

    Se respetan las variables ya definidas en el proceso, de modo que las
    pruebas o un despliegue puedan sobrescribirlas sin tocar el archivo.
    """
    if not path.exists():
        return
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        # La configuración por variables de entorno sigue siendo válida.
        pass


_load_env_file()

APP_ENV = os.getenv("APP_ENV", "local").strip().lower()
ADMIN_USER = os.getenv("ADMIN_USER", "admin").strip() or "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "").strip() or None
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
SESSION_COOKIE_NAME = "evoting_admin_session"
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", str(8 * 3600)))

AUTO_OPEN_POLLS = os.getenv("AUTO_OPEN_POLLS", "true").strip().lower() in {"1", "true", "yes", "si", "sí"}
DEV_RELOAD = os.getenv("DEV_RELOAD", "false").strip().lower() in {"1", "true", "yes", "si", "sí"}
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'e_voting.db'}")
