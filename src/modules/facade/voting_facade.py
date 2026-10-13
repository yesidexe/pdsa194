"""Módulo que implementa el patrón Facade para orquestar y simplificar todo el subsistema electoral."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

# Núcleo y Configuración (Singleton)
from src.core.config import ElectoralConfigManager

# Módulo de Censo (Adapter)
from src.modules.census.census_adapter import ICensusRegistry, VoterCensusRecord

# Módulo de Elección (Abstract Factory, Prototype, Composite)
from src.modules.election.election_factory import (
    ElectoralFamilyFactory,
    CredentialValidator,
    BallotHeader,
    TallyRule,
)
from src.modules.election.station_prototype import VotingStation, StationPrototypeRegistry
from src.modules.election.jurisdiction_composite import ElectoralUnit, ElectoralJurisdictionComposite, VotingStationLeaf

# Módulo de Votación (Factory Method y Decorator)
from src.modules.voting.ballot_factory import (
    Ballot,
    BallotCreator,
    CandidateBallotCreator,
    ReferendumBallotCreator,
    BlankBallotCreator,
)
from src.modules.voting.ballot_decorator import (
    BallotSecurityDecorator,
    TimestampSecurityDecorator,
    DigitalSignatureDecorator,
    AuditWatermarkDecorator,
)

# Módulo de Escrutinio (Builder)
from src.modules.tally.report_builder import OfficialTallyReportBuilder, ElectoralTallyReport

# Módulo de Transmisión (Bridge)
from src.modules.transmission.bulletin_bridge import (
    ITransmissionChannel,
    ElectoralBulletin,
    PreliminaryBulletin,
    OfficialClosingBulletin,
    AuditAlertBulletin,
)


class VotingSystemFacade:
    """Fachada unificada de alto nivel que simplifica la interacción con el sistema electoral completo."""

    def __init__(
        self,
        institution_name: str = "Consejo Nacional Electoral",
        election_title: str = "Elecciones Oficiales 2026",
    ) -> None:
        # 1. Configuración Centralizada (Singleton)
        self._config: ElectoralConfigManager = ElectoralConfigManager(
            institution_name=institution_name,
            election_title=election_title,
        )

        # 2. Catálogo de Prototipos de Estaciones (Prototype)
        self._station_registry: StationPrototypeRegistry = StationPrototypeRegistry()

        # 3. Creadores de Papeletas (Factory Method)
        self._candidate_creator: CandidateBallotCreator = CandidateBallotCreator()
        self._referendum_creator: ReferendumBallotCreator = ReferendumBallotCreator()
        self._blank_creator: BlankBallotCreator = BlankBallotCreator()

        # 4. Constructor de Actas (Builder)
        self._tally_builder: OfficialTallyReportBuilder = OfficialTallyReportBuilder()

        # 5. Componentes configurables del ecosistema
        self._census: Optional[ICensusRegistry] = None
        self._family_factory: Optional[ElectoralFamilyFactory] = None
        self._transmission_channel: Optional[ITransmissionChannel] = None
        self._jurisdiction_tree: Optional[ElectoralUnit] = None

        # 6. Almacén anónimo de votos y control de sufragio único
        self._ballot_box: List[Ballot] = []
        self._voted_citizens: Set[str] = set()

    # =========================================================================
    # A. CONFIGURACIÓN DEL ECOSISTEMA (Setup & Configuration)
    # =========================================================================

    def setup_environment(
        self,
        census_registry: ICensusRegistry,
        family_factory: Optional[ElectoralFamilyFactory] = None,
        transmission_channel: Optional[ITransmissionChannel] = None,
        jurisdiction_tree: Optional[ElectoralUnit] = None,
    ) -> None:
        """Asocia adaptadores, fábricas de familia y canales de salida al sistema."""
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
    # B. CONTROL DE LA JORNADA ELECTORAL (Polls Lifecycle)
    # =========================================================================

    @property
    def is_voting_open(self) -> bool:
        return self._config.is_open

    def open_polls(self) -> None:
        """Abre formalmente la urna electoral permitiendo sufragar."""
        self._config.open_voting()

    def close_polls(self) -> None:
        """Cierra la urna electoral bloqueando nuevos sufragios."""
        self._config.close_voting()

    # =========================================================================
    # C. AUTENTICACIÓN Y VERIFICACIÓN DE VOTANTES (Inbound & Security)
    # =========================================================================

    def verify_voter(self, document_id: str) -> Dict[str, Any]:
        """Valida si un votante está habilitado, verificando censo, urna y no duplicidad."""
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
                    "reason": f"Formato de credencial inválido para {validator.get_document_type()} en esta elección.",
                }

        if doc in self._voted_citizens:
            return {
                "document_id": doc,
                "is_eligible": False,
                "reason": "El ciudadano ya ejerció su derecho al voto en esta jornada.",
            }

        if self._census is not None:
            if not self._census.is_eligible(doc):
                return {
                    "document_id": doc,
                    "is_eligible": False,
                    "reason": f"El documento no figura habilitado en el censo oficial para: {self._config.election_title}.",
                }

            record = self._census.get_voter_record(doc)
            return {
                "document_id": doc,
                "is_eligible": True,
                "full_name": record.full_name if record else "Ciudadano Autorizado",
                "assigned_station": record.assigned_station_id if record else "MESA-01",
                "source_type": record.source_type if record else "DEFAULT",
            }

        return {
            "document_id": doc,
            "is_eligible": True,
            "full_name": "Ciudadano Registrado",
            "assigned_station": "MESA-01",
        }

    # =========================================================================
    # D. EMISIÓN SEGURA Y ANÓNIMA DEL VOTO (Casting Ballot & Decorators)
    # =========================================================================

    def cast_secure_vote(
        self,
        document_id: str,
        ballot_type: str,
        selection_kwargs: Dict[str, Any],
        security_layers: List[str] = ("timestamp", "signature", "watermark"),
        signing_key: str = "MASTER_FACADE_SECRET_2026",
    ) -> Dict[str, Any]:
        """Emite el voto, lo decora con seguridad y lo ingresa a la urna desvinculado de la identidad."""
        # 1. Validación previa de elegibilidad
        verification = self.verify_voter(document_id)
        if not verification.get("is_eligible", False):
            raise PermissionError(f"No autorizado para sufragar: {verification.get('reason')}")

        # 2. Fabricación del voto base según tipo (Factory Method)
        b_type = ballot_type.strip().lower()
        if b_type == "candidate":
            base_ballot = self._candidate_creator.issue_ballot(**selection_kwargs)
        elif b_type == "referendum":
            base_ballot = self._referendum_creator.issue_ballot(**selection_kwargs)
        elif b_type == "blank":
            base_ballot = self._blank_creator.issue_ballot(**selection_kwargs)
        else:
            raise ValueError(f"Modalidad de papeleta desconocida: '{ballot_type}'")

        # 3. Aplicación dinámica de capas de seguridad (Decorator)
        decorated_ballot: Ballot = base_ballot
        if "timestamp" in security_layers:
            decorated_ballot = TimestampSecurityDecorator(decorated_ballot)

        if "signature" in security_layers:
            decorated_ballot = DigitalSignatureDecorator(
                decorated_ballot,
                signing_key=signing_key,
                officer_token=selection_kwargs.get("officer_token", "TERM-FACADE-01"),
            )

        if "watermark" in security_layers:
            decorated_ballot = AuditWatermarkDecorator(decorated_ballot)

        # 4. Custodia en urna anónima y registro de elector (Secreto de Voto)
        self._ballot_box.append(decorated_ballot)
        self._voted_citizens.add(str(document_id).strip())

        # 5. Generación del comprobante de votación oficial para el elector
        security_meta: Dict[str, Any] = {}
        if isinstance(decorated_ballot, BallotSecurityDecorator):
            security_meta = decorated_ballot.get_security_metadata()

        return {
            "status": "VOTO_REGISTRADO_EXITOSAMENTE",
            "receipt_code": security_meta.get("receipt_code", "COMPROBANTE-OK"),
            "ballot_id": decorated_ballot.ballot_id,
            "issued_at": decorated_ballot.issued_at.isoformat(),
            "selection": decorated_ballot.get_selection(),
            "security_layers_applied": [layer.lower() for layer in security_layers],
            "digital_signature": security_meta.get("digital_signature"),
            "timestamp_seal": security_meta.get("timestamp_seal"),
        }

    # =========================================================================
    # E. TRANSMISIÓN Y ESCRUTINIO DE RESULTADOS (Bridge & Builder)
    # =========================================================================

    def emit_preliminary_bulletin(
        self,
        bulletin_number: int,
        destination: str = "CENTRO_DE_DATOS_CENTRAL",
    ) -> Optional[bool]:
        """Genera un boletín parcial y lo transmite a través del canal configurado (Bridge)."""
        if self._transmission_channel is None:
            return None

        # Consolidación rápida de conteos
        candidate_votes: Dict[str, int] = {}
        for ballot in self._ballot_box:
            sel = ballot.get_selection()
            candidate_votes[sel] = candidate_votes.get(sel, 0) + 1

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
        """Cierra urnas, totaliza votos, construye acta inmutable (Builder) y la despacha."""
        self.close_polls()

        # Desglose de votos
        candidate_votes: Dict[str, int] = {}
        blank_votes = 0
        null_votes = 0

        for ballot in self._ballot_box:
            sel = ballot.get_selection()
            if "VOTO EN BLANCO" in sel.upper():
                blank_votes += 1
            else:
                candidate_votes[sel] = candidate_votes.get(sel, 0) + 1

        tables = self.get_registered_station_ids() or ["MESA-01"]
        jurisdiction = "Jurisdicción General"
        if self._jurisdiction_tree is not None:
            jurisdiction = self._jurisdiction_tree.name

        # Evaluación de ganador si hay regla de la familia abstracta (Abstract Factory)
        winner_verdict = "Escrutinio completado."
        if self._family_factory is not None:
            tally_rule: TallyRule = self._family_factory.create_tally_rule()
            winner_verdict = tally_rule.evaluate_winner(candidate_votes)

        # Ensamble de Acta mediante Builder
        builder = self._tally_builder.reset()
        builder.set_header(election_title=self._config.election_title, jurisdiction=jurisdiction)
        builder.add_table_batch(tables)
        builder.set_votes(candidate_votes=candidate_votes, blank_votes=blank_votes, null_votes=null_votes)
        for sig in officer_signatures:
            builder.add_officer_signature(sig)
        builder.set_winner_verdict(winner_verdict)

        report = builder.build()

        # Transmisión formal vía Bridge si se especificó destino
        if dispatch_destination and self._transmission_channel is not None:
            closing_bulletin = OfficialClosingBulletin(
                channel=self._transmission_channel,
                election_title=report.election_title,
                jurisdiction=report.jurisdiction,
                total_votes=report.total_votes,
                integrity_hash=report.integrity_hash,
            )
            closing_bulletin.dispatch(destination=dispatch_destination)

        return report

    # =========================================================================
    # F. CONSULTA DE ESTADÍSTICAS Y JERARQUÍA (Dashboard & Queries)
    # =========================================================================

    def get_registered_station_ids(self) -> List[str]:
        if self._jurisdiction_tree is not None:
            return self._jurisdiction_tree.get_station_ids()
        return []

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Genera un resumen métrico en tiempo real para paneles gráficos y APIs."""
        total_census = self._census.get_total_registered() if self._census else 0
        total_votes = len(self._ballot_box)
        turnout_pct = (total_votes / total_census * 100) if total_census > 0 else 0.0

        header_str = "Encabezado Institucional Estándar"
        if self._family_factory is not None:
            header_str = self._family_factory.create_header().render_header()

        return {
            "institution_name": self._config.institution_name,
            "election_title": self._config.election_title,
            "header": header_str,
            "is_open": self._config.is_open,
            "total_registered_citizens": total_census,
            "total_votes_cast": total_votes,
            "turnout_percentage": round(turnout_pct, 2),
            "total_stations_count": self._jurisdiction_tree.count_stations() if self._jurisdiction_tree else 0,
        }
