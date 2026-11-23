"""Auditoría append-only con notificación a varios observadores (Observer)."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.core.database import (
    list_audit_events,
    record_audit_event,
    verify_audit_chain,
)

logger = logging.getLogger("evoting.audit")


@dataclass(frozen=True)
class AuditEvent:
    """Evento inmutable que se publica a todos los observadores."""

    action: str
    user_id: str
    role: str
    status: str
    details: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "user_id": self.user_id,
            "role": self.role,
            "status": self.status,
            "details": self.details,
        }


class AuditObserver(ABC):
    """Interfaz de los interesados en los eventos de auditoría."""

    @abstractmethod
    def on_event(self, event: AuditEvent) -> None:
        """Reacciona al evento."""


class SqliteAuditObserver(AuditObserver):
    """Observador primario: persiste el evento y su hash chain."""

    def on_event(self, event: AuditEvent) -> None:
        record_audit_event(
            action=event.action,
            user_id=event.user_id,
            role=event.role,
            status=event.status,
            details=event.details,
            timestamp=event.timestamp,
        )


class JsonLogObserver(AuditObserver):
    """Observador secundario: deja una línea JSON en el log técnico."""

    def on_event(self, event: AuditEvent) -> None:
        logger.info("audit_event %s", json.dumps(event.as_dict(), ensure_ascii=False))


class AuditEventBus:
    """Sujeto del patrón Observer: mantiene y notifica a los suscriptores."""

    def __init__(self) -> None:
        self._observers: List[AuditObserver] = []

    def subscribe(self, observer: AuditObserver) -> None:
        self._observers.append(observer)

    def publish(self, event: AuditEvent) -> None:
        for observer in self._observers:
            observer.on_event(event)


class AuditService:
    """Fachada mínima de auditoría usada por el Proxy y los estados."""

    def __init__(self, extra_observers: Optional[List[AuditObserver]] = None) -> None:
        self._bus = AuditEventBus()
        self._bus.subscribe(SqliteAuditObserver())
        self._bus.subscribe(JsonLogObserver())
        for observer in extra_observers or []:
            self._bus.subscribe(observer)

    def record(
        self,
        action: str,
        user_id: str,
        role: str,
        status: str,
        details: str = "",
    ) -> None:
        self._bus.publish(
            AuditEvent(
                action=action,
                user_id=user_id,
                role=role,
                status=status,
                details=details,
            )
        )

    def history(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        return list_audit_events(limit=limit, offset=offset)

    def verify(self) -> Dict[str, Any]:
        return verify_audit_chain()
