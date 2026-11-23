"""Persistencia relacional local (SQLite + SQLAlchemy).

Tablas de la jornada electoral:

1. ``census_citizens``: censo oficial (quién puede votar y con qué PIN).
2. ``voter_participation``: quién ya votó. No conoce la papeleta.
3. ``ballot_records``: qué se votó. No conoce al votante.
4. ``election_state``: estado de la jornada (borrador, abierta, cerrada, escrutada).
5. ``audit_events``: bitácora append-only con hash chain.
6. ``candidates``: catálogo administrable por modalidad.
7. ``tally_reports``: actas persistidas para consulta y descarga.

La separación entre ``voter_participation`` y ``ballot_records`` es deliberada:
permite saber cuántos votaron y qué se votó sin poder unir ambas cosas.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError
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


class ElectionStateModel(Base):
    """Estado persistente de la jornada, independiente de la urna y del censo."""

    __tablename__ = "election_state"
    __table_args__ = (
        UniqueConstraint("election_type", name="uq_election_state_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    election_type = Column(String(20), nullable=False, index=True)
    # DRAFT -> OPEN -> CLOSED -> TALLIED. ``is_tallied`` se conserva por
    # compatibilidad con la base anterior, pero la fuente de verdad es ``status``.
    status = Column(String(20), default="DRAFT", nullable=False)
    is_tallied = Column(Boolean, default=False, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class AuditEventModel(Base):
    """Evento de auditoría append-only.

    No guarda documentos completos ni relaciona identidad con papeleta. Cada
    fila incluye el hash del evento anterior para detectar alteraciones.
    """

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    user_id = Column(String(100), nullable=False)
    role = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    details = Column(String(500), default="", nullable=False)
    prev_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False, unique=True, index=True)


class CandidateModel(Base):
    """Catálogo oficial de candidatos por modalidad electoral."""

    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint("election_type", "candidate_id", name="uq_candidate_election_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(50), nullable=False, index=True)
    election_type = Column(String(20), nullable=False, index=True)
    candidate_name = Column(String(150), nullable=False)
    party_name = Column(String(150), nullable=False)
    campaign_slogan = Column(String(300), default="", nullable=False)
    party_color_hex = Column(String(7), default="#2563EB", nullable=False)
    photo_url = Column(String(300), default="/static/candidates/default.svg", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TallyReportModel(Base):
    """Acta de escrutinio persistida para consulta y verificación posterior."""

    __tablename__ = "tally_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    election_type = Column(String(20), nullable=False, index=True)
    election_title = Column(String(200), nullable=False)
    jurisdiction = Column(String(200), nullable=False)
    generated_at = Column(DateTime, nullable=False)
    total_votes = Column(Integer, nullable=False)
    candidate_votes = Column(Text, nullable=False)
    blank_votes = Column(Integer, nullable=False)
    null_votes = Column(Integer, nullable=False)
    winner_verdict = Column(String(500), nullable=True)
    officer_signatures = Column(Text, nullable=False)
    integrity_hash = Column(String(64), nullable=False)
    payload = Column(Text, nullable=False)


# El hash chain necesita una escritura serializada: dos eventos concurrentes no
# pueden leer el mismo "prev_hash" y romper la cadena.
_AUDIT_LOCK = threading.Lock()
AUDIT_GENESIS_HASH = "0" * 64


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


def count_ballots(election_type: str) -> int:
    """Cuenta las papeletas de una elección sin cargar sus filas."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        return (
            session.query(BallotRecordModel)
            .filter(BallotRecordModel.election_type == target)
            .count()
        )
    finally:
        session.close()


