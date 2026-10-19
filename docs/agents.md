# DIRECTRICES Y PROTOCOLO OPERATIVO PARA AGENTES IA (AGENTS.MD)

> **Propósito de este archivo:**  
> Este documento contiene las instrucciones fundamentales, directrices de diseño y reglas de comportamiento que cualquier Agente de Inteligencia Artificial (Antigravity, Cursor, Copilot o sesiones en otros equipos) DEBE seguir al trabajar en este repositorio.

---

## 1. Contexto y Filosofía del Proyecto

1. **Proyecto Real y de Usuario Final:**
   - **El proyecto se trata como un producto personal en construcción.** Por ahora es un simulador local; no es un sistema electoral certificado. Los patrones de diseño son un medio para organizar el código, no el objetivo del producto.
   - **REGLA DE ORO:** **CERO JERGA TÉCNICA O INTERNA EN LA INTERFAZ WEB.**
   - **Está terminantemente prohibido** colocar palabras como *"Patrón Adapter"*, *"Patrón Decorator"*, *"Patrón Abstract Factory"*, *"Patrón Proxy"*, *"Arquitectura Hexagonal"* o similares en los archivos de interfaz visual (`src/presentation/templates/*.html`) o en los mensajes que ve el votante o jurado.
   - En la interfaz web, el sistema debe leerse y sentirse como una plataforma institucional y profesional (ej: *"Configuración de Jornada"*, *"Censo Electoral"*, *"Acta Oficial de Escrutinio"*, *"Control de Urna"*, *"Bitácora de Auditoría"*).

2. **¿Dónde va lo técnico y explicativo?**
   - **Únicamente en dos lugares:**
     1. En la carpeta `docs/` (especialmente en `docs/project_state.md` y `docs/avances/`).
     2. En los comentarios y *docstrings* internos del código fuente Python (`src/**/*.py`).

3. **Comentarios en el Código Fuente (Nivel Ultra-Didáctico):**
   - El usuario requiere entender cómo funciona el backend al 100%. Por tanto, todo el código Python debe estar documentado profusamente en español, explicando no solo *qué* hace el código, sino *por qué* se diseñó así, qué problemas resuelve y qué significa cada término (ORM, sesiones, hilos, dataclasses, decorators, etc.), como para alguien que sabe programar pero no recuerda bien todos los conceptos.

---

## 2. Protocolo de Inicio al Abrir una Nueva Sesión

Si un Agente inicia una nueva conversación o se cambia de computador, debe seguir esta secuencia:
1. **Leer `docs/project_state.md`:** Para conocer la arquitectura actual, los endpoints disponibles y el roadmap.
2. **Leer `docs/agents.md` (este documento):** Para alinearse con las restricciones y estilo de trabajo.
3. **Comprobar el entorno:**
   - Verificar la existencia de `venv/` y ejecutar `./venv/bin/pytest tests/ --cov=src` para confirmar que las 18 pruebas pasen al 100%.
   - Si no existe el entorno virtual, instruir o crear el `venv` e instalar `requirements.txt`.
4. **Respetar archivos protegidos:**
   - **NUNCA borrar ni modificar** los archivos en `docs/guias/` (son las guías oficiales evaluativas en PDF).

---

## 3. Convenciones Técnicas del Código

### Backend (Python + FastAPI)
- **Ruta de ejecución:** Siempre ejecutar desde la raíz del proyecto `/home/.../patrones_proyecto`.
- **Imports absolutos:** Siempre usar imports del paquete raíz `src.` (ej. `from src.core.database import SessionLocal`).
- **Autenticación de elector:** documento + PIN (`1234` en la demo). No usar la cédula sola como prueba de identidad.
- **Control de Acceso:** las acciones protegidas (abrir/cerrar urna, generar acta, reiniciar jornada, modificar censo, ver auditoría) exigen la cookie de sesión del administrador. El token no se escribe en el JavaScript.
- **Secreto del voto:** `voter_participation` y `ballot_records` no se relacionan; no guardar documento + ballot_id en la misma fila ni en la auditoría.
- **Estructura Hexagonal / Dominio Desacoplado:** El dominio electoral (`src/modules/`) no debe depender directamente de FastAPI ni de HTML. La capa de presentación (`src/presentation/`) es la única que conoce FastAPI y Jinja2.

### Base de Datos (SQLite + SQLAlchemy)
- El archivo de base de datos es `e_voting.db` en la raíz.
- En FastAPI, SQLite corre con múltiples hilos, por lo que `create_engine` usa `connect_args={"check_same_thread": False}` y las sesiones se manejan con `scoped_session` o abriendo y cerrando en bloques `try...finally session.close()`.
- La adaptación de la base de datos al sistema electoral se hace a través de `SqliteCensusAdapter` en `src/modules/census/census_adapter.py`, el cual implementa `ICensusRegistry`. De esta manera, el resto del sistema de votación no sabe si los electores vienen de SQL, CSV o JSON.

### Frontend (HTML + Tailwind CSS + Jinja2)
- Ubicación: `src/presentation/templates/`.
  - `index.html`: Cabina de votación digital para el ciudadano/estudiante.
  - `dashboard.html`: Resultados públicos en vivo y gráficos de barras.
  - `admin.html`: Consola protegida para jurados/administradores (conmutar modalidad, abrir/cerrar urna, generar acta, gestionar censo en SQLite y ver auditoría).
- No requiere compiladores externos (usa Tailwind CDN y FontAwesome 6).

---

## 4. Requisitos de Calidad y Testing

- Cada nueva característica debe contar con sus pruebas correspondientes en `tests/test_system.py`.
- Antes de dar por finalizada cualquier tarea, ejecutar:
  ```bash
  ./venv/bin/pytest tests/ --cov=src --cov-report=term-missing
  ```
- **Umbral de Cobertura Exigido:** $\ge 85\%$.
- **Todas las pruebas deben pasar exitosamente** sin excepciones no controladas.

---

## 5. Resumen de Credenciales y Parámetros del Sistema

- **Modo Nacional:**
  - Cédulas de prueba habilitadas: `10203040`, `50607080`, `70809010`.
  - Cédula inhabilitada: `99999999`.
- **Modo Universitario:**
  - Carnets habilitados: `EST-2024`, `EST-9012`, `EST-3341`.
  - Carnet inhabilitado: `EST-9999`.
- **Administrador local:** usuario `admin` y contraseña definida en `.env` (por defecto `admin1234`).
- **PIN de electores de demostración:** `1234`.
