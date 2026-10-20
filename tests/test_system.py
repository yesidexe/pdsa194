"""Suite de pruebas del simulador electoral local.

Las pruebas usan una base separada (ver ``tests/conftest.py``) y verifican los
invariantes principales: autenticación con PIN, candidato validado, voto único,
persistencia, protección de administración y reset de jornada.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from src.main import app
from src.modules.census import CsvCensusAdapter, JsonCensusAdapter
from src.modules.election import (
    ElectoralJurisdictionComposite,
    NationalElectionFactory,
    UniversityElectionFactory,
    VotingStationLeaf,
    VotingStation,
)
from src.modules.voting import (
    AuditWatermarkDecorator,
    BlankBallotCreator,
    CandidateFlyweightFactory,
    DigitalSignatureDecorator,
    ReferendumBallotCreator,
    TimestampSecurityDecorator,
)
from src.modules.transmission import (
    FileTransmissionChannel,
    MemoryAuditSinkTransmissionChannel,
    PreliminaryBulletin,
)


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
    assert "PANEL DE CONTROL ELECTORAL" in admin_client.get("/admin").text


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


def test_csv_adapter_still_works():
    """El adaptador CSV conserva su contrato de lectura."""
    csv_raw = "cedula,nombre,mesa,habilitado\n123456,Pedro Gomez,MESA-01,SI\n654321,Maria,MESA-01,NO"
    adapter = CsvCensusAdapter(csv_raw)
    assert adapter.is_eligible("123456") is True
    assert adapter.is_eligible("654321") is False
    assert adapter.get_total_registered() == 2
    assert adapter.get_total_eligible() == 1

    # El adaptador JSON no debe convertir la cadena "false" en True.
    import json
    json_adapter = JsonCensusAdapter(json.dumps({
        "electores": [
            {"documento_id": "J1", "nombre_completo": "Persona Uno", "habilitado": "false"},
            {"documento_id": "J2", "nombre_completo": "Persona Dos", "habilitado": True},
        ]
    }))
    assert json_adapter.is_eligible("J1") is False
    assert json_adapter.is_eligible("J2") is True
    assert json_adapter.get_total_eligible() == 1


def test_abstract_factory_families():
    """Cada familia produce validador, encabezado y regla coherentes."""
    national = NationalElectionFactory()
    assert national.create_validator().validate_credential("10203040") is True
    assert "COLOMBIA" in national.create_header().render_header()
    assert "Mayoría" in national.create_tally_rule().evaluate_winner({"A": 100, "B": 10})

    university = UniversityElectionFactory()
    assert university.create_validator().validate_credential("EST-2024") is True
    assert "UNIVERSIDAD" in university.create_header().render_header()
    assert "Simple" in university.create_tally_rule().evaluate_winner({"A": 50, "B": 30})


def test_composite_hierarchy():
    """El árbol de mesas cuenta y busca hojas de forma recursiva."""
    station = VotingStation("M-TEST", "Colegio", "Z1")
    leaf = VotingStationLeaf(station)
    assert leaf.count_stations() == 1
    assert "M-TEST" in leaf.get_station_ids()
    assert leaf.find_unit("M-TEST") is not None

    composite = ElectoralJurisdictionComposite("ZONA-1", "Zona Norte", "ZONA")
    composite.add(leaf)
    assert composite.count_stations() == 1
    assert "M-TEST" in composite.get_station_ids()
    assert composite.find_unit("M-TEST") is not None
    assert composite.find_unit("INEXISTENTE") is None


def test_ballot_creators_and_decorators():
    """Las papeletas y las capas de seguridad conservan su contrato."""
    referendum = ReferendumBallotCreator().issue_ballot(question_code="REF-01", decision="SI")
    assert "REF-01" in referendum.get_selection()

    blank = BlankBallotCreator().issue_ballot(category="General")
    assert "BLANCO" in blank.get_selection()

    timestamped = TimestampSecurityDecorator(referendum)
    signed = DigitalSignatureDecorator(timestamped, signing_key="KEY_TEST")
    watermarked = AuditWatermarkDecorator(signed)

    assert watermarked.get_selection() == referendum.get_selection()
    assert watermarked.base_ballot is referendum
    assert signed.verify_signature("KEY_TEST") is True
    assert signed.verify_signature("WRONG_KEY") is False
    metadata = watermarked.get_security_metadata()
    assert {"digital_signature", "timestamp_seal", "watermark"} <= set(metadata)
    assert len(watermarked.get_audit_trail()) == 3


def test_bridge_transmission(tmp_path):
    """El canal de archivo y el sink de memoria reciben el boletín."""
    sink = MemoryAuditSinkTransmissionChannel()
    bulletin = PreliminaryBulletin(sink, 1, "Elección", ["M1"], {"A": 10})
    assert bulletin.dispatch("AUDITORIA") is True
    assert len(sink.sent_messages) == 1

    file_channel = FileTransmissionChannel(str(tmp_path))
    bulletin.channel = file_channel
    assert bulletin.dispatch("LOG_FILE") is True


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


def test_admin_endpoints_require_auth():
    """Censo, auditoría y acciones de urna no son públicos."""
    raw = TestClient(app)
    assert raw.get("/api/census/voters").status_code == 401
    assert raw.get("/api/security/audit-log").status_code == 401
    assert raw.post("/api/election/open").status_code == 401
    assert raw.post("/api/admin/reset-election").status_code == 401


def test_tally_builder_and_proxy_audit(admin_client):
    """El acta se genera y la bitácora es accesible solo con sesión."""
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


def test_sqlite_census_adapter_direct():
    """El adaptador SQLite autentica, actualiza y cuenta habilitados."""
    from src.modules.census.census_adapter import SqliteCensusAdapter

    adapter = SqliteCensusAdapter(election_type="NATIONAL")
    record = adapter.register_voter(
        document_id="TEST-CITIZEN-99",
        full_name="Prueba Ciudadana",
        assigned_station_id="MESA-99",
        is_eligible=True,
        election_type="NATIONAL",
        pin="4321",
    )
    assert record.document_id == "TEST-CITIZEN-99"
    assert adapter.authenticate("TEST-CITIZEN-99", "4321") is not None
    assert adapter.authenticate("TEST-CITIZEN-99", "0000") is None

    assert adapter.toggle_eligibility("TEST-CITIZEN-99", False) is True
    assert adapter.authenticate("TEST-CITIZEN-99", "4321") is None
    assert adapter.toggle_eligibility("TEST-CITIZEN-99", True) is True

    assert adapter.get_total_registered() > 0
    assert adapter.get_total_eligible() > 0
    assert len(adapter.get_all_voters()) > 0


def test_census_api_endpoints(admin_client):
    """Inscripción, consulta y cambio de habilitación desde el panel."""
    admin_client.post("/api/admin/reset-election")
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
    admin_client.post("/api/admin/reset-election")
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
    assert mode["is_open"] is True
    assert mode["is_tallied"] is False
    # El censo sigue disponible (incluye los electores añadidos por otras pruebas).
    census = admin_client.get("/api/census/voters").json()
    assert len(census) >= 41
