"""Catálogo público y administración de candidatos."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.security.access_proxy import UserSession
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.presentation.auth import require_admin_session
from src.presentation.holder import ElectoralSystemHolder
from src.presentation.schemas import (
    CandidateCreateRequest,
    CandidateStatusRequest,
    CandidateUpdateRequest,
)


def build_router(holder: ElectoralSystemHolder) -> APIRouter:
    router = APIRouter(tags=["Candidatos"])

    @router.get("/api/candidates")
    def get_candidates_catalog() -> List[Dict[str, Any]]:
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
            for c in CandidateFlyweightFactory.get_all_candidates()
        ]

    @router.get("/api/admin/candidates")
    def admin_list_candidates(
        session: UserSession = Depends(require_admin_session),
    ) -> List[Dict[str, Any]]:
        return holder.proxy.list_candidates(session, include_inactive=True)

    @router.post("/api/admin/candidates")
    def admin_create_candidate(
        req: CandidateCreateRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        try:
            candidate = holder.proxy.create_candidate(session, req.model_dump())
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return {"status": "CANDIDATO_CREADO", "candidate": candidate}

    @router.put("/api/admin/candidates/{candidate_id}")
    def admin_update_candidate(
        candidate_id: str,
        req: CandidateUpdateRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        try:
            candidate = holder.proxy.update_candidate(session, candidate_id, req.model_dump())
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return {"status": "CANDIDATO_ACTUALIZADO", "candidate": candidate}

    @router.put("/api/admin/candidates/{candidate_id}/status")
    def admin_set_candidate_status(
        candidate_id: str,
        req: CandidateStatusRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        try:
            candidate = holder.proxy.set_candidate_active(session, candidate_id, req.is_active)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return {"status": "CANDIDATO_ACTUALIZADO", "candidate": candidate}

    return router
