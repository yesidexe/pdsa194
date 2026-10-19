"""Fachada de alto nivel del sistema electoral.

La fachada coordina los subsistemas, pero ya no guarda los votos en memoria:
la urna vive en SQLite y se accede a través de ``vote_store``. La separación
entre participación y papeleta permite mantener el secreto del voto.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.config import ElectoralConfigManager
from src.modules.census.census_adapter import ICensusRegistry
from src.modules.election.election_factory import (
    ElectoralFamilyFactory,
    CredentialValidator,
    TallyRule,
)
from src.modules.election.station_prototype import VotingStation, StationPrototypeRegistry
from src.modules.election.jurisdiction_composite import ElectoralUnit
from src.modules.voting.ballot_factory import (
    Ballot,
    CandidateBallotCreator,
    ReferendumBallotCreator,
    BlankBallotCreator,
)
from src.modules.voting.ballot_decorator import (
    AuditWatermarkDecorator,
    BallotSecurityDecorator,
    DigitalSignatureDecorator,
    TimestampSecurityDecorator,
)
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.modules.voting.vote_store import (
    has_voted,
    list_ballots,
    register_vote,
    reset_election as reset_election_store,
)
from src.modules.tally.report_builder import OfficialTallyReportBuilder, ElectoralTallyReport
from src.modules.transmission.bulletin_bridge import (
    ITransmissionChannel,
    PreliminaryBulletin,
    OfficialClosingBulletin,
)


class VotingSystemFacade:
    """Punto de entrada único para las operaciones de la jornada electoral."""

    def __init__(
        self,
        institution_name: str = "Consejo Nacional Electoral",
        election_title: str = "Elecciones Oficiales 2026",
        election_type: str = "NATIONAL",
    ) -> None:
        self.election_type = election_type.upper().strip()
        self._config: ElectoralConfigManager = ElectoralConfigManager(
            institution_name=institution_name,
            election_title=election_title,
        )
        self._station_registry: StationPrototypeRegistry = StationPrototypeRegistry()
        self._candidate_creator: CandidateBallotCreator = CandidateBallotCreator()
        self._referendum_creator: ReferendumBallotCreator = ReferendumBallotCreator()
        self._blank_creator: BlankBallotCreator = BlankBallotCreator()
        self._tally_builder: OfficialTallyReportBuilder = OfficialTallyReportBuilder()

        self._census: Optional[ICensusRegistry] = None
        self._family_factory: Optional[ElectoralFamilyFactory] = None
        self._transmission_channel: Optional[ITransmissionChannel] = None
        self._jurisdiction_tree: Optional[ElectoralUnit] = None
        self._tally_generated: bool = False

    # =========================================================================
    # A. CONFIGURACIÓN DEL ECOSISTEMA
    # =========================================================================

    def setup_environment(
        self,
        census_registry: ICensusRegistry,
        family_factory: Optional[ElectoralFamilyFactory] = None,
        transmission_channel: Optional[ITransmissionChannel] = None,
        jurisdiction_tree: Optional[ElectoralUnit] = None,
    ) -> None:
        """Asocia censo, familia electoral, canal y jerarquía de mesas."""
        self._census = census_registry
        self._family_factory = family_factory
        self._transmission_channel = transmission_channel
        self._jurisdiction_tree = jurisdiction_tree

    def register_station_template(self, template_key: str, station_template: VotingStation) -> None:
        """Registra una plantilla operativa de mesa mediante Prototype."""
        self._station_registry.register_prototype(template_key, station_template)

    def spawn_station(
        self,
        template_key: str,
        station_id: str,
        terminal_code: str,
        officers: Optional[List[str]] = None,
    ) -> VotingStation:
        """Clona y personaliza una mesa a partir de una plantilla registrada."""
        return self._station_registry.get_clone(template_key).assign_station(
            new_station_id=station_id,
            new_terminal_code=terminal_code,
            new_officers=officers,
        )

    # =========================================================================
    # B. ESTADO DE LA JORNADA
    # =========================================================================

    @property
    def is_voting_open(self) -> bool:
        return self._config.is_open

    @property
    def is_tallied(self) -> bool:
        """Indica si ya se generó el acta de esta jornada."""
        return self._tally_generated

    @property
    def institution_name(self) -> str:
        return self._config.institution_name

    @property
    def election_title(self) -> str:
        return self._config.election_title

    @property
    def ballot_header(self) -> str:
        if self._family_factory is None:
            return "Encabezado Oficial"
        return self._family_factory.create_header().render_header()

    @property
    def document_type(self) -> str:
        if self._family_factory is None:
            return "Documento de Identidad"
        return self._family_factory.create_validator().get_document_type()

    def open_polls(self) -> None:
        if self._tally_generated:
            raise ValueError(
                "La jornada ya fue escrutada. Reinicia la jornada para volver a abrir la urna."
            )
        self._config.open_voting()

    def close_polls(self) -> None:
        self._config.close_voting()

    def reset_election(self) -> int:
        """Borra votos y participaciones de esta elección y reabre la urna."""
        removed = reset_election_store(self.election_type)
        self._tally_generated = False
        self.open_polls()
        return removed

    # =========================================================================
    # C. AUTENTICACIÓN DEL ELECTOR
    # =========================================================================

    def verify_voter(self, document_id: str, pin: str, check_existing: bool = True) -> Dict[str, Any]:
        """Valida documento + PIN, estado de la urna y voto único.

        La comprobación de PIN la hace el censo (Adapter). Si la fuente censal
        no soporta credenciales, se falla cerrado.

        ``check_existing=False`` se usa al emitir el voto: la garantía final
        contra el doble voto es la restricción única de la base de datos, no
        una consulta previa que podría competir con otra petición.
        """
        doc = str(document_id).strip()

        if not self._config.is_open:
            return {
                "document_id": doc,
                "is_eligible": False,
                "reason": "La jornada de votación no está abierta.",
            }

        if self._family_factory is not None:
            validator: CredentialValidator = self._family_factory.create_validator()
            if not validator.validate_credential(doc):
                return {
                    "document_id": doc,
                    "is_eligible": False,
                    "reason": f"Formato de credencial inválido para {validator.get_document_type()}.",
                }

        if self._census is None:
            return {
                "document_id": doc,
                "is_eligible": False,
                "reason": "El censo electoral no está disponible.",
            }

        record = self._census.authenticate(doc, pin)
        if record is None:
            return {
                "document_id": doc,
                "is_eligible": False,
                "reason": "Documento o PIN incorrecto, o elector no habilitado.",
            }

        if check_existing and has_voted(self.election_type, doc):
            return {
                "document_id": doc,
                "is_eligible": False,
                "reason": "El ciudadano ya ejerció su derecho al voto en esta jornada.",
            }

        return {
            "document_id": doc,
            "is_eligible": True,
            "full_name": record.full_name,
            "assigned_station": record.assigned_station_id,
            "source_type": record.source_type,
        }

    # =========================================================================
    # D. EMISIÓN DEL VOTO
    # =========================================================================

    def cast_secure_vote(
        self,
        document_id: str,
        pin: str,
        ballot_type: str,
        selection_kwargs: Dict[str, Any],
        security_layers: Optional[List[str]] = None,
        signing_key: str = "MASTER_FACADE_SECRET_2026",
    ) -> Dict[str, Any]:
        """Emite un voto validado, sellado y persistido de forma atómica.

        El cliente solo puede elegir el ``candidate_id`` (o la categoría del
        voto en blanco). El nombre, partido y capas de seguridad los decide el
        servidor para evitar votos con datos inventados o sin firma.
        """
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

        # Las capas de seguridad son una política del servidor, no una opción
        # del cliente. Se aplican siempre las tres.
        decorated_ballot: Ballot = TimestampSecurityDecorator(base_ballot)
        decorated_ballot = DigitalSignatureDecorator(
            decorated_ballot,
            signing_key=signing_key,
            officer_token="TERM-FACADE-01",
        )
        decorated_ballot = AuditWatermarkDecorator(decorated_ballot)

        metadata: Dict[str, Any] = {}
        if isinstance(decorated_ballot, BallotSecurityDecorator):
            metadata = decorated_ballot.get_security_metadata()

        receipt_code = str(metadata.get("receipt_code") or f"REC-{decorated_ballot.ballot_id[:8].upper()}")

        # Participación + papeleta en una sola transacción. La restricción
        # única de participación es la garantía final contra el doble voto.
        register_vote(
            self.election_type,
            document_id,
            ballot_id=decorated_ballot.ballot_id,
            ballot_type=b_type,
            candidate_id=candidate_id,
            selection=decorated_ballot.get_selection(),
            receipt_code=receipt_code,
            digital_signature=metadata.get("digital_signature"),
            timestamp_seal=metadata.get("timestamp_seal"),
        )

        return {
            "status": "VOTO_REGISTRADO_EXITOSAMENTE",
            "receipt_code": receipt_code,
            "ballot_id": decorated_ballot.ballot_id,
            "issued_at": decorated_ballot.issued_at.isoformat(),
            "selection": decorated_ballot.get_selection(),
            "security_layers_applied": ["timestamp", "signature", "watermark"],
            "digital_signature": metadata.get("digital_signature"),
            "timestamp_seal": metadata.get("timestamp_seal"),
        }

    # =========================================================================
    # E. TRANSMISIÓN Y ESCRUTINIO
    # =========================================================================

    def emit_preliminary_bulletin(
        self,
        bulletin_number: int,
        destination: str = "CENTRO_DE_DATOS_CENTRAL",
    ) -> Optional[bool]:
        """Genera y transmite un boletín parcial con los votos persistidos."""
        if self._transmission_channel is None:
            return None

        candidate_votes: Dict[str, int] = {}
        for ballot in list_ballots(self.election_type):
            if ballot.ballot_type == "blank" or "VOTO EN BLANCO" in ballot.selection.upper():
                label = "VOTO EN BLANCO"
            elif ballot.candidate_id:
                official = next(
                    (
                        c
                        for c in CandidateFlyweightFactory.get_all_candidates()
                        if c.candidate_id == ballot.candidate_id
                    ),
                    None,
                )
                label = (
                    f"{official.candidate_name} ({official.party_name})"
                    if official
                    else ballot.selection
                )
            else:
                label = ballot.selection
            candidate_votes[label] = candidate_votes.get(label, 0) + 1

        tables = self.get_registered_station_ids() or ["MESA-UNICA"]
        bulletin = PreliminaryBulletin(
            channel=self._transmission_channel,
            bulletin_number=bulletin_number,
            election_title=self._config.election_title,
            processed_tables=tables,
            candidate_votes=candidate_votes,
        )
        return bulletin.dispatch(destination=destination)

    def close_and_generate_tally(
        self,
        officer_signatures: List[str],
        dispatch_destination: Optional[str] = None,
    ) -> ElectoralTallyReport:
        """Cierra la urna, cuenta por identificador y construye el acta."""
        self.close_polls()

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
                label = (
                    f"{official.candidate_name} ({official.party_name})"
                    if official
                    else ballot.selection
                )
                candidate_votes[label] = candidate_votes.get(label, 0) + 1
            else:
                other_votes[ballot.selection] = other_votes.get(ballot.selection, 0) + 1
        candidate_votes.update(other_votes)

        tables = self.get_registered_station_ids() or ["MESA-01"]
        jurisdiction = "Jurisdicción General"
        if self._jurisdiction_tree is not None:
            jurisdiction = self._jurisdiction_tree.name

        winner_verdict = "Escrutinio completado."
        if self._family_factory is not None:
            tally_rule: TallyRule = self._family_factory.create_tally_rule()
            winner_verdict = tally_rule.evaluate_winner(candidate_votes)

        builder = self._tally_builder.reset()
        builder.set_header(election_title=self._config.election_title, jurisdiction=jurisdiction)
        builder.add_table_batch(tables)
        builder.set_votes(candidate_votes=candidate_votes, blank_votes=blank_votes, null_votes=null_votes)
        for sig in officer_signatures:
            builder.add_officer_signature(sig)
        builder.set_winner_verdict(winner_verdict)
        report = builder.build()

        if dispatch_destination and self._transmission_channel is not None:
            closing_bulletin = OfficialClosingBulletin(
                channel=self._transmission_channel,
                election_title=report.election_title,
                jurisdiction=report.jurisdiction,
                total_votes=report.total_votes,
                integrity_hash=report.integrity_hash,
            )
            closing_bulletin.dispatch(destination=dispatch_destination)

        self._tally_generated = True
        return report

    # =========================================================================
    # F. CONSULTAS Y MÉTRICAS
    # =========================================================================

    def get_registered_station_ids(self) -> List[str]:
        if self._jurisdiction_tree is not None:
            return self._jurisdiction_tree.get_station_ids()
        return []

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Resumen de lectura calculado desde las papeletas persistidas."""
        total_census = self._census.get_total_eligible() if self._census else 0
        ballots = list_ballots(self.election_type)
        total_votes = len(ballots)
        turnout_pct = (total_votes / total_census * 100) if total_census > 0 else 0.0

        candidate_votes: Dict[str, int] = {}
        votes_by_candidate_id: Dict[str, int] = {}
        votes_by_candidate_name: Dict[str, int] = {}
        blank_votes = 0
        null_votes = 0

        for ballot in ballots:
            if ballot.ballot_type == "blank":
                blank_votes += 1
                continue
            if ballot.candidate_id:
                official = next(
                    (
                        c
                        for c in CandidateFlyweightFactory.get_all_candidates()
                        if c.candidate_id == ballot.candidate_id
                    ),
                    None,
                )
                name = official.candidate_name if official else ballot.selection
                votes_by_candidate_id[ballot.candidate_id] = (
                    votes_by_candidate_id.get(ballot.candidate_id, 0) + 1
                )
                votes_by_candidate_name[name] = votes_by_candidate_name.get(name, 0) + 1
                candidate_votes[ballot.selection] = candidate_votes.get(ballot.selection, 0) + 1
            else:
                candidate_votes[ballot.selection] = candidate_votes.get(ballot.selection, 0) + 1

        return {
            "institution_name": self._config.institution_name,
            "election_title": self._config.election_title,
            "header": self.ballot_header,
            "is_open": self._config.is_open,
            "total_registered_citizens": total_census,
            "total_votes_cast": total_votes,
            "turnout_percentage": round(turnout_pct, 2),
            "total_stations_count": self._jurisdiction_tree.count_stations() if self._jurisdiction_tree else 0,
            "candidate_votes": candidate_votes,
            "votes_by_candidate_id": votes_by_candidate_id,
            "votes_by_candidate_name": votes_by_candidate_name,
            "blank_votes": blank_votes,
            "null_votes": null_votes,
        }
