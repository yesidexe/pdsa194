"""Familias electorales, papeletas y decoradores."""
from __future__ import annotations

from src.modules.election import NationalElectionFactory, UniversityElectionFactory
from src.modules.voting import (
    AuditWatermarkDecorator,
    BlankBallotCreator,
    DigitalSignatureDecorator,
    ReferendumBallotCreator,
    TimestampSecurityDecorator,
)


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
