"""Genera un hash PBKDF2 para la contraseña del administrador.

Uso:
    ./venv/bin/python scripts/hash_password.py "mi-clave"

Copia el resultado en .env como ADMIN_PASSWORD_HASH=... y elimina
ADMIN_PASSWORD del archivo.
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
