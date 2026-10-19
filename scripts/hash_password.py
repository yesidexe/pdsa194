"""Genera el hash PBKDF2 de la contraseña del administrador.

Uso:
    ./venv/bin/python scripts/hash_password.py "mi-clave"

El resultado tiene el formato salt$hash. Cópialo en .env como
ADMIN_PASSWORD_HASH=... y elimina o comenta ADMIN_PASSWORD.
No toca la base de datos ni arranca la aplicación.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.security import hash_password  # noqa: E402


def main() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Contraseña: ")
    print(hash_password(password))


if __name__ == "__main__":
    main()