def _seed_candidate_rows() -> List[CandidateModel]:
    """Candidatos sintéticos iniciales para que la demo no arranque vacía."""
    rows: List[CandidateModel] = [
        CandidateModel(
            candidate_id="CAND-01",
            election_type="NATIONAL",
            candidate_name="Gabriel Silva",
            party_name="Alianza Verde Digital",
            campaign_slogan="Tecnología, transparencia y educación para el futuro",
            party_color_hex="#16A34A",
            display_order=1,
        ),
        CandidateModel(
            candidate_id="CAND-02",
            election_type="NATIONAL",
            candidate_name="Elena Torres",
            party_name="Pacto Innovación Ciudadana",
            campaign_slogan="Gestión abierta, cero corrupción y participación real",
            party_color_hex="#2563EB",
            display_order=2,
        ),
        CandidateModel(
            candidate_id="CAND-03",
            election_type="NATIONAL",
            candidate_name="Carlos Mendoza",
            party_name="Movimiento Renovación",
            campaign_slogan="Experiencia y liderazgo con rigor institucional",
            party_color_hex="#D97706",
            display_order=3,
        ),
        CandidateModel(
            candidate_id="CAND-04",
            election_type="NATIONAL",
            candidate_name="Lucía Herrera",
            party_name="Frente Ciudadano Independiente",
            campaign_slogan="Servicios públicos cercanos y presupuesto participativo",
            party_color_hex="#7C3AED",
            display_order=4,
        ),
        CandidateModel(
            candidate_id="VOC-01",
            election_type="UNIVERSITY",
            candidate_name="Camilo Suárez",
            party_name="Lista 1 - Estudiantes por el Cambio",
            campaign_slogan="Liderazgo, transparencia e innovación académica",
            party_color_hex="#4F46E5",
            display_order=1,
        ),
        CandidateModel(
            candidate_id="VOC-02",
            election_type="UNIVERSITY",
            candidate_name="Valentina Gómez",
            party_name="Lista 2 - Innovación Universitaria",
            campaign_slogan="Conectividad, investigación y bienestar estudiantil",
            party_color_hex="#0D9488",
            display_order=2,
        ),
        CandidateModel(
            candidate_id="VOC-03",
            election_type="UNIVERSITY",
            candidate_name="Sofía Vargas",
            party_name="Lista 3 - Voces UDI",
            campaign_slogan="Cultura, representación y participación activa",
            party_color_hex="#EA580C",
            display_order=3,
        ),
        CandidateModel(
            candidate_id="VOC-04",
            election_type="UNIVERSITY",
            candidate_name="Daniel Rojas",
            party_name="Lista 4 - Bienestar y Deporte",
            campaign_slogan="Campus saludable, inclusivo y con más apoyo estudiantil",
            party_color_hex="#7C3AED",
            display_order=4,
        ),
    ]
    return rows


def _candidate_to_dict(row: CandidateModel) -> Dict[str, Any]:
    return {
        "candidate_id": row.candidate_id,
        "election_type": row.election_type,
        "candidate_name": row.candidate_name,
        "party_name": row.party_name,
        "campaign_slogan": row.campaign_slogan,
        "party_color_hex": row.party_color_hex,
        "photo_url": row.photo_url,
        "is_active": bool(row.is_active),
        "display_order": row.display_order,
    }


def list_candidates(election_type: str, only_active: bool = False) -> List[Dict[str, Any]]:
    """Lista el catálogo de una modalidad, opcionalmente solo los activos."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        query = session.query(CandidateModel).filter(CandidateModel.election_type == target)
        if only_active:
            query = query.filter(CandidateModel.is_active.is_(True))
        rows = query.order_by(CandidateModel.display_order.asc(), CandidateModel.candidate_id.asc()).all()
        return [_candidate_to_dict(row) for row in rows]
    finally:
        session.close()


def get_candidate(election_type: str, candidate_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve un candidato del catálogo o ``None`` si no existe."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        row = (
            session.query(CandidateModel)
            .filter(
                CandidateModel.election_type == target,
                CandidateModel.candidate_id == str(candidate_id).strip().upper(),
            )
            .first()
        )
        return _candidate_to_dict(row) if row else None
    finally:
        session.close()


def count_active_candidates(election_type: str) -> int:
    """Cuenta candidatos activos de una modalidad."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        return (
            session.query(CandidateModel)
            .filter(CandidateModel.election_type == target, CandidateModel.is_active.is_(True))
            .count()
        )
    finally:
        session.close()


def create_candidate(
    *,
    election_type: str,
    candidate_id: str,
    candidate_name: str,
    party_name: str,
    campaign_slogan: str = "",
    party_color_hex: str = "#2563EB",
    photo_url: str = "/static/candidates/default.svg",
    display_order: int = 0,
) -> Dict[str, Any]:
    """Inserta un candidato; falla si el identificador ya existe en la modalidad."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        row = CandidateModel(
            candidate_id=str(candidate_id).strip().upper(),
            election_type=target,
            candidate_name=candidate_name.strip(),
            party_name=party_name.strip(),
            campaign_slogan=campaign_slogan.strip(),
            party_color_hex=party_color_hex,
            photo_url=photo_url,
            display_order=int(display_order),
            is_active=True,
        )
        session.add(row)
        session.commit()
        return _candidate_to_dict(row)
    except IntegrityError as exc:
        session.rollback()
        raise ValueError(f"El candidato '{candidate_id}' ya existe en esta modalidad.") from exc
    finally:
        session.close()


def update_candidate(
    *,
    election_type: str,
    candidate_id: str,
    candidate_name: str,
    party_name: str,
    campaign_slogan: str = "",
    party_color_hex: str = "#2563EB",
    photo_url: str = "/static/candidates/default.svg",
    display_order: int = 0,
) -> Dict[str, Any]:
    """Actualiza la ficha de un candidato existente."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        row = (
            session.query(CandidateModel)
            .filter(
                CandidateModel.election_type == target,
                CandidateModel.candidate_id == str(candidate_id).strip().upper(),
            )
            .first()
        )
        if row is None:
            raise LookupError(f"No existe el candidato '{candidate_id}' en esta modalidad.")
        row.candidate_name = candidate_name.strip()
        row.party_name = party_name.strip()
        row.campaign_slogan = campaign_slogan.strip()
        row.party_color_hex = party_color_hex
        row.photo_url = photo_url
        row.display_order = int(display_order)
        session.commit()
        return _candidate_to_dict(row)
    finally:
        session.close()


