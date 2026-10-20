"""API REST local de la plataforma electoral.

Las operaciones de administración exigen una cookie de sesión firmada; el
elector se autentica con documento + PIN. Las respuestas de error no exponen
detalles internos de la base de datos.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.core.settings import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from src.modules.census.census_adapter import SqliteCensusAdapter
from src.modules.facade.voting_facade import TallyAlreadyGeneratedError
from src.modules.security.access_proxy import ElectoralAccessProxy, UserSession
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.modules.voting.vote_store import AlreadyVotedError
from src.presentation.auth import (
    create_session_token,
    require_admin_session,
    verify_admin_credentials,
)


# -------------------------------------------------------------------------
# Modelos de entrada
# -------------------------------------------------------------------------
_DOC_PATTERN = r"^[A-Za-z0-9-]{5,20}$"
_PIN_PATTERN = r"^\d{4,8}$"


class VerifyVoterRequest(BaseModel):
    document_id: str = Field(..., pattern=_DOC_PATTERN, examples=["10203040"])
    pin: str = Field(..., pattern=_PIN_PATTERN, examples=["1234"])


class CastVoteRequest(BaseModel):
    document_id: str = Field(..., pattern=_DOC_PATTERN, examples=["10203040"])
    pin: str = Field(..., pattern=_PIN_PATTERN, examples=["1234"])
    ballot_type: Literal["candidate", "blank", "referendum"] = Field("candidate")
    selection: Dict[str, Any] = Field(default_factory=dict)
    # Se conserva por compatibilidad, pero el servidor ya no confía en este campo.
    security_layers: Optional[List[str]] = None


class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=200)


class SwitchElectionModeRequest(BaseModel):
    mode: Literal["national", "university"]


class GenerateTallyRequest(BaseModel):
    officer_signatures: List[str] = Field(
        default_factory=lambda: ["JURADO-FIRMA-MESA-01", "JURADO-FIRMA-MESA-02"]
    )


class RegisterVoterRequest(BaseModel):
    document_id: str = Field(..., pattern=_DOC_PATTERN, examples=["10998877"])
    full_name: str = Field(..., min_length=3, max_length=150, examples=["Marcela Gómez"])
    assigned_station_id: str = Field("MESA-01", pattern=r"^[A-Za-z0-9-]{3,20}$")
    is_eligible: bool = True
    pin: str = Field("1234", pattern=_PIN_PATTERN)
    election_type: Optional[Literal["NATIONAL", "UNIVERSITY"]] = None


class ToggleEligibilityRequest(BaseModel):
    is_eligible: bool


class ElectoralSystemHolder:
    """Contenedor de estado que permite conmutar la instancia del sistema."""

    def __init__(self, proxy: ElectoralAccessProxy, mode: str = "national") -> None:
        self.proxy: ElectoralAccessProxy = proxy
        self.current_mode: str = mode

    def switch_mode(self, new_mode: str) -> ElectoralAccessProxy:
        self.current_mode = new_mode.lower().strip()
        return self.proxy


def create_api_app(target: Union[ElectoralAccessProxy, ElectoralSystemHolder]) -> FastAPI:
    """Fábrica de la aplicación FastAPI conectada al Proxy o Holder de seguridad."""
    if isinstance(target, ElectoralAccessProxy):
        holder = ElectoralSystemHolder(proxy=target, mode="national")
    else:
        holder = target

    api = FastAPI(
        title="Plataforma de Votación Electrónica (E-Voting API)",
        description="API REST local para la simulación de la jornada electoral y el censo.",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @api.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    # -------------------------------------------------------------------------
    # Estado y sesión
    # -------------------------------------------------------------------------
    @api.get("/api/health", tags=["Estado"])
    def health_check() -> Dict[str, str]:
        return {"status": "ONLINE", "system": "E-Voting Platform", "mode": holder.current_mode}

    @api.post("/api/admin/login", tags=["Administración"])
    def admin_login(req: AdminLoginRequest, response: Response) -> Dict[str, str]:
        """Inicia sesión con la única cuenta administradora configurada."""
        if not verify_admin_credentials(req.username, req.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos.",
            )
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=create_session_token(),
            max_age=SESSION_MAX_AGE_SECONDS,
            httponly=True,
            samesite="strict",
            secure=False,  # local HTTP; en producción debe ser True con TLS
            path="/",
        )
        return {"status": "SESION_INICIADA"}

    @api.post("/api/admin/logout", tags=["Administración"])
    def admin_logout(response: Response) -> Dict[str, str]:
        response.delete_cookie(SESSION_COOKIE_NAME, path="/")
        return {"status": "SESION_CERRADA"}

    @api.get("/api/admin/session", tags=["Administración"])
    def admin_session(session: UserSession = Depends(require_admin_session)) -> Dict[str, str]:
        return {"status": "AUTENTICADO", "user_id": session.user_id, "role": session.role.value}

    # -------------------------------------------------------------------------
    # Consulta pública
    # -------------------------------------------------------------------------
    @api.get("/api/candidates", tags=["Candidatos"])
    def get_candidates_catalog() -> List[Dict[str, Any]]:
        candidates = CandidateFlyweightFactory.get_all_candidates()
        return [
            {
                "candidate_id": c.candidate_id,
                "candidate_name": c.candidate_name,
                "party_name": c.party_name,
                "slogan": c.campaign_slogan,
                "color": c.party_color_hex,
                "photo_url": c.photo_url,
                "card_display": c.format_card_display(),
            }
            for c in candidates
        ]

    @api.get("/api/dashboard", tags=["Escrutinio"])
    def get_dashboard() -> Dict[str, Any]:
        return holder.proxy.get_dashboard_summary()

    @api.get("/api/election/mode", tags=["Configuración Electoral"])
    def get_election_mode() -> Dict[str, Any]:
        return {
            "mode": holder.current_mode,
            "institution_name": holder.proxy.institution_name,
            "election_title": holder.proxy.election_title,
            "ballot_header": holder.proxy.ballot_header,
            "document_type": holder.proxy.document_type,
            "election_type": holder.proxy.election_type,
            "is_open": holder.proxy.is_voting_open,
            "is_tallied": holder.proxy.is_tallied,
        }

    # -------------------------------------------------------------------------
    # Elector
    # -------------------------------------------------------------------------
    @api.post("/api/auth/verify", tags=["Elector"])
    def verify_voter(req: VerifyVoterRequest) -> Dict[str, Any]:
        """Valida documento + PIN contra el censo y el estado de la jornada."""
        result = holder.proxy.verify_voter(req.document_id, req.pin)
        if not result.get("is_eligible", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result.get("reason", "No habilitado para sufragar"),
            )
        return result

    @api.post("/api/votes/cast", tags=["Elector"])
    def cast_vote(req: CastVoteRequest) -> Dict[str, Any]:
        """Emite un voto validado y persistido; el servidor decide la seguridad."""
        try:
            return holder.proxy.cast_secure_vote(
                document_id=req.document_id,
                pin=req.pin,
                ballot_type=req.ballot_type,
                selection_kwargs=req.selection,
                security_layers=req.security_layers,
            )
        except AlreadyVotedError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No fue posible registrar el voto. Intente nuevamente.",
            )

    # -------------------------------------------------------------------------
    # Administración electoral (requiere cookie)
    # -------------------------------------------------------------------------
    @api.post("/api/election/switch-mode", tags=["Administración"])
    def switch_election_mode(
        req: SwitchElectionModeRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        try:
            new_proxy = holder.switch_mode(req.mode)
            return {
                "status": "MODO_ELECTORAL_ACTUALIZADO",
                "mode": holder.current_mode,
                "election_title": new_proxy.election_title,
                "institution_name": new_proxy.institution_name,
                "ballot_header": new_proxy.ballot_header,
                "document_type": new_proxy.document_type,
            }
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @api.post("/api/election/open", tags=["Administración"])
    def open_election(session: UserSession = Depends(require_admin_session)) -> Dict[str, Any]:
        try:
            holder.proxy.open_polls(session)
            return {
                "status": "JORNADA_ABIERTA",
                "is_open": holder.proxy.is_voting_open,
                "is_tallied": holder.proxy.is_tallied,
            }
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    @api.post("/api/election/close", tags=["Administración"])
    def close_election(session: UserSession = Depends(require_admin_session)) -> Dict[str, Any]:
        try:
            holder.proxy.close_polls(session)
            return {
                "status": "JORNADA_CERRADA",
                "is_open": holder.proxy.is_voting_open,
                "is_tallied": holder.proxy.is_tallied,
            }
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    @api.post("/api/admin/reset-election", tags=["Administración"])
    def reset_election(session: UserSession = Depends(require_admin_session)) -> Dict[str, Any]:
        """Borra todos los votos de la elección activa y reabre la jornada."""
        try:
            removed = holder.proxy.reset_election(session)
            return {
                "status": "JORNADA_REINICIADA",
                "removed_ballots": removed,
                "mode": holder.current_mode,
                "is_open": holder.proxy.is_voting_open,
                "is_tallied": holder.proxy.is_tallied,
            }
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    @api.post("/api/tally/generate", tags=["Escrutinio"])
    def generate_official_tally(
        req: GenerateTallyRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        try:
            report = holder.proxy.close_and_generate_tally(
                session=session,
                officer_signatures=req.officer_signatures,
                dispatch_destination="REGISTRADURIA_CENTRAL_AUDITORIA",
            )
            return {
                "title": report.election_title,
                "jurisdiction": report.jurisdiction,
                "total_votes": report.total_votes,
                "candidate_votes": report.candidate_votes,
                "blank_votes": report.blank_votes,
                "null_votes": report.null_votes,
                "winner_verdict": report.winner_verdict,
                "integrity_hash_sha256": report.integrity_hash,
                "signatures": report.officer_signatures,
                "formatted_summary": report.to_formatted_summary(),
            }
        except TallyAlreadyGeneratedError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No fue posible generar el acta.",
            )

    @api.get("/api/security/audit-log", tags=["Auditoría"])
    def get_proxy_audit_log(
        session: UserSession = Depends(require_admin_session),
    ) -> List[Dict[str, Any]]:
        return holder.proxy.audit_log

    # -------------------------------------------------------------------------
    # Censo electoral (requiere cookie)
    # -------------------------------------------------------------------------
    @api.get("/api/census/voters", tags=["Censo Electoral"])
    def get_census_voters(
        election_type: Optional[str] = None,
        session: UserSession = Depends(require_admin_session),
    ) -> List[Dict[str, Any]]:
        target_mode = election_type or holder.current_mode
        adapter = SqliteCensusAdapter(election_type=target_mode)
        voters = adapter.get_all_voters(target_mode)
        return [
            {
                "document_id": v.document_id,
                "full_name": v.full_name,
                "assigned_station_id": v.assigned_station_id,
                "is_eligible": v.is_eligible,
                "source_type": v.source_type,
            }
            for v in voters
        ]

    @api.post("/api/census/voters", tags=["Censo Electoral"])
    def register_census_voter(
        req: RegisterVoterRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        target_mode = (req.election_type or holder.current_mode).upper()
        adapter = SqliteCensusAdapter(election_type=target_mode)
        voter = adapter.register_voter(
            document_id=req.document_id,
            full_name=req.full_name,
            assigned_station_id=req.assigned_station_id,
            is_eligible=req.is_eligible,
            election_type=target_mode,
            pin=req.pin,
        )
        return {
            "status": "ELECTOR_REGISTRADO",
            "document_id": voter.document_id,
            "full_name": voter.full_name,
            "assigned_station_id": voter.assigned_station_id,
            "is_eligible": voter.is_eligible,
        }

    @api.put("/api/census/voters/{document_id}/status", tags=["Censo Electoral"])
    def toggle_voter_eligibility(
        document_id: str,
        req: ToggleEligibilityRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        adapter = SqliteCensusAdapter(election_type=holder.current_mode)
        success = adapter.toggle_eligibility(document_id=document_id, is_eligible=req.is_eligible)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Elector no encontrado en el censo.")
        return {
            "status": "ESTADO_ACTUALIZADO",
            "document_id": document_id,
            "is_eligible": req.is_eligible,
        }

    return api
