# Plataforma de Votación Electrónica
## 1. Contextualización del Tema

### 1.1 ¿Qué es una Plataforma de Votación Electrónica?
Una plataforma de votación electrónica es un sistema de información diseñado para registrar, procesar, tabular y auditar sufragios de manera digital, ya sea en puestos de votación presenciales (mediante dispositivos de registro directo o DRE) o de forma remota a través de redes seguras.

A nivel global, la adopción del voto electrónico busca mejorar la eficiencia en la tabulación de resultados, reducir el uso de papel, eliminar errores humanos en el escrutinio de mesas y permitir la entrega de resultados preliminares en tiempos reducidos. Países como Estonia han consolidado modelos de voto por internet, mientras que otros como Brasil utilizan urnas electrónicas presenciales con respaldo digital.

### 1.2 Problemática de los Procesos Electorales Tradicionales
Los métodos de votación tradicionales basados en papeletas físicas presentan desafíos recurrentes que impactan la eficiencia y la confianza en los resultados:
* **Errores humanos y lentitud en el escrutinio:** El conteo manual de votos es un proceso dispendioso y propenso a equivocaciones al momento de tabular y diligenciar las actas físicas.
* **Riesgos de custodia e integridad:** El transporte y almacenamiento de material electoral físico implica riesgos de extravío, daño o alteración de votos.
* **Altos costos logísticos:** Requieren una gran inversión de recursos en la impresión de tarjetones, distribución de material y despliegue de personal.
* **Dificultad de auditoría y verificación:** El recuento físico de votos ante controversias o inconsistencias es complejo y demorado, lo que suele generar incertidumbre en los participantes.

### 1.3 El Dilema Central del Voto Digital
En la ingeniería de software, diseñar un sistema electoral representa un reto singular debido a que debe satisfacer dos principios fundamentales:
1. **Secreto del Voto (Anonimato):** Nadie (ni los administradores del sistema, ni los auditores, ni otros votantes) debe poder asociar la identidad de un ciudadano con su elección específica.
2. **Integridad y Verificabilidad (Auditabilidad):** Cada voto emitido debe ser registrado exactamente como el votante lo expresó, sin alteraciones, y debe ser posible auditar que el conteo final corresponde con la totalidad de los votos emitidos.

Adicionalmente, se deben mitigar riesgos como la coerción, el fraude informático, la suplantación de identidad, la denegación de servicio (DoS) y la pérdida de confianza de los participantes.

---

## 2. Objetivos del Proyecto

### 2.1 Objetivo General
Desarrollar un prototipo funcional de una **Plataforma de Votación Electrónica** que permita simular un proceso electoral, facilitando la autenticación de votantes, la emisión anónima del voto, el conteo automatizado de resultados y el registro de auditoría de la jornada.

### 2.2 Objetivos Específicos
1. **Permitir la configuración de la jornada electoral:** Facilitar el registro de los candidatos y opciones de votación necesarios para llevar a cabo el proceso electoral.
2. **Implementar el control de acceso y validación de votantes:** Desarrollar un mecanismo para autenticar a los electores y verificar que solo puedan ejercer su derecho al voto una única vez.
3. **Garantizar el secreto y la privacidad del voto:** Diseñar la lógica de emisión de papeletas digitales de forma que la identidad del usuario no quede vinculada a la opción seleccionada.
4. **Construir el motor de conteo automatizado:** Desarrollar el módulo encargado de registrar, tabular y totalizar los votos emitidos para presentar los resultados del escrutinio de manera precisa.
5. **Crear un registro de eventos y auditoría:** Implementar un sistema de registro cronológico (*logs*) para rastrear eventos clave (apertura de votación, emisión de votos, cierre de jornada y emisión de resultados), permitiendo verificar la transparencia del proceso.

---

## 3. Arquitectura y Diseño del Sistema

### 3.1 Vista general

La aplicación es un monolito local con una separación clara entre presentación, dominio y persistencia:

```text
Navegador
   │  HTML + JavaScript + Tailwind
   ▼
FastAPI (src/presentation)
   │  API REST + rutas HTML + cookie de administrador
   ▼
Proxy de seguridad (src/modules/security)
   │  roles, auditoría y operaciones protegidas
   ▼
Fachada (src/modules/facade)
   │  coordina censo, votación, escrutinio y transmisión
   ├── Censo (Adapter: SQLite / JSON / CSV)
   ├── Papeletas (Factory Method + Decorator)
   ├── Familias electorales (Abstract Factory)
   ├── Mesas (Prototype + Composite)
   ├── Actas (Builder)
   └── Boletines (Bridge)
   ▼
SQLite (e_voting.db)
   ├── census_citizens
   ├── voter_participation
   └── ballot_records
```

