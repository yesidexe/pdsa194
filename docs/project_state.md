# ESTADO DEL PROYECTO: PLATAFORMA DE VOTACIÓN ELECTRÓNICA (E-VOTING SYSTEM)

> **Última Actualización:** 18 de Octubre de 2026  
> **Estado General:** 🟡 Prototipo funcional local en construcción / Persistencia de votos y participación / Autenticación básica de elector y administrador

---

## 1. Visión General del Proyecto

La **Plataforma de Votación Electrónica** es un sistema de sufragio digital, escrutinio en vivo y gestión de censo electoral de nivel institucional.
El objetivo del proyecto es funcionar como una plataforma real, moderna y robusta para sufragio ciudadano y universitario, garantizando:
- **Secreto del voto** mediante separación entre la tabla de participación y la tabla de papeletas (sin clave que las una).
- **Integridad** mediante sellos HMAC-SHA256, sello SHA-256 del acta y marcas de auditoría. El no repudio con firmas asimétricas queda como trabajo futuro.
- **Persistencia de electores y mesas** en una base de datos relacional SQLite (`e_voting.db`) gestionada con SQLAlchemy.
- **Conmutación en caliente de tipo de elección** (Elecciones Nacionales de Representantes a la Cámara vs. Elecciones Universitarias de Voceros).
- **Interfaz web limpia, responsiva y moderna** construida con Tailwind CSS y Jinja2, con animaciones sutiles y sin jerga interna para el usuario final.
- **Arquitectura modular de software** basada en principios SOLID y 12 patrones de diseño GoF trabajando en conjunto.

---

## 2. Pila Tecnológica (Tech Stack)

| Capa | Tecnología | Propósito |
| :--- | :--- | :--- |
| **Lenguaje** | Python 3.12+ / 3.14+ | Núcleo del sistema y lógica de negocio |
| **Framework Web & API** | FastAPI + Starlette + Uvicorn | Endpoints REST, enrutamiento y servicio de vistas web |
| **Motor de Base de Datos** | SQLite (`e_voting.db`) | Persistencia local ligera y portable sin requerir servicios externos |
| **ORM de Persistencia** | SQLAlchemy 2.0 | Mapeo objeto-relacional y sesiones thread-safe para FastAPI |
| **Validación de Esquemas** | Pydantic 2.0 | Validación estricta de payloads JSON en requests/responses |
| **Motor de Plantillas** | Jinja2 | Renderizado del frontend (`index.html`, `dashboard.html`, `admin.html`) |
| **Frontend Styling** | Tailwind CSS (CDN) + FontAwesome 6 | Interfaz responsiva, diseño accesible y profesional |
| **Testing & Cobertura** | Pytest + Pytest-Cov | Suite de pruebas unitarias y de integración (18 pruebas, base de test separada, 86% de cobertura de líneas) |

---

## 3. Arquitectura del Código y Estructura de Carpetas

```text
patrones_proyecto/
│
├── e_voting.db                      # SQLite: censo, participación y papeletas
├── requirements.txt                 # Dependencias (FastAPI, SQLAlchemy, Pytest, etc.)
├── pytest.ini                       # Configuración de pruebas
├── .env.example                     # Variables de entorno de ejemplo
│
├── src/
│   ├── main.py                      # Arranque, rutas HTML y Uvicorn
│   ├── core/
│   │   ├── config.py                # Configuración global (Singleton)
│   │   ├── database.py              # Modelos citizen, participation y ballot
│   │   ├── security.py              # Hash de PIN y contraseña
│   │   └── settings.py              # Variables de entorno y carga de .env
│   │
│   ├── modules/
│   │   ├── census/census_adapter.py # Adapter SQLite/JSON/CSV
│   │   ├── election/                # Abstract Factory, Prototype, Composite
│   │   ├── voting/
│   │   │   ├── ballot_factory.py    # Factory Method
│   │   │   ├── ballot_decorator.py  # Decorator
│   │   │   ├── candidate_flyweight.py
│   │   │   └── vote_store.py        # Participación + papeleta atómica
│   │   ├── tally/report_builder.py  # Builder del acta
│   │   ├── transmission/            # Bridge de boletines
│   │   ├── security/access_proxy.py # Proxy de acceso y auditoría
│   │   └── facade/voting_facade.py  # Fachada de alto nivel
│   │
│   └── presentation/
│       ├── api.py                   # Endpoints REST
│       ├── auth.py                  # Login y cookie del administrador
│       └── templates/               # index, dashboard, admin, admin_login
│
├── tests/
│   ├── conftest.py                  # Base de test separada y fixtures
│   └── test_system.py               # 18 pruebas automatizadas
│
├── scripts/
│   ├── reset_db.py                  # Reinicia y siembra la base de demo
│   ├── cast_demo_votes.py           # Genera votos de demostración
│   └── hash_password.py             # Hash opcional para ADMIN_PASSWORD_HASH
│
├── avances/                         # Documentos por patrón + manual de uso
│   ├── README.md
│   ├── manual_de_uso.md
│   └── capturas/
│
└── docs/
    ├── project_state.md             # Estado y memoria viva
    ├── agents.md                    # Directrices para agentes
    ├── plan_mejora_patrones_y_arquitectura_local.md
    └── avances/                     # Guía personal: mapa, patrones y guion
```

