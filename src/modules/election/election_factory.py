"""Módulo para la creación de familias coherentes de componentes electorales."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any


# --- PRODUCTO FAMILIA A: Validador de Credencial del Votante ---
class CredentialValidator(ABC):
    """Interfaz abstracta para validar el documento del votante según la elección."""

    @abstractmethod
    def validate_credential(self, document_id: str) -> bool:
        pass

    @abstractmethod
    def get_document_type(self) -> str:
        pass


class NationalCitizenValidator(CredentialValidator):
    """Validador para elecciones nacionales (Cédula de Ciudadanía)."""

    def validate_credential(self, document_id: str) -> bool:
        return document_id.isdigit() and 6 <= len(document_id) <= 10

    def get_document_type(self) -> str:
        return "Cédula de Ciudadanía (C.C.)"


class StudentCodeValidator(CredentialValidator):
    """Validador para elecciones universitarias (Código Estudiantil alfanumérico)."""

    def validate_credential(self, document_id: str) -> bool:
        return len(document_id) >= 5 and any(c.isdigit() for c in document_id)

    def get_document_type(self) -> str:
        return "Código de Carnet Estudiantil"


# --- PRODUCTO FAMILIA B: Encabezado Oficial de la Papeleta ---
class BallotHeader(ABC):
    """Interfaz abstracta para el encabezado oficial de las papeletas."""

    @abstractmethod
    def render_header(self) -> str:
        pass


class NationalBallotHeader(BallotHeader):
    """Encabezado oficial para elecciones de orden nacional."""

    def render_header(self) -> str:
        return "REPÚBLICA DE COLOMBIA - REGISTRADURÍA NACIONAL DEL ESTADO CIVIL"


class UniversityBallotHeader(BallotHeader):
    """Encabezado oficial para elecciones institucionales o de consejo estudiantil."""

    def render_header(self) -> str:
        return "UNIVERSIDAD DE INVESTIGACIÓN Y DESARROLLO - CONSEJO SUPERIOR"


# --- PRODUCTO FAMILIA C: Regla de Escrutinio / Decisión ---
class TallyRule(ABC):
    """Interfaz abstracta para determinar el criterio de victoria en el escrutinio."""

    @abstractmethod
    def evaluate_winner(self, votes_summary: Dict[str, int]) -> str:
        pass


class AbsoluteMajorityTallyRule(TallyRule):
    """Regla nacional: Requiere más del 50% de votos para ganar sin segunda vuelta."""

    def evaluate_winner(self, votes_summary: Dict[str, int]) -> str:
        total = sum(votes_summary.values())
        if total == 0:
            return "Sin votos registrados"

        for option, count in votes_summary.items():
            if count > total / 2:
                return f"Ganador directo por Mayoría Absoluta (>50%): {option}"
        return "No hay mayoría absoluta: Requiere Segunda Vuelta (Balotaje)"


class SimplePluralityTallyRule(TallyRule):
    """Regla universitaria: Gana la opción con mayor cantidad de votos simples."""

    def evaluate_winner(self, votes_summary: Dict[str, int]) -> str:
        if not votes_summary:
            return "Sin votos registrados"
        winner = max(votes_summary, key=votes_summary.get)
        return f"Ganador electo por Mayoría Simple: {winner} ({votes_summary[winner]} votos)"


# --- FÁBRICA ABSTRACTA ---
class ElectoralFamilyFactory(ABC):
    """Define los métodos de fabricación para una familia coherente de componentes electorales."""

    @abstractmethod
    def create_validator(self) -> CredentialValidator:
        pass

    @abstractmethod
    def create_header(self) -> BallotHeader:
        pass

    @abstractmethod
    def create_tally_rule(self) -> TallyRule:
        pass


# --- FÁBRICAS CONCRETAS ---
class NationalElectionFactory(ElectoralFamilyFactory):
    """Produce componentes específicos para elecciones nacionales."""

    def create_validator(self) -> CredentialValidator:
        return NationalCitizenValidator()

    def create_header(self) -> BallotHeader:
        return NationalBallotHeader()

    def create_tally_rule(self) -> TallyRule:
        return AbsoluteMajorityTallyRule()


class UniversityElectionFactory(ElectoralFamilyFactory):
    """Produce componentes específicos para elecciones universitarias."""

    def create_validator(self) -> CredentialValidator:
        return StudentCodeValidator()

    def create_header(self) -> BallotHeader:
        return UniversityBallotHeader()

    def create_tally_rule(self) -> TallyRule:
        return SimplePluralityTallyRule()