La decisión de diseño más importante es la **separación entre participación y papeleta**: `voter_participation` sabe quién votó; `ballot_records` sabe qué se votó; no existe una clave que las una. Así el panel administrativo puede reiniciar la jornada sin poder consultar el voto de una persona concreta.

### 3.2 Módulos y responsabilidades

| Módulo | Responsabilidad | Piezas principales |
|---|---|---|
| `src/core` | Configuración, seguridad, base de datos y utilidades | `settings.py`, `security.py`, `database.py` |
| `src/modules/census` | Traducir censos externos al modelo canónico | `ICensusRegistry`, `SqliteCensusAdapter`, `JsonCensusAdapter`, `CsvCensusAdapter` |
| `src/modules/election` | Familias electorales, mesas y jerarquías | `ElectoralFamilyFactory`, `VotingStation`, `ElectoralJurisdictionComposite` |
| `src/modules/voting` | Crear papeletas, sellarlas y persistirlas | `BallotCreator`, `BallotSecurityDecorator`, `vote_store.py` |
| `src/modules/tally` | Construir el acta de escrutinio | `OfficialTallyReportBuilder`, `ElectoralTallyReport` |
| `src/modules/transmission` | Enviar boletines por distintos canales | `ITransmissionChannel`, `PreliminaryBulletin`, `OfficialClosingBulletin` |
| `src/modules/security` | Proteger operaciones y auditar | `ElectoralAccessProxy`, `UserSession`, `UserRole` |
| `src/modules/facade` | Punto de entrada de alto nivel | `VotingSystemFacade` |
| `src/presentation` | API, plantillas y autenticación local | `api.py`, `auth.py`, `templates/*.html` |

### 3.3 Recorrido de un voto

1. El elector abre la cabina, ingresa **documento + PIN** y el sistema valida censo, habilitación y jornada abierta.
2. El cliente envía solo el `candidate_id` (o el tipo de voto en blanco). El servidor busca el candidato en el tarjetón oficial.
3. La fachada crea la papeleta, aplica las tres capas de seguridad (timestamp, sello HMAC y marca de agua) y registra participación y papeleta en una sola transacción.
4. La restricción única `(election_type, document_id)` impide el doble voto incluso con peticiones concurrentes.
5. El elector recibe un comprobante; el dashboard lee únicamente los agregados anónimos de `ballot_records`.

### 3.4 Detalle de patrones

Los diagramas UML y la explicación de cada patrón están en [`avances/`](avances/) y la guía personal de estudio en [`docs/avances/`](docs/avances/). Este README resume la arquitectura; no duplica los diagramas.

---

## 4. Documentación por patrón

La documentación técnica de los 5 patrones creacionales y los 7 estructurales está en `avances/` y se enlaza a continuación. El recorrido de uso con capturas está en [`avances/manual_de_uso.md`](avances/manual_de_uso.md).

### 4.1 Patrón Singleton
* **Módulo:** `src/core/config.py` (`ElectoralConfigManager`).
* **Resumen:** Se centralizó el estado y la configuración global de la jornada electoral garantizando una única instancia en memoria con soporte de concurrencia segura (*thread-safety*) mediante *Double-Checked Locking*. Se implementó control de re-inicialización y un método de aislamiento para pruebas automatizadas.
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_1/patron_singleton.md)

### 4.2 Patrón Factory Method
* **Módulo:** `src/modules/voting/ballot_factory.py` (`BallotCreator` y jerarquía `Ballot`).
* **Resumen:** Se desacopló la lógica de emisión de votos de la instanciación concreta de papeletas electorales (`CandidateBallot`, `ReferendumBallot`, `BlankBallot`). Cumple con el principio Open/Closed (OCP), permitiendo incorporar nuevas modalidades de voto sin modificar el código base.
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_2/patron_factory_method.md)

### 4.3 Patrón Abstract Factory
* **Módulo:** `src/modules/election/election_factory.py` (`ElectoralFamilyFactory`).
* **Resumen:** Se implementó la creación de familias completas y coherentes de componentes según la jurisdicción de la elección (Nacional vs. Universitaria), abarcando validación de identidad, membrete oficial de papeleta y reglas de decisión para el escrutinio, garantizando la inversión de dependencias (DIP).
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_3/patron_abstract_factory.md)

### 4.4 Patrón Builder
* **Módulo:** `src/modules/tally/report_builder.py` (`TallyReportBuilder` y `ElectoralTallyReport`).
* **Resumen:** Se implementó la construcción progresiva y desacoplada del Acta Oficial de Escrutinio y Cierre de Urnas, evitando el antipatrón de constructor telescópico. Consolida los cómputos y añade un sello de integridad SHA-256 al acta.
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_4/patron_builder.md)

