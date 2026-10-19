"""Deja la base local limpia y vuelve a sembrar el censo de demostración.

Uso:
    ./venv/bin/python scripts/reset_db.py

Borra votos, participaciones y censo; luego recrea las tablas y vuelve a
insertar el censo sintético. La base no queda vacía: queda sin votos, pero
con las personas de demostración. No toca archivos del proyecto.
Ejecútalo con la aplicación detenida.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.database import CitizenModel, SessionLocal, reset_database  # noqa: E402


def main() -> None:
    reset_database()
    session = SessionLocal()
    try:
        for election_type in ("NATIONAL", "UNIVERSITY"):
            total = session.query(CitizenModel).filter_by(election_type=election_type).count()
            eligible = (
                session.query(CitizenModel)
                .filter_by(election_type=election_type, is_eligible=True)
                .count()
            )
            print(f"{election_type}: {total} electores ({eligible} habilitados)")
    finally:
        session.close()
    print("Base reiniciada. PIN de demostración: 1234")


if __name__ == "__main__":
    main()
