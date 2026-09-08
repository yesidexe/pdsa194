"""Módulo de configuración electoral centralizado."""
from __future__ import annotations
import threading
from typing import Optional


class ElectoralConfigManager:
    """Gestiona la configuración global de la jornada electoral garantizando una única instancia."""

    _instance: Optional[ElectoralConfigManager] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls, *args, **kwargs) -> ElectoralConfigManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        institution_name: str = "Consejo Nacional Electoral",
        election_title: str = "Elecciones Generales",
        max_votes_per_citizen: int = 1,
    ) -> None:
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self.institution_name = institution_name
                self.election_title = election_title
                self.max_votes_per_citizen = max_votes_per_citizen
                self._is_open: bool = False
                self._initialized = True

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open_voting(self) -> None:
        self._is_open = True

    def close_voting(self) -> None:
        self._is_open = False

    @classmethod
    def reset_for_testing(cls) -> None:
        """Permite reiniciar la instancia en entornos controlados de prueba."""
        with cls._lock:
            cls._instance = None
            cls._initialized = False
