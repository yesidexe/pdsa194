"""Modelos de entrada de la API.

Se mantienen separados de las rutas para que `api.py` y los routers no mezclen
validación de payloads con lógica HTTP.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

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


class CandidateFields(BaseModel):
    candidate_name: str = Field(..., min_length=2, max_length=150)
    party_name: str = Field(..., min_length=2, max_length=150)
    campaign_slogan: str = Field("", max_length=300)
    party_color_hex: str = Field("#2563EB", pattern=r"^#[0-9A-Fa-f]{6}$")
    photo_url: str = Field(
        "/static/candidates/default.svg",
        max_length=300,
        pattern=r"^(/static/|https://)",
    )
    display_order: int = Field(0, ge=0, le=999)


class CandidateCreateRequest(CandidateFields):
    candidate_id: str = Field(..., pattern=r"^[A-Za-z0-9-]{2,20}$")


class CandidateUpdateRequest(CandidateFields):
    pass


class CandidateStatusRequest(BaseModel):
    is_active: bool
