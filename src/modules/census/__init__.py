"""Paquete para gestión del censo electoral y sus adaptadores de integración."""
from src.modules.census.census_adapter import (
    ICensusRegistry,
    VoterCensusRecord,
    JsonCensusAdapter,
    CsvCensusAdapter,
)

__all__ = [
    "ICensusRegistry",
    "VoterCensusRecord",
    "JsonCensusAdapter",
    "CsvCensusAdapter",
]
