"""Métricas de lectura para el dashboard público."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.modules.census.census_adapter import ICensusRegistry
from src.modules.election.election_factory import ElectoralFamilyFactory
from src.modules.election.state import ElectionStateMachine
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.modules.voting.vote_store import list_ballots


class DashboardService:
    """Calcula participación y conteo sin modificar el estado de la jornada."""

    def __init__(
        self,
        election_type: str,
        institution_name: str,
        election_title: str,
        state_machine: ElectionStateMachine,
        station_ids: List[str],
    ) -> None:
        self.election_type = election_type
        self._institution_name = institution_name
        self._election_title = election_title
        self._state = state_machine
        self._station_ids = list(station_ids)
        self._census: Optional[ICensusRegistry] = None
        self._family_factory: Optional[ElectoralFamilyFactory] = None

    def configure(
        self,
        census: Optional[ICensusRegistry],
        family_factory: Optional[ElectoralFamilyFactory],
        station_ids: List[str],
    ) -> None:
        self._census = census
        self._family_factory = family_factory
        self._station_ids = list(station_ids)

    @property
    def ballot_header(self) -> str:
        if self._family_factory is None:
            return "Encabezado Oficial"
        return self._family_factory.create_header().render_header()

    def summary(self) -> Dict[str, Any]:
        total_census = self._census.get_total_eligible() if self._census else 0
        ballots = list_ballots(self.election_type)
        total_votes = len(ballots)
        turnout_pct = (total_votes / total_census * 100) if total_census > 0 else 0.0

        candidate_votes: Dict[str, int] = {}
        votes_by_candidate_id: Dict[str, int] = {}
        votes_by_candidate_name: Dict[str, int] = {}
        blank_votes = 0
        null_votes = 0

        for ballot in ballots:
            if ballot.ballot_type == "blank":
                blank_votes += 1
                continue
            if ballot.candidate_id:
                official = next(
                    (
                        c
                        for c in CandidateFlyweightFactory.get_all_candidates()
                        if c.candidate_id == ballot.candidate_id
                    ),
                    None,
                )
                name = official.candidate_name if official else ballot.selection
                votes_by_candidate_id[ballot.candidate_id] = (
                    votes_by_candidate_id.get(ballot.candidate_id, 0) + 1
                )
                votes_by_candidate_name[name] = votes_by_candidate_name.get(name, 0) + 1
                candidate_votes[ballot.selection] = candidate_votes.get(ballot.selection, 0) + 1
            else:
                candidate_votes[ballot.selection] = candidate_votes.get(ballot.selection, 0) + 1

        return {
            "institution_name": self._institution_name,
            "election_title": self._election_title,
            "header": self.ballot_header,
            "is_open": self._state.is_open,
            "is_tallied": self._state.is_tallied,
            "election_status": self._state.status.value,
            "total_registered_citizens": total_census,
            "total_votes_cast": total_votes,
            "turnout_percentage": round(turnout_pct, 2),
            "total_stations_count": len(self._station_ids),
            "candidate_votes": candidate_votes,
            "votes_by_candidate_id": votes_by_candidate_id,
            "votes_by_candidate_name": votes_by_candidate_name,
            "blank_votes": blank_votes,
            "null_votes": null_votes,
        }
