"""Transiciones del ciclo de vida de la jornada."""
from __future__ import annotations

import pytest

from src.modules.election import ElectionStateMachine, ElectionStatus, InvalidStateTransition


def test_election_state_machine_transitions():
    """State permite solo transiciones válidas y las persiste."""
    machine = ElectionStateMachine("TEST-STATE")
    assert machine.status is ElectionStatus.DRAFT
    assert machine.can_edit_ballot() is True

    machine.open()
    assert machine.status is ElectionStatus.OPEN
    assert machine.is_open is True
    assert machine.can_edit_ballot() is False

    machine.close()
    assert machine.status is ElectionStatus.CLOSED
    assert machine.is_open is False

    machine.tally()
    assert machine.status is ElectionStatus.TALLIED
    assert machine.is_tallied is True

    with pytest.raises(InvalidStateTransition):
        machine.open()

    machine.reset()
    assert machine.status is ElectionStatus.DRAFT
