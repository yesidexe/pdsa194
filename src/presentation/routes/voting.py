"""Rutas del elector, dashboard y acta pública."""
from __future__ import annotations

from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException, Response, status

from src.modules.voting.vote_store import AlreadyVotedError
from src.presentation.exporters import csv_attachment, json_attachment
from src.presentation.holder import ElectoralSystemHolder
from src.presentation.schemas import CastVoteRequest, VerifyVoterRequest


def build_router(holder: ElectoralSystemHolder) -> APIRouter:
    router = APIRouter(tags=["Elector y escrutinio"])

    def latest_report() -> Dict[str, Any]:
        report = holder.proxy.get_latest_tally_report()
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Todavía no hay un acta generada para esta modalidad.",
            )
        return report

    @router.get("/api/dashboard")
    def get_dashboard() -> Dict[str, Any]:
        return holder.proxy.get_dashboard_summary()

    @router.get("/api/election/mode")
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
            "election_status": holder.proxy.election_status,
            "election_status_label": holder.proxy.election_status_label,
        }

    @router.post("/api/auth/verify")
    def verify_voter(req: VerifyVoterRequest) -> Dict[str, Any]:
        result = holder.proxy.verify_voter(req.document_id, req.pin)
        if not result.get("is_eligible", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=result.get("reason", "No habilitado para sufragar"),
            )
        return result

    @router.post("/api/votes/cast")
    def cast_vote(req: CastVoteRequest) -> Dict[str, Any]:
        try:
            return holder.proxy.cast_secure_vote(
                document_id=req.document_id,
                pin=req.pin,
                ballot_type=req.ballot_type,
                selection_kwargs=req.selection,
                security_layers=req.security_layers,
            )
        except AlreadyVotedError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No fue posible registrar el voto. Intente nuevamente.",
            ) from exc

    @router.get("/api/tally/latest")
    def get_latest_tally() -> Dict[str, Any]:
        return latest_report()

    @router.get("/api/tally/latest/export")
    def export_latest_tally(format: Literal["json", "csv"] = "json") -> Response:
        report = latest_report()
        election_type = str(report.get("election_type", "NATIONAL")).lower()
        if format == "json":
            return json_attachment(f"acta_{election_type}.json", report)
        rows = [
            [field, report.get(field)]
            for field in (
                "election_title",
                "jurisdiction",
                "generated_at",
                "total_votes",
                "blank_votes",
                "null_votes",
                "winner_verdict",
                "integrity_hash",
            )
        ]
        rows.extend([f"candidato:{name}", votes] for name, votes in report.get("candidate_votes", {}).items())
        return csv_attachment(f"acta_{election_type}.csv", ["campo", "valor"], rows)

    return router