### 4.5 Patrón Prototype
* **Módulo:** `src/modules/election/station_prototype.py` (`VotingStation` y `StationPrototypeRegistry`).
* **Resumen:** Se formalizó la clonación y replicación rápida de mesas y estaciones de votación a partir de plantillas operativas preconfiguradas. Se implementó copia profunda (*deep copy*) para asegurar el aislamiento de colecciones mutables (jurados y tarjetones autorizados) y personalización segura de terminales.
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_5/patron_prototype.md)

### 4.6 Patrones Adapter y Bridge
* **Módulos:** `src/modules/census/census_adapter.py` (`ICensusRegistry`, `JsonCensusAdapter`, `CsvCensusAdapter`) y `src/modules/transmission/bulletin_bridge.py` (`ElectoralBulletin`, `ITransmissionChannel`).
* **Resumen:** Se implementó el patrón **Adapter** para homogeneizar censos electorales de fuentes heterogéneas (archivos planos CSV de Registraduría vs exportaciones JSON institucionales) hacia el modelo canónico del dominio. En paralelo, se implementó el patrón **Bridge** para desacoplar los tipos de boletines y alertas electorales de sus canales físicos de transporte (consola oficial, archivo persistente y sink de auditoría en memoria), evitando la explosión combinatoria multidimensional.
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_6/patron_adapter_bridge.md)

### 4.7 Patrones Composite, Decorator y Facade
* **Módulos:** `src/modules/election/jurisdiction_composite.py` (`ElectoralUnit`, `VotingStationLeaf`, `ElectoralJurisdictionComposite`), `src/modules/voting/ballot_decorator.py` (`BallotSecurityDecorator`, `TimestampSecurityDecorator`, `DigitalSignatureDecorator`, `AuditWatermarkDecorator`), y `src/modules/facade/voting_facade.py` (`VotingSystemFacade`).
* **Resumen:** Se implementó el patrón **Composite** para estructurar jerárquicamente el censo y mesas de votación (País -> Departamento/Puesto -> Mesa) tratando unidades individuales y agrupaciones de forma uniforme. Se implementó el patrón **Decorator** para envolver dinámicamente las papeletas con capas de seguridad acumulativas (sello de tiempo ISO-8601, sello de integridad HMAC-SHA256 y marca de agua de auditoría) sin alterar la clase base `Ballot`. Finalmente, se integró el patrón **Facade** como punto de entrada unificado que coordina todos los subsistemas creacionales y estructurales de cara a la interfaz web y la API REST.
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_7/patron_composite_decorator_facade.md)

### 4.8 Patrones Proxy y Flyweight
* **Módulos:** `src/modules/security/access_proxy.py` (`ElectoralAccessProxy`, `UserSession`, `UserRole`) y `src/modules/voting/candidate_flyweight.py` (`CandidateMetadataFlyweight`, `CandidateFlyweightFactory`).
* **Resumen:** Se implementó el patrón **Proxy** como sustituto protector que intercepta operaciones críticas del sistema electoral (apertura/cierre de urnas, emisión de votos y reinicio de jornada) validando la sesión del administrador y roles, además de registrar una bitácora de auditoría. En paralelo, se implementó el patrón **Flyweight** para compartir metadatos de los candidatos en memoria. El catálogo compartido alimenta el tarjetón y la validación server-side de candidatos; la papeleta persiste el identificador de la opción para no duplicar la ficha completa en cada voto. Con esto se completaron los **7 patrones estructurales** del catálogo GoF.
* **Documentación:** [Lectura en línea (Markdown)](avances/avance_8/patron_proxy_flyweight.md)

---

## 5. Instrucciones de Ejecución y Pruebas del Sistema

### 5.1 Requisitos Previos
* **Python 3.11 o superior** instalado en el sistema.
* Entorno virtual de Python configurado.

### 5.2 Configuración del Entorno Virtual e Instalación de Dependencias
```bash
# 1. Crear el entorno virtual en la raíz del proyecto
python3 -m venv venv

# 2. Activar el entorno virtual
source venv/bin/activate

# 3. Instalar las dependencias oficiales del sistema
pip install -r requirements.txt

# 4. Crear la configuración local
cp .env.example .env
# Edita .env: ADMIN_PASSWORD, SECRET_KEY y, si quieres, AUTO_OPEN_POLLS
```

> `.env.example` es la plantilla versionada; `.env` es tu configuración real y está en `.gitignore`.
> Si borras `.env`, la app usa valores por defecto locales; si borras `.env.example`, puedes recuperarlo desde el repositorio.

