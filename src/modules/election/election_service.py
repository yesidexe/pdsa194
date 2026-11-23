"""Ciclo de vida de la jornada y catálogo de candidatos."""
from __future__ import annotations

from typing import Any, Dict, List

from src.modules.election.candidate_catalog import CandidateCatalog
from src.modules.election.state import ElectionStateMachine, ElectionStatus
from src.modules.voting.vote_store import reset_election as reset_election_store


class ElectionService:
    """Coordina apertura, cierre, reset y edición de la papeleta."""

    def __init__(self, state_machine: ElectionStateMachine, candidate_catalog: CandidateCatalog) -> None:
        self._state = state_machine
        self._catalog = candidate_catalog

    @property
    def is_open(self) -> bool:
        return self._state.is_open

    @property
    def is_tallied(self) -> bool:
        return self._state.is_tallied

    @property
    def status(self) -> ElectionStatus:
        return self._state.status

    @property
    def status_label(self) -> str:
        return self._state.status_label

    def open(self) -> None:
        if self.is_tallied:
            raise ValueError("La jornada ya fue escrutada. Reinicia la jornada para volver a abrir la urna.")
        if self._catalog.count_active() < 2:
            raise ValueError("La papeleta necesita al menos dos candidatos activos para abrir la urna.")
        self._state.open()

    def close(self) -> None:
        self._state.close()

    def reset(self) -> int:
        removed = reset_election_store(self._state.election_type)
        self._state.reset()
        return removed

    def _assert_ballot_editable(self) -> None:
        if not self._state.can_edit_ballot():
            raise ValueError("La papeleta no se puede editar en este estado o después de registrar votos.")

    def list_candidates(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        return self._catalog.list_all(only_active=not include_inactive)

    def refresh_candidate_catalog(self) -> int:
        return self._catalog.refresh_flyweight()

    def create_candidate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_ballot_editable()
        return self._catalog.create(payload)

    def update_candidate(self, candidate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._assert_ballot_editable()
        return self._catalog.update(candidate_id, payload)

    def set_candidate_active(self, candidate_id: str, is_active: bool) -> Dict[str, Any]:
        self._assert_ballot_editable()
        if not is_active and self._catalog.count_active() <= 2:
            raise ValueError("La papeleta necesita al menos dos candidatos activos.")
        return self._catalog.set_active(candidate_id, is_active)
