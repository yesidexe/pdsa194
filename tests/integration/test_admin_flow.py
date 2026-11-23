"""Panel administrativo: urna, acta y auditoría."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app
from tests.helpers import reset_and_open


def test_admin_endpoints_require_auth():
    """Censo, auditoría y acciones de urna no son públicos."""
    raw = TestClient(app)
    assert raw.get("/api/census/voters").status_code == 401
    assert raw.get("/api/security/audit-log").status_code == 401
    assert raw.post("/api/election/open").status_code == 401
    assert raw.post("/api/admin/reset-election").status_code == 401


def test_tally_builder_and_proxy_audit(admin_client):
    """El acta se genera y la bitácora es accesible solo con sesión."""
    vote = admin_client.post(
        "/api/votes/cast",
        json={
            "document_id": "20000012",
            "pin": "1234",
            "ballot_type": "candidate",
            "selection": {"candidate_id": "CAND-01"},
        },
    )
    assert vote.status_code == 200, vote.text

    response = admin_client.post(
        "/api/tally/generate",
        json={"officer_signatures": ["FIRMA-PRESIDENTE-TEST", "FIRMA-VOCAL-TEST"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["integrity_hash_sha256"]) == 64
    assert len(data["signatures"]) == 2
    assert data["total_votes"] >= 1

    audit = admin_client.get("/api/security/audit-log")
    assert audit.status_code == 200
    assert len(audit.json()) > 0

    # Una jornada escrutada no se reabre sin reiniciarla.
    reopen = admin_client.post("/api/election/open")
    assert reopen.status_code == 409

    # Tampoco se puede generar una segunda acta sin reiniciar la jornada.
    repeat = admin_client.post(
        "/api/tally/generate",
        json={"officer_signatures": ["FIRMA-PRESIDENTE-TEST", "FIRMA-VOCAL-TEST"]},
    )
    assert repeat.status_code == 409

    from src.core.database import get_election_tallied
    assert get_election_tallied("NATIONAL") is True


def test_abstract_factory_mode_switching(admin_client):
    """La conmutación cambia validación, encabezado y regla de escrutinio."""
    mode = admin_client.get("/api/election/mode")
    assert mode.status_code == 200
    assert "mode" in mode.json()

    switch = admin_client.post("/api/election/switch-mode", json={"mode": "university"})
    assert switch.status_code == 200
    info = switch.json()
    assert info["mode"] == "university"
    assert "Universidad" in info["institution_name"]
    assert "Carnet Estudiantil" in info["document_type"]

    voter = admin_client.post("/api/auth/verify", json={"document_id": "EST-2024", "pin": "1234"})
    assert voter.status_code == 200
    assert voter.json()["is_eligible"] is True

    invalid = admin_client.post("/api/auth/verify", json={"document_id": "10203040", "pin": "1234"})
    assert invalid.status_code == 403

    vote = admin_client.post(
        "/api/votes/cast",
        json={
            "document_id": "EST-2024",
            "pin": "1234",
            "ballot_type": "candidate",
            "selection": {"candidate_id": "VOC-01"},
        },
    )
    assert vote.status_code == 200, vote.text

    tally = admin_client.post(
        "/api/tally/generate",
        json={"officer_signatures": ["FIRMA-JURADO-UNI-01"]},
    )
    assert tally.status_code == 200
    assert "Mayoría Simple" in tally.json().get("winner_verdict", "")

    back = admin_client.post("/api/election/switch-mode", json={"mode": "national"})
    assert back.status_code == 200
    assert back.json()["mode"] == "national"


def test_audit_log_is_persistent_and_verifiable(admin_client):
    """Los eventos se leen de SQLite y la cadena de hashes está intacta."""
    from src.core.database import list_audit_events
    from src.modules.audit.service import AuditService

    reset_and_open(admin_client)
    audit = admin_client.get("/api/security/audit-log")
    assert audit.status_code == 200
    assert len(audit.json()) > 0

    verification = admin_client.get("/api/security/audit-log/verify")
    assert verification.status_code == 200
    assert verification.json()["valid"] is True

    # Una instancia nueva lee los mismos eventos: no dependen de la memoria del Proxy.
    assert len(AuditService().history()) == len(list_audit_events())


def test_audit_chain_detects_tampering(admin_client):
    """Alterar un evento rompe la cadena; restaurarlo la repara."""
    from src.core.database import AuditEventModel, SessionLocal, verify_audit_chain

    reset_and_open(admin_client)
    session = SessionLocal()
    try:
        row = session.query(AuditEventModel).order_by(AuditEventModel.id.asc()).first()
        assert row is not None
        original_details = row.details
        row.details = f"{original_details} alterado"
        session.commit()
    finally:
        session.close()

    assert verify_audit_chain()["valid"] is False

    session = SessionLocal()
    try:
        row = session.query(AuditEventModel).order_by(AuditEventModel.id.asc()).first()
        row.details = original_details
        session.commit()
    finally:
        session.close()

    assert verify_audit_chain()["valid"] is True


def test_audit_log_can_be_exported(admin_client):
    """La bitácora se descarga en JSON y CSV solo con sesión."""
    reset_and_open(admin_client)
    as_json = admin_client.get("/api/security/audit-log/export?format=json")
    assert as_json.status_code == 200
    assert isinstance(as_json.json(), list)

    as_csv = admin_client.get("/api/security/audit-log/export?format=csv")
    assert as_csv.status_code == 200
    assert "action" in as_csv.text
