"""Módulo para la construcción paso a paso de actas electorales complejas."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import json


@dataclass(frozen=True)
class ElectoralTallyReport:
    """Producto complejo e inmutable que representa el acta final de escrutinio."""
    election_title: str
    jurisdiction: str
    generated_at: datetime
    table_ids: List[str]
    candidate_votes: Dict[str, int]
    blank_votes: int
    null_votes: int
    total_votes: int
    officer_signatures: List[str]
    integrity_hash: str

    def to_formatted_summary(self) -> str:
        lines = [
            f"=== ACTA OFICIAL DE ESCRUTINIO: {self.election_title.upper()} ===",
            f"Jurisdicción: {self.jurisdiction} | Fecha: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Mesas Escrutadas ({len(self.table_ids)}): {', '.join(self.table_ids)}",
            "--- DESGLOSE DE RESULTADOS ---",
        ]
        for candidate, votes in self.candidate_votes.items():
            pct = (votes / self.total_votes * 100) if self.total_votes > 0 else 0.0
            lines.append(f"• {candidate}: {votes} votos ({pct:.2f}%)")
        lines.extend([
            f"• Votos en Blanco: {self.blank_votes}",
            f"• Votos Nulos: {self.null_votes}",
            f"• Total Sufragios Emitidos: {self.total_votes}",
            f"Firmas de Jurados Registradas: {len(self.officer_signatures)}",
            f"Sello Digital SHA-256: {self.integrity_hash}",
        ])
        return "\n".join(lines)


class TallyReportBuilder(ABC):
    """Interfaz abstracta que define las etapas de construcción del acta electoral."""

    @abstractmethod
    def reset(self) -> TallyReportBuilder:
        pass

    @abstractmethod
    def set_header(self, election_title: str, jurisdiction: str) -> TallyReportBuilder:
        pass

    @abstractmethod
    def add_table_batch(self, table_ids: List[str]) -> TallyReportBuilder:
        pass

    @abstractmethod
    def set_votes(self, candidate_votes: Dict[str, int], blank_votes: int, null_votes: int) -> TallyReportBuilder:
        pass

    @abstractmethod
    def add_officer_signature(self, signature_code: str) -> TallyReportBuilder:
        pass

    @abstractmethod
    def build(self) -> ElectoralTallyReport:
        pass


class OfficialTallyReportBuilder(TallyReportBuilder):
    """Constructor concreto que implementa el ensamble progresivo y sellado digital."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> OfficialTallyReportBuilder:
        self._election_title: str = "Jornada Electoral"
        self._jurisdiction: str = "Nacional"
        self._table_ids: List[str] = []
        self._candidate_votes: Dict[str, int] = {}
        self._blank_votes: int = 0
        self._null_votes: int = 0
        self._officer_signatures: List[str] = []
        return self

    def set_header(self, election_title: str, jurisdiction: str) -> OfficialTallyReportBuilder:
        self._election_title = election_title
        self._jurisdiction = jurisdiction
        return self

    def add_table_batch(self, table_ids: List[str]) -> OfficialTallyReportBuilder:
        self._table_ids.extend(table_ids)
        return self

    def set_votes(
        self,
        candidate_votes: Dict[str, int],
        blank_votes: int,
        null_votes: int,
    ) -> OfficialTallyReportBuilder:
        self._candidate_votes = dict(candidate_votes)
        self._blank_votes = max(0, blank_votes)
        self._null_votes = max(0, null_votes)
        return self

    def add_officer_signature(self, signature_code: str) -> OfficialTallyReportBuilder:
        if signature_code not in self._officer_signatures:
            self._officer_signatures.append(signature_code)
        return self

    def build(self) -> ElectoralTallyReport:
        total = sum(self._candidate_votes.values()) + self._blank_votes + self._null_votes
        now = datetime.utcnow()

        payload = {
            "title": self._election_title,
            "jurisdiction": self._jurisdiction,
            "timestamp": now.isoformat(),
            "tables": sorted(self._table_ids),
            "candidate_votes": self._candidate_votes,
            "blank": self._blank_votes,
            "null": self._null_votes,
            "total": total,
            "signatures": self._officer_signatures,
        }
        hash_digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

        return ElectoralTallyReport(
            election_title=self._election_title,
            jurisdiction=self._jurisdiction,
            generated_at=now,
            table_ids=list(self._table_ids),
            candidate_votes=dict(self._candidate_votes),
            blank_votes=self._blank_votes,
            null_votes=self._null_votes,
            total_votes=total,
            officer_signatures=list(self._officer_signatures),
            integrity_hash=hash_digest,
        )


class TallyReportDirector:
    """Director opcional que define secuencias estándar de ensamble de actas."""

    def __init__(self, builder: TallyReportBuilder) -> None:
        self._builder = builder

    def construct_preliminary_bulletin(
        self,
        title: str,
        jurisdiction: str,
        tables: List[str],
        votes: Dict[str, int],
    ) -> ElectoralTallyReport:
        return (
            self._builder.reset()
            .set_header(f"Boletín Preliminar - {title}", jurisdiction)
            .add_table_batch(tables)
            .set_votes(candidate_votes=votes, blank_votes=0, null_votes=0)
            .build()
        )
