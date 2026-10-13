"""Módulo de votación."""
from src.modules.voting.ballot_factory import (
    Ballot,
    CandidateBallot,
    ReferendumBallot,
    BlankBallot,
    BallotCreator,
    CandidateBallotCreator,
    ReferendumBallotCreator,
    BlankBallotCreator,
)
from src.modules.voting.ballot_decorator import (
    BallotSecurityDecorator,
    TimestampSecurityDecorator,
    DigitalSignatureDecorator,
    AuditWatermarkDecorator,
)
from src.modules.voting.candidate_flyweight import (
    CandidateMetadataFlyweight,
    CandidateFlyweightFactory,
)

__all__ = [
    "Ballot",
    "CandidateBallot",
    "ReferendumBallot",
    "BlankBallot",
    "BallotCreator",
    "CandidateBallotCreator",
    "ReferendumBallotCreator",
    "BlankBallotCreator",
    "BallotSecurityDecorator",
    "TimestampSecurityDecorator",
    "DigitalSignatureDecorator",
    "AuditWatermarkDecorator",
    "CandidateMetadataFlyweight",
    "CandidateFlyweightFactory",
]
