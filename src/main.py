"""Punto de arranque oficial de la plataforma electoral modular (E-Voting System)."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# Núcleo y Patrones
from src.core.config import ElectoralConfigManager
from src.modules.census.census_adapter import JsonCensusAdapter, SqliteCensusAdapter
from src.modules.election.election_factory import (
    NationalElectionFactory,
    UniversityElectionFactory,
)
from src.modules.election.station_prototype import VotingStation
from src.modules.election.jurisdiction_composite import (
    ElectoralJurisdictionComposite,
    VotingStationLeaf,
)
from src.modules.transmission.bulletin_bridge import ConsoleTransmissionChannel
from src.modules.voting.candidate_flyweight import CandidateFlyweightFactory
from src.modules.facade.voting_facade import VotingSystemFacade
from src.modules.security.access_proxy import ElectoralAccessProxy, UserSession, UserRole
from src.presentation.api import create_api_app, ElectoralSystemHolder


def bootstrap_electoral_system(mode: str = "national") -> ElectoralAccessProxy:
    """Inicializa y orquesta todos los componentes del sistema según el modo seleccionado."""
    mode_clean = mode.lower().strip()
    ElectoralConfigManager.reset_for_testing()
    CandidateFlyweightFactory.reset_pool()

    if mode_clean == "university":
        # =====================================================================
        # PERFIL 2: ELECCIONES UNIVERSITARIAS (UDI - CONSEJO SUPERIOR)
        # =====================================================================
        facade = VotingSystemFacade(
            institution_name="Universidad de Investigación y Desarrollo (UDI)",
            election_title="Elecciones de Voceros al Consejo Superior Universitario 2026",
        )

        # Candidatos compartidos en memoria (Flyweight)
        CandidateFlyweightFactory.get_candidate(
            candidate_id="VOC-01",
            candidate_name="Camilo Suárez",
            party_name="Lista 1 - Estudiantes por el Cambio",
            campaign_slogan="Liderazgo, transparencia e innovación académica",
            party_color_hex="#4F46E5",
        )
        CandidateFlyweightFactory.get_candidate(
            candidate_id="VOC-02",
            candidate_name="Valentina Gómez",
            party_name="Lista 2 - Innovación Universitaria",
            campaign_slogan="Conectividad, investigación y bienestar estudiantil",
            party_color_hex="#0D9488",
        )
        CandidateFlyweightFactory.get_candidate(
            candidate_id="VOC-03",
            candidate_name="Sofía Vargas",
            party_name="Lista 3 - Voces UDI",
            campaign_slogan="Cultura, representación y participación activa",
            party_color_hex="#EA580C",
        )

        # Censo Estudiantil Oficial persistido en SQLite (Adapter)
        census = SqliteCensusAdapter(election_type="UNIVERSITY")

        station_template = VotingStation(
            station_id="TEMPLATE",
            polling_place="Campus Central Universitario",
            zone_code="ZONA-CAMPUS",
            allowed_ballot_types=["CANDIDATE", "BLANK"],
        )
        facade.register_station_template("STD_POLL", station_template)

        m1 = facade.spawn_station("STD_POLL", "MESA-01", "TERM-UNI-01", ["Jurado López", "Jurado Méndez"])
        m2 = facade.spawn_station("STD_POLL", "MESA-02", "TERM-UNI-02", ["Jurado Díaz", "Jurado Silva"])

        sede = ElectoralJurisdictionComposite("SEDE-01", "Campus Central UDI", "SEDE")
        facultad = ElectoralJurisdictionComposite("FAC-ING", "Edificio de Ingenierías", "FACULTAD")
        facultad.add(VotingStationLeaf(m1)).add(VotingStationLeaf(m2))
        sede.add(facultad)

        channel = ConsoleTransmissionChannel()

        facade.setup_environment(
            census_registry=census,
            family_factory=UniversityElectionFactory(),
            transmission_channel=channel,
            jurisdiction_tree=sede,
        )

    else:
        # =====================================================================
        # PERFIL 1: ELECCIÓN NACIONAL (CNE - REGISTRADURÍA NACIONAL)
        # =====================================================================
        facade = VotingSystemFacade(
            institution_name="Consejo Nacional Electoral",
            election_title="Elección Oficial de Representantes a la Cámara 2026",
        )

        CandidateFlyweightFactory.get_candidate(
            candidate_id="CAND-01",
            candidate_name="Gabriel Silva",
            party_name="Alianza Verde Digital",
            campaign_slogan="Tecnología, transparencia y educación para el futuro",
            party_color_hex="#16A34A",
        )
        CandidateFlyweightFactory.get_candidate(
            candidate_id="CAND-02",
            candidate_name="Elena Torres",
            party_name="Pacto Innovación Ciudadana",
            campaign_slogan="Gestión abierta, cero corrupción y participación real",
            party_color_hex="#2563EB",
        )
        CandidateFlyweightFactory.get_candidate(
            candidate_id="CAND-03",
            candidate_name="Carlos Mendoza",
            party_name="Movimiento Renovación",
            campaign_slogan="Experiencia y liderazgo con rigor institucional",
            party_color_hex="#D97706",
        )

        # Censo Nacional Oficial persistido en SQLite (Adapter)
        census = SqliteCensusAdapter(election_type="NATIONAL")

        station_template = VotingStation(
            station_id="TEMPLATE",
            polling_place="Colegio Mayor Nacional",
            zone_code="ZONA-NORTE",
            allowed_ballot_types=["CANDIDATE", "BLANK"],
        )
        facade.register_station_template("STD_POLL", station_template)

        m1 = facade.spawn_station("STD_POLL", "MESA-01", "TERM-BIO-01", ["Jurado Pérez", "Jurado Gómez"])
        m2 = facade.spawn_station("STD_POLL", "MESA-02", "TERM-BIO-02", ["Jurado Rojas", "Jurado Castro"])

        distrito = ElectoralJurisdictionComposite("DIS-01", "Circunscripción Central", "DISTRITO")
        puesto = ElectoralJurisdictionComposite("PUE-01", "Colegio Mayor Nacional", "PUESTO")
        puesto.add(VotingStationLeaf(m1)).add(VotingStationLeaf(m2))
        distrito.add(puesto)

        channel = ConsoleTransmissionChannel()

        facade.setup_environment(
            census_registry=census,
            family_factory=NationalElectionFactory(),
            transmission_channel=channel,
            jurisdiction_tree=distrito,
        )

    # Envoltura con Proxy de Seguridad y Control de Acceso
    proxy = ElectoralAccessProxy(facade)

    # 8. Apertura de la Jornada Inicial mediante credenciales de Administrador
    admin_session = UserSession(user_id="ADMIN-CNE-01", role=UserRole.ADMINISTRADOR, session_token="SESSION-BOOTSTRAP")
    proxy.open_polls(admin_session)

    return proxy


class AppSystemHolder(ElectoralSystemHolder):
    """Manejador de estado que reconstruye el ecosistema de patrones al conmutar de elección."""

    def switch_mode(self, new_mode: str) -> ElectoralAccessProxy:
        self.current_mode = new_mode.lower().strip()
        self.proxy = bootstrap_electoral_system(self.current_mode)
        return self.proxy


# Instanciación del sistema
initial_mode = os.getenv("ELECTION_MODE", "national")
system_holder = AppSystemHolder(
    proxy=bootstrap_electoral_system(initial_mode),
    mode=initial_mode,
)
app = create_api_app(system_holder)

# Configuración de Plantillas Web (Jinja2)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "presentation" / "templates"))


@app.get("/", response_class=HTMLResponse, tags=["Interfaz Web"])
def render_voting_booth(request: Request):
    """Página principal: Cabina de votación digital interactiva para el elector."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/dashboard", response_class=HTMLResponse, tags=["Interfaz Web"])
