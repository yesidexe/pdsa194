"""Routers HTTP de la plataforma, agrupados por dominio."""
from src.presentation.routes.admin import build_router as build_admin_router
from src.presentation.routes.candidates import build_router as build_candidates_router
from src.presentation.routes.census import build_router as build_census_router
from src.presentation.routes.system import build_router as build_system_router
from src.presentation.routes.voting import build_router as build_voting_router

__all__ = [
    "build_admin_router",
    "build_candidates_router",
    "build_census_router",
    "build_system_router",
    "build_voting_router",
]
