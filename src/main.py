"""Punto de arranque oficial de la plataforma electoral modular (E-Voting System)."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from src.core import settings
from src.core.config import ElectoralConfigManager
from src.core.database import init_db
from src.modules.audit.service import AuditService
from src.modules.census.census_adapter import SqliteCensusAdapter
from src.modules.election.election_factory import (
    NationalElectionFactory,
    UniversityElectionFactory,
)
from src.modules.facade.voting_facade import VotingSystemFacade
from src.modules.security.access_proxy import ElectoralAccessProxy, UserSession, UserRole
from src.presentation.api import create_api_app, ElectoralSystemHolder
from src.presentation.auth import is_admin_request


def bootstrap_electoral_system(mode: str = "national") -> ElectoralAccessProxy:
    """Inicializa y orquesta todos los componentes del sistema según el modo seleccionado."""
    mode_clean = mode.lower().strip()
    init_db()
    ElectoralConfigManager.reset_for_testing()

    if mode_clean == "university":
        facade = VotingSystemFacade(
            institution_name="Universidad de Investigación y Desarrollo (UDI)",
            election_title="Elecciones de Voceros al Consejo Superior Universitario 2026",
            election_type="UNIVERSITY",
        )

        census = SqliteCensusAdapter(election_type="UNIVERSITY")

        facade.setup_environment(
            census_registry=census,
            family_factory=UniversityElectionFactory(),
            station_ids=["MESA-01", "MESA-02"],
            jurisdiction_name="Campus Central UDI",
        )
        facade.refresh_candidate_catalog()

    else:
        facade = VotingSystemFacade(
            institution_name="Consejo Nacional Electoral",
            election_title="Elección Oficial de Representantes a la Cámara 2026",
            election_type="NATIONAL",
        )

        census = SqliteCensusAdapter(election_type="NATIONAL")

        facade.setup_environment(
            census_registry=census,
            family_factory=NationalElectionFactory(),
            station_ids=["MESA-01", "MESA-02"],
            jurisdiction_name="Circunscripción Central",
        )
        facade.refresh_candidate_catalog()

    proxy = ElectoralAccessProxy(facade, audit_service=AuditService())

    # La demo abre la urna al arrancar; en una jornada real la abre el admin.
    if settings.AUTO_OPEN_POLLS:
        admin_session = UserSession(
            user_id="ADMIN-BOOTSTRAP",
            role=UserRole.ADMINISTRADOR,
            session_token="SESSION-BOOTSTRAP",
        )
        try:
            proxy.open_polls(admin_session)
        except ValueError:
            pass

    return proxy


class AppSystemHolder(ElectoralSystemHolder):
    """Manejador de estado que reconstruye el ecosistema de patrones al conmutar de elección."""

    def switch_mode(self, new_mode: str) -> ElectoralAccessProxy:
        self.current_mode = new_mode.lower().strip()
        self.proxy = bootstrap_electoral_system(self.current_mode)
        return self.proxy


initial_mode = os.getenv("ELECTION_MODE", "national").strip().lower()
if initial_mode not in {"national", "university"}:
    initial_mode = "national"
system_holder = AppSystemHolder(
    proxy=bootstrap_electoral_system(initial_mode),
    mode=initial_mode,
)
app = create_api_app(system_holder)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "presentation" / "templates"))
STATIC_DIR = BASE_DIR / "presentation" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, tags=["Interfaz Web"])
def render_voting_booth(request: Request):
    """Página principal: Cabina de votación digital interactiva para el elector."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/dashboard", response_class=HTMLResponse, tags=["Interfaz Web"])
def render_monitoring_dashboard(request: Request):
    """Panel de escrutinio y resultados públicos en vivo para electores y observadores."""
    return templates.TemplateResponse(request=request, name="dashboard.html")


@app.get("/admin/login", response_class=HTMLResponse, tags=["Interfaz Web"])
def render_admin_login(request: Request):
    """Pantalla de acceso para la única cuenta administradora local."""
    if is_admin_request(request):
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse(request=request, name="admin_login.html")


@app.get("/admin", response_class=HTMLResponse, tags=["Interfaz Web"])
def render_admin_console(request: Request):
    """Panel protegido de administración y control de la jornada."""
    if not is_admin_request(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return templates.TemplateResponse(request=request, name="admin.html")


if __name__ == "__main__":
    print("\n" + "=" * 75)
    print(" INICIANDO PLATAFORMA DE VOTACIÓN ELECTRÓNICA (E-VOTING SYSTEM)")
    print("=" * 75)
    print(f" • Modo Activo:        {system_holder.current_mode.upper()}")
    print(f" • Cabina de Votación: http://{settings.HOST}:{settings.PORT}/")
    print(f" • Resultados en Vivo: http://{settings.HOST}:{settings.PORT}/dashboard")
    print(f" • Panel de Admin:     http://{settings.HOST}:{settings.PORT}/admin")
    print(f" • Swagger UI (API):   http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 75)
    print(" ACCESO DE DEMOSTRACIÓN:")
    print(f"  - Administrador: {settings.ADMIN_USER} (contraseña definida en .env)")
    print("  - PIN de electores de prueba: 1234")
    print("  - Modo Nacional:     10203040, 50607080, 70809010")
    print("  - Modo Universitario: EST-2024, EST-9012, EST-3341")
    print("=" * 75 + "\n")
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEV_RELOAD,
    )
