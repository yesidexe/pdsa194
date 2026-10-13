"""Módulo API REST con FastAPI para la plataforma de votación electrónica."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.modules.facade.voting_facade import VotingSystemFacade
from src.modules.security.access_proxy import ElectoralAccessProxy, UserSession, UserRole
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.modules.census.census_adapter import SqliteCensusAdapter


# -------------------------------------------------------------------------
# Modelos Pydantic para Validación de Esquemas (Nivel de Módulo)
# -------------------------------------------------------------------------
class VerifyVoterRequest(BaseModel):
    document_id: str = Field(..., description="Cédula o código de identificación del votante", examples=["10203040"])

class CastVoteRequest(BaseModel):
    document_id: str = Field(..., description="Cédula del votante habilitado", examples=["10203040"])
    ballot_type: str = Field("candidate", description="'candidate', 'referendum' o 'blank'", examples=["candidate"])
    selection: Dict[str, Any] = Field(
        ...,
        description="Metadatos de la selección (candidato, pregunta o categoría)",
        examples=[{"candidate_id": "CAND-01", "candidate_name": "Gabriel Silva", "party_name": "Pact E-Col"}],
    )
    security_layers: List[str] = Field(
        default=["timestamp", "signature", "watermark"],
        description="Capas de seguridad a aplicar",
        examples=[["timestamp", "signature", "watermark"]],
    )

class AdminSessionRequest(BaseModel):
    user_id: str = Field("ADMIN-01", examples=["ADMIN-01"])
    session_token: str = Field("TOKEN-ADMIN-MASTER-2026", examples=["TOKEN-ADMIN-MASTER-2026"])

class SwitchElectionModeRequest(BaseModel):
    mode: str = Field("national", description="'national' o 'university'", examples=["university"])
    user_id: str = Field("ADMIN-01", examples=["ADMIN-01"])
    session_token: str = Field("TOKEN-ADMIN-MASTER-2026", examples=["TOKEN-ADMIN-MASTER-2026"])

class GenerateTallyRequest(BaseModel):
    officer_signatures: List[str] = Field(
        default=["JURADO-FIRMA-MESA-01", "JURADO-FIRMA-MESA-02"],
        examples=[["JURADO-FIRMA-MESA-01", "JURADO-FIRMA-MESA-02"]],
    )
    user_id: str = Field("ADMIN-01", examples=["ADMIN-01"])
    session_token: str = Field("TOKEN-ADMIN-MASTER-2026", examples=["TOKEN-ADMIN-MASTER-2026"])

class RegisterVoterRequest(BaseModel):
    document_id: str = Field(..., description="Cédula o carnet estudiantil a inscribir")
    full_name: str = Field(..., description="Nombre completo legal del elector")
    assigned_station_id: str = Field("MESA-01", description="Mesa asignada")
    is_eligible: bool = Field(True, description="Estado legal (True=Habilitado, False=Inhabilitado)")
    election_type: Optional[str] = Field(None, description="'NATIONAL' o 'UNIVERSITY'")
    user_id: str = Field("ADMIN-01")
    session_token: str = Field("TOKEN-ADMIN-MASTER-2026")

class ToggleEligibilityRequest(BaseModel):
    is_eligible: bool = Field(..., description="Nuevo estado de habilitación política")
    user_id: str = Field("ADMIN-01")
    session_token: str = Field("TOKEN-ADMIN-MASTER-2026")


class ElectoralSystemHolder:
    """Contenedor de estado que permite conmutar la instancia del sistema en caliente."""

    def __init__(self, proxy: ElectoralAccessProxy, mode: str = "national") -> None:
        self.proxy: ElectoralAccessProxy = proxy
        self.current_mode: str = mode

    def switch_mode(self, new_mode: str) -> ElectoralAccessProxy:
        self.current_mode = new_mode.lower().strip()
        return self.proxy


def _authenticate_admin(user_id: str, session_token: str) -> UserSession:
    """Verifica si el token corresponde al perfil de Administrador."""
    if session_token == "TOKEN-ADMIN-MASTER-2026":
        return UserSession(user_id=user_id, role=UserRole.ADMINISTRADOR, session_token=session_token)
    return UserSession(user_id=user_id, role=UserRole.ELECTOR, session_token=session_token)


def create_api_app(target: Union[ElectoralAccessProxy, ElectoralSystemHolder]) -> FastAPI:
    """Fábrica de la aplicación FastAPI conectada al Proxy o Holder de seguridad."""
    if isinstance(target, ElectoralAccessProxy):
        holder = ElectoralSystemHolder(proxy=target, mode="national")
    else:
        holder = target
    api = FastAPI(
        title="Plataforma de Votación Electrónica (E-Voting API)",
        description="API REST de servicios para la plataforma de votación electrónica y censo electoral.",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -------------------------------------------------------------------------
    # Endpoints de la API
    # -------------------------------------------------------------------------
    @api.get("/api/health", tags=["Estado"])
    def health_check() -> Dict[str, str]:
        return {"status": "ONLINE", "system": "E-Voting Platform"}

    @api.get("/api/candidates", tags=["Candidatos"])
    def get_candidates_catalog() -> List[Dict[str, Any]]:
        """Recupera el catálogo de candidatos activos para la votación."""
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
        """Obtiene métricas consolidadas en tiempo real para visualización."""
        return holder.proxy.get_dashboard_summary()

    @api.get("/api/election/mode", tags=["Configuración Electoral"])
    def get_election_mode() -> Dict[str, Any]:
        """Obtiene la configuración activa de la jornada electoral."""
        facade = holder.proxy._facade
        header_str = "Encabezado Oficial"
        doc_type_str = "Cédula de Ciudadanía"
        if facade._family_factory is not None:
            header_str = facade._family_factory.create_header().render_header()
            doc_type_str = facade._family_factory.create_validator().get_document_type()

        return {
            "mode": holder.current_mode,
            "institution_name": facade._config.institution_name,
            "election_title": facade._config.election_title,
            "ballot_header": header_str,
            "document_type": doc_type_str,
            "is_open": holder.proxy.is_voting_open,
        }

    @api.post("/api/election/switch-mode", tags=["Configuración Electoral"])
    def switch_election_mode(req: SwitchElectionModeRequest) -> Dict[str, Any]:
        """Conmuta el tipo de elección (Nacional vs Universitaria)."""
        session = _authenticate_admin(req.user_id, req.session_token)
        if session.role != UserRole.ADMINISTRADOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso denegado: Requiere rol ADMINISTRADOR.")

        try:
            new_proxy = holder.switch_mode(req.mode)
            facade = new_proxy._facade
            header_str = facade._family_factory.create_header().render_header() if facade._family_factory else ""
            doc_type_str = facade._family_factory.create_validator().get_document_type() if facade._family_factory else ""
            return {
                "status": "MODO_ELECTORAL_ACTUALIZADO",
                "mode": holder.current_mode,
                "election_title": facade._config.election_title,
                "institution_name": facade._config.institution_name,
                "ballot_header": header_str,
                "document_type": doc_type_str,
            }
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @api.post("/api/auth/verify", tags=["Elector"])
    def verify_voter(req: VerifyVoterRequest) -> Dict[str, Any]:
        """Verifica si el elector está facultado legalmente para votar en el censo."""
        result = holder.proxy.verify_voter(req.document_id)
        if not result.get("is_eligible", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result.get("reason", "No habilitado para sufragar"),
            )
        return result

    @api.post("/api/votes/cast", tags=["Elector"])
    def cast_vote(req: CastVoteRequest) -> Dict[str, Any]:
        """Emite el voto, aplica sellos de seguridad y lo almacena anónimamente en la urna."""
        try:
            receipt = holder.proxy.cast_secure_vote(
                document_id=req.document_id,
                ballot_type=req.ballot_type,
                selection_kwargs=req.selection,
                security_layers=req.security_layers,
            )
            return receipt
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @api.post("/api/election/open", tags=["Administración"])
    def open_election(req: AdminSessionRequest) -> Dict[str, Any]:
        """Abre la urna electoral para iniciar la jornada de votación."""
        session = _authenticate_admin(req.user_id, req.session_token)
        try:
            holder.proxy.open_polls(session)
            return {"status": "JORNADA_ABIERTA", "is_open": holder.proxy.is_voting_open}
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    @api.post("/api/election/close", tags=["Administración"])
    def close_election(req: AdminSessionRequest) -> Dict[str, Any]:
        """Cierra la urna electoral para finalizar la jornada de votación."""
        session = _authenticate_admin(req.user_id, req.session_token)
        try:
            holder.proxy.close_polls(session)
            return {"status": "JORNADA_CERRADA", "is_open": holder.proxy.is_voting_open}
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    @api.post("/api/tally/generate", tags=["Escrutinio"])
    def generate_official_tally(req: GenerateTallyRequest) -> Dict[str, Any]:
        """Consolida votos, evalúa ganador y produce acta oficial sellada con firma criptográfica."""
        session = _authenticate_admin(req.user_id, req.session_token)
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
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @api.get("/api/security/audit-log", tags=["Auditoría"])
    def get_proxy_audit_log() -> List[Dict[str, Any]]:
        """Recupera la bitácora de eventos del sistema de seguridad."""
        return holder.proxy.audit_log

    # -------------------------------------------------------------------------
    # Endpoints del Censo Electoral (Persistencia en SQLite)
    # -------------------------------------------------------------------------
    @api.get("/api/census/voters", tags=["Censo Electoral"])
    def get_census_voters(election_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna la lista de ciudadanos registrados en el censo electoral oficial."""
        target_mode = election_type or holder.current_mode
        sqlite_adapter = SqliteCensusAdapter(election_type=target_mode)
        voters = sqlite_adapter.get_all_voters(target_mode)
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
    def register_census_voter(req: RegisterVoterRequest) -> Dict[str, Any]:
        """Inscribe o actualiza un ciudadano en el censo electoral oficial."""
        session = _authenticate_admin(req.user_id, req.session_token)
        if session.role != UserRole.ADMINISTRADOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso denegado: Requiere rol ADMINISTRADOR.")

        target_mode = req.election_type or holder.current_mode
        sqlite_adapter = SqliteCensusAdapter(election_type=target_mode)
        voter = sqlite_adapter.register_voter(
            document_id=req.document_id,
            full_name=req.full_name,
            assigned_station_id=req.assigned_station_id,
            is_eligible=req.is_eligible,
            election_type=target_mode,
        )
        return {
            "status": "ELECTOR_REGISTRADO",
            "document_id": voter.document_id,
            "full_name": voter.full_name,
            "assigned_station_id": voter.assigned_station_id,
            "is_eligible": voter.is_eligible,
        }

    @api.put("/api/census/voters/{document_id}/status", tags=["Censo Electoral"])
    def toggle_voter_eligibility(document_id: str, req: ToggleEligibilityRequest) -> Dict[str, Any]:
        """Modifica el estado de habilitación política de un elector en el censo."""
        session = _authenticate_admin(req.user_id, req.session_token)
        if session.role != UserRole.ADMINISTRADOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso denegado: Requiere rol ADMINISTRADOR.")

        sqlite_adapter = SqliteCensusAdapter(election_type=holder.current_mode)
        success = sqlite_adapter.toggle_eligibility(document_id=document_id, is_eligible=req.is_eligible)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Elector no encontrado en el censo.")
        return {
            "status": "ESTADO_ACTUALIZADO",
            "document_id": document_id,
            "is_eligible": req.is_eligible,
        }
    return api
