"""Paquete del censo electoral y sus adaptadores."""
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
