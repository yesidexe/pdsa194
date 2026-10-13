"""Suite de pruebas automatizadas del sistema electoral modular."""
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.modules.census import CsvCensusAdapter, JsonCensusAdapter
from src.modules.election import (
    UniversityElectionFactory,
    NationalElectionFactory,
    ElectoralJurisdictionComposite,
    VotingStationLeaf,
    VotingStation,
)
from src.modules.voting import (
    CandidateFlyweightFactory,
    ReferendumBallotCreator,
    BlankBallotCreator,
    TimestampSecurityDecorator,
    DigitalSignatureDecorator,
    AuditWatermarkDecorator,
)
from src.modules.transmission import (
    FileTransmissionChannel,
    PreliminaryBulletin,
    MemoryAuditSinkTransmissionChannel,
)
from src.modules.security.access_proxy import UserRole, UserSession


@pytest.fixture
def client():
    return TestClient(app)


def test_html_views(client):
    """Verifica que las vistas web principales rendericen con éxito."""
    r_home = client.get("/")
    assert r_home.status_code == 200
    assert "Cabina de Votación Digital" in r_home.text

    r_dash = client.get("/dashboard")
    assert r_dash.status_code == 200
    assert "RESULTADOS EN VIVO" in r_dash.text

    r_admin = client.get("/admin")
    assert r_admin.status_code == 200
    assert "PANEL DE CONTROL ELECTORAL" in r_admin.text


def test_flyweight_candidates_pool(client):
    """Verifica que el catálogo de candidatos comparta referencias en memoria."""
    r = client.get("/api/candidates")
    assert r.status_code == 200
    candidates = r.json()
    assert len(candidates) >= 3

    c1 = CandidateFlyweightFactory.get_candidate("CAND-01")
    c2 = CandidateFlyweightFactory.get_candidate("CAND-01")
    assert c1 is c2
    assert CandidateFlyweightFactory.total_shared_instances() >= 1


def test_voter_authentication_adapter(client):
    """Verifica la validación del elector contra el Censo adaptado (JSON y CSV)."""
    # JSON adapter
    r_ok = client.post("/api/auth/verify", json={"document_id": "10203040"})
    assert r_ok.status_code == 200
    assert r_ok.json()["is_eligible"] is True

    r_ineligible = client.post("/api/auth/verify", json={"document_id": "99999999"})
    assert r_ineligible.status_code == 403

    # CSV adapter
    csv_raw = "cedula,nombre,mesa,habilitado\n123456,Pedro Gomez,MESA-01,SI\n654321,Maria,MESA-01,NO"
    csv_adapter = CsvCensusAdapter(csv_raw)
    assert csv_adapter.is_eligible("123456") is True
    assert csv_adapter.is_eligible("654321") is False
    assert csv_adapter.get_total_registered() == 2


def test_abstract_factory_families():
    """Evalúa la coherencia de familias de componentes en Abstract Factory."""
    nat_fac = NationalElectionFactory()
    assert nat_fac.create_validator().validate_credential("10203040") is True
    assert "COLOMBIA" in nat_fac.create_header().render_header()
    assert "Mayoría" in nat_fac.create_tally_rule().evaluate_winner({"A": 100, "B": 10})

    uni_fac = UniversityElectionFactory()
    assert uni_fac.create_validator().validate_credential("U202401") is True
    assert "UNIVERSIDAD" in uni_fac.create_header().render_header()
    assert "Simple" in uni_fac.create_tally_rule().evaluate_winner({"A": 50, "B": 30})


def test_composite_hierarchy():
    """Evalúa la estructura recursiva de Composite."""
    st = VotingStation("M-TEST", "Colegio", "Z1")
    leaf = VotingStationLeaf(st)
    assert leaf.count_stations() == 1
    assert "M-TEST" in leaf.get_station_ids()
    assert leaf.find_unit("M-TEST") is not None

    comp = ElectoralJurisdictionComposite("ZONA-1", "Zona Norte", "ZONA")
    comp.add(leaf)
    assert comp.count_stations() == 1
    assert "M-TEST" in comp.get_station_ids()
    assert comp.find_unit("M-TEST") is not None
    assert comp.find_unit("INEXISTENTE") is None
    assert "ZONA" in comp.display_hierarchy()