def render_monitoring_dashboard(request: Request):
    """Panel de escrutinio y resultados públicos en vivo para electores y observadores."""
    return templates.TemplateResponse(request=request, name="dashboard.html")


@app.get("/admin", response_class=HTMLResponse, tags=["Interfaz Web"])
def render_admin_console(request: Request):
    """Panel de administración electoral y control de urnas protegido para jurados y administradores."""
    return templates.TemplateResponse(request=request, name="admin.html")


if __name__ == "__main__":
    print("\n" + "=" * 75)
    print(" INICIANDO PLATAFORMA DE VOTACIÓN ELECTRÓNICA (E-VOTING SYSTEM)")
    print("=" * 75)
    print(f" • Modo Activo:        {system_holder.current_mode.upper()}")
    print(" • Cabina de Votación: http://127.0.0.1:8000/")
    print(" • Resultados en Vivo: http://127.0.0.1:8000/dashboard")
    print(" • Panel de Admin:     http://127.0.0.1:8000/admin")
    print(" • Swagger UI (API):   http://127.0.0.1:8000/docs")
    print("=" * 75)
    print(" CREDENCIALES DE PRUEBA (CENSO):")
    print("  - Modo Nacional:     10203040, 50607080, 70809010 (Inhabilitado: 99999999)")
    print("  - Modo Universitario: EST-2024, EST-9012, EST-3341 (Inhabilitado: EST-9999)")
    print("=" * 75 + "\n")
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