def set_candidate_active(election_type: str, candidate_id: str, is_active: bool) -> Dict[str, Any]:
    """Activa o desactiva un candidato sin borrar su histórico."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        row = (
            session.query(CandidateModel)
            .filter(
                CandidateModel.election_type == target,
                CandidateModel.candidate_id == str(candidate_id).strip().upper(),
            )
            .first()
        )
        if row is None:
            raise LookupError(f"No existe el candidato '{candidate_id}' en esta modalidad.")
        row.is_active = bool(is_active)
        session.commit()
        return _candidate_to_dict(row)
    finally:
        session.close()


def record_tally_report(
    *,
    election_type: str,
    election_title: str,
    jurisdiction: str,
    generated_at: datetime,
    total_votes: int,
    candidate_votes: Dict[str, int],
    blank_votes: int,
    null_votes: int,
    winner_verdict: Optional[str],
    officer_signatures: List[str],
    integrity_hash: str,
) -> int:
    """Persiste el acta ya construida, con su payload canónico y su sello."""
    target = str(election_type).upper().strip()
    payload = {
        "election_title": election_title,
        "jurisdiction": jurisdiction,
        "generated_at": generated_at.isoformat(),
        "total_votes": total_votes,
        "candidate_votes": candidate_votes,
        "blank_votes": blank_votes,
        "null_votes": null_votes,
        "winner_verdict": winner_verdict,
        "officer_signatures": officer_signatures,
        "integrity_hash": integrity_hash,
    }
    session = SessionLocal()
    try:
        row = TallyReportModel(
            election_type=target,
            election_title=election_title,
            jurisdiction=jurisdiction,
            generated_at=generated_at,
            total_votes=total_votes,
            candidate_votes=json.dumps(candidate_votes, ensure_ascii=False),
            blank_votes=blank_votes,
            null_votes=null_votes,
            winner_verdict=winner_verdict,
            officer_signatures=json.dumps(officer_signatures, ensure_ascii=False),
            integrity_hash=integrity_hash,
            payload=json.dumps(payload, ensure_ascii=False),
        )
        session.add(row)
        session.commit()
        return int(row.id)
    finally:
        session.close()


def get_latest_tally_report(election_type: str) -> Optional[Dict[str, Any]]:
    """Devuelve el acta más reciente de una modalidad, si existe."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        row = (
            session.query(TallyReportModel)
            .filter(TallyReportModel.election_type == target)
            .order_by(TallyReportModel.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            "id": row.id,
            "election_type": row.election_type,
            "election_title": row.election_title,
            "jurisdiction": row.jurisdiction,
            "generated_at": _audit_timestamp_text(row.generated_at) if row.generated_at else "",
            "total_votes": row.total_votes,
            "candidate_votes": json.loads(row.candidate_votes or "{}"),
            "blank_votes": row.blank_votes,
            "null_votes": row.null_votes,
            "winner_verdict": row.winner_verdict,
            "officer_signatures": json.loads(row.officer_signatures or "[]"),
            "integrity_hash": row.integrity_hash,
            "payload": json.loads(row.payload or "{}"),
        }
    finally:
        session.close()


def get_election_status(election_type: str) -> str:
    """Devuelve el estado de la jornada; si no existe fila, la jornada es borrador."""
    target = str(election_type).upper().strip()
    session = SessionLocal()
    try:
        row = (
            session.query(ElectionStateModel)
            .filter(ElectionStateModel.election_type == target)
            .first()
        )
        if row is None:
            return "DRAFT"
        if row.status:
            return str(row.status).upper()
        return "TALLIED" if row.is_tallied else "DRAFT"
    finally:
        session.close()


def set_election_status(election_type: str, status: str) -> None:
    """Guarda el estado de la jornada y mantiene ``is_tallied`` sincronizado."""
    target = str(election_type).upper().strip()
    normalized = str(status).upper().strip()
    session = SessionLocal()
    try:
        row = (
            session.query(ElectionStateModel)
            .filter(ElectionStateModel.election_type == target)
            .first()
        )
        if row is None:
            row = ElectionStateModel(election_type=target)
            session.add(row)
        row.status = normalized
        row.is_tallied = normalized == "TALLIED"
        session.commit()
    finally:
        session.close()


def get_election_tallied(election_type: str) -> bool:
    """Indica si la elección ya tiene un acta generada."""
    return get_election_status(election_type) == "TALLIED"


