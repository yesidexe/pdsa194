"""Flujo público: cabina, autenticación y emisión del voto."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from src.main import app
from src.modules.voting import CandidateFlyweightFactory
from tests.helpers import reset_and_open


def test_html_views_and_admin_protection(admin_client):
    """Las vistas públicas cargan y el panel exige sesión."""
    raw = TestClient(app, follow_redirects=False)
    assert raw.get("/").status_code == 200
    assert "Cabina de Votación Digital" in raw.get("/").text
    assert raw.get("/dashboard").status_code == 200
    assert "RESULTADOS EN VIVO" in raw.get("/dashboard").text

    assert raw.get("/admin").status_code == 303
    assert raw.get("/admin/login").status_code == 200
    assert "Acceso administrativo" in raw.get("/admin/login").text
    assert admin_client.get("/admin").status_code == 200
    admin_html = admin_client.get("/admin").text
    assert "PANEL DE CONTROL ELECTORAL" in admin_html
    assert "Catálogo de Candidatos" in admin_html


def test_flyweight_candidates_pool(client):
    """El catálogo comparte instancias y expone los cuatro candidatos."""
    response = client.get("/api/candidates")
    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) >= 4

    c1 = CandidateFlyweightFactory.get_candidate("CAND-01")
    c2 = CandidateFlyweightFactory.get_candidate("CAND-01")
    assert c1 is c2
    assert CandidateFlyweightFactory.total_shared_instances() >= 4


def test_voter_authentication_with_pin(client):
    """El elector debe presentar documento y PIN correctos."""
    ok = client.post("/api/auth/verify", json={"document_id": "10203040", "pin": "1234"})
    assert ok.status_code == 200
    assert ok.json()["is_eligible"] is True

    bad_pin = client.post("/api/auth/verify", json={"document_id": "10203040", "pin": "0000"})
    assert bad_pin.status_code == 403

    ineligible = client.post("/api/auth/verify", json={"document_id": "99999999", "pin": "1234"})
    assert ineligible.status_code == 403


def test_secure_vote_and_duplicate(client):
    """Un elector vota una vez; el segundo intento recibe 409."""
    document_id = "20000002"
    first = client.post(
        "/api/votes/cast",
        json={
            "document_id": document_id,
            "pin": "1234",
            "ballot_type": "candidate",
            "selection": {"candidate_id": "CAND-02"},
        },
    )
    assert first.status_code == 200, first.text
    receipt = first.json()
    assert receipt["status"] == "VOTO_REGISTRADO_EXITOSAMENTE"
    assert receipt["digital_signature"] is not None
    assert receipt["receipt_code"]
    assert receipt["security_layers_applied"] == ["timestamp", "signature", "watermark"]

    duplicate = client.post(
        "/api/votes/cast",
        json={
            "document_id": document_id,
            "pin": "1234",
            "ballot_type": "blank",
            "selection": {},
        },
    )
    assert duplicate.status_code == 409


def test_fake_candidate_is_rejected(client):
    """El servidor no acepta candidatos que no estén en el tarjetón."""
    fake = client.post(
        "/api/votes/cast",
        json={
            "document_id": "20000003",
            "pin": "1234",
            "ballot_type": "candidate",
            "selection": {
                "candidate_id": "HACK-999",
                "candidate_name": "Candidato Fantasma",
                "party_name": "Partido Inexistente",
            },
        },
    )
    assert fake.status_code == 400
    # No quedó registrado: el elector sigue habilitado.
    verify = client.post("/api/auth/verify", json={"document_id": "20000003", "pin": "1234"})
    assert verify.status_code == 200


def test_concurrent_duplicate_vote_only_one_wins():
    """La restricción única de la base impide el doble voto concurrente."""
    document_id = "20000004"

    def cast_once(_):
        local_client = TestClient(app)
        return local_client.post(
            "/api/votes/cast",
            json={
                "document_id": document_id,
                "pin": "1234",
                "ballot_type": "candidate",
                "selection": {"candidate_id": "CAND-01"},
            },
        ).status_code

    with ThreadPoolExecutor(max_workers=6) as executor:
        statuses = list(executor.map(cast_once, range(6)))

    assert statuses.count(200) == 1, statuses
    assert all(status in (200, 409) for status in statuses), statuses


def test_validation_chain_rejects_closed_poll(admin_client):
    """Chain devuelve un motivo claro cuando la urna está cerrada."""
    reset_and_open(admin_client)
    closed = admin_client.post("/api/election/close")
    assert closed.status_code == 200

    rejected = admin_client.post(
        "/api/auth/verify",
        json={"document_id": "10203040", "pin": "1234"},
    )
    assert rejected.status_code == 403
    assert "no está abierta" in rejected.json()["detail"]

    reopened = admin_client.post("/api/election/open")
    assert reopened.status_code == 200
