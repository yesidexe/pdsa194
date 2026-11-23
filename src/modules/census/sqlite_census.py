"""Adaptador de censo persistido en SQLite."""
from __future__ import annotations

from typing import List, Optional

from src.core.database import CitizenModel, SessionLocal, init_db
from src.core.security import hash_pin, verify_pin
from src.modules.census.contracts import ICensusRegistry, VoterCensusRecord


class SqliteCensusAdapter(ICensusRegistry):
    """Consulta y administra el censo real de la demo en SQLite."""

    def __init__(self, election_type: str = "NATIONAL") -> None:
        self.election_type = election_type.upper().strip()
        init_db()

    @staticmethod
    def _to_record(citizen: CitizenModel) -> VoterCensusRecord:
        return VoterCensusRecord(
            document_id=citizen.document_id,
            full_name=citizen.full_name,
            assigned_station_id=citizen.assigned_station_id,
            is_eligible=citizen.is_eligible,
            source_type="SQLITE_DATABASE",
        )

    def _find(self, session, document_id: str) -> Optional[CitizenModel]:
        return (
            session.query(CitizenModel)
            .filter(
                CitizenModel.document_id == str(document_id).strip(),
                CitizenModel.election_type == self.election_type,
            )
            .first()
        )

    def is_eligible(self, document_id: str) -> bool:
        session = SessionLocal()
        try:
            citizen = self._find(session, document_id)
            return bool(citizen and citizen.is_eligible)
        finally:
            session.close()

    def get_voter_record(self, document_id: str) -> Optional[VoterCensusRecord]:
        session = SessionLocal()
        try:
            citizen = self._find(session, document_id)
            return self._to_record(citizen) if citizen else None
        finally:
            session.close()

    def get_total_registered(self) -> int:
        session = SessionLocal()
        try:
            return session.query(CitizenModel).filter(CitizenModel.election_type == self.election_type).count()
        finally:
            session.close()

    def get_total_eligible(self) -> int:
        session = SessionLocal()
        try:
            return (
                session.query(CitizenModel)
                .filter(
                    CitizenModel.election_type == self.election_type,
                    CitizenModel.is_eligible.is_(True),
                )
                .count()
            )
        finally:
            session.close()

    def authenticate(self, document_id: str, pin: str) -> Optional[VoterCensusRecord]:
        session = SessionLocal()
        try:
            citizen = self._find(session, document_id)
            if not citizen or not citizen.is_eligible or not verify_pin(pin, citizen.pin_hash):
                return None
            return self._to_record(citizen)
        finally:
            session.close()

    def get_all_voters(self, election_type: Optional[str] = None) -> List[VoterCensusRecord]:
        session = SessionLocal()
        target = (election_type or self.election_type).upper().strip()
        try:
            query = session.query(CitizenModel)
            if target != "ALL":
                query = query.filter(CitizenModel.election_type == target)
            return [self._to_record(citizen) for citizen in query.order_by(CitizenModel.id.desc()).all()]
        finally:
            session.close()

    def register_voter(
        self,
        document_id: str,
        full_name: str,
        assigned_station_id: str = "MESA-01",
        is_eligible: bool = True,
        election_type: Optional[str] = None,
        pin: str = "1234",
    ) -> VoterCensusRecord:
        session = SessionLocal()
        target = (election_type or self.election_type).upper().strip()
        document = str(document_id).strip()
        try:
            citizen = (
                session.query(CitizenModel)
                .filter(
                    CitizenModel.document_id == document,
                    CitizenModel.election_type == target,
                )
                .first()
            )
            if citizen:
                citizen.full_name = full_name.strip()
                citizen.assigned_station_id = assigned_station_id.strip()
                citizen.is_eligible = is_eligible
                if pin:
                    citizen.pin_hash = hash_pin(pin)
            else:
                citizen = CitizenModel(
                    document_id=document,
                    full_name=full_name.strip(),
                    assigned_station_id=assigned_station_id.strip(),
                    is_eligible=is_eligible,
                    election_type=target,
                    pin_hash=hash_pin(pin or "1234"),
                )
                session.add(citizen)
            session.commit()
            return self._to_record(citizen)
        finally:
            session.close()

    def toggle_eligibility(self, document_id: str, is_eligible: bool) -> bool:
        session = SessionLocal()
        try:
            citizen = self._find(session, document_id)
            if not citizen:
                return False
            citizen.is_eligible = is_eligible
            session.commit()
            return True
        finally:
            session.close()
