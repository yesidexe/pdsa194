"""Conteo, construcción y persistencia del acta de escrutinio."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.database import get_latest_tally_report, record_tally_report
from src.modules.election.election_factory import ElectoralFamilyFactory, TallyRule
from src.modules.election.state import ElectionStateMachine
from src.modules.tally.report_builder import ElectoralTallyReport, OfficialTallyReportBuilder
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.modules.voting.vote_store import list_ballots


class TallyAlreadyGeneratedError(Exception):
    """La jornada ya tiene un acta y no puede escrutarse dos veces sin reiniciar."""


class TallyService:
    """Cuenta papeletas, arma el acta y la deja persistida."""

    def __init__(
        self,
        election_type: str,
        state_machine: ElectionStateMachine,
        election_title: str,
        jurisdiction_name: str,
        station_ids: List[str],
    ) -> None:
        self.election_type = election_type
        self._state = state_machine
        self._election_title = election_title
        self._jurisdiction_name = jurisdiction_name
        self._station_ids = list(station_ids)
        self._family_factory: Optional[ElectoralFamilyFactory] = None
        self._builder = OfficialTallyReportBuilder()

    def configure(
        self,
        family_factory: Optional[ElectoralFamilyFactory],
        election_title: str,
        jurisdiction_name: str,
        station_ids: List[str],
    ) -> None:
        self._family_factory = family_factory
        self._election_title = election_title
        self._jurisdiction_name = jurisdiction_name
        self._station_ids = list(station_ids)

    def get_station_ids(self) -> List[str]:
        return list(self._station_ids)

    def get_latest(self) -> Optional[Dict[str, Any]]:
        return get_latest_tally_report(self.election_type)

    def close_and_generate_tally(self, officer_signatures: List[str]) -> ElectoralTallyReport:
        if self._state.is_tallied:
            raise TallyAlreadyGeneratedError(
                "La jornada ya fue escrutada. Reinicia la jornada para generar una nueva acta."
            )

        candidate_votes: Dict[str, int] = {}
        blank_votes = 0
        null_votes = 0
        other_votes: Dict[str, int] = {}

        for ballot in list_ballots(self.election_type):
            if ballot.ballot_type == "blank" or "VOTO EN BLANCO" in ballot.selection.upper():
                blank_votes += 1
            elif ballot.candidate_id:
                official = next(
                    (
                        c
                        for c in CandidateFlyweightFactory.get_all_candidates()
                        if c.candidate_id == ballot.candidate_id
                    ),
                    None,
                )
                label = f"{official.candidate_name} ({official.party_name})" if official else ballot.selection
                candidate_votes[label] = candidate_votes.get(label, 0) + 1
            else:
                other_votes[ballot.selection] = other_votes.get(ballot.selection, 0) + 1
        candidate_votes.update(other_votes)

        tables = self.get_station_ids() or ["MESA-01"]
        winner_verdict = "Escrutinio completado."
        if self._family_factory is not None:
            tally_rule: TallyRule = self._family_factory.create_tally_rule()
            winner_verdict = tally_rule.evaluate_winner(candidate_votes)

        builder = self._builder.reset()
        builder.set_header(election_title=self._election_title, jurisdiction=self._jurisdiction_name)
        builder.add_table_batch(tables)
        builder.set_votes(candidate_votes=candidate_votes, blank_votes=blank_votes, null_votes=null_votes)
        for signature in officer_signatures:
            builder.add_officer_signature(signature)
        builder.set_winner_verdict(winner_verdict)
        report = builder.build()

        record_tally_report(
            election_type=self.election_type,
            election_title=report.election_title,
            jurisdiction=report.jurisdiction,
            generated_at=report.generated_at,
            total_votes=report.total_votes,
            candidate_votes=report.candidate_votes,
            blank_votes=report.blank_votes,
            null_votes=report.null_votes,
            winner_verdict=report.winner_verdict,
            officer_signatures=report.officer_signatures,
            integrity_hash=report.integrity_hash,
        )
        self._state.tally()
        return report
