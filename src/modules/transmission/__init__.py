"""Paquete para transmisión y despacho multicanal de boletines mediante Bridge."""
from src.modules.transmission.bulletin_bridge import (
    ITransmissionChannel,
    ConsoleTransmissionChannel,
    FileTransmissionChannel,
    MemoryAuditSinkTransmissionChannel,
    ElectoralBulletin,
    PreliminaryBulletin,
    AuditAlertBulletin,
    OfficialClosingBulletin,
)

__all__ = [
    "ITransmissionChannel",
    "ConsoleTransmissionChannel",
    "FileTransmissionChannel",
    "MemoryAuditSinkTransmissionChannel",
    "ElectoralBulletin",
    "PreliminaryBulletin",
    "AuditAlertBulletin",
    "OfficialClosingBulletin",
]