---

## 4. Resumen de Patrones GoF Implementados en el Código

| # | Patrón | Tipo | Archivo Principal | Rol en el Dominio Electoral |
| :-: | :--- | :--- | :--- | :--- |
| **1** | **Singleton** | Creacional | `src/core/config.py` | Configuración electoral global única y thread-safe. |
| **2** | **Factory Method** | Creacional | `src/modules/voting/ballot_factory.py` | Creación especializada de papeletas (Candidato, Referendo, Blanco). |
| **3** | **Abstract Factory** | Creacional | `src/modules/election/election_factory.py` | Familias completas de componentes para Elección Nacional vs Universitaria. |
| **4** | **Builder** | Creacional | `src/modules/tally/report_builder.py` | Ensamblado incremental del Acta Oficial de Cierre y firma criptográfica SHA-256. |
| **5** | **Prototype** | Creacional | `src/modules/election/station_prototype.py` | Clonación profunda de plantillas de mesas de votación. |
| **6** | **Adapter** | Estructural | `src/modules/census/census_adapter.py` | Homogeneización de censos en formatos heterogéneos (JSON, CSV y Base de Datos SQLite). |
| **7** | **Bridge** | Estructural | `src/modules/transmission/bulletin_bridge.py` | Desacoplamiento entre tipos de boletines y canales de transmisión (Consola, Disco, Webhooks). |
| **8** | **Composite** | Estructural | `src/modules/election/jurisdiction_composite.py`| Organización jerárquica en árbol (Distrito -> Puesto -> Mesa). |
| **9** | **Decorator** | Estructural | `src/modules/voting/ballot_decorator.py` | Aplicación dinámica de sellos de seguridad (Timestamp, Firma, Marca de Agua). |
| **10** | **Facade** | Estructural | `src/modules/facade/voting_facade.py` | Interfaz simplificada que oculta la complejidad del subsistema electoral. |
| **11** | **Flyweight** | Estructural | `src/modules/voting/candidate_flyweight.py` | Compartición eficiente en memoria de datos intrínsecos de candidatos. |
| **12** | **Proxy** | Estructural | `src/modules/security/access_proxy.py` | Control de acceso por roles, reset protegido y bitácora de auditoría. |

---

## 5. Base de Datos SQLite (`e_voting.db`)

- **Archivo físico:** `e_voting.db` en la raíz del proyecto.
- **Tabla del censo:** `census_citizens`
  - `id`: Entero autoincremental (clave primaria).
  - `document_id`: Documento (cédula o carnet; único junto con `election_type`).
  - `full_name`: Nombre completo sintético.
  - `assigned_station_id`: Mesa asignada (e.g. `MESA-01`).
  - `is_eligible`: Booleano (1 = habilitado, 0 = inhabilitado).
  - `election_type`: `NATIONAL` o `UNIVERSITY`.
  - `pin_hash`: Huella PBKDF2 del PIN de demostración.
  - `created_at`: Marca de tiempo UTC de inscripción.
- **Tabla de participación:** `voter_participation` (`election_type`, `document_id`, `voted_at`; restricción única por elección).
- **Tabla de papeletas:** `ballot_records` (`ballot_id`, `election_type`, `ballot_type`, `candidate_id`, `selection`, `receipt_code`, `digital_signature`, `timestamp_seal`, `created_at`). No guarda documento.
- **Secreto del voto:** no existe clave foránea entre participación y papeleta.
- **Interacción:** El panel de administración (`/admin`) permite listar, inscribir nuevos ciudadanos y alternar en tiempo real si están habilitados o inhabilitados. El acceso exige login con cookie `HttpOnly`.

---

## 6. Endpoints REST de la API

