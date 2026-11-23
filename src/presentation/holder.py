"""Contenedor de estado de la aplicación.

Permite que la API cambie de modalidad sin reconstruir el objeto FastAPI: los
routers leen siempre `holder.proxy` y `holder.current_mode`.
"""
from __future__ import annotations

from src.modules.security.access_proxy import ElectoralAccessProxy


class ElectoralSystemHolder:
    """Contenedor de estado que permite conmutar la instancia del sistema."""

    def __init__(self, proxy: ElectoralAccessProxy, mode: str = "national") -> None:
        self.proxy: ElectoralAccessProxy = proxy
        self.current_mode: str = mode

    def switch_mode(self, new_mode: str) -> ElectoralAccessProxy:
        self.current_mode = new_mode.lower().strip()
        return self.proxy
