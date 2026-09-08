"""Módulo para la creación de papeletas de votación desacopladas."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid


@dataclass(frozen=True)
class Ballot(ABC):
    """Producto abstracto base para cualquier sufragio emitido."""
    ballot_id: str
    issued_at: datetime

    @abstractmethod
    def get_selection(self) -> str:
        """Devuelve la opción seleccionada de forma legible."""
        pass


@dataclass(frozen=True)
class CandidateBallot(Ballot):
    """Papeleta emitida para un candidato o fórmula nominal."""
    candidate_id: str
    candidate_name: str
    party_name: str

    def get_selection(self) -> str:
        return f"{self.candidate_name} ({self.party_name})"


@dataclass(frozen=True)
class ReferendumBallot(Ballot):
    """Papeleta para consultas populares o referéndums temáticos."""
    question_code: str
    decision: str  # Ej: 'SI', 'NO', 'ABSTENCION'

    def get_selection(self) -> str:
        return f"[{self.question_code}] {self.decision.upper()}"


@dataclass(frozen=True)
class BlankBallot(Ballot):
    """Papeleta en blanco con validez legal."""
    category: str

    def get_selection(self) -> str:
        return f"VOTO EN BLANCO - {self.category.upper()}"


class BallotCreator(ABC):
    """Creador abstracto que define el Factory Method y la lógica de emisión."""

    @abstractmethod
    def create_ballot(self, **kwargs) -> Ballot:
        """Factory Method que deben implementar las subclases concretas."""
        pass

    def issue_ballot(self, **kwargs) -> Ballot:
        """Operación de negocio que procesa y registra la papeleta emitida."""
        ballot = self.create_ballot(**kwargs)
        return ballot


class CandidateBallotCreator(BallotCreator):
    """Creador concreto para votos uninominales o de listas cerradas."""

    def create_ballot(self, **kwargs) -> CandidateBallot:
        return CandidateBallot(
            ballot_id=str(uuid.uuid4()),
            issued_at=datetime.utcnow(),
            candidate_id=kwargs["candidate_id"],
            candidate_name=kwargs["candidate_name"],
            party_name=kwargs.get("party_name", "Independiente"),
        )


class ReferendumBallotCreator(BallotCreator):
    """Creador concreto para votos de tipo consulta/plebiscito."""

    def create_ballot(self, **kwargs) -> ReferendumBallot:
        return ReferendumBallot(
            ballot_id=str(uuid.uuid4()),
            issued_at=datetime.utcnow(),
            question_code=kwargs["question_code"],
            decision=kwargs["decision"],
        )


class BlankBallotCreator(BallotCreator):
    """Creador concreto para votos en blanco."""

    def create_ballot(self, **kwargs) -> BlankBallot:
        return BlankBallot(
            ballot_id=str(uuid.uuid4()),
            issued_at=datetime.utcnow(),
            category=kwargs.get("category", "General"),
        )
