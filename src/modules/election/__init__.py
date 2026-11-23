"""Módulo de elecciones: familias, estados y reglas de escrutinio."""
from src.modules.election.election_factory import (
    CredentialValidator,
    NationalCitizenValidator,
    StudentCodeValidator,
    BallotHeader,
    NationalBallotHeader,
    UniversityBallotHeader,
    TallyRule,
    AbsoluteMajorityTallyRule,
    SimplePluralityTallyRule,
    ElectoralFamilyFactory,
    NationalElectionFactory,
    UniversityElectionFactory,
)
from src.modules.election.state import (
    ElectionState,
    ElectionStateMachine,
    ElectionStatus,
    InvalidStateTransition,
)

__all__ = [
    "CredentialValidator",
    "NationalCitizenValidator",
    "StudentCodeValidator",
    "BallotHeader",
    "NationalBallotHeader",
    "UniversityBallotHeader",
    "TallyRule",
    "AbsoluteMajorityTallyRule",
    "SimplePluralityTallyRule",
    "ElectoralFamilyFactory",
    "NationalElectionFactory",
    "UniversityElectionFactory",
    "ElectionState",
    "ElectionStateMachine",
    "ElectionStatus",
    "InvalidStateTransition",
]
