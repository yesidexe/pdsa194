"""Módulo para la transmisión multicanal de boletines y alertas electorales mediante el patrón Bridge."""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# 1. JERARQUÍA DEL IMPLEMENTADOR (Implementor) - Canales Físicos de Salida
# ============================================================================

class ITransmissionChannel(ABC):
    """Interfaz Implementor que define el contrato de transporte de datos."""

    @abstractmethod
    def send_payload(self, destination: str, payload: Dict[str, Any]) -> bool:
        """Transmite el paquete de datos al destino indicado."""
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """Identificador textual del canal de transmisión."""
        pass


class ConsoleTransmissionChannel(ITransmissionChannel):
    """Implementador concreto que despacha transmisiones a la consola/log oficial."""

    def send_payload(self, destination: str, payload: Dict[str, Any]) -> bool:
        timestamp = payload.get("timestamp", datetime.now(timezone.utc).isoformat())
        bulletin_type = payload.get("type", "GENERAL")
        print(f"\n[CANAL CONSOLA :: {destination}] ({timestamp}) Tipo: {bulletin_type}")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return True

    def get_channel_name(self) -> str:
        return "CONSOLE_LOG"


class FileTransmissionChannel(ITransmissionChannel):
    """Implementador concreto que almacena y sella boletines en el sistema de archivos."""

    def __init__(self, output_dir: str = "/tmp") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def send_payload(self, destination: str, payload: Dict[str, Any]) -> bool:
        safe_name = destination.replace("/", "_").replace(" ", "_").lower()
        file_path = self._output_dir / f"transmission_{safe_name}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return True

    def get_channel_name(self) -> str:
        return f"FILE_STORAGE ({self._output_dir})"


class MemoryAuditSinkTransmissionChannel(ITransmissionChannel):
    """Implementador concreto en memoria para testing automatizado y auditoría local."""

    def __init__(self) -> None:
        self.sent_messages: List[Dict[str, Any]] = []

    def send_payload(self, destination: str, payload: Dict[str, Any]) -> bool:
        self.sent_messages.append({"destination": destination, "payload": dict(payload)})
        return True

    def get_channel_name(self) -> str:
        return "IN_MEMORY_SINK"


# ============================================================================
# 2. JERARQUÍA DE LA ABSTRACCIÓN (Abstraction) - Tipos de Boletines
# ============================================================================

class ElectoralBulletin(ABC):
    """Abstracción base que mantiene una referencia al implementador (Bridge)."""

    def __init__(self, channel: ITransmissionChannel) -> None:
        self._channel: ITransmissionChannel = channel

    @property
    def channel(self) -> ITransmissionChannel:
        return self._channel

    @channel.setter
    def channel(self, new_channel: ITransmissionChannel) -> None:
        """Permite intercambiar el canal de transporte en tiempo de ejecución."""
        self._channel = new_channel

    @abstractmethod
    def dispatch(self, destination: str) -> bool:
        """Operación de alto nivel que compone el mensaje y delega en el canal."""
        pass


class PreliminaryBulletin(ElectoralBulletin):
    """Abstracción refinada: Boletín oficial de escrutinio parcial en vivo."""

    def __init__(
        self,
        channel: ITransmissionChannel,
        bulletin_number: int,
        election_title: str,
        processed_tables: List[str],
        candidate_votes: Dict[str, int],
    ) -> None:
        super().__init__(channel)
        self.bulletin_number = bulletin_number
        self.election_title = election_title
        self.processed_tables = list(processed_tables)
        self.candidate_votes = dict(candidate_votes)

    def dispatch(self, destination: str) -> bool:
        total_votes = sum(self.candidate_votes.values())
        payload = {
            "type": "PRELIMINARY_BULLETIN",
            "bulletin_number": self.bulletin_number,
            "election_title": self.election_title,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tables_processed_count": len(self.processed_tables),
            "tables": self.processed_tables,
            "candidate_votes": self.candidate_votes,
            "total_votes_tallied": total_votes,
        }
        return self._channel.send_payload(destination=destination, payload=payload)


class AuditAlertBulletin(ElectoralBulletin):
    """Abstracción refinada: Alerta prioritaria de seguridad o anomalía de auditoría."""

    def __init__(
        self,
        channel: ITransmissionChannel,
        alert_code: str,
        severity: str,
        description: str,
        affected_station_id: str,
    ) -> None:
        super().__init__(channel)
        self.alert_code = alert_code
        self.severity = severity.upper()
        self.description = description
        self.affected_station_id = affected_station_id

    def dispatch(self, destination: str) -> bool:
        payload = {
            "type": "AUDIT_SECURITY_ALERT",
            "alert_code": self.alert_code,
            "severity": self.severity,
            "station_id": self.affected_station_id,
            "description": self.description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return self._channel.send_payload(destination=destination, payload=payload)


class OfficialClosingBulletin(ElectoralBulletin):
    """Abstracción refinada: Boletín formal de cierre definitivo de urna y escrutinio."""

    def __init__(
        self,
        channel: ITransmissionChannel,
        election_title: str,
        jurisdiction: str,
        total_votes: int,
        integrity_hash: str,
    ) -> None:
        super().__init__(channel)
        self.election_title = election_title
        self.jurisdiction = jurisdiction
        self.total_votes = total_votes
        self.integrity_hash = integrity_hash

    def dispatch(self, destination: str) -> bool:
        payload = {
            "type": "OFFICIAL_CLOSING_BULLETIN",
            "election_title": self.election_title,
            "jurisdiction": self.jurisdiction,
            "total_votes": self.total_votes,
            "integrity_hash": self.integrity_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return self._channel.send_payload(destination=destination, payload=payload)
