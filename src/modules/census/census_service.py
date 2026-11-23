"""Servicio de administración del censo electoral."""
from __future__ import annotations

from typing import Any, Dict, List

from src.modules.census.census_adapter import SqliteCensusAdapter, VoterCensusRecord


class CensusService:
    """Operaciones de lectura y mantenimiento del censo persistido."""

    def __init__(self, election_type: str) -> None:
        self.adapter = SqliteCensusAdapter(election_type=election_type)

    def list_voters(self, election_type: str | None = None) -> List[VoterCensusRecord]:
        target = (election_type or self.adapter.election_type).upper()
        return self.adapter.get_all_voters(target)

    def register_voter(
        self,
        *,
        document_id: str,
        full_name: str,
        assigned_station_id: str,
        is_eligible: bool,
        election_type: str,
        pin: str,
    ) -> VoterCensusRecord:
        return self.adapter.register_voter(
            document_id=document_id,
            full_name=full_name,
            assigned_station_id=assigned_station_id,
            is_eligible=is_eligible,
            election_type=election_type,
            pin=pin,
        )

    def toggle_eligibility(self, document_id: str, is_eligible: bool) -> bool:
        return self.adapter.toggle_eligibility(document_id=document_id, is_eligible=is_eligible)

    @staticmethod
    def serialize(record: VoterCensusRecord) -> Dict[str, Any]:
        return {
            "document_id": record.document_id,
            "full_name": record.full_name,
            "assigned_station_id": record.assigned_station_id,
            "is_eligible": record.is_eligible,
            "source_type": record.source_type,
        }
