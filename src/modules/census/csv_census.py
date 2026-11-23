"""Adaptador de censo para archivos CSV."""
from __future__ import annotations

import csv
import io
from typing import Dict, Optional

from src.modules.census.contracts import ICensusRegistry, VoterCensusRecord


class CsvCensusAdapter(ICensusRegistry):
    """Normaliza columnas de un CSV al contrato del censo."""

    def __init__(self, csv_content: str, delimiter: str = ",") -> None:
        self._records_by_id: Dict[str, VoterCensusRecord] = {}
        self._parse_csv(csv_content, delimiter)

    def _parse_csv(self, csv_content: str, delimiter: str) -> None:
        reader = csv.DictReader(io.StringIO(csv_content.strip()), delimiter=delimiter)
        for row in reader:
            normalized = {key.strip().lower(): value.strip() for key, value in row.items() if key}
            doc = (
                normalized.get("cedula")
                or normalized.get("documento")
                or normalized.get("document_id")
                or normalized.get("identificacion", "")
            )
            name = (
                normalized.get("nombre")
                or normalized.get("nombre_completo")
                or normalized.get("nombres_apellidos")
                or normalized.get("full_name", "Desconocido")
            )
            station = (
                normalized.get("mesa")
                or normalized.get("mesa_asignada")
                or normalized.get("station_id", "MESA-GENERAL")
            )
            status = (normalized.get("habilitado") or normalized.get("estado") or normalized.get("eligible", "si")).lower()
            if doc:
                self._records_by_id[doc] = VoterCensusRecord(
                    document_id=doc,
                    full_name=name,
                    assigned_station_id=station,
                    is_eligible=status in ("si", "sí", "true", "1", "habilitado", "activo"),
                    source_type="CSV_ADAPTER",
                )

    def is_eligible(self, document_id: str) -> bool:
        record = self._records_by_id.get(str(document_id).strip())
        return record.is_eligible if record else False

    def get_voter_record(self, document_id: str) -> Optional[VoterCensusRecord]:
        return self._records_by_id.get(str(document_id).strip())

    def get_total_registered(self) -> int:
        return len(self._records_by_id)

    def get_total_eligible(self) -> int:
        return sum(1 for record in self._records_by_id.values() if record.is_eligible)

    def authenticate(self, document_id: str, pin: str) -> Optional[VoterCensusRecord]:
        return None
