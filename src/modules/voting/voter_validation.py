"""Cadena de validación del elector (Chain of Responsibility).

Cada eslabón resuelve una comprobación y detiene el flujo con un motivo claro.
La fachada no acumula condicionales: arma la cadena una vez y la ejecuta.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from src.modules.census.census_adapter import ICensusRegistry, VoterCensusRecord
from src.modules.election.election_factory import ElectoralFamilyFactory
from src.modules.election.state import ElectionStateMachine
from src.modules.voting.vote_store import has_voted


class VoterValidationError(ValueError):
    """El elector no pasó una comprobación; el mensaje es apto para el usuario."""


@dataclass
class VoterValidationContext:
    """Datos que viajan por la cadena y resultado parcial."""

    document_id: str
    pin: str
    election_type: str
    check_existing: bool = True
    record: Optional[VoterCensusRecord] = None


class VoterValidator(ABC):
    """Eslabón de la cadena."""

    @abstractmethod
    def validate(self, context: VoterValidationContext) -> None:
        """Valida o lanza ``VoterValidationError``."""


class PollOpenValidator(VoterValidator):
    """La jornada debe estar abierta."""

    def __init__(self, state_machine: ElectionStateMachine) -> None:
        self._state_machine = state_machine

    def validate(self, context: VoterValidationContext) -> None:
        if not self._state_machine.is_open:
            raise VoterValidationError("La jornada de votación no está abierta.")


class CredentialFormatValidator(VoterValidator):
    """El documento debe tener el formato de la modalidad activa."""

    def __init__(self, family_factory: Optional[ElectoralFamilyFactory]) -> None:
        self._family_factory = family_factory

    def validate(self, context: VoterValidationContext) -> None:
        if self._family_factory is None:
            return
        validator = self._family_factory.create_validator()
        if not validator.validate_credential(context.document_id):
            raise VoterValidationError(
                f"Formato de credencial inválido para {validator.get_document_type()}."
            )


class CensusAuthenticationValidator(VoterValidator):
    """Documento + PIN deben existir en el censo y estar habilitados."""

    def __init__(self, census: Optional[ICensusRegistry]) -> None:
        self._census = census

    def validate(self, context: VoterValidationContext) -> None:
        if self._census is None:
            raise VoterValidationError("El censo electoral no está disponible.")
        record = self._census.authenticate(context.document_id, context.pin)
        if record is None:
            raise VoterValidationError("Documento o PIN incorrecto, o elector no habilitado.")
        context.record = record


class AlreadyVotedValidator(VoterValidator):
    """Evita el doble voto en la verificación previa (la base es la garantía final)."""

    def validate(self, context: VoterValidationContext) -> None:
        if context.check_existing and has_voted(context.election_type, context.document_id):
            raise VoterValidationError(
                "El ciudadano ya ejerció su derecho al voto en esta jornada."
            )


class EligibilityValidator(VoterValidator):
    """El registro censal debe estar explícitamente habilitado."""

    def validate(self, context: VoterValidationContext) -> None:
        if context.record is None or not context.record.is_eligible:
            raise VoterValidationError("Documento o PIN incorrecto, o elector no habilitado.")


class VoterValidationChain:
    """Recorre los eslabones en orden; el primero que falla detiene la cadena."""

    def __init__(self, validators: List[VoterValidator]) -> None:
        self._validators = list(validators)

    def validate(self, context: VoterValidationContext) -> None:
        for validator in self._validators:
            validator.validate(context)