def test_ballot_creators_and_decorators():
    """Evalúa creación de papeletas y capas de seguridad acumulativas."""
    ref_creator = ReferendumBallotCreator()
    ballot = ref_creator.issue_ballot(question_code="REF-01", decision="SI")
    assert "REF-01" in ballot.get_selection()

    blank_creator = BlankBallotCreator()
    blank = blank_creator.issue_ballot(category="General")
    assert "BLANCO" in blank.get_selection()

    # Decorators
    dec_time = TimestampSecurityDecorator(ballot)
    dec_sig = DigitalSignatureDecorator(dec_time, signing_key="KEY_TEST")
    dec_water = AuditWatermarkDecorator(dec_sig)

    assert dec_water.get_selection() == ballot.get_selection()
    assert dec_sig.verify_signature("KEY_TEST") is True
    assert dec_sig.verify_signature("WRONG_KEY") is False
    meta = dec_water.get_security_metadata()
    assert "digital_signature" in meta
    assert "timestamp_seal" in meta
    assert "watermark" in meta
    assert len(dec_water.get_audit_trail()) == 3


def test_bridge_transmission(tmp_path):
    """Evalúa despacho multicanal mediante Bridge."""
    sink = MemoryAuditSinkTransmissionChannel()
    bulletin = PreliminaryBulletin(sink, 1, "Elección", ["M1"], {"A": 10})
    assert bulletin.dispatch("AUDITORIA") is True
    assert len(sink.sent_messages) == 1

    file_chan = FileTransmissionChannel(str(tmp_path))
    bulletin.channel = file_chan
    assert bulletin.dispatch("LOG_FILE") is True


def test_secure_vote_casting_and_double_vote_prevention(client):
    """Verifica la emisión de voto, aplicación de decoradores y control de voto único."""
    # Primer voto exitoso
    r_vote = client.post(
        "/api/votes/cast",
        json={
            "document_id": "70809010",
            "ballot_type": "candidate",
            "selection": {
                "candidate_id": "CAND-02",
                "candidate_name": "Elena Torres",
                "party_name": "Pacto Innovación Ciudadana",
            },
            "security_layers": ["timestamp", "signature", "watermark"],
        },
    )
    assert r_vote.status_code == 200
    receipt = r_vote.json()
    assert receipt["status"] == "VOTO_REGISTRADO_EXITOSAMENTE"
    assert receipt["digital_signature"] is not None
    assert receipt["receipt_code"] is not None

    # Intento de segundo voto con la misma cédula (bloqueo)
    r_duplicate = client.post(
        "/api/votes/cast",
        json={
            "document_id": "70809010",
            "ballot_type": "blank",
            "selection": {"category": "General"},
        },
    )
    assert r_duplicate.status_code == 403


def test_tally_builder_and_proxy_audit(client):
    """Verifica la generación del acta oficial sellada con SHA-256 y la auditoría del Proxy."""
    r_tally = client.post(
        "/api/tally/generate",
        json={
            "officer_signatures": ["FIRMA-PRESIDENTE-TEST", "FIRMA-VOCAL-TEST"],
            "user_id": "ADMIN-01",
            "session_token": "TOKEN-ADMIN-MASTER-2026",
        },
    )
    assert r_tally.status_code == 200
    data = r_tally.json()
    assert len(data["integrity_hash_sha256"]) == 64
    assert len(data["signatures"]) == 2

    # Consulta de bitácora del Proxy
    r_audit = client.get("/api/security/audit-log")
    assert r_audit.status_code == 200
    logs = r_audit.json()
    assert len(logs) > 0


def test_abstract_factory_mode_switching(client):
    """Verifica la conmutación entre familias electorales (Nacional vs. Universitaria) del Abstract Factory."""
    # 1. Consultar modo inicial
    r_mode = client.get("/api/election/mode")
    assert r_mode.status_code == 200
    initial_info = r_mode.json()
    assert "mode" in initial_info

    # 2. Conmutar a modo universitario
    r_switch = client.post(
        "/api/election/switch-mode",
        json={
            "mode": "university",
            "user_id": "ADMIN-01",
            "session_token": "TOKEN-ADMIN-MASTER-2026",
        },
    )
    assert r_switch.status_code == 200
    uni_info = r_switch.json()
    assert uni_info["mode"] == "university"
    assert "Universidad" in uni_info["institution_name"]
    assert "Carnet Estudiantil" in uni_info["document_type"]

    # 3. Validar credencial estudiantil (EST-2024 habilitado)
    r_voter = client.post("/api/auth/verify", json={"document_id": "EST-2024"})
    assert r_voter.status_code == 200
    assert r_voter.json()["is_eligible"] is True

    # 4. Validar rechazo de cédula o formato no estudiantil
    r_invalid = client.post("/api/auth/verify", json={"document_id": "10203040"})
    assert r_invalid.status_code == 403

    # 5. Emitir voto en modo universitario
    r_vote = client.post(
        "/api/votes/cast",
        json={
            "document_id": "EST-2024",
            "ballot_type": "candidate",
            "selection": {
                "candidate_id": "VOC-01",
                "candidate_name": "Camilo Suárez",
                "party_name": "Lista 1 - Estudiantes por el Cambio",
            },
            "security_layers": ["timestamp", "signature", "watermark"],
        },
    )
    assert r_vote.status_code == 200

    # 6. Generar acta y validar regla de mayoría simple (SimplePluralityTallyRule)
    r_tally = client.post(
        "/api/tally/generate",
        json={
            "officer_signatures": ["FIRMA-JURADO-UNI-01"],
            "user_id": "ADMIN-01",
            "session_token": "TOKEN-ADMIN-MASTER-2026",
        },
    )
    assert r_tally.status_code == 200
    tally_data = r_tally.json()
    assert "Mayoría Simple" in tally_data.get("winner_verdict", "")

    # 7. Conmutar de regreso a nacional
    r_back = client.post(
        "/api/election/switch-mode",
        json={
            "mode": "national",
            "user_id": "ADMIN-01",
            "session_token": "TOKEN-ADMIN-MASTER-2026",
        },
    )
    assert r_back.status_code == 200
    assert r_back.json()["mode"] == "national"


