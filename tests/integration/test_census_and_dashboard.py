"""Censo administrativo, dashboard y reset de jornada."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app
from tests.helpers import reset_and_open


def test_census_api_endpoints(admin_client):
    """Inscripción, consulta y cambio de habilitación desde el panel."""
    reset_and_open(admin_client)
    listing = admin_client.get("/api/census/voters")
    assert listing.status_code == 200
    assert len(listing.json()) > 0

    created = admin_client.post(
        "/api/census/voters",
        json={
            "document_id": "88776655",
            "full_name": "Nuevo Elector API",
            "assigned_station_id": "MESA-01",
            "is_eligible": True,
            "pin": "1234",
            "election_type": "NATIONAL",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "ELECTOR_REGISTRADO"

    verify = admin_client.post("/api/auth/verify", json={"document_id": "88776655", "pin": "1234"})
    assert verify.status_code == 200

    toggled = admin_client.put(
        "/api/census/voters/88776655/status",
        json={"is_eligible": False},
    )
    assert toggled.status_code == 200
    assert toggled.json()["is_eligible"] is False

    rejected = admin_client.post("/api/auth/verify", json={"document_id": "88776655", "pin": "1234"})
    assert rejected.status_code == 403

    raw = TestClient(app)
    unauthorized = raw.post(
        "/api/census/voters",
        json={
            "document_id": "00000001",
            "full_name": "Intruso",
            "assigned_station_id": "MESA-01",
            "is_eligible": True,
            "pin": "1234",
            "election_type": "NATIONAL",
        },
    )
    assert unauthorized.status_code == 401


def test_dashboard_realtime_metrics(admin_client):
    """El dashboard refleja votos por ID y cuenta solo electores habilitados."""
    reset_and_open(admin_client)
    public = TestClient(app)
    for document_id in ("20000006", "20000007"):
        verify = public.post("/api/auth/verify", json={"document_id": document_id, "pin": "1234"})
        assert verify.status_code == 200, verify.text

    first = public.post(
        "/api/votes/cast",
        json={
            "document_id": "20000006",
            "pin": "1234",
            "ballot_type": "candidate",
            "selection": {"candidate_id": "CAND-01"},
        },
    )
    assert first.status_code == 200, first.text

    second = public.post(
        "/api/votes/cast",
        json={
            "document_id": "20000007",
            "pin": "1234",
            "ballot_type": "blank",
            "selection": {},
        },
    )
    assert second.status_code == 200, second.text

    dashboard = public.get("/api/dashboard")
    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["total_votes_cast"] >= 2
    assert data["votes_by_candidate_id"].get("CAND-01", 0) >= 1
    assert data["votes_by_candidate_name"].get("Gabriel Silva", 0) >= 1
    assert data["blank_votes"] >= 1
    assert data["total_registered_citizens"] >= 37  # habilitados del seed
    assert data["total_registered_citizens"] < 41  # no cuenta inhabilitados


def test_reset_election_keeps_census(admin_client):
    """Reiniciar la jornada borra votos y participaciones, no el censo."""
    before = admin_client.get("/api/dashboard").json()
    response = admin_client.post("/api/admin/reset-election")
    assert response.status_code == 200
    data = response.json()
    assert data["removed_ballots"] == before["total_votes_cast"]
    after = admin_client.get("/api/dashboard").json()
    assert after["total_votes_cast"] == 0
    mode = admin_client.get("/api/election/mode").json()
    assert mode["is_open"] is False
    assert mode["is_tallied"] is False
    assert mode["election_status"] == "DRAFT"
    # El censo sigue disponible (incluye los electores añadidos por otras pruebas).
    census = admin_client.get("/api/census/voters").json()
    assert len(census) >= 41
