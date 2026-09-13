"""Módulo para la clonación y replicación de mesas de votación mediante el patrón Prototype."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TypeVar, Generic
import copy

T = TypeVar("T", bound="Prototype")


class Prototype(ABC, Generic[T]):
    """Interfaz abstracta que define el contrato de clonación profunda."""

    @abstractmethod
    def clone(self) -> T:
        """Retorna una copia profunda e independiente del objeto."""
        pass


@dataclass
class VotingStation(Prototype["VotingStation"]):
    """Representa una mesa de votación parametrizable y clonable."""
    station_id: str
    polling_place: str
    zone_code: str
    allowed_ballot_types: List[str] = field(default_factory=list)
    hardware_terminal_code: Optional[str] = None
    is_active: bool = True
    assigned_officers: List[str] = field(default_factory=list)

    def clone(self) -> VotingStation:
        """Genera una copia profunda asegurando independencia de listas mutables."""
        cloned_station = copy.deepcopy(self)
        return cloned_station

    def assign_station(
        self,
        new_station_id: str,
        new_terminal_code: str,
        new_officers: Optional[List[str]] = None,
    ) -> VotingStation:
        """Personaliza la estación clonada con identificadores únicos."""
        self.station_id = new_station_id
        self.hardware_terminal_code = new_terminal_code
        if new_officers is not None:
            self.assigned_officers = list(new_officers)
        return self


class StationPrototypeRegistry:
    """Registro de catálogo para almacenar y clonar plantillas de mesas de votación."""

    def __init__(self) -> None:
        self._prototypes: Dict[str, VotingStation] = {}

    def register_prototype(self, prototype_key: str, station: VotingStation) -> None:
        self._prototypes[prototype_key] = station

    def get_clone(self, prototype_key: str) -> VotingStation:
        if prototype_key not in self._prototypes:
            raise KeyError(f"Plantilla prototipo '{prototype_key}' no registrada en el catálogo.")
        return self._prototypes[prototype_key].clone()