### 5.3 Ejecución de la Plataforma Web y API
Para iniciar el servidor local (por defecto sin recarga, para no perder el estado de la jornada):
```bash
python3 -m src.main
# O directamente mediante Uvicorn:
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Una vez levantado el servidor, accede desde cualquier navegador a los siguientes módulos:
* **Cabina de Votación Digital (Elector):** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
  - Terminal limpia y sobria para el ciudadano/estudiante (sin anotaciones técnicas internas).
  - Digita tu documento y el PIN de demostración (`1234`) según el modo activo.
  - Selecciona un candidato o **Voto en Blanco**.
  - Emite el sufragio y obtén tu **Comprobante Digital con Sello de Tiempo y Sello HMAC**.
  - Al hacer clic en *Ver Resultados en Vivo*, serás dirigido al panel público sin riesgos de tocar controles de jurados.
* **Panel de Transmisión de Resultados en Vivo (Público):** [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)
  - Visualización transparente en vivo para electores y observadores.
  - Gráfico dinámico Chart.js y tabla de desglose porcentual en tiempo real.
  - **No contiene botones administrativos destructivos.**
* **Panel de Control Electoral (Administración):** [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
  - **Acceso protegido:** redirige a `/admin/login`; usa la cuenta definida en `.env`.
  - **Conmutador de Familia (Abstract Factory):** Alterna en caliente entre la *Elección Nacional (CNE)* y las *Elecciones Universitarias / Voceros (UDI)*.
  - **Control Operativo de Urna (Proxy):** Abrir y cerrar la jornada con credenciales protegidas de Administrador.
  - **Cierre y Escrutinio Definitivo (Builder):** Emite el Acta Oficial con sello de integridad SHA-256 y muestra el veredicto oficial de victoria emitido por la `TallyRule` (Mayoría Absoluta vs. Mayoría Simple).
  - **Bitácora de Auditoría Forense (Proxy):** Inspecciona en vivo cada evento interceptado por el sistema.
* **Documentación Interactiva Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
  - Prueba interactivamente cada endpoint REST (`/api/election/mode`, `/api/election/switch-mode`, `/api/auth/verify`, `/api/votes/cast`, `/api/tally/generate`).

### 5.4 Credenciales de Prueba en el Censo Electoral

El censo de demostración es sintético y contiene **41 electores por modalidad**. Todos usan el **PIN `1234`** para la simulación local.

* **Modo Nacional (CNE - Cédula de Ciudadanía):**
  - **Habilitados:** `10203040`, `50607080`, `70809010`, `80901020`, `20000002`…`20000036`.
  - **Inhabilitado:** `99999999`.
* **Modo Universitario (UDI - Carnet Estudiantil):**
  - **Habilitados:** `EST-2024`, `EST-9012`, `EST-3341`, `EST-5520`, `EST-1001`…`EST-1036`.
  - **Inhabilitado:** `EST-9999`.
* **Administrador local:** usuario `admin` y contraseña definida en `.env` (por defecto `admin1234`).

### 5.5 Ejecución de la Suite de Pruebas Automatizadas (Pytest)
La suite usa una base separada (`test_e_voting.db`) y verifica autenticación con PIN, validación de candidato, voto único, concurrencia, protección de administración y reset de jornada:
```bash
# Ejecutar todas las pruebas con reporte de cobertura en consola
pytest tests/ --cov=src --cov-report=term-missing
```
* **Resultado actual:** **18 pruebas pasando (100%)** con una cobertura de líneas del **86%** sobre `src/`.

---

## 6. Demostración Visual y Próximos Pasos

A partir de este hito, el prototipo local es funcional e interactivo:
* **Autenticación e ingreso:** documento + PIN del elector contra el censo y control de voto único persistido en SQLite.
* **Cabina de Votación Digital:** Selección interactiva de candidatos (Flyweight) y emisión anónima con sellos de seguridad (Decorator).
* **Panel de Escrutinio y Resultados:** Visualización gráfica en tiempo real (Chart.js) y generación del acta sellada con SHA-256 (Builder).
### 6.1 Próximos pasos

El roadmap funcional está en [`docs/registro_mejoras.md`](docs/registro_mejoras.md), sección 5. Los siguientes hitos son:

1. Guardar `station_id` en el voto y agregar resultados por mesa.
2. Mover instituciones, elecciones y candidatos a tablas normalizadas.
3. Persistir la auditoría y las actas.
4. Firmas asimétricas y verificación de recibos.
5. Migración a PostgreSQL, backups y HTTPS.
