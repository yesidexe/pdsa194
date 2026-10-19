"""Módulo para optimización de memoria de opciones electorales mediante el patrón Flyweight."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CandidateMetadataFlyweight:
    """Estado intrínseco e inmutable compartido en el catálogo de candidatos."""
    candidate_id: str
    candidate_name: str
    party_name: str
    campaign_slogan: str
    party_color_hex: str
    photo_url: str

    def format_card_display(self) -> str:
        """Formatea la representación visual para el tarjetón electoral."""
        return f"[{self.party_name.upper()}] {self.candidate_name} - '{self.campaign_slogan}'"


class CandidateFlyweightFactory:
    """Fábrica y almacén común (Pool) para garantizar instancias únicas de candidatos en memoria."""

    _flyweights: Dict[str, CandidateMetadataFlyweight] = {}

    @classmethod
    def get_candidate(
        cls,
        candidate_id: str,
        candidate_name: str = "Desconocido",
        party_name: str = "Independiente",
        campaign_slogan: str = "Por un futuro transparente",
        party_color_hex: str = "#2563EB",
        photo_url: str = "/static/candidates/default.png",
    ) -> CandidateMetadataFlyweight:
        """Retorna la instancia compartida existente o crea una nueva si no está en el catálogo."""
        c_id = str(candidate_id).strip()

        if c_id not in cls._flyweights:
            cls._flyweights[c_id] = CandidateMetadataFlyweight(
                candidate_id=c_id,
                candidate_name=candidate_name,
                party_name=party_name,
                campaign_slogan=campaign_slogan,
                party_color_hex=party_color_hex,
                photo_url=photo_url,
            )
        return cls._flyweights[c_id]

    @classmethod
    def get_all_candidates(cls) -> List[CandidateMetadataFlyweight]:
        """Recupera la lista completa de candidatos del tarjetón oficial."""
        return list(cls._flyweights.values())

    @classmethod
    def total_shared_instances(cls) -> int:
        """Retorna el número de instancias flyweight residentes en memoria."""
        return len(cls._flyweights)

    @classmethod
    def reset_pool(cls) -> None:
        """Limpia el catálogo para entornos de prueba."""
        cls._flyweights.clear()
