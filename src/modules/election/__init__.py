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
from src.modules.election.jurisdiction_composite import (
    ElectoralUnit,
    VotingStationLeaf,
    ElectoralJurisdictionComposite,
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
    "ElectoralUnit",
    "VotingStationLeaf",
    "ElectoralJurisdictionComposite",
]
