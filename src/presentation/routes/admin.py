"""Operaciones administrativas sobre la jornada y la auditoría."""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.modules.facade.voting_facade import TallyAlreadyGeneratedError
from src.modules.security.access_proxy import UserSession
from src.presentation.auth import require_admin_session
from src.presentation.exporters import csv_attachment, json_attachment
from src.presentation.holder import ElectoralSystemHolder
from src.presentation.schemas import GenerateTallyRequest, SwitchElectionModeRequest


def build_router(holder: ElectoralSystemHolder) -> APIRouter:
    router = APIRouter(tags=["Administración"])

    @router.post("/api/election/switch-mode")
    def switch_election_mode(
        req: SwitchElectionModeRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        try:
            new_proxy = holder.switch_mode(req.mode)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {
            "status": "MODO_ELECTORAL_ACTUALIZADO",
            "mode": holder.current_mode,
            "election_title": new_proxy.election_title,
            "institution_name": new_proxy.institution_name,
            "ballot_header": new_proxy.ballot_header,
            "document_type": new_proxy.document_type,
        }

    @router.post("/api/election/open")
    def open_election(session: UserSession = Depends(require_admin_session)) -> Dict[str, Any]:
        try:
            holder.proxy.open_polls(session)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return {
            "status": "JORNADA_ABIERTA",
            "is_open": holder.proxy.is_voting_open,
            "is_tallied": holder.proxy.is_tallied,
            "election_status": holder.proxy.election_status,
        }

    @router.post("/api/election/close")
    def close_election(session: UserSession = Depends(require_admin_session)) -> Dict[str, Any]:
        try:
            holder.proxy.close_polls(session)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return {
            "status": "JORNADA_CERRADA",
            "is_open": holder.proxy.is_voting_open,
            "is_tallied": holder.proxy.is_tallied,
            "election_status": holder.proxy.election_status,
        }

    @router.post("/api/admin/reset-election")
    def reset_election(session: UserSession = Depends(require_admin_session)) -> Dict[str, Any]:
        try:
            removed = holder.proxy.reset_election(session)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        return {
            "status": "JORNADA_REINICIADA",
            "removed_ballots": removed,
            "mode": holder.current_mode,
            "is_open": holder.proxy.is_voting_open,
            "is_tallied": holder.proxy.is_tallied,
            "election_status": holder.proxy.election_status,
        }

    @router.post("/api/tally/generate")
    def generate_official_tally(
        req: GenerateTallyRequest,
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        try:
            report = holder.proxy.close_and_generate_tally(
                session=session,
                officer_signatures=req.officer_signatures,
            )
        except TallyAlreadyGeneratedError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No fue posible generar el acta.",
            ) from exc
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

    @router.get("/api/security/audit-log")
    def get_proxy_audit_log(
        session: UserSession = Depends(require_admin_session),
    ) -> List[Dict[str, Any]]:
        return holder.proxy.audit_log

    @router.get("/api/security/audit-log/verify")
    def verify_proxy_audit_log(
        session: UserSession = Depends(require_admin_session),
    ) -> Dict[str, Any]:
        return holder.proxy.verify_audit_log()

    @router.get("/api/security/audit-log/export")
    def export_proxy_audit_log(
        format: Literal["json", "csv"] = "json",
        session: UserSession = Depends(require_admin_session),
    ) -> Response:
        events = holder.proxy.audit_log
        if format == "json":
            return json_attachment("auditoria.json", events)
        rows = [
            [
                event.get("id"),
                event.get("timestamp"),
                event.get("action"),
                event.get("user_id"),
                event.get("role"),
                event.get("status"),
                event.get("details"),
            ]
            for event in events
        ]
        return csv_attachment(
            "auditoria.csv",
            ["id", "timestamp", "action", "user_id", "role", "status", "details"],
            rows,
        )

    return router
