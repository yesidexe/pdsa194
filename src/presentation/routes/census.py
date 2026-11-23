"""Censo electoral: consulta, inscripción y habilitación."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.census.census_service import CensusService
from src.modules.security.access_proxy import UserSession
from src.presentation.auth import require_admin_session
from src.presentation.holder import ElectoralSystemHolder
from src.presentation.schemas import RegisterVoterRequest, ToggleEligibilityRequest


def build_router(holder: ElectoralSystemHolder) -> APIRouter:
    router = APIRouter(tags=["Censo Electoral"])

    @router.get("/api/census/voters")
    def get_census_voters(
        election_type: Optional[str] = None,
        session: UserSession = Depends(require_admin_session),
    ) -> List[Dict[str, Any]]:
        service = CensusService(election_type or holder.current_mode)
        return [CensusService.serialize(voter) for voter in service.list_voters(election_type)]

    @router.post("/api/census/voters")
    def register_census_voter(
        req: RegisterVoterRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        target_mode = (req.election_type or holder.current_mode).upper()
        service = CensusService(target_mode)
        voter = service.register_voter(
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

    @router.put("/api/census/voters/{document_id}/status")
    def toggle_voter_eligibility(
        document_id: str,
        req: ToggleEligibilityRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        service = CensusService(holder.current_mode)
        success = service.toggle_eligibility(document_id=document_id, is_eligible=req.is_eligible)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Elector no encontrado en el censo.",
            )
        return {
            "status": "ESTADO_ACTUALIZADO",
            "document_id": document_id,
            "is_eligible": req.is_eligible,
        }

    return router
