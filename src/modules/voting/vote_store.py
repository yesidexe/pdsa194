"""Almacén de votos y participaciones.

La urna es la base de datos, no una lista en memoria. Esto permite que los
votos sobrevivan a un reinicio y que la restricción única de participación
impida el doble voto incluso con peticiones concurrentes.

Importante: ``voter_participation`` y ``ballot_records`` no se relacionan entre
sí. El sistema puede saber quién votó y qué se votó, pero no puede unirlos.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError

from src.core.database import BallotRecordModel, SessionLocal, VoterParticipationModel


class AlreadyVotedError(Exception):
    """El elector ya tiene una participación registrada en esta elección."""


@dataclass(frozen=True)
class StoredBallot:
    """Vista de lectura de una papeleta anónima."""

    ballot_id: str
    ballot_type: str
    candidate_id: Optional[str]
    selection: str
    receipt_code: str
    digital_signature: Optional[str]
    timestamp_seal: Optional[str]
    created_at: datetime


def has_voted(election_type: str, document_id: str) -> bool:
    """Indica si el documento ya votó en la elección indicada."""
    session = SessionLocal()
    try:
        return (
            session.query(VoterParticipationModel)
            .filter(
                VoterParticipationModel.election_type == election_type,
                VoterParticipationModel.document_id == str(document_id).strip(),
            )
            .first()
            is not None
        )
    finally:
        session.close()


def register_vote(
    election_type: str,
    document_id: str,
    *,
    ballot_id: str,
    ballot_type: str,
    candidate_id: Optional[str],
    selection: str,
    receipt_code: str,
    digital_signature: Optional[str],
    timestamp_seal: Optional[str],
) -> None:
    """Registra participación y papeleta en una sola transacción.

    La restricción única ``(election_type, document_id)`` es la garantía final
    contra el doble voto. Si dos peticiones compiten, solo una inserta la
    participación; la otra recibe ``AlreadyVotedError``.
    """
    session = SessionLocal()
    try:
        session.add(
            VoterParticipationModel(
                election_type=election_type,
                document_id=str(document_id).strip(),
            )
        )
        session.add(
            BallotRecordModel(
                ballot_id=ballot_id,
                election_type=election_type,
                ballot_type=ballot_type,
                candidate_id=candidate_id,
                selection=selection,
                receipt_code=receipt_code,
                digital_signature=digital_signature,
                timestamp_seal=timestamp_seal,
            )
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AlreadyVotedError("El elector ya ejerció su voto en esta jornada.") from exc
    finally:
        session.close()


def list_ballots(election_type: str) -> List[StoredBallot]:
    """Devuelve las papeletas anónimas de una elección, en orden de emisión."""
    session = SessionLocal()
    try:
        rows = (
            session.query(BallotRecordModel)
            .filter(BallotRecordModel.election_type == election_type)
            .order_by(BallotRecordModel.created_at.asc(), BallotRecordModel.id.asc())
            .all()
        )
        return [
            StoredBallot(
                ballot_id=row.ballot_id,
                ballot_type=row.ballot_type,
                candidate_id=row.candidate_id,
                selection=row.selection,
                receipt_code=row.receipt_code,
                digital_signature=row.digital_signature,
                timestamp_seal=row.timestamp_seal,
                created_at=row.created_at,
            )
            for row in rows
        ]
    finally:
        session.close()


def count_votes(election_type: str) -> int:
    """Cuenta las papeletas almacenadas para una elección."""
    session = SessionLocal()
    try:
        return (
            session.query(BallotRecordModel)
            .filter(BallotRecordModel.election_type == election_type)
            .count()
        )
    finally:
        session.close()


def reset_election(election_type: str) -> int:
    """Borra votos y participaciones de una elección; conserva el censo.

    Devuelve cuántas papeletas se eliminaron. Es la operación recomendada para
    volver a probar la jornada sin romper el secreto del voto.
    """
    session = SessionLocal()
    try:
        removed = (
            session.query(BallotRecordModel)
            .filter(BallotRecordModel.election_type == election_type)
            .delete(synchronize_session=False)
        )
        session.query(VoterParticipationModel).filter(
            VoterParticipationModel.election_type == election_type
        ).delete(synchronize_session=False)
        session.commit()
        return int(removed or 0)
    finally:
        session.close()