def set_election_tallied(election_type: str, is_tallied: bool) -> None:
    """Compatibilidad: marca la jornada como escrutada o cerrada."""
    set_election_status(election_type, "TALLIED" if is_tallied else "CLOSED")


def _audit_timestamp_text(value: datetime) -> str:
    """Normaliza la marca de tiempo para que el hash no dependa del driver."""
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat()


def _canonical_audit_payload(event: Dict[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _append_audit_event(
    *,
    action: str,
    user_id: str,
    role: str,
    status: str,
    details: str,
    timestamp: datetime,
) -> int:
    payload = {
        "timestamp": _audit_timestamp_text(timestamp),
        "action": action,
        "user_id": user_id,
        "role": role,
        "status": status,
        "details": details,
    }
    canonical = _canonical_audit_payload(payload)

    with _AUDIT_LOCK:
        session = SessionLocal()
        try:
            previous = (
                session.query(AuditEventModel)
                .order_by(AuditEventModel.id.desc())
                .first()
            )
            prev_hash = previous.event_hash if previous else AUDIT_GENESIS_HASH
            event_hash = hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()
            row = AuditEventModel(
                timestamp=timestamp,
                action=action,
                user_id=user_id,
                role=role,
                status=status,
                details=details,
                prev_hash=prev_hash,
                event_hash=event_hash,
            )
            session.add(row)
            session.commit()
            return int(row.id)
        finally:
            session.close()


def record_audit_event(
    action: str,
    user_id: str,
    role: str,
    status: str,
    details: str = "",
    timestamp: Optional[datetime] = None,
) -> int:
    """Registra un evento en la bitácora persistente y devuelve su id."""
    event_time = timestamp or datetime.now(timezone.utc)
    return _append_audit_event(
        action=str(action)[:50],
        user_id=str(user_id)[:100],
        role=str(role)[:30],
        status=str(status)[:30],
        details=str(details)[:500],
        timestamp=event_time,
    )


def list_audit_events(limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
    """Lista eventos en orden cronológico ascendente (más recientes al final)."""
    session = SessionLocal()
    try:
        rows = (
            session.query(AuditEventModel)
            .order_by(AuditEventModel.id.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 1000)))
            .all()
        )
        rows.reverse()
        return [
            {
                "id": row.id,
                "timestamp": _audit_timestamp_text(row.timestamp) if row.timestamp else "",
                "action": row.action,
                "user_id": row.user_id,
                "role": row.role,
                "status": row.status,
                "details": row.details,
                "prev_hash": row.prev_hash,
                "event_hash": row.event_hash,
            }
            for row in rows
        ]
    finally:
        session.close()


def verify_audit_chain() -> Dict[str, Any]:
    """Recalcula la cadena completa y reporta el primer evento alterado."""
    session = SessionLocal()
    try:
        rows = session.query(AuditEventModel).order_by(AuditEventModel.id.asc()).all()
        previous_hash = AUDIT_GENESIS_HASH
        for row in rows:
            payload = {
                "timestamp": _audit_timestamp_text(row.timestamp) if row.timestamp else "",
                "action": row.action,
                "user_id": row.user_id,
                "role": row.role,
                "status": row.status,
                "details": row.details,
            }
            expected = hashlib.sha256(
                (previous_hash + _canonical_audit_payload(payload)).encode("utf-8")
            ).hexdigest()
            if row.prev_hash != previous_hash or row.event_hash != expected:
                return {
                    "valid": False,
                    "events": len(rows),
                    "broken_at": row.id,
                    "expected_hash": expected,
                }
            previous_hash = row.event_hash
        return {"valid": True, "events": len(rows), "broken_at": None, "head_hash": previous_hash}
    finally:
        session.close()


def _ensure_schema() -> None:
    """Migraciones mínimas para bases creadas antes de existir ``status``."""
    inspector = inspect(engine)
    if "election_state" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("election_state")}
    if "status" in columns:
        return
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE election_state "
                "ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'CLOSED'"
            )
        )
        connection.execute(
            text("UPDATE election_state SET status = 'TALLIED' WHERE is_tallied = 1")
        )


def init_db() -> None:
    """Crea las tablas, aplica la migración mínima y precarga el censo."""
    Base.metadata.create_all(bind=engine)
    _ensure_schema()
    session = SessionLocal()
    try:
        if session.query(CitizenModel).count() == 0:
            session.add_all(_seed_rows())
        if session.query(CandidateModel).count() == 0:
            session.add_all(_seed_candidate_rows())
        session.commit()
    finally:
        session.close()


def reset_database() -> None:
    """Recrea todas las tablas y vuelve a sembrar el censo de demostración.

    Se usa desde ``scripts/reset_db.py`` antes de una demo. Borra votos,
    participaciones, estado de escrutinio, auditoría y censo.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_db()
