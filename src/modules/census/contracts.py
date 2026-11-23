"""Contrato común del censo electoral."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class VoterCensusRecord:
    """Ficha canónica e inmutable de un elector."""

    document_id: str
    full_name: str
    assigned_station_id: str
    is_eligible: bool
    source_type: str


class ICensusRegistry(ABC):
    """Puerto que deben implementar todas las fuentes de censo."""

    @abstractmethod
    def is_eligible(self, document_id: str) -> bool:
        """Indica si el elector existe y está habilitado."""

    @abstractmethod
    def get_voter_record(self, document_id: str) -> Optional[VoterCensusRecord]:
        """Devuelve la ficha del elector, o ``None`` si no existe."""

    @abstractmethod
    def get_total_registered(self) -> int:
        """Número total de electores registrados."""

    @abstractmethod
    def get_total_eligible(self) -> int:
        """Número de electores habilitados."""

    @abstractmethod
    def authenticate(self, document_id: str, pin: str) -> Optional[VoterCensusRecord]:
        """Valida documento + PIN; las fuentes sin PIN fallan cerrado."""
