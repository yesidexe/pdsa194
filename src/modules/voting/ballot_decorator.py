"""Módulo para la aplicación dinámica de sellos y firmas de seguridad mediante el patrón Decorator."""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import hmac
from typing import Any, Dict, List
from src.modules.voting.ballot_factory import Ballot


class BallotSecurityDecorator(Ballot, ABC):
    """Decorador abstracto base que envuelve una papeleta electoral conservando su contrato."""

    def __init__(self, wrapped_ballot: Ballot) -> None:
        super().__init__(ballot_id=wrapped_ballot.ballot_id, issued_at=wrapped_ballot.issued_at)
        object.__setattr__(self, "_wrapped_ballot", wrapped_ballot)

    @property
    def wrapped_ballot(self) -> Ballot:
        return getattr(self, "_wrapped_ballot")

    @property
    def base_ballot(self) -> Ballot:
        """Desenvuelve recursivamente las capas de seguridad para acceder a la papeleta original."""
        if isinstance(self.wrapped_ballot, BallotSecurityDecorator):
            return self.wrapped_ballot.base_ballot
        return self.wrapped_ballot

    def get_selection(self) -> str:
        """Delega la obtención de la opción elegida al componente envuelto."""
        return self.wrapped_ballot.get_selection()

    @abstractmethod
    def get_security_metadata(self) -> Dict[str, Any]:
        """Recupera los metadatos de seguridad acumulados por este decorador y sus capas internas."""
        pass

    def get_audit_trail(self) -> List[str]:
        """Construye la lista cronológica de capas de seguridad aplicadas a la papeleta."""
        trail: List[str] = []
        if isinstance(self.wrapped_ballot, BallotSecurityDecorator):
            trail.extend(self.wrapped_ballot.get_audit_trail())
        trail.append(self.__class__.__name__)
        return trail


class TimestampSecurityDecorator(BallotSecurityDecorator):
    """Decorador concreto que agrega un sello de tiempo UTC a la papeleta."""

    def __init__(
        self,
        wrapped_ballot: Ballot,
        authority_name: str = "CNE-ATOMIC-CLOCK-01",
    ) -> None:
        super().__init__(wrapped_ballot)
        now_utc = datetime.now(timezone.utc)
        object.__setattr__(self, "_timestamp_seal", now_utc.isoformat())
        object.__setattr__(self, "_authority_name", authority_name)

    def get_security_metadata(self) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        if isinstance(self.wrapped_ballot, BallotSecurityDecorator):
            metadata.update(self.wrapped_ballot.get_security_metadata())

        metadata["timestamp_seal"] = getattr(self, "_timestamp_seal")
        metadata["time_authority"] = getattr(self, "_authority_name")
        return metadata


class DigitalSignatureDecorator(BallotSecurityDecorator):
    """Decorador concreto que agrega un sello HMAC-SHA256 a la papeleta."""

    def __init__(
        self,
        wrapped_ballot: Ballot,
        signing_key: str = "MASTER_ELECTORAL_HMAC_KEY_2026",
        officer_token: str = "TERMINAL-OFFICER-SECURE-KEY",
    ) -> None:
        super().__init__(wrapped_ballot)
        signature = self._compute_signature(signing_key, officer_token)
        object.__setattr__(self, "_signature", signature)
        object.__setattr__(self, "_officer_token", officer_token)

    def _compute_signature(self, signing_key: str, officer_token: str) -> str:
        canonical_content = f"{self.ballot_id}:{self.get_selection()}:{self.issued_at.isoformat()}:{officer_token}"
        return hmac.new(
            key=signing_key.encode("utf-8"),
            msg=canonical_content.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def verify_signature(self, signing_key: str) -> bool:
        """Permite a los auditores comprobar matemáticamente que el voto no fue manipulado."""
        expected = self._compute_signature(signing_key, getattr(self, "_officer_token"))
        return hmac.compare_digest(getattr(self, "_signature"), expected)

    def get_security_metadata(self) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        if isinstance(self.wrapped_ballot, BallotSecurityDecorator):
            metadata.update(self.wrapped_ballot.get_security_metadata())

        metadata["digital_signature"] = getattr(self, "_signature")
        metadata["signature_algorithm"] = "HMAC-SHA256"
        metadata["officer_token"] = getattr(self, "_officer_token")
        return metadata


class AuditWatermarkDecorator(BallotSecurityDecorator):
    """Decorador concreto que añade marca de agua y código de recibo para el ciudadano."""

    def __init__(
        self,
        wrapped_ballot: Ballot,
        watermark_text: str = "OFICIAL - PROCESO ELECTORAL REGISTRADO",
        citizen_receipt_code: str = "",
    ) -> None:
        super().__init__(wrapped_ballot)
        if not citizen_receipt_code:
            receipt = hashlib.sha256(f"{self.ballot_id}:RECEIPT".encode("utf-8")).hexdigest()[:12].upper()
        else:
            receipt = citizen_receipt_code

        object.__setattr__(self, "_watermark_text", watermark_text)
        object.__setattr__(self, "_citizen_receipt_code", receipt)

    def get_security_metadata(self) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        if isinstance(self.wrapped_ballot, BallotSecurityDecorator):
            metadata.update(self.wrapped_ballot.get_security_metadata())

        metadata["watermark"] = getattr(self, "_watermark_text")
        metadata["receipt_code"] = getattr(self, "_citizen_receipt_code")
        return metadata
