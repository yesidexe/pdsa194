"""Ciclo de vida de la jornada electoral mediante el patrón State.

Cada estado conoce qué transiciones permite. La fachada no decide con banderas
sueltas: delega en el estado actual y este persiste el cambio en ``election_state``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Type

from src.core.database import (
    count_ballots,
    get_election_status,
    init_db,
    set_election_status,
)


class ElectionStatus(str, Enum):
    """Estados posibles de una jornada electoral."""

    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    TALLIED = "TALLIED"


class InvalidStateTransition(ValueError):
    """La operación no es válida para el estado actual de la jornada."""


class ElectionState(ABC):
    """Interfaz común de los estados. Solo el estado actual decide."""

    status: ElectionStatus

    @abstractmethod
    def open(self, machine: "ElectionStateMachine") -> None:
        """Intenta abrir la jornada."""

    @abstractmethod
    def close(self, machine: "ElectionStateMachine") -> None:
        """Intenta cerrar la jornada."""

    @abstractmethod
    def tally(self, machine: "ElectionStateMachine") -> None:
        """Intenta generar el acta."""

    @abstractmethod
    def reset(self, machine: "ElectionStateMachine") -> None:
        """Vuelve a borrador después de borrar los votos."""

    @abstractmethod
    def can_edit_ballot(self, has_votes: bool) -> bool:
        """Indica si la papeleta todavía se puede configurar."""

    def _invalid(self, action: str) -> InvalidStateTransition:
        return InvalidStateTransition(
            f"No se puede {action} la jornada desde el estado {self.status.value}."
        )


class DraftState(ElectionState):
    """Jornada en configuración: se pueden cargar candidatos y opciones."""

    status = ElectionStatus.DRAFT

    def open(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.OPEN)

    def close(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.CLOSED)

    def tally(self, machine: "ElectionStateMachine") -> None:
        raise self._invalid("escrutar")

    def reset(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.DRAFT)

    def can_edit_ballot(self, has_votes: bool) -> bool:
        return True


class OpenState(ElectionState):
    """Urna abierta: recibe votos y no permite editar la papeleta."""

    status = ElectionStatus.OPEN

    def open(self, machine: "ElectionStateMachine") -> None:
        return None

    def close(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.CLOSED)

    def tally(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.TALLIED)

    def reset(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.DRAFT)

    def can_edit_ballot(self, has_votes: bool) -> bool:
        return False


class ClosedState(ElectionState):
    """Urna cerrada sin acta: se puede reabrir o escrutar."""

    status = ElectionStatus.CLOSED

    def open(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.OPEN)

    def close(self, machine: "ElectionStateMachine") -> None:
        return None

    def tally(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.TALLIED)

    def reset(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.DRAFT)

    def can_edit_ballot(self, has_votes: bool) -> bool:
        return not has_votes


class TalliedState(ElectionState):
    """Acta generada: la jornada es inmutable hasta un reinicio explícito."""

    status = ElectionStatus.TALLIED

    def open(self, machine: "ElectionStateMachine") -> None:
        raise self._invalid("abrir")

    def close(self, machine: "ElectionStateMachine") -> None:
        return None

    def tally(self, machine: "ElectionStateMachine") -> None:
        raise self._invalid("escrutar")

    def reset(self, machine: "ElectionStateMachine") -> None:
        machine.transition_to(ElectionStatus.DRAFT)

    def can_edit_ballot(self, has_votes: bool) -> bool:
        return False


_STATES: Dict[ElectionStatus, Type[ElectionState]] = {
    ElectionStatus.DRAFT: DraftState,
    ElectionStatus.OPEN: OpenState,
    ElectionStatus.CLOSED: ClosedState,
    ElectionStatus.TALLIED: TalliedState,
}

_STATUS_LABELS = {
    ElectionStatus.DRAFT: "BORRADOR",
    ElectionStatus.OPEN: "ABIERTA",
    ElectionStatus.CLOSED: "CERRADA",
    ElectionStatus.TALLIED: "ESCRUTADA",
}


class ElectionStateMachine:
    """Contexto del patrón: carga el estado persistido y delega las operaciones."""

    def __init__(self, election_type: str) -> None:
        init_db()
        self.election_type = str(election_type).upper().strip()
        self._state = self._build_state(get_election_status(self.election_type))

    def _build_state(self, raw_status: str) -> ElectionState:
        try:
            status = ElectionStatus(str(raw_status).upper().strip())
        except ValueError:
            status = ElectionStatus.DRAFT
        return _STATES[status]()

    def transition_to(self, status: ElectionStatus) -> None:
        set_election_status(self.election_type, status.value)
        self._state = self._build_state(status.value)

    @property
    def status(self) -> ElectionStatus:
        return self._state.status

    @property
    def status_label(self) -> str:
        return _STATUS_LABELS[self._state.status]

    @property
    def is_open(self) -> bool:
        return self._state.status is ElectionStatus.OPEN

    @property
    def is_tallied(self) -> bool:
        return self._state.status is ElectionStatus.TALLIED

    def open(self) -> None:
        self._state.open(self)

    def close(self) -> None:
        self._state.close(self)

    def tally(self) -> None:
        self._state.tally(self)

    def reset(self) -> None:
        self._state.reset(self)

    def can_edit_ballot(self) -> bool:
        return self._state.can_edit_ballot(count_ballots(self.election_type) > 0)