### Identificación y Votación
- `POST /api/auth/verify`: Verifica documento + PIN, habilitación y voto único.
- `POST /api/votes/cast`: Valida el candidato en el servidor, aplica sellos, persiste el voto y previene doble voto con restricción única.
- `GET /api/candidates`: Retorna el catálogo de candidatos activos para el tarjetón.

### Escrutinio y Monitoreo
- `GET /api/dashboard`: Métricas en vivo (total votos, porcentajes, desglose por opción).
- `POST /api/tally/generate`: Cierra formalmente la urna y genera el acta con hash SHA-256 (requiere rol de administrador).

### Administración y Configuración
- `POST /api/admin/login` y `POST /api/admin/logout`: Sesión local del administrador.
- `POST /api/admin/reset-election`: Borra votos y participaciones de la elección activa; conserva el censo.
- `GET /api/election/mode`: Retorna la modalidad electoral activa y sus metadatos.
- `POST /api/election/switch-mode`: Conmuta entre Elección Nacional y Elección Universitaria.
- `POST /api/election/open` y `POST /api/election/close`: Apertura y bloqueo de la urna.
- `GET /api/security/audit-log`: Bitácora de eventos (requiere sesión de administrador).

### Censo Electoral (SQLite)
- `GET /api/census/voters`: Listado de votantes de la modalidad activa.
- `POST /api/census/voters`: Inscribe o actualiza un elector en la base de datos.
- `PUT /api/census/voters/{document_id}/status`: Habilita o inhabilita a un elector en el censo.

---

## 7. Cómo Ejecutar el Proyecto en Cualquier Computador

### Paso 1: Clonar el repositorio y entrar a la carpeta
```bash
git clone <url-del-repositorio>
cd patrones_proyecto
```

### Paso 2: Crear y activar entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### Paso 3: Instalar dependencias y configurar el entorno
```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env: ADMIN_PASSWORD, SECRET_KEY y AUTO_OPEN_POLLS
```
> `.env.example` se versiona; `.env` es local y está ignorado por git.

### Paso 4: Ejecutar pruebas automatizadas
```bash
pytest tests/ --cov=src --cov-report=term-missing
```

### Paso 5: Iniciar el servidor web
```bash
python3 -m src.main
```
El servidor se iniciará en `http://127.0.0.1:8000` (un solo worker, estado local):
- **Cabina de Votación:** `http://127.0.0.1:8000/`
- **Resultados en Vivo:** `http://127.0.0.1:8000/dashboard`
- **Acceso administrativo:** `http://127.0.0.1:8000/admin/login`
- **Documentación Swagger:** `http://127.0.0.1:8000/docs`

Credenciales de demostración: administrador `admin` (contraseña en `.env`) y PIN de electores `1234`.

---

## 7.1 Cambios de esta iteración

- Autenticación de elector con documento + PIN y login de administrador con cookie `HttpOnly`.
- Persistencia de participación y papeletas en SQLite, con restricción única y voto atómico.
- Validación server-side del candidato y aplicación obligatoria de las tres capas de seguridad.
- Reset de jornada y bloqueo de reapertura después de generar el acta.
- Dashboard con conteo por `candidate_id` y participación sobre electores habilitados.
- Corrección de XSS y protección de censo, auditoría y acciones administrativas.
- Interfaz responsiva con CSS propio, animaciones sutiles, toasts y mejor jerarquía visual.
- Documentación depurada, manual de uso con capturas y guía personal de exposición.

## 8. Lo que Queda por Hacer (Roadmap Futuro)

1. **Persistir la bitácora de auditoría:** hoy vive en memoria y se pierde al reiniciar. Debe pasar a SQLite con encadenamiento de hashes.
2. **Verificación criptográfica real:** sustituir HMAC por firmas Ed25519, firmar el acta y publicar un verificador de recibos.
3. **Autenticación de elector más fuerte:** OTP, SSO institucional o verificación presencial; el PIN `1234` es solo de simulación.
4. **Escrutinio por mesa:** guardar `station_id` en el voto y explotar el Composite para resultados por mesa.
5. **Exportación de actas en PDF/QR:** descarga del acta y verificación pública.
6. **Migración a PostgreSQL, backups y HTTPS** antes de cualquier despliegue fuera de local.
7. **Roadmap funcional completo:** resultados por mesa, filtros, tablas de instituciones/elecciones/candidatos y gráficas de participación. Ver [`docs/registro_mejoras.md`](registro_mejoras.md), sección 5.
