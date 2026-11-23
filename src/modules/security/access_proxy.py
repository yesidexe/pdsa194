"""Módulo de seguridad y control de acceso mediante el patrón estructural Proxy."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from src.modules.audit.service import AuditService
from src.modules.facade.voting_facade import VotingSystemFacade
from src.modules.tally.report_builder import ElectoralTallyReport
from src.modules.voting.vote_store import AlreadyVotedError


logger = logging.getLogger("evoting.proxy")


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

    def __init__(
        self,
        target_facade: VotingSystemFacade,
        audit_service: Optional[AuditService] = None,
    ) -> None:
        self._facade = target_facade
        self._audit = audit_service or AuditService()

    @property
    def audit_log(self) -> List[Dict[str, Any]]:
        """Bitácora persistente, en orden cronológico ascendente."""
        return self._audit.history()

    def verify_audit_log(self) -> Dict[str, Any]:
        """Recalcula la cadena de hashes de la bitácora."""
        return self._audit.verify()

    @property
    def election_type(self) -> str:
        return self._facade.election_type

    @property
    def institution_name(self) -> str:
        return self._facade.institution_name

    @property
    def election_title(self) -> str:
        return self._facade.election_title

    @property
    def ballot_header(self) -> str:
        return self._facade.ballot_header

    @property
    def document_type(self) -> str:
        return self._facade.document_type

    def _record_audit_event(self, action: str, user_id: str, role: str, status: str, details: str = "") -> None:
        # La auditoría no debe tumbar una operación que ya se confirmó (por
        # ejemplo, un voto que ya hizo commit). Se registra el fallo en el log
        # técnico; en producción esto iría a una outbox transaccional.
        try:
            self._audit.record(
                action=action,
                user_id=user_id,
                role=role,
                status=status,
                details=details,
            )
        except Exception:
            logger.exception("No fue posible registrar el evento de auditoría %s", action)


    def open_polls(self, session: UserSession) -> None:
        """Permite abrir la urna únicamente a usuarios con rol ADMINISTRADOR."""
        if session.role != UserRole.ADMINISTRADOR:
            self._record_audit_event("OPEN_POLLS", session.user_id, session.role.value, "RECHAZADO", "Permiso denegado")
            raise PermissionError("Acceso denegado: Se requiere rol ADMINISTRADOR para abrir la jornada electoral.")

        try:
            self._facade.open_polls()
        except Exception as exc:
            self._record_audit_event(
                "OPEN_POLLS",
                session.user_id,
                session.role.value,
                "RECHAZADO",
                str(exc)[:300],
            )
            raise
        self._record_audit_event(
            "OPEN_POLLS", session.user_id, session.role.value, "AUTORIZADO", "Apertura formal de urnas"
        )

    def close_polls(self, session: UserSession) -> None:
        """Permite cerrar la urna a usuarios con rol ADMINISTRADOR o JURADO."""
        if session.role not in (UserRole.ADMINISTRADOR, UserRole.JURADO):
            self._record_audit_event("CLOSE_POLLS", session.user_id, session.role.value, "RECHAZADO", "Permiso denegado")
            raise PermissionError("Acceso denegado: Se requiere rol ADMINISTRADOR o JURADO para cerrar urnas.")

        self._record_audit_event("CLOSE_POLLS", session.user_id, session.role.value, "AUTORIZADO", "Cierre formal de urnas")
        self._facade.close_polls()


    def _require_admin(self, session: UserSession, action: str) -> None:
        if session.role != UserRole.ADMINISTRADOR:
            self._record_audit_event(
                action, session.user_id, session.role.value, "RECHAZADO", "Permiso denegado"
            )
            raise PermissionError("Acceso denegado: se requiere rol ADMINISTRADOR.")

    def list_candidates(self, session: UserSession, include_inactive: bool = True) -> List[Dict[str, Any]]:
        self._require_admin(session, "LIST_CANDIDATES")
        return self._facade.list_candidates(include_inactive=include_inactive)

    def create_candidate(self, session: UserSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._require_admin(session, "CREATE_CANDIDATE")
        try:
            candidate = self._facade.create_candidate(payload)
        except Exception as exc:
            self._record_audit_event(
                "CREATE_CANDIDATE", session.user_id, session.role.value, "RECHAZADO", str(exc)[:300]
            )
            raise
        self._record_audit_event(
            "CREATE_CANDIDATE",
            session.user_id,
            session.role.value,
            "AUTORIZADO",
            f"Candidato: {candidate.get('candidate_id')}",
        )
        return candidate

    def update_candidate(
        self, session: UserSession, candidate_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._require_admin(session, "UPDATE_CANDIDATE")
        try:
            candidate = self._facade.update_candidate(candidate_id, payload)
        except Exception as exc:
            self._record_audit_event(
                "UPDATE_CANDIDATE", session.user_id, session.role.value, "RECHAZADO", str(exc)[:300]
            )
            raise
        self._record_audit_event(
            "UPDATE_CANDIDATE",
            session.user_id,
            session.role.value,
            "AUTORIZADO",
            f"Candidato: {candidate_id}",
        )
        return candidate

    def set_candidate_active(
        self, session: UserSession, candidate_id: str, is_active: bool
    ) -> Dict[str, Any]:
        self._require_admin(session, "TOGGLE_CANDIDATE")
        try:
            candidate = self._facade.set_candidate_active(candidate_id, is_active)
        except Exception as exc:
            self._record_audit_event(
                "TOGGLE_CANDIDATE", session.user_id, session.role.value, "RECHAZADO", str(exc)[:300]
            )
            raise
        state = "ACTIVO" if is_active else "INACTIVO"
        self._record_audit_event(
            "TOGGLE_CANDIDATE",
            session.user_id,
            session.role.value,
            "AUTORIZADO",
            f"Candidato: {candidate_id} -> {state}",
        )
        return candidate


    def verify_voter(
        self,
        document_id: str,
        pin: str,
        session: Optional[UserSession] = None,
    ) -> Dict[str, Any]:
        """Consulta la habilitación del elector registrando la auditoría de consulta.

        En la auditoría no se guarda el documento completo: se enmascara para
        reducir la exposición de datos personales.
        """
        user = session.user_id if session else "ELECTOR-ANONIMO"
        role = session.role.value if session else UserRole.ELECTOR.value
        masked = f"***{str(document_id)[-4:]}" if document_id else "***"

        result = self._facade.verify_voter(document_id, pin)
        status = "HABILITADO" if result.get("is_eligible") else "INHABILITADO"
        self._record_audit_event("VERIFY_VOTER", user, role, status, f"Doc: {masked}")
        return result

    def cast_secure_vote(
        self,
        document_id: str,
        pin: str,
        ballot_type: str,
        selection_kwargs: Dict[str, Any],
        session: Optional[UserSession] = None,
        security_layers: Optional[List[str]] = None,
        signing_key: str = "MASTER_PROXY_KEY_2026",
    ) -> Dict[str, Any]:
        """Emite el voto y audita solo la papeleta, nunca el documento.

        Antes se registraba ``ELECTOR-<documento>`` junto al ``ballot_id``, lo
        que permitía reconstruir qué votó cada persona. Ahora la auditoría de
        emisión es anónima y la relación identidad-papeleta no existe.
        """
        user = session.user_id if session else "ELECTOR-ANONIMO"
        role = session.role.value if session else UserRole.ELECTOR.value

        try:
            result = self._facade.cast_secure_vote(
                document_id=document_id,
                pin=pin,
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
            safe_detail = (
                str(e)[:300]
                if isinstance(e, (AlreadyVotedError, PermissionError, ValueError))
                else f"Error interno: {type(e).__name__}"
            )
            self._record_audit_event("CAST_VOTE", user, role, "FALLIDO", safe_detail)
            raise


    def reset_election(self, session: UserSession) -> int:
        """Borra todos los votos y participaciones de la elección activa.

        Es la operación segura para volver a probar la jornada: elimina todas
        las papeletas a la vez, sin identificar ni borrar el voto de una
        persona concreta. El censo queda intacto.
        """
        if session.role != UserRole.ADMINISTRADOR:
            self._record_audit_event(
                "RESET_ELECTION",
                session.user_id,
                session.role.value,
                "RECHAZADO",
                "Permiso denegado",
            )
            raise PermissionError("Acceso denegado: solo el administrador puede reiniciar la jornada.")

        removed = self._facade.reset_election()
        self._record_audit_event(
            "RESET_ELECTION",
            session.user_id,
            session.role.value,
            "AUTORIZADO",
            f"Papeletas eliminadas: {removed}. Censo conservado.",
        )
        return removed


    def close_and_generate_tally(
        self,
        session: UserSession,
        officer_signatures: List[str],
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
        )
        self._record_audit_event(
            "GENERATE_TALLY",
            session.user_id,
            session.role.value,
            "CONCLUIDO",
            f"Hash: {report.integrity_hash[:16]}... | Total votos: {report.total_votes}",
        )
        return report


    @property
    def is_voting_open(self) -> bool:
        return self._facade.is_voting_open

    @property
    def is_tallied(self) -> bool:
        return self._facade.is_tallied

    @property
    def election_status(self) -> str:
        return self._facade.election_status.value

    @property
    def election_status_label(self) -> str:
        return self._facade.election_status_label

    def get_dashboard_summary(self) -> Dict[str, Any]:
        return self._facade.get_dashboard_summary()

    def get_registered_station_ids(self) -> List[str]:
        return self._facade.get_registered_station_ids()

    def get_latest_tally_report(self) -> Optional[Dict[str, Any]]:
        return self._facade.get_latest_tally_report()
