"""Adaptador de censo para payloads JSON."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.modules.census.contracts import ICensusRegistry, VoterCensusRecord


class JsonCensusAdapter(ICensusRegistry):
    """Traduce un JSON heterogéneo al contrato del censo."""

    def __init__(self, raw_json_payload: str | Dict[str, Any]) -> None:
        data = json.loads(raw_json_payload) if isinstance(raw_json_payload, str) else raw_json_payload
        self._records_by_id: Dict[str, VoterCensusRecord] = {}
        self._parse_payload(data)

    def _parse_payload(self, data: Dict[str, Any]) -> None:
        items: List[Dict[str, Any]] = data.get(
            "electores", data.get("estudiantes", data.get("citizens", []))
        )
        for item in items:
            doc = str(item.get("documento_id", item.get("codigo", item.get("id", "")))).strip()
            name = item.get("nombre_completo", item.get("nombres", item.get("name", "Desconocido"))).strip()
            station = item.get("mesa_asignada", item.get("mesa", item.get("station", "MESA-GENERAL"))).strip()
            raw_eligible = item.get("habilitado", item.get("activo", item.get("eligible", True)))
            if isinstance(raw_eligible, str):
                eligible = raw_eligible.strip().lower() in {"true", "1", "si", "sí", "habilitado", "activo"}
            else:
                eligible = bool(raw_eligible)
            if doc:
                self._records_by_id[doc] = VoterCensusRecord(
                    document_id=doc,
                    full_name=name,
                    assigned_station_id=station,
                    is_eligible=eligible,
                    source_type="JSON_ADAPTER",
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
