"""Fachada de alto nivel del sistema electoral.

La fachada ya no concentra la lógica: coordina servicios pequeños y mantiene la
interfaz pública que usan el Proxy y la API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.config import ElectoralConfigManager
from src.modules.census.census_adapter import ICensusRegistry
from src.modules.election.candidate_catalog import CandidateCatalog
from src.modules.election.election_factory import ElectoralFamilyFactory
from src.modules.election.election_service import ElectionService
from src.modules.election.state import ElectionStateMachine, ElectionStatus
from src.modules.tally.dashboard_service import DashboardService
from src.modules.tally.report_builder import ElectoralTallyReport
from src.modules.tally.tally_service import TallyAlreadyGeneratedError, TallyService
from src.modules.voting.vote_service import VoteService

__all__ = ["TallyAlreadyGeneratedError", "VotingSystemFacade"]


class VotingSystemFacade:
    """Punto de entrada único para las operaciones de la jornada electoral."""

    def __init__(
        self,
        institution_name: str = "Consejo Nacional Electoral",
        election_title: str = "Elecciones Oficiales 2026",
        election_type: str = "NATIONAL",
        jurisdiction_name: str = "Jurisdicción General",
        station_ids: Optional[List[str]] = None,
    ) -> None:
        self.election_type = election_type.upper().strip()
        self._config = ElectoralConfigManager(
            institution_name=institution_name,
            election_title=election_title,
        )
        self._state_machine = ElectionStateMachine(self.election_type)
        self._candidate_catalog = CandidateCatalog(self.election_type)
        self._station_ids = list(station_ids or [])
        self._jurisdiction_name = jurisdiction_name
        self._census: Optional[ICensusRegistry] = None
        self._family_factory: Optional[ElectoralFamilyFactory] = None

        self._election_service = ElectionService(self._state_machine, self._candidate_catalog)
        self._vote_service = VoteService(self.election_type, self._state_machine)
        self._tally_service = TallyService(
            self.election_type,
            self._state_machine,
            self._config.election_title,
            self._jurisdiction_name,
            self._station_ids,
        )
        self._dashboard_service = DashboardService(
            self.election_type,
            self._config.institution_name,
            self._config.election_title,
            self._state_machine,
            self._station_ids,
        )

    def setup_environment(
        self,
        census_registry: ICensusRegistry,
        family_factory: Optional[ElectoralFamilyFactory] = None,
        station_ids: Optional[List[str]] = None,
        jurisdiction_name: Optional[str] = None,
    ) -> None:
        """Inyecta censo, familia electoral, mesas y jurisdicción en los servicios."""
        self._census = census_registry
        self._family_factory = family_factory
        if station_ids is not None:
            self._station_ids = list(station_ids)
        if jurisdiction_name:
            self._jurisdiction_name = jurisdiction_name

        self._vote_service.configure(self._census, self._family_factory)
        self._tally_service.configure(
            self._family_factory,
            self._config.election_title,
            self._jurisdiction_name,
            self._station_ids,
        )
        self._dashboard_service.configure(self._census, self._family_factory, self._station_ids)

    @property
    def is_voting_open(self) -> bool:
        return self._election_service.is_open

    @property
    def is_tallied(self) -> bool:
        return self._election_service.is_tallied

    @property
    def election_status(self) -> ElectionStatus:
        return self._election_service.status

    @property
    def election_status_label(self) -> str:
        return self._election_service.status_label

    @property
    def institution_name(self) -> str:
        return self._config.institution_name

    @property
    def election_title(self) -> str:
        return self._config.election_title

    @property
    def ballot_header(self) -> str:
        if self._family_factory is None:
            return "Encabezado Oficial"
        return self._family_factory.create_header().render_header()

    @property
    def document_type(self) -> str:
        if self._family_factory is None:
            return "Documento de Identidad"
        return self._family_factory.create_validator().get_document_type()

    def open_polls(self) -> None:
        self._election_service.open()

    def close_polls(self) -> None:
        self._election_service.close()

    def reset_election(self) -> int:
        return self._election_service.reset()

    def list_candidates(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        return self._election_service.list_candidates(include_inactive=include_inactive)

    def refresh_candidate_catalog(self) -> int:
        return self._election_service.refresh_candidate_catalog()

    def create_candidate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._election_service.create_candidate(payload)

    def update_candidate(self, candidate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._election_service.update_candidate(candidate_id, payload)

    def set_candidate_active(self, candidate_id: str, is_active: bool) -> Dict[str, Any]:
        return self._election_service.set_candidate_active(candidate_id, is_active)

    def verify_voter(self, document_id: str, pin: str, check_existing: bool = True) -> Dict[str, Any]:
        return self._vote_service.verify_voter(document_id, pin, check_existing=check_existing)

    def cast_secure_vote(
        self,
        document_id: str,
        pin: str,
        ballot_type: str,
        selection_kwargs: Dict[str, Any],
        security_layers: Optional[List[str]] = None,
        signing_key: str = "MASTER_FACADE_SECRET_2026",
    ) -> Dict[str, Any]:
        return self._vote_service.cast_secure_vote(
            document_id=document_id,
            pin=pin,
            ballot_type=ballot_type,
            selection_kwargs=selection_kwargs,
            security_layers=security_layers,
            signing_key=signing_key,
        )

    def close_and_generate_tally(self, officer_signatures: List[str]) -> ElectoralTallyReport:
        return self._tally_service.close_and_generate_tally(officer_signatures)

    def get_registered_station_ids(self) -> List[str]:
        return self._tally_service.get_station_ids()

    def get_latest_tally_report(self) -> Optional[Dict[str, Any]]:
        return self._tally_service.get_latest()

    def get_dashboard_summary(self) -> Dict[str, Any]:
        return self._dashboard_service.summary()
