"""Adaptadores de censo CSV, JSON y SQLite."""
from __future__ import annotations

from src.modules.census import CsvCensusAdapter, JsonCensusAdapter


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
