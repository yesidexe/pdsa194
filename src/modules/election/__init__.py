"""Módulo de elecciones."""
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
from src.modules.election.station_prototype import (
    Prototype,
    VotingStation,
    StationPrototypeRegistry,
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
    "Prototype",
    "VotingStation",
    "StationPrototypeRegistry",
]

