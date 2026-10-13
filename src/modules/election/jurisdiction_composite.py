"""Módulo para la organización jerárquica territorial y de recintos electorales mediante el patrón Composite."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
from src.modules.election.station_prototype import VotingStation


class ElectoralUnit(ABC):
    """Componente abstracto base para elementos de la jerarquía territorial electoral."""

    def __init__(self, unit_id: str, name: str) -> None:
        self.unit_id = unit_id
        self.name = name

    @abstractmethod
    def count_stations(self) -> int:
        """Devuelve el total de mesas de votación contenidas en esta unidad."""
        pass

    @abstractmethod
    def get_station_ids(self) -> List[str]:
        """Recupera la lista plana de identificadores de mesas de votación."""
        pass

    @abstractmethod
    def display_hierarchy(self, indent: int = 0) -> str:
        """Genera una representación jerárquica estructurada en texto."""
        pass

    @abstractmethod
    def find_unit(self, unit_id: str) -> Optional[ElectoralUnit]:
        """Busca recursivamente una unidad por su identificador."""
        pass


class VotingStationLeaf(ElectoralUnit):
    """Hoja (Leaf) que representa una mesa de votación individual terminal."""

    def __init__(self, station: VotingStation) -> None:
        super().__init__(unit_id=station.station_id, name=f"Mesa {station.station_id}")
        self.station = station

    def count_stations(self) -> int:
        return 1

    def get_station_ids(self) -> List[str]:
        return [self.station.station_id]

    def display_hierarchy(self, indent: int = 0) -> str:
        prefix = "  " * indent
        officers = ", ".join(self.station.assigned_officers) if self.station.assigned_officers else "Sin jurados"
        return f"{prefix}└── [MESA] {self.station.station_id} (Terminal: {self.station.hardware_terminal_code} | Jurados: {officers})"

    def find_unit(self, unit_id: str) -> Optional[ElectoralUnit]:
        return self if self.unit_id == unit_id else None


class ElectoralJurisdictionComposite(ElectoralUnit):
    """Compuesto (Composite) que agrupa unidades electorales (zonas, colegios, facultades o mesas)."""

    def __init__(self, unit_id: str, name: str, jurisdiction_type: str = "ZONA") -> None:
        super().__init__(unit_id, name)
        self.jurisdiction_type = jurisdiction_type.upper()
        self._children: List[ElectoralUnit] = []

    def add(self, unit: ElectoralUnit) -> ElectoralJurisdictionComposite:
        """Añade una subunidad (hoja o compuesto) a la jerarquía."""
        if unit not in self._children:
            self._children.append(unit)
        return self

    def remove(self, unit: ElectoralUnit) -> ElectoralJurisdictionComposite:
        """Elimina una subunidad de la jerarquía."""
        if unit in self._children:
            self._children.remove(unit)
        return self

    def count_stations(self) -> int:
        """Calcula recursivamente el total de mesas en todos los niveles inferiores."""
        return sum(child.count_stations() for child in self._children)

    def get_station_ids(self) -> List[str]:
        """Consolida la lista de mesas a lo largo de todo el subárbol."""
        station_ids: List[str] = []
        for child in self._children:
            station_ids.extend(child.get_station_ids())
        return station_ids

    def display_hierarchy(self, indent: int = 0) -> str:
        prefix = "  " * indent
        lines = [f"{prefix}├── [{self.jurisdiction_type}] {self.name} (ID: {self.unit_id} | Total Mesas: {self.count_stations()})"]
        for child in self._children:
            lines.append(child.display_hierarchy(indent + 1))
        return "\n".join(lines)

    def find_unit(self, unit_id: str) -> Optional[ElectoralUnit]:
        if self.unit_id == unit_id:
            return self
        for child in self._children:
            result = child.find_unit(unit_id)
            if result is not None:
                return result
        return None
