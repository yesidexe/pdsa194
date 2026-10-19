# Mapa del proyecto: cómo funciona la plataforma electoral

> Documento personal de estudio y apoyo para la exposición.
> Objetivo: entender el sistema de punta a punta y poder explicarlo oralmente sin memorizar.

---

## 1. La idea en una frase

La plataforma es un **simulador local de una jornada electoral**: un elector se identifica, emite un voto anónimo, el sistema lo sella y lo guarda en una urna; un administrador puede abrir/cerrar la jornada, ver resultados agregados y generar un acta.

No es un sistema electoral certificable. Es un laboratorio para aprender arquitectura, patrones, persistencia y seguridad.

---

## 2. El mapa mental

Piensa en el sistema como un edificio con cuatro zonas:

```text
1. La puerta        → Navegador (HTML + JavaScript)
2. El mostrador     → FastAPI (API y rutas web)
3. La oficina       → Fachada + módulos de dominio
4. El archivo        → SQLite (censo, participación y papeletas)
```

El elector nunca habla directamente con la base de datos. Habla con la API, la API habla con la fachada, y la fachada coordina los módulos. La base de datos es la última capa.

---

## 3. Estructura de carpetas

```text
code/
├── src/
│   ├── main.py                  # arranque, rutas HTML, configuración de Uvicorn
│   ├── core/
│   │   ├── config.py            # Singleton de configuración electoral
│   │   ├── database.py          # modelos SQLAlchemy y semillas
│   │   ├── security.py          # hash de PIN y contraseña
│   │   └── settings.py          # variables de entorno y .env
│   ├── modules/
│   │   ├── census/              # Adapter: censo desde SQLite/JSON/CSV
│   │   ├── election/            # Abstract Factory, Prototype, Composite
│   │   ├── voting/              # Factory Method, Decorator, Flyweight, urna
│   │   ├── tally/               # Builder del acta
│   │   ├── transmission/        # Bridge de boletines
│   │   ├── security/            # Proxy de acceso y auditoría
│   │   └── facade/              # orquestador de alto nivel
│   └── presentation/
│       ├── api.py               # endpoints REST
│       ├── auth.py              # login de administrador y cookie
│       └── templates/           # cabina, dashboard, admin, login
├── tests/                       # pruebas con base separada
├── scripts/                     # reset, votos de demo, hash de contraseña
├── avances/                     # documentos técnicos por patrón + manual
├── docs/                        # esta guía y documentos de trabajo
└── e_voting.db                  # base local de demostración
```

---

## 4. Qué hace cada pieza importante

### 4.1 `src/main.py`

Es el punto de arranque. Hace tres cosas:

1. Construye el sistema según la modalidad (`national` o `university`).
2. Crea la aplicación FastAPI y registra las rutas HTML.
3. Arranca Uvicorn en `127.0.0.1:8000`.

También decide si la urna se abre automáticamente (`AUTO_OPEN_POLLS`) y si el servidor recarga al cambiar el código (`DEV_RELOAD`).

### 4.2 `src/core/database.py`

Define las tres tablas clave:

| Tabla | Qué guarda | Qué NO guarda |
|---|---|---|
| `census_citizens` | Documento, nombre, mesa, habilitación, PIN y modalidad | Votos |
| `voter_participation` | Documento y modalidad de quien ya votó | Qué votó |
| `ballot_records` | ID de papeleta, selección, sello y fecha | Quién votó |

La separación entre las dos últimas es la base del secreto del voto. Si una consulta necesita unir “quién” con “qué”, el diseño está mal.

### 4.3 `src/modules/census`

El **Adapter** traduce censos externos al modelo del sistema. En la demo, el adaptador real es SQLite. Los adaptadores JSON y CSV existen para mostrar que el sistema puede cambiar de fuente sin tocar la cabina.

La autenticación del elector se hace aquí: `authenticate(documento, PIN)` busca al elector, comprueba que esté habilitado y verifica el PIN.

### 4.4 `src/modules/voting`

Contiene:

- `ballot_factory.py`: crea papeletas de candidato, referendo o blanco.
- `ballot_decorator.py`: agrega sello de tiempo, sello HMAC y marca de agua.
- `candidate_flyweight.py`: catálogo compartido de candidatos.
- `vote_store.py`: guarda participación y papeleta en una transacción.

La papeleta se crea con datos que decide el servidor. El cliente solo envía el `candidate_id`; no puede inventar el nombre del candidato ni elegir si el voto lleva sello.

### 4.5 `src/modules/tally`

El **Builder** construye el acta paso a paso. Junta título, jurisdicción, mesas, votos, firmas y veredicto, y genera un sello SHA-256.

### 4.6 `src/modules/transmission`

El **Bridge** separa el tipo de boletín (preliminar, alerta, cierre) del canal de salida (consola, archivo, memoria). En la demo, el canal real es la consola.

### 4.7 `src/modules/security`

