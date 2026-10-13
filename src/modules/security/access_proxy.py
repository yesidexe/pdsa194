"""Módulo de seguridad y control de acceso mediante el patrón estructural Proxy."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from src.modules.facade.voting_facade import VotingSystemFacade
from src.modules.tally.report_builder import ElectoralTallyReport


class UserRole(str, Enum):
    """Roles de acceso permitidos en la plataforma electoral."""
    ADMINISTRADOR = "ADMINISTRADOR"
    JURADO = "JURADO"
    AUDITOR = "AUDITOR"
    ELECTOR = "ELECTOR"


@dataclass(frozen=True)
class UserSession:
    """Credencial de sesión verificada para operaciones protegidas."""
    user_id: str
    role: UserRole
    session_token: str


class ElectoralAccessProxy:
    """Proxy de protección y auditoría sobre VotingSystemFacade."""

    def __init__(self, target_facade: VotingSystemFacade) -> None:
        self._facade = target_facade
        self._audit_log: List[Dict[str, Any]] = []

    @property
    def audit_log(self) -> List[Dict[str, Any]]:
        """Bitácora inmutable de eventos interceptados por el Proxy."""
        return list(self._audit_log)

    def _record_audit_event(self, action: str, user_id: str, role: str, status: str, details: str = "") -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": user_id,
            "role": role,
            "status": status,
            "details": details,
        }
        self._audit_log.append(event)

    # =========================================================================
    # OPERACIONES ADMINISTRATIVAS PROTEGIDAS (Solo ADMINISTRADOR)
    # =========================================================================

    def open_polls(self, session: UserSession) -> None:
        """Permite abrir la urna únicamente a usuarios con rol ADMINISTRADOR."""
        if session.role != UserRole.ADMINISTRADOR:
            self._record_audit_event("OPEN_POLLS", session.user_id, session.role.value, "RECHAZADO", "Permiso denegado")
            raise PermissionError(f"Acceso denegado: Se requiere rol ADMINISTRADOR para abrir la jornada electoral.")

        self._record_audit_event("OPEN_POLLS", session.user_id, session.role.value, "AUTORIZADO", "Apertura formal de urnas")
        self._facade.open_polls()

    def close_polls(self, session: UserSession) -> None:
        """Permite cerrar la urna a usuarios con rol ADMINISTRADOR o JURADO."""
        if session.role not in (UserRole.ADMINISTRADOR, UserRole.JURADO):
            self._record_audit_event("CLOSE_POLLS", session.user_id, session.role.value, "RECHAZADO", "Permiso denegado")
            raise PermissionError(f"Acceso denegado: Se requiere rol ADMINISTRADOR o JURADO para cerrar urnas.")

        self._record_audit_event("CLOSE_POLLS", session.user_id, session.role.value, "AUTORIZADO", "Cierre formal de urnas")
        self._facade.close_polls()

    # =========================================================================
    # OPERACIONES DE VOTACIÓN (ELECTOR o JURADO)
    # =========================================================================

    def verify_voter(self, document_id: str, session: Optional[UserSession] = None) -> Dict[str, Any]:
        """Consulta la habilitación del elector registrando la auditoría de consulta."""
        user = session.user_id if session else f"ELECTOR-{document_id}"
        role = session.role.value if session else UserRole.ELECTOR.value

        result = self._facade.verify_voter(document_id)
        status = "HABILITADO" if result.get("is_eligible") else "INHABILITADO"
        self._record_audit_event("VERIFY_VOTER", user, role, status, f"Doc: {document_id}")
        return result

    def cast_secure_vote(
        self,
        document_id: str,
        ballot_type: str,
        selection_kwargs: Dict[str, Any],
        session: Optional[UserSession] = None,
        security_layers: List[str] = ("timestamp", "signature", "watermark"),
        signing_key: str = "MASTER_PROXY_KEY_2026",
    ) -> Dict[str, Any]:
        """Intercepta la emisión de votos validando que la jornada esté abierta y registrando auditoría."""
        user = session.user_id if session else f"ELECTOR-{document_id}"
        role = session.role.value if session else UserRole.ELECTOR.value

        try:
            result = self._facade.cast_secure_vote(
                document_id=document_id,
                ballot_type=ballot_type,
                selection_kwargs=selection_kwargs,
                security_layers=security_layers,
                signing_key=signing_key,
            )
            self._record_audit_event(
                "CAST_VOTE",
                user,
                role,
                "EXITOSO",
                f"Papeleta ID: {result.get('ballot_id')} | Recibo: {result.get('receipt_code')}",
            )
            return result
        except Exception as e:
            self._record_audit_event("CAST_VOTE", user, role, "FALLIDO", str(e))
            raise

    # =========================================================================
    # ESCRUTINIO Y ACTA FINAL (ADMINISTRADOR o JURADO)
    # =========================================================================

    def close_and_generate_tally(
        self,
        session: UserSession,
        officer_signatures: List[str],
        dispatch_destination: Optional[str] = None,
    ) -> ElectoralTallyReport:
        """Controla el escrutinio final exigiendo firmas oficiales de jurados acreditados."""
        if session.role not in (UserRole.ADMINISTRADOR, UserRole.JURADO):
            self._record_audit_event("GENERATE_TALLY", session.user_id, session.role.value, "RECHAZADO", "Permiso denegado")
            raise PermissionError("Acceso denegado: Solo jurados o administradores pueden consolidar el acta final.")

        if not officer_signatures:
            self._record_audit_event("GENERATE_TALLY", session.user_id, session.role.value, "RECHAZADO", "Faltan firmas de jurados")
            raise ValueError("No se puede generar el acta sin las firmas oficiales de los jurados de mesa.")

        report = self._facade.close_and_generate_tally(
            officer_signatures=officer_signatures,
            dispatch_destination=dispatch_destination,
        )
        self._record_audit_event(
            "GENERATE_TALLY",
            session.user_id,
            session.role.value,
            "CONCLUIDO",
            f"Hash: {report.integrity_hash[:16]}... | Total votos: {report.total_votes}",
        )
        return report

    # =========================================================================
    # CONSULTAS DE ACCESO PÚBLICO O AUDITORÍA (Pasan directo al Facade)
    # =========================================================================

    @property
    def is_voting_open(self) -> bool:
        return self._facade.is_voting_open

    def get_dashboard_summary(self) -> Dict[str, Any]:
        return self._facade.get_dashboard_summary()

    def get_registered_station_ids(self) -> List[str]:
        return self._facade.get_registered_station_ids()
