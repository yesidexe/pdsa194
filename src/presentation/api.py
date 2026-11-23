"""Composición de la API REST local.

Los endpoints viven en `src/presentation/routes/`, agrupados por dominio. Este
módulo solo crea la app, instala el middleware de cabeceras y conecta los routers
con el holder del sistema.
"""
from __future__ import annotations

from typing import Union

from fastapi import FastAPI

from src.modules.security.access_proxy import ElectoralAccessProxy
from src.presentation.holder import ElectoralSystemHolder
from src.presentation.routes import (
    build_admin_router,
    build_candidates_router,
    build_census_router,
    build_system_router,
    build_voting_router,
)


def create_api_app(target: Union[ElectoralAccessProxy, ElectoralSystemHolder]) -> FastAPI:
    """Construye la app FastAPI sobre el Proxy o el holder recibido."""
    if isinstance(target, ElectoralAccessProxy):
        holder = ElectoralSystemHolder(proxy=target, mode="national")
    else:
        holder = target

    api = FastAPI(
        title="Plataforma de Votación Electrónica (E-Voting API)",
        description="API REST local para la simulación de la jornada electoral y el censo.",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @api.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    api.include_router(build_system_router(holder))
    api.include_router(build_candidates_router(holder))
    api.include_router(build_voting_router(holder))
    api.include_router(build_admin_router(holder))
    api.include_router(build_census_router(holder))
    return api