def test_sqlite_census_adapter_direct():
    """Verifica operaciones directas sobre el adaptador SQLite del censo."""
    from src.modules.census.census_adapter import SqliteCensusAdapter

    adapter = SqliteCensusAdapter(election_type="NATIONAL")
    # Inscribir votante de prueba
    record = adapter.register_voter(
        document_id="TEST-CITIZEN-99",
        full_name="Prueba Ciudadana",
        assigned_station_id="MESA-99",
        is_eligible=True,
        election_type="NATIONAL",
    )
    assert record.document_id == "TEST-CITIZEN-99"
    assert record.is_eligible is True

    # Comprobar consulta
    assert adapter.is_eligible("TEST-CITIZEN-99") is True
    rec_fetched = adapter.get_voter_record("TEST-CITIZEN-99")
    assert rec_fetched is not None
    assert rec_fetched.full_name == "Prueba Ciudadana"

    # Inhabilitar y comprobar
    assert adapter.toggle_eligibility("TEST-CITIZEN-99", False) is True
    assert adapter.is_eligible("TEST-CITIZEN-99") is False

    # Habilitar nuevamente
    assert adapter.toggle_eligibility("TEST-CITIZEN-99", True) is True
    assert adapter.is_eligible("TEST-CITIZEN-99") is True

    # Total registrado
    assert adapter.get_total_registered() > 0
    all_voters = adapter.get_all_voters()
    assert len(all_voters) > 0


def test_census_api_endpoints(client):
    """Verifica los endpoints REST de administración del censo electoral en SQLite."""
    # 1. Listar votantes
    r_list = client.get("/api/census/voters")
    assert r_list.status_code == 200
    voters = r_list.json()
    assert isinstance(voters, list)
    assert len(voters) > 0

    # 2. Inscribir nuevo votante
    r_create = client.post(
        "/api/census/voters",
        json={
            "document_id": "88776655",
            "full_name": "Nuevo Elector API",
            "assigned_station_id": "MESA-01",
            "is_eligible": True,
            "election_type": "NATIONAL",
            "user_id": "ADMIN-01",
            "session_token": "TOKEN-ADMIN-MASTER-2026",
        },
    )
    assert r_create.status_code == 200
    created = r_create.json()
    assert created["status"] == "ELECTOR_REGISTRADO"
    assert created["document_id"] == "88776655"

    # 3. Verificar que ahora puede autenticarse
    r_verify = client.post("/api/auth/verify", json={"document_id": "88776655"})
    assert r_verify.status_code == 200
    assert r_verify.json()["is_eligible"] is True

    # 4. Inhabilitar vía API
    r_toggle = client.put(
        "/api/census/voters/88776655/status",
        json={
            "is_eligible": False,
            "user_id": "ADMIN-01",
            "session_token": "TOKEN-ADMIN-MASTER-2026",
        },
    )
    assert r_toggle.status_code == 200
    assert r_toggle.json()["is_eligible"] is False

    # 5. Verificar que ahora es rechazado
    r_verify_disabled = client.post("/api/auth/verify", json={"document_id": "88776655"})
    assert r_verify_disabled.status_code == 403

    # 6. Intentar registrar sin rol administrador
    r_unauth = client.post(
        "/api/census/voters",
        json={
            "document_id": "00000001",
            "full_name": "Intruso",
            "assigned_station_id": "MESA-01",
            "is_eligible": True,
            "user_id": "INTRUDER",
            "session_token": "WRONG_TOKEN",
        },
    )
    assert r_unauth.status_code == 403