El **Proxy** protege las operaciones de administración: abrir, cerrar, generar acta y reiniciar jornada. También registra la bitácora.

La autenticación real del administrador vive en `src/presentation/auth.py`: valida la contraseña, firma una cookie y protege las rutas.

### 4.8 `src/modules/facade`

La **Fachada** es el punto de entrada de alto nivel. La API no necesita saber cómo se crea una papeleta o cómo se cuenta un voto; solo llama a métodos como `verify_voter`, `cast_secure_vote` o `close_and_generate_tally`.

### 4.9 `src/presentation`

- `api.py`: endpoints REST y reglas de entrada.
- `auth.py`: login, logout y verificación de la cookie.
- `templates/`: cabina, dashboard, panel admin y login.

---

## 5. El recorrido completo de un voto

### Paso 1. El elector se identifica

El navegador envía:

```json
{"document_id": "10203040", "pin": "1234"}
```

La API llama a la fachada. La fachada comprueba que la urna esté abierta, que el formato del documento corresponda a la modalidad y que el PIN sea válido contra el censo.

### Paso 2. El elector elige

El navegador envía solo:

```json
{
  "document_id": "10203040",
  "pin": "1234",
  "ballot_type": "candidate",
  "selection": {"candidate_id": "CAND-01"}
}
```

El servidor busca `CAND-01` en el catálogo oficial. Si no existe, rechaza la petición.

### Paso 3. Se crea la papeleta

El Factory Method crea la papeleta base. Luego el Decorator aplica, en orden:

1. Sello de tiempo UTC.
2. Sello HMAC-SHA256.
3. Marca de agua y código de recibo.

### Paso 4. Se guarda en la urna

`vote_store.py` hace dos inserciones en una sola transacción:

- `voter_participation`: documento + modalidad.
- `ballot_records`: papeleta + selección.

Si el elector ya votó, la restricción única de participación impide la segunda inserción. La respuesta es `409 Conflict`.

### Paso 5. El elector recibe el comprobante

La API devuelve el código de recibo, el ID de papeleta, el sello de tiempo y el sello HMAC. No devuelve el documento.

### Paso 6. El dashboard lee agregados

El dashboard no lee la bitácora ni la tabla de participación. Lee solo `ballot_records` y cuenta por `candidate_id` y por voto en blanco.

---

## 6. El recorrido del administrador

1. Entra a `/admin/login`.
2. Envía usuario y contraseña.
3. El servidor valida y devuelve una cookie `HttpOnly` firmada.
4. `/admin` comprueba la cookie antes de servir el panel.
5. Los endpoints de censo, auditoría y urna exigen la misma cookie.
6. El administrador puede abrir/cerrar la urna, cambiar de modalidad, generar el acta o reiniciar la jornada.
7. Después de generar el acta, la jornada queda escrutada y no se puede reabrir sin reiniciarla.

El administrador **no puede** ver “quién votó por quién”. Puede ver el censo, la participación y los agregados; la papeleta es anónima.

---

## 7. Las reglas que el sistema intenta garantizar

- Un elector habilitado vota una sola vez por modalidad.
- El voto no se puede alterar sin que cambie el sello HMAC.
- El cliente no puede inventar candidatos.
- El voto no se guarda en memoria: sobrevive a un reinicio.
- El secreto del voto se apoya en separar identidad de papeleta.
- Las acciones de administración requieren sesión.

---

## 8. Glosario para explicar sin trabarte

| Término | Explicación corta |
|---|---|
| **Censo** | Lista oficial de personas habilitadas para votar. |
| **Urna** | Lugar donde se guardan las papeletas; aquí es la tabla `ballot_records`. |
| **Papeleta** | Objeto que representa un voto. |
| **Participación** | Registro de que una persona ya votó, sin decir qué votó. |
| **PIN** | Clave numérica de demostración que acompaña al documento. |
| **HMAC** | Sello con una clave compartida; detecta cambios, pero no es una firma digital asimétrica. |
| **Hash** | Huella digital de un contenido; sirve para detectar alteraciones. |
| **Cookie HttpOnly** | Cookie que el JavaScript de la página no puede leer. |
| **Transacción** | Conjunto de operaciones que se guardan todas o no se guarda ninguna. |
| **Restricción única** | Regla de la base que impide dos filas iguales. |
| **Reset de jornada** | Borra todos los votos y participaciones de una modalidad; conserva el censo. |

---

## 9. Cómo estudiar este documento

1. Lee la sección 5 (recorrido de un voto) hasta poder contarla sin mirar.
2. Lee la sección 6 (recorrido del administrador).
3. Abre `src/main.py`, `api.py` y `voting_facade.py` y sigue el recorrido en el código.
4. Lee `10_los_patrones_en_simple.md` y practica la explicación de cada patrón en un minuto.
5. Usa `11_guion_de_exposicion.md` para ensayar la exposición completa.
