"""Catálogo administrable de candidatos.

La base es la fuente de verdad; el pool Flyweight se refresca después de cada
cambio para que el tarjetón y la validación usen la misma ficha.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.core.database import (
    count_active_candidates,
    create_candidate,
    list_candidates,
    set_candidate_active,
    update_candidate,
)
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory


class CandidateCatalog:
    """Operaciones de lectura y administración del catálogo de una modalidad."""

    def __init__(self, election_type: str) -> None:
        self.election_type = str(election_type).upper().strip()

    def list_all(self, only_active: bool = False) -> List[Dict[str, Any]]:
        return list_candidates(self.election_type, only_active=only_active)

    def count_active(self) -> int:
        return count_active_candidates(self.election_type)

    def refresh_flyweight(self) -> int:
        """Reconstruye el pool en memoria con los candidatos activos."""
        CandidateFlyweightFactory.reset_pool()
        active = self.list_all(only_active=True)
        for record in active:
            CandidateFlyweightFactory.get_candidate(
                candidate_id=record["candidate_id"],
                candidate_name=record["candidate_name"],
                party_name=record["party_name"],
                campaign_slogan=record["campaign_slogan"],
                party_color_hex=record["party_color_hex"],
                photo_url=record["photo_url"],
            )
        return len(active)

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        created = create_candidate(
            election_type=self.election_type,
            candidate_id=payload["candidate_id"],
            candidate_name=payload["candidate_name"],
            party_name=payload["party_name"],
            campaign_slogan=payload.get("campaign_slogan", ""),
            party_color_hex=payload.get("party_color_hex", "#2563EB"),
            photo_url=payload.get("photo_url", "/static/candidates/default.svg"),
            display_order=payload.get("display_order", 0),
        )
        self.refresh_flyweight()
        return created

    def update(self, candidate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        updated = update_candidate(
            election_type=self.election_type,
            candidate_id=candidate_id,
            candidate_name=payload["candidate_name"],
            party_name=payload["party_name"],
            campaign_slogan=payload.get("campaign_slogan", ""),
            party_color_hex=payload.get("party_color_hex", "#2563EB"),
            photo_url=payload.get("photo_url", "/static/candidates/default.svg"),
            display_order=payload.get("display_order", 0),
        )
        self.refresh_flyweight()
        return updated

    def set_active(self, candidate_id: str, is_active: bool) -> Dict[str, Any]:
        updated = set_candidate_active(self.election_type, candidate_id, is_active)
        self.refresh_flyweight()
        return updated
