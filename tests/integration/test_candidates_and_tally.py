"""Catálogo de candidatos y acta persistida."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app
from tests.helpers import reset_and_open


def test_candidate_crud_and_ballot_freeze(admin_client):
    """El admin administra candidatos solo mientras la papeleta es editable."""
    admin_client.post("/api/admin/reset-election")  # queda en DRAFT

    created = admin_client.post(
        "/api/admin/candidates",
        json={
            "candidate_id": "CAND-TEST",
            "candidate_name": "Candidato de Prueba",
            "party_name": "Partido de Prueba",
            "campaign_slogan": "Lema de prueba",
            "party_color_hex": "#123456",
            "display_order": 9,
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["candidate"]["candidate_id"] == "CAND-TEST"

    public = admin_client.get("/api/candidates")
    assert any(c["candidate_id"] == "CAND-TEST" for c in public.json())

    updated = admin_client.put(
        "/api/admin/candidates/CAND-TEST",
        json={
            "candidate_name": "Candidato Actualizado",
            "party_name": "Partido Actualizado",
            "campaign_slogan": "Nuevo lema",
            "party_color_hex": "#654321",
            "display_order": 8,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["candidate"]["candidate_name"] == "Candidato Actualizado"

    deactivated = admin_client.put(
        "/api/admin/candidates/CAND-TEST/status",
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    public = admin_client.get("/api/candidates")
    assert all(c["candidate_id"] != "CAND-TEST" for c in public.json())

    opened = admin_client.post("/api/election/open")
    assert opened.status_code == 200, opened.text

    blocked = admin_client.post(
        "/api/admin/candidates",
        json={
            "candidate_id": "CAND-BLOCKED",
            "candidate_name": "No permitido",
            "party_name": "Ninguno",
        },
    )
    assert blocked.status_code == 409

    # Con votos registrados, editar la papeleta también se bloquea.
    vote = admin_client.post(
        "/api/votes/cast",
        json={
            "document_id": "20000010",
            "pin": "1234",
            "ballot_type": "candidate",
            "selection": {"candidate_id": "CAND-01"},
        },
    )
    assert vote.status_code == 200, vote.text
    closed = admin_client.post("/api/election/close")
    assert closed.status_code == 200
    blocked_edit = admin_client.put(
        "/api/admin/candidates/CAND-01",
        json={
            "candidate_name": "Cambio tardío",
            "party_name": "Partido",
            "campaign_slogan": "",
            "party_color_hex": "#111111",
            "display_order": 1,
        },
    )
    assert blocked_edit.status_code == 409

    admin_client.post("/api/admin/reset-election")


def test_candidate_admin_requires_session():
    raw = TestClient(app)
    assert raw.get("/api/admin/candidates").status_code == 401
    assert raw.post("/api/admin/candidates", json={}).status_code == 401


def test_tally_is_persisted_and_exportable(admin_client):
    """El acta queda en SQLite y se puede consultar y descargar."""
    reset_and_open(admin_client)
    vote = admin_client.post(
        "/api/votes/cast",
        json={
            "document_id": "20000011",
            "pin": "1234",
            "ballot_type": "candidate",
            "selection": {"candidate_id": "CAND-01"},
        },
    )
    assert vote.status_code == 200, vote.text

    generated = admin_client.post(
        "/api/tally/generate",
        json={"officer_signatures": ["FIRMA-PRESIDENTE-TEST", "FIRMA-VOCAL-TEST"]},
    )
    assert generated.status_code == 200, generated.text

    latest = admin_client.get("/api/tally/latest")
    assert latest.status_code == 200, latest.text
    report = latest.json()
    assert len(report["integrity_hash"]) == 64
    assert report["total_votes"] >= 1
    assert report["payload"]["integrity_hash"] == report["integrity_hash"]

    as_json = admin_client.get("/api/tally/latest/export?format=json")
    assert as_json.status_code == 200
    assert "attachment" in as_json.headers["content-disposition"]
    assert as_json.json()["integrity_hash"] == report["integrity_hash"]

    as_csv = admin_client.get("/api/tally/latest/export?format=csv")
    assert as_csv.status_code == 200
    assert "text/csv" in as_csv.headers["content-type"]
    assert "integrity_hash" in as_csv.text
