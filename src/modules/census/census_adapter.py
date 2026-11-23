"""Compatibilidad: reexporta los adaptadores del censo.

La implementación vive en `contracts.py`, `json_census.py`, `csv_census.py` y
`sqlite_census.py`. Este módulo se conserva para no romper imports y enlaces.
"""
from src.modules.census.contracts import ICensusRegistry, VoterCensusRecord
from src.modules.census.csv_census import CsvCensusAdapter
from src.modules.census.json_census import JsonCensusAdapter
from src.modules.census.sqlite_census import SqliteCensusAdapter

__all__ = [
    "ICensusRegistry",
    "VoterCensusRecord",
    "CsvCensusAdapter",
    "JsonCensusAdapter",
    "SqliteCensusAdapter",
]
