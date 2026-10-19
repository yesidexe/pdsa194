"""Persistencia relacional local (SQLite + SQLAlchemy).

Este módulo contiene las tres tablas que sostienen la jornada electoral:

1. ``census_citizens``: censo oficial (quién puede votar y con qué PIN).
2. ``voter_participation``: quién ya votó. No conoce la papeleta.
3. ``ballot_records``: qué se votó. No conoce al votante.

La separación entre las tablas 2 y 3 es deliberada: permite saber cuántos
votaron y qué se votó sin poder unir ambas cosas en una sola consulta.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from src.core.security import hash_pin
from src.core.settings import DATABASE_URL

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BASE_DIR / "e_voting.db"

# SQLite necesita check_same_thread=False para FastAPI, y un timeout razonable
# para que dos votos concurrentes no fallen con "database is locked".
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    echo=False,
)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()


class CitizenModel(Base):
    """Registro del censo electoral oficial."""

    __tablename__ = "census_citizens"
    __table_args__ = (
        UniqueConstraint("document_id", "election_type", name="uq_citizen_document_election"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    document_id = Column(String(50), index=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    assigned_station_id = Column(String(50), default="MESA-01", nullable=False)
    is_eligible = Column(Boolean, default=True, nullable=False)
    election_type = Column(String(20), default="NATIONAL", nullable=False, index=True)
    pin_hash = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return (
            f"<CitizenModel(doc='{self.document_id}', name='{self.full_name}', "
            f"eligible={self.is_eligible}, type='{self.election_type}')>"
        )


class VoterParticipationModel(Base):
    """Marca de participación: quién ya ejerció su voto en una elección.

    No guarda ballot_id ni selección. Es la única tabla que conoce el documento
    del votante en el flujo de emisión.
    """

    __tablename__ = "voter_participation"
    __table_args__ = (
        UniqueConstraint("election_type", "document_id", name="uq_participation_election_document"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    election_type = Column(String(20), nullable=False, index=True)
    document_id = Column(String(50), nullable=False, index=True)
    voted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class BallotRecordModel(Base):
    """Papeleta anónima almacenada en la urna digital.

    No tiene relación con ``voter_participation``; no hay document_id aquí.
    """

    __tablename__ = "ballot_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ballot_id = Column(String(64), unique=True, index=True, nullable=False)
    election_type = Column(String(20), nullable=False, index=True)
    ballot_type = Column(String(20), nullable=False)
    candidate_id = Column(String(50), nullable=True)
    selection = Column(String(300), nullable=False)
    receipt_code = Column(String(20), nullable=False)
    digital_signature = Column(String(128), nullable=True)
    timestamp_seal = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


def _seed_rows() -> List[CitizenModel]:
    """Genera un censo sintético y reproducible para la demo local.

    Se conservan algunos documentos conocidos por las pruebas, pero todos los
    nombres son ficticios. No se usan datos de personas reales.
    """
    national = [
        ("10203040", "Ana Torres", "MESA-01", True),
        ("50607080", "Bruno Díaz", "MESA-01", True),
        ("70809010", "Carla Méndez", "MESA-02", True),
        ("80901020", "Diego Rojas", "MESA-02", True),
        ("99999999", "Elena Vargas", "MESA-01", False),
    ]
    university = [
        ("EST-2024", "Ana Torres", "MESA-01", True),
        ("EST-9012", "Bruno Díaz", "MESA-01", True),
        ("EST-3341", "Carla Méndez", "MESA-02", True),
        ("EST-5520", "Diego Rojas", "MESA-02", True),
        ("EST-9999", "Elena Vargas", "MESA-01", False),
    ]

    first_names = [
        "Mariana", "Julián", "Sofía", "Andrés", "Valentina", "Camilo", "Paula", "Mateo",
        "Isabella", "Sebastián", "Daniela", "Nicolás", "Gabriela", "Santiago", "Laura",
        "Felipe", "Manuela", "Alejandro", "Carolina", "Tomás",
    ]
    last_names = [
        "Restrepo", "Cepeda", "Pajón", "Román", "Suárez", "Gómez", "Vargas", "Silva",
        "Torres", "Mendoza", "Rojas", "Castro", "López", "Méndez", "Díaz", "Ramírez",
    ]

    rows: List[CitizenModel] = []
    pin_hash = hash_pin("1234")

    for doc, name, station, eligible in national:
        rows.append(
            CitizenModel(
                document_id=doc,
                full_name=name,
                assigned_station_id=station,
                is_eligible=eligible,
                election_type="NATIONAL",
                pin_hash=pin_hash,
            )
        )
    for idx in range(36):
        name = f"{first_names[idx % len(first_names)]} {last_names[(idx * 3) % len(last_names)]}"
        rows.append(
            CitizenModel(
                document_id=f"2000{idx + 1:04d}",
                full_name=name,
                assigned_station_id="MESA-01" if idx % 2 == 0 else "MESA-02",
                is_eligible=idx % 12 != 0,
                election_type="NATIONAL",
                pin_hash=pin_hash,
            )
        )

    for doc, name, station, eligible in university:
        rows.append(
            CitizenModel(
                document_id=doc,
                full_name=name,
                assigned_station_id=station,
                is_eligible=eligible,
                election_type="UNIVERSITY",
                pin_hash=pin_hash,
            )
        )
    for idx in range(36):
        name = f"{first_names[(idx + 5) % len(first_names)]} {last_names[(idx * 5 + 2) % len(last_names)]}"
        rows.append(
            CitizenModel(
                document_id=f"EST-{1001 + idx}",
                full_name=name,
                assigned_station_id="MESA-01" if idx % 2 == 0 else "MESA-02",
                is_eligible=idx % 12 != 0,
                election_type="UNIVERSITY",
                pin_hash=pin_hash,
            )
        )
    return rows


def init_db() -> None:
    """Crea las tablas y precarga el censo sintético si está vacío."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        if session.query(CitizenModel).count() == 0:
            session.add_all(_seed_rows())
            session.commit()
    finally:
        session.close()


def reset_database() -> None:
    """Recrea todas las tablas y vuelve a sembrar el censo de demostración.

    Se usa desde ``scripts/reset_db.py`` antes de una demo. Borra votos,
    participaciones y censo; no toca archivos del proyecto.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_db()
