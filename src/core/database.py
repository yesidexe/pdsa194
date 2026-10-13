"""Módulo central de persistencia relacional con SQLite y SQLAlchemy.

Este módulo gestiona la conexión a la base de datos local SQLite ('e_voting.db'),
define los modelos relacionales para el censo electoral (Registraduría) y
proporciona funciones de inicialización y precarga segura de datos (seeding).
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# Ruta absoluta al archivo SQLite local en la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BASE_DIR / "e_voting.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Motor de base de datos SQLite con soporte para concurrencia segura entre hilos
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Requerido para SQLite en aplicaciones web multihilo
    echo=False,
)

# Creador de sesiones atómicas con ámbito seguro (thread-scoped)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# Clase base declarativa para modelos ORM
Base = declarative_base()


class CitizenModel(Base):
    """Modelo relacional que representa el registro oficial de un ciudadano en el censo.

    Representa la base de datos oficial gestionada por la autoridad electoral
    (Registraduría Nacional o Secretaría Académica Universitaria).
    """
    __tablename__ = "census_citizens"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    # Documento oficial único (Cédula de Ciudadanía o Carnet Estudiantil)
    document_id = Column(String(50), unique=True, index=True, nullable=False)
    # Nombre completo legal del sufragante
    full_name = Column(String(150), nullable=False)
    # Mesa o estación de votación asignada geográficamente
    assigned_station_id = Column(String(50), default="MESA-01", nullable=False)
    # Estado legal: True si está habilitado para votar, False si tiene sanción o inhabilitación
    is_eligible = Column(Boolean, default=True, nullable=False)
    # Ámbito electoral: 'NATIONAL' (elecciones de orden nacional) o 'UNIVERSITY' (elecciones universitarias)
    election_type = Column(String(20), default="NATIONAL", nullable=False)
    # Fecha y hora UTC del registro o inscripción
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<CitizenModel(doc='{self.document_id}', name='{self.full_name}', eligible={self.is_eligible}, type='{self.election_type}')>"


def init_db() -> None:
    """Crea las tablas en la base de datos si no existen y precarga los electores iniciales.

    Esta función es idempotente: si la base de datos ya contiene registros,
    no sobreescribe ni duplica los datos existentes.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Verificar si la tabla ya tiene datos precargados
        if session.query(CitizenModel).count() == 0:
            seed_data = [
                # --- Electores Oficiales para Elección Nacional (Cédulas) ---
                CitizenModel(
                    document_id="10203040",
                    full_name="Laura Restrepo",
                    assigned_station_id="MESA-01",
                    is_eligible=True,
                    election_type="NATIONAL",
                ),
                CitizenModel(
                    document_id="50607080",
                    full_name="Andrés Cepeda",
                    assigned_station_id="MESA-01",
                    is_eligible=True,
                    election_type="NATIONAL",
                ),
                CitizenModel(
                    document_id="70809010",
                    full_name="Mariana Pajón",
                    assigned_station_id="MESA-02",
                    is_eligible=True,
                    election_type="NATIONAL",
                ),
                CitizenModel(
                    document_id="80901020",
                    full_name="Julián Román",
                    assigned_station_id="MESA-02",
                    is_eligible=True,
                    election_type="NATIONAL",
                ),
                CitizenModel(
                    document_id="99999999",
                    full_name="Carlos Vives (Inhabilitado judicialmente)",
                    assigned_station_id="MESA-01",
                    is_eligible=False,
                    election_type="NATIONAL",
                ),
                # --- Electores Oficiales para Elección Universitaria (Carnets) ---
                CitizenModel(
                    document_id="EST-2024",
                    full_name="Laura Restrepo",
                    assigned_station_id="MESA-01",
                    is_eligible=True,
                    election_type="UNIVERSITY",
                ),
                CitizenModel(
                    document_id="EST-9012",
                    full_name="Andrés Cepeda",
                    assigned_station_id="MESA-01",
                    is_eligible=True,
                    election_type="UNIVERSITY",
                ),
                CitizenModel(
                    document_id="EST-3341",
                    full_name="Mariana Pajón",
                    assigned_station_id="MESA-02",
                    is_eligible=True,
                    election_type="UNIVERSITY",
                ),
                CitizenModel(
                    document_id="EST-5520",
                    full_name="Julián Román",
                    assigned_station_id="MESA-02",
                    is_eligible=True,
                    election_type="UNIVERSITY",
                ),
                CitizenModel(
                    document_id="EST-9999",
                    full_name="Carlos Vives (Sancionado disciplinariamente)",
                    assigned_station_id="MESA-01",
                    is_eligible=False,
                    election_type="UNIVERSITY",
                ),
            ]
            session.add_all(seed_data)
            session.commit()
    finally:
        session.close()
