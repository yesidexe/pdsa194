"""Validación del elector y emisión del voto."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.modules.census.census_adapter import ICensusRegistry
from src.modules.election.election_factory import ElectoralFamilyFactory
from src.modules.election.state import ElectionStateMachine
from src.modules.voting.ballot_decorator import (
    AuditWatermarkDecorator,
    BallotSecurityDecorator,
    DigitalSignatureDecorator,
    TimestampSecurityDecorator,
)
from src.modules.voting.ballot_factory import (
    Ballot,
    BlankBallotCreator,
    CandidateBallotCreator,
    ReferendumBallotCreator,
)
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.modules.voting.vote_store import register_vote
from src.modules.voting.voter_validation import (
    AlreadyVotedValidator,
    CensusAuthenticationValidator,
    CredentialFormatValidator,
    EligibilityValidator,
    PollOpenValidator,
    VoterValidationChain,
    VoterValidationContext,
    VoterValidationError,
)


class VoteService:
    """Autentica al elector, construye la papeleta y la persiste."""

    def __init__(self, election_type: str, state_machine: ElectionStateMachine) -> None:
        self.election_type = election_type
        self._state = state_machine
        self._census: Optional[ICensusRegistry] = None
        self._family_factory: Optional[ElectoralFamilyFactory] = None
        self._chain: Optional[VoterValidationChain] = None
        self._candidate_creator = CandidateBallotCreator()
        self._referendum_creator = ReferendumBallotCreator()
        self._blank_creator = BlankBallotCreator()

    def configure(
        self,
        census: Optional[ICensusRegistry],
        family_factory: Optional[ElectoralFamilyFactory],
    ) -> None:
        self._census = census
        self._family_factory = family_factory
        self._chain = VoterValidationChain(
            [
                PollOpenValidator(self._state),
                CredentialFormatValidator(self._family_factory),
                CensusAuthenticationValidator(self._census),
                AlreadyVotedValidator(),
                EligibilityValidator(),
            ]
        )

    def verify_voter(self, document_id: str, pin: str, check_existing: bool = True) -> Dict[str, Any]:
        doc = str(document_id).strip()
        if self._chain is None:
            raise RuntimeError("La cadena de validación no está configurada.")

        context = VoterValidationContext(
            document_id=doc,
            pin=pin,
            election_type=self.election_type,
            check_existing=check_existing,
        )
        try:
            self._chain.validate(context)
        except VoterValidationError as exc:
            return {"document_id": doc, "is_eligible": False, "reason": str(exc)}

        record = context.record
        return {
            "document_id": doc,
            "is_eligible": True,
            "full_name": record.full_name if record else "",
            "assigned_station": record.assigned_station_id if record else "",
            "source_type": record.source_type if record else "",
        }

    def cast_secure_vote(
        self,
        document_id: str,
        pin: str,
        ballot_type: str,
        selection_kwargs: Dict[str, Any],
        security_layers: Optional[List[str]] = None,
        signing_key: str = "MASTER_FACADE_SECRET_2026",
    ) -> Dict[str, Any]:
        verification = self.verify_voter(document_id, pin, check_existing=False)
        if not verification.get("is_eligible", False):
            raise PermissionError(f"No autorizado para sufragar: {verification.get('reason')}")

        b_type = str(ballot_type).strip().lower()
        candidate_id: Optional[str] = None
        base_ballot: Ballot

        if b_type == "candidate":
            candidate_id = str(selection_kwargs.get("candidate_id", "")).strip()
            official = next(
                (c for c in CandidateFlyweightFactory.get_all_candidates() if c.candidate_id == candidate_id),
                None,
            )
            if official is None:
                raise ValueError("El candidato seleccionado no existe en el tarjetón oficial.")
            base_ballot = self._candidate_creator.issue_ballot(
                candidate_id=official.candidate_id,
                candidate_name=official.candidate_name,
                party_name=official.party_name,
            )
        elif b_type == "blank":
            base_ballot = self._blank_creator.issue_ballot(category="General")
        elif b_type == "referendum":
            question_code = str(selection_kwargs.get("question_code", "")).strip()
            decision = str(selection_kwargs.get("decision", "")).strip()
            if not question_code or not decision:
                raise ValueError("La papeleta de referendo requiere pregunta y decisión.")
            base_ballot = self._referendum_creator.issue_ballot(
                question_code=question_code,
                decision=decision,
            )
        else:
            raise ValueError(f"Modalidad de papeleta desconocida: '{ballot_type}'")

        decorated: Ballot = TimestampSecurityDecorator(base_ballot)
        decorated = DigitalSignatureDecorator(
            decorated,
            signing_key=signing_key,
            officer_token="TERM-FACADE-01",
        )
        decorated = AuditWatermarkDecorator(decorated)

        metadata: Dict[str, Any] = {}
        if isinstance(decorated, BallotSecurityDecorator):
            metadata = decorated.get_security_metadata()

        receipt_code = str(metadata.get("receipt_code") or f"REC-{decorated.ballot_id[:8].upper()}")
        register_vote(
            self.election_type,
            document_id,
            ballot_id=decorated.ballot_id,
            ballot_type=b_type,
            candidate_id=candidate_id,
            selection=decorated.get_selection(),
            receipt_code=receipt_code,
            digital_signature=metadata.get("digital_signature"),
            timestamp_seal=metadata.get("timestamp_seal"),
        )

        return {
            "status": "VOTO_REGISTRADO_EXITOSAMENTE",
            "receipt_code": receipt_code,
            "ballot_id": decorated.ballot_id,
            "issued_at": decorated.issued_at.isoformat(),
            "selection": decorated.get_selection(),
            "security_layers_applied": ["timestamp", "signature", "watermark"],
            "digital_signature": metadata.get("digital_signature"),
            "timestamp_seal": metadata.get("timestamp_seal"),
        }
