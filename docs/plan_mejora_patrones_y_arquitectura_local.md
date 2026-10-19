# Plan de mejora: de prototipo de patrones a producto personal local-first

> **Documento de trabajo — versión 1.0**
> **Alcance:** este documento asume que el proyecto se trata como un producto personal que quieres llevar, con suerte, a producción real. Por ahora se queda **en local**, ejecutándose con `python3 -m src.main`, mientras aprendes lo necesario para la nube.
>
> **Nota de estado:** este documento es el plan de mejora inicial. Varias brechas ya se corrigieron en la iteración actual (autenticación con PIN, login de administrador, persistencia de votos, reset de jornada, validación de candidato y limpieza de documentación). Úsalo como hoja de ruta para lo que sigue: persistencia de auditoría, verificación criptográfica, escrutinio por mesa y migración a PostgreSQL.
>
> **Idea central:** no necesitas reescribir todo. Necesitas **cerrar los huecos que rompen las promesas del sistema** y **quitar los patrones que hoy no aportan**. La base es buena; el problema es que algunas cosas “de vitrina” están mezcladas con cosas críticas.

---

## 0. Cómo leer este documento

Está dividido en tres partes:

1. **Entender** (secciones 1 a 4): qué tienes, qué funciona, qué falla y por qué, explicado sin tecnicismos.
2. **Patrones** (secciones 5 y 6): cuáles se quedan, cuáles se mejoran y cuáles sobran, con el porqué.
3. **Plan local-first** (secciones 7 a 12): cómo mantenerlo robusto en tu máquina, cómo endurecerlo y cómo prepararlo para una nube futura sin prisa.

Si solo tienes 10 minutos, lee la sección 1, la tabla de la sección 5 y el checklist de la sección 12.

---

## 1. Resumen ejecutivo en lenguaje sencillo

### Qué es hoy el proyecto

Una aplicación web local de votación con:

- Dos elecciones: Nacional (CNE) y Universitaria (UDI).
- Un censo en SQLite con ciudadanos habilitados/inhabilitados.
- Una cabina para votar, un dashboard de resultados y un panel de administración.
- 12 patrones de diseño GoF implementados.
- 18 pruebas automatizadas (estado actual).
- Documentación bastante extensa.

**Como proyecto de patrones:** está muy bien. Los patrones no son solo nombres: están implementados y se entienden. Eso es valioso.

**Como producto personal:** todavía no está listo. Funciona en el camino feliz, pero hay fallos que, en una elección real, serían graves: se puede votar por otra persona, se puede votar dos veces, se puede inventar un candidato, el administrador no tiene login real y el secreto del voto se puede romper mirando la bitácora.

### Las 5 cosas que hay que arreglar primero

1. **Que el votante sea quien dice ser.** Hoy basta con enviar una cédula; no se prueba que sea del titular.
2. **Que no se pueda votar dos veces.** Hoy una carrera entre dos peticiones puede aceptar dos votos; además, al reiniciar se borra el control.
3. **Que el voto lo valide el servidor.** Hoy el cliente decide el candidato y hasta si el voto lleva firma.
4. **Que el panel de administración esté protegido de verdad.** Hoy la “llave” está escrita en el código y en el navegador.
5. **Que el secreto del voto no se rompa por la bitácora.** Hoy la bitácora relaciona la cédula con el ID de la papeleta.

### La decisión de fondo

Para tu caso, **local-first es una decisión correcta**:

- Es más fácil de entender y de controlar.
- No expones la aplicación a Internet.
- Puedes aprender seguridad, bases de datos y despliegue sin arriesgar datos reales.

Pero **local no significa “sin seguridad”**. Significa que el perímetro es más pequeño. Aun en tu máquina, un XSS puede robar el token del administrador, un error puede borrar la base de datos y un archivo con datos personales puede filtrarse. La estrategia correcta es: **local ahora, cloud-ready desde el diseño, nube solo cuando los fundamentos estén sólidos.**

### Lo que sí está bien y no hay que tocar

- La separación por módulos: `census`, `voting`, `tally`, `transmission`, `security`, `facade`, `presentation`.
- La interfaz: clara, coherente, sin jerga innecesaria.
- La implementación de Factory Method, Builder, Adapter, Decorator y Proxy.
- La documentación pedagógica.
- La idea de un sistema con dos familias de elección.

---

## 2. Glosario mínimo (para que nada quede en el aire)

| Palabra | Qué significa en simple |
|---|---|
| **Autenticación** | Demostrar quién eres. No basta con decir “soy Juan”; hay que probarlo con algo que solo Juan tenga. |
| **Autorización** | Decidir qué puede hacer quien ya se autenticó. Una cosa es ser Juan; otra es que Juan sea administrador. |
| **Token** | Una llave temporal que el sistema entrega después de autenticarte. Si está escrita en el código, deja de ser una llave. |
| **Hash** | Una huella digital de un contenido. Sirve para detectar si algo cambió, pero no para ocultarlo. |
| **HMAC** | Un sello hecho con una contraseña compartida. Sirve para detectar cambios, pero **no** prueba ante un tercero quién lo firmó. |
| **Firma digital** | Un sello hecho con criptografía asimétrica: una llave privada firma y una pública verifica. Eso sí permite verificar sin compartir el secreto. |
| **Cifrado** | Transformar datos para que nadie los lea sin la clave. El proyecto actual **no cifra** los votos; solo los sella. |
| **XSS** | “Cross-site scripting”: alguien mete código malicioso en un texto que luego se muestra en la página. Cuando el administrador la abre, el código se ejecuta. |
| **Condición de carrera** | Dos operaciones miran el mismo dato al mismo tiempo, las dos creen que está libre y las dos lo ocupan. |
| **PII** | “Personally Identifiable Information”: datos que identifican a una persona (cédula, nombre, dirección). |
| **Idempotencia** | Que repetir una operación no cambie el resultado. Si reintentas un voto, no debería contarse dos veces. |
| **Persistencia** | Que los datos sobrevivan a reiniciar el programa. Hoy los votos viven en memoria. |
| **Migración** | Un cambio controlado en la estructura de la base de datos, sin perder datos. |
| **Verificabilidad** | Poder demostrar, con pruebas, que el resultado corresponde a los votos emitidos. |
| **Local-first** | La aplicación está diseñada para funcionar primero en tu máquina, sin depender de la nube, pero sin cerrarse a ella. |
| **Cloud-ready** | Que migrar a la nube sea un cambio de infraestructura, no una reescritura. |

---

## 3. Mapa actual del proyecto (sin jerga)

### 3.1 Qué hace cada parte

| Parte | Qué hace | Estado |
|---|---|---|
| `src/core/config.py` | Guarda la configuración global de la elección | Funciona, pero es un objeto global |
| `src/core/database.py` | Crea la base SQLite y precarga el censo | Funciona; los tests la contaminan |
| `modules/census` | Lee el censo desde SQLite, JSON o CSV | SQLite es el real; JSON/CSV solo se usan en tests |
| `modules/election` | Define familias de elección, mesas y jerarquías | Funciona, pero las mesas no se conectan al voto |
| `modules/voting` | Crea papeletas, las envuelve con seguridad y comparte candidatos | Funciona; el Flyweight no ahorra lo que dice |
| `modules/tally` | Construye el acta de escrutinio | Funciona, pero no se guarda ni se verifica después |
| `modules/transmission` | Envía boletines por consola, archivo o memoria | Solo consola es real; el resto es de test |
| `modules/security` | Protege acciones administrativas y audita | La idea está; falta autenticación real |
| `modules/facade` | Coordina todo | Funciona, pero hace demasiado |
| `presentation` | API FastAPI y las tres pantallas | Muy buena presentación; seguridad de cliente nula |

### 3.2 Lo que está bien

- **Los patrones existen de verdad.** No son solo diagramas: hay clases, interfaces y flujo.
- **La UI está pensada para una persona real.** La cabina, el dashboard y el panel admin se entienden.
- **La separación de responsabilidades es razonable.** El dominio no depende de FastAPI.
- **Hay documentación y pruebas.** No estás empezando de cero.
- **La idea del producto es clara.** No es un CRUD genérico; tiene lenguaje electoral.

### 3.3 Lo que está en construcción

- La seguridad real (autenticación, autorización, secretos, XSS).
- La persistencia de los votos y de las actas.
- El ciclo de vida de una elección (abrir, cerrar, escrutar, certificar).
- El escrutinio por mesa.
- La verificabilidad del resultado.
- La separación entre “datos de identidad” y “datos de voto”.

---

## 4. Los problemas explicados sin tecnicismos

Esta sección es la versión “para humanos” de los hallazgos. Cada problema tiene: qué pasa, una analogía, por qué importa y cómo se arregla.

### 4.1. Cualquiera puede votar por cualquiera

**Qué pasa:** para votar solo se envía la cédula. El sistema comprueba que esa cédula exista en el censo, pero no comprueba que quien envía la petición sea el dueño de la cédula. Además, el censo completo se puede leer sin login.

**En simple:** es como una mesa de votación donde el jurado pregunta “¿cuál es tu cédula?”, tú dices un número y te entregan el tarjetón, sin pedirte la cédula física ni comparar la foto.

**Por qué importa:** cualquiera que vea la lista de cédulas puede votar a nombre de otros. El secreto del voto no sirve si el voto es de otra persona.

**Cómo se arregla:**
- Autenticación real: código de un solo uso al correo/teléfono, contraseña + PIN, SSO de la universidad, o verificación presencial.
- Una sesión de elector de un solo uso, con vencimiento.
- No aceptar la cédula como prueba de identidad; el servidor debe saber quién está conectado.
- Cerrar el acceso público al censo.

### 4.2. Se puede votar dos veces (y al reiniciar se borra el control)

**Qué pasa:** el sistema revisa “¿ya votó?” y después marca “votó”. Entre esas dos acciones hay una pequeña ventana. Si llegan dos peticiones al mismo tiempo, las dos pueden ver “no ha votado” y las dos registrar el voto. Lo probé con 12 peticiones simultáneas para la misma cédula: **3 fueron aceptadas**. Además, el control vive en la memoria; al reiniciar el servidor, se borra.

**En simple:** dos personas miran la misma silla, las dos ven que está libre y las dos se sientan. Y cuando se reinicia la oficina, se borra la lista de quién ya se sentó.

**Por qué importa:** el invariante más importante de una elección —“una persona, un voto”— no se cumple.

**Cómo se arregla:**
- Guardar la participación en la base de datos con una restricción única: `(elección, votante)`.
- Hacer la operación en una transacción atómica: o se registra el voto y la participación, o no se registra nada.
- Si no se puede usar base de datos todavía, usar un candado en memoria (`threading.Lock`) y un solo worker, y documentar que es una limitación temporal.
- Persistir los votos para que un reinicio no los borre.

### 4.3. El cliente decide el candidato y hasta si el voto lleva firma

**Qué pasa:** el frontend envía un objeto libre con `candidate_id`, `candidate_name`, `party_name` y `security_layers`. El servidor no comprueba que el candidato exista ni que pertenezca a la elección. Yo envié un candidato inventado, sin capas de seguridad, y la API respondió 200, sin firma, y el dashboard lo contó como si fuera real.

**En simple:** es como dejar que el votante escriba a mano el nombre del candidato en el tarjetón y decida si quiere sello de la mesa o no. El sistema debería tener un tarjetón oficial y sellarlo siempre.

**Por qué importa:** se pueden inventar candidatos, inflar conteos y meter votos sin sello. Los números del dashboard y del acta pueden no coincidir.

**Cómo se arregla:**
- El cliente solo envía `candidate_id` (o `option_id`).
- El servidor busca el candidato en el catálogo oficial y valida que sea de la elección activa.
- El servidor **siempre** aplica las capas de seguridad; el cliente no decide.
- Rechazar candidatos inexistentes con un error claro (400/422).
- Devolver la selección tal como quedó registrada en el servidor.

### 4.4. La bitácora rompe el secreto del voto

**Qué pasa:** cuando alguien vota, la bitácora guarda “el elector con cédula X emitió la papeleta Y”. La urna guarda la papeleta Y con la selección. Juntando las dos cosas, se sabe qué votó la cédula X. Y la bitácora es pública.

**En simple:** es como una urna transparente con una etiqueta que dice “este sobre es de Juan”. El sobre es anónimo por fuera, pero la etiqueta lo delata.

**Por qué importa:** es exactamente lo que el README dice que el sistema no debe permitir. Sin secreto, una elección pierde legitimidad.

**Cómo se arregla:**
- No guardar la cédula en los eventos de emisión del voto.
- Usar un token anónimo de un solo uso: el sistema sabe que alguien votó, pero no guarda junto “quién” y “qué”.
- Separar la base de identidad (quién votó) de la base de papeletas (qué se votó), sin una clave que las una.
- Restringir la bitácora y hacerla pseudónima.
- No publicar resultados parciales durante la votación sin una política clara.

### 4.5. El panel de administración no tiene login real

**Qué pasaba (ya corregido):** el token de administrador era una constante escrita en el código, aparecía en la página del panel y en Swagger. El Proxy confiaba en el rol que le pasaban y `/admin` se servía sin autenticación. Ahora hay login con cookie `HttpOnly` y rutas protegidas.

**En simple:** la llave del cuarto de control está pegada con cinta en la puerta, y además está impresa en el manual.

**Por qué importa:** cualquiera puede abrir/cerrar la urna, cambiar de elección, generar un acta o modificar el censo.

**Cómo se arregla:**
- Login real con contraseña hasheada (Argon2id) o SSO.
- Sesión en cookie `HttpOnly; Secure; SameSite`, o token firmado con vencimiento.
- El Proxy no debe confiar en un rol que le pasan; debe recibir una sesión emitida por el servicio de autenticación.
- Sacar el token del código, del HTML y de Swagger.
- Proteger `/admin` y `/docs`; desactivar Swagger en producción.
- Rate limiting, bloqueo por intentos y MFA para administradores.

### 4.6. Los datos personales y la bitácora son públicos

**Qué pasa:** `GET /api/census/voters` devuelve cédula, nombre, mesa y estado sin autenticación. `GET /api/security/audit-log` también es público. En mi prueba, el censo devolvió 11 filas.

**En simple:** la lista de quiénes votan y dónde están está en la calle.

**Por qué importa:** privacidad (Ley 1581 en Colombia, GDPR en Europa), enumeración de votantes, coerción, venta de datos y daño reputacional.

**Cómo se arregla:**
- Autenticación y autorización por rol.
- Minimizar datos: el elector ve solo su ficha; el administrador ve lo necesario.
- Enmascarar documentos en listados.
- Encriptación en reposo, retención definida y auditoría de accesos.
- No usar datos de personas reales en el seed; usar datos sintéticos.

### 4.7. El panel admin es vulnerable a XSS almacenado

**Qué pasa:** el panel construye filas con `innerHTML` usando nombres, documentos y detalles de auditoría. Un atacante no autenticado puede enviar un documento con `<img src=x onerror=...>`; el sistema lo guarda en la bitácora; cuando el admin abre el panel, el código se ejecuta.

**En simple:** alguien escribe un cartel con un código que se activa cuando el administrador entra al cuarto. Como la llave está en el mismo cuarto, se la puede llevar.

**Por qué importa:** robo del token de administrador y control total de la elección. Es una cadena completa: sin login → XSS → robo de token → acciones de admin.

**Cómo se arregla:**
- Usar `textContent` o crear nodos DOM, nunca `innerHTML` con datos de usuario.
- Escapar/sanitizar; validar el formato del documento.
- CSP sin `unsafe-inline`; quitar `onclick` inline.
- Sacar el token del JavaScript; usar cookie `HttpOnly`.

### 4.8. Cambiar de modo borra la elección y reabre la urna

**Qué pasa:** al cambiar de Nacional a Universitaria, el sistema crea una fachada nueva, borra los votos, borra la bitácora, reinicia candidatos y **abre la urna**. Si vuelves al modo anterior, todos pueden votar otra vez. No hay un estado formal de la elección.

**En simple:** es como cerrar la urna, cambiar el tarjetón, volver a abrirla y empezar de cero, sin dejar acta de lo anterior.

**Por qué importa:** pérdida de datos, reapertura de una elección cerrada, doble voto entre cambios y actas inconsistentes.

**Cómo se arregla:**
- Modelar la elección como una entidad con estado: `BORRADOR → ABIERTA → CERRADA → ESCRUTADA → CERTIFICADA`.
- No permitir cambiar de modo con la urna abierta.
- Archivar la elección anterior.
- No reabrir una elección cerrada sin una operación explícita, auditada y con doble control.
- Validar el modo contra una lista cerrada (`NATIONAL`, `UNIVERSITY`).

### 4.9. La “firma digital” y la “verificabilidad” todavía no existen

**Qué pasa:** el voto se sella con HMAC-SHA256 usando una clave que está en el código. Eso no es una firma digital: es un sello con contraseña compartida. No hay endpoint para verificar el recibo, el acta no está firmada y no hay forma de que un tercero compruebe el resultado.

**En simple:** el sello demuestra que el sobre no cambió, pero no demuestra ante un juez quién lo selló. Y si alguien tiene la misma contraseña, puede hacer sellos iguales.

**Por qué importa:** la promesa de “no repudio” y “auditoría” no se sostiene. En una elección real, la verificabilidad es el producto.

**Cómo se arregla (más adelante, no hoy):**
- Firmas asimétricas Ed25519: una llave privada firma, una pública verifica.
- Acta firmada y publicada.
- Árbol de Merkle de papeletas con raíz firmada.
- Código de retorno verificable para el votante.
- Verificador independiente.
- Si el marco legal lo exige, auditoría de riesgo limitante y respaldo en papel.

---

## 5. Los patrones: cuáles se quedan, cuáles se mejoran y cuáles sobran

> **Regla de oro:** un patrón no es un adorno. Es una herramienta para resolver un problema. Si no resuelve un problema real de **este** producto, sobra, aunque sea muy bonito en un diagrama.

### 5.1 Veredicto rápido

| Patrón | Qué hace en simple | ¿Aporta hoy? | Decisión | Por qué |
|---|---|---|---|---|
| **Singleton** | Un único objeto global de configuración | No como patrón; sí como objeto | **Simplificar** | Crea estado global, acopla los tests y te impide tener dos elecciones a la vez. |
| **Factory Method** | Subclases deciden qué papeleta crear | Sí | **Mantener** | Es un punto de extensión real para nuevos tipos de voto. |
| **Abstract Factory** | Crea una familia de piezas coherentes (validador, encabezado, regla) | Condicional | **Mantener con reservas** | Con dos familias está bien; si no crecen, un Strategy/Policy sería más simple. |
| **Builder** | Construye el acta paso a paso | Sí | **Mantener** | El acta tiene muchos campos y reglas; el Builder evita un constructor gigante. |
| **Prototype** | Clona plantillas de mesa | No hoy | **Simplificar o eliminar** | Solo se clonan dos mesas al arrancar; una función de seed bastaría. |
| **Adapter** | Traduce censos de distintos formatos | Sí | **Mantener** | Aísla SQLite y te permitirá conectar Excel, CSV o una API externa. |
| **Bridge** | Separa el tipo de boletín del canal de envío | Condicional | **Mantener si habrá 2+ canales reales** | Hoy solo la consola es real; si no vas a agregar webhook/email, es maquinaria extra. |
| **Composite** | Árbol de país → departamento → puesto → mesa | Condicional | **Mantener y conectar** | Hoy solo cuenta mesas; si no hay resultados por mesa, es decorativo. |
| **Decorator** | Envuelve el voto con capas de seguridad | Sí | **Mantener** | Encaja muy bien; eso sí, las capas deben decidirlas el servidor. |
| **Facade** | Un punto de entrada único | Sí, pero delgado | **Refactorizar** | La idea es correcta; el objeto actual hace demasiado y esconde problemas. |
| **Flyweight** | Comparte datos comunes de candidatos | No hoy | **Arreglar o eliminar** | Las papeletas copian nombre y partido; con 3 candidatos no hay problema de memoria. |
| **Proxy** | Guardia que protege operaciones | Sí | **Mantener** | Encaja para acciones administrativas; falta autenticación real. |

### 5.2 Los que se quedan (y por qué)

**Factory Method — se queda.**
Tiene sentido cuando mañana agregues voto nulo, voto en blanco especial, referendo o voto por lista. Hoy ya hay tres productos y el creador está separado del producto. Es barato y limpio.

**Builder — se queda.**
El acta tiene título, jurisdicción, mesas, votos, firmas, hash y veredicto. Construirla con un constructor de 10 parámetros sería un antipatrón. El Builder es el patrón correcto. Eso sí: el `TallyReportDirector` no se usa; o lo usas para un flujo real, o lo eliminas.

**Adapter — se queda.**
Es uno de los patrones que más te va a servir cuando conectes una fuente externa (Registraduría, Excel, API universitaria). Hoy SQLite es el adaptador real. JSON y CSV están bien como aprendizaje, pero no los presentes como si estuvieran en producción. Además, conviene separar la interfaz de lectura de la de escritura: `ICensusQuery` y `ICensusAdmin`; el adaptador actual mezcla ambas.

**Decorator — se queda.**
Es el ejemplo más claro del proyecto: el voto base no sabe de sellos; los decoradores agregan timestamp, firma y marca de agua. Es un buen uso. El problema no es el patrón; es que el cliente decide las capas. El servidor debería aplicar siempre la política completa.

**Proxy — se queda.**
Un “guardia” delante de las operaciones administrativas es una idea correcta. El problema es que el guardia confía en una credencial que le dan, en lugar de verificar la identidad. Arregla la autenticación y el Proxy se vuelve valioso.

**Facade — se queda, pero adelgazado.**
La fachada debe **coordinar**, no hacerlo todo. Hoy `VotingSystemFacade` cuenta votos, consulta el censo, arma el dashboard y transmite boletines. Eso es un “god object”. Divídela en servicios:
- `VoteService`: validar y emitir voto.
- `TallyService`: contar y construir acta.
- `CensusService`: consultar y administrar censo.
- `DashboardService`: armar métricas de lectura.
- `ElectionService`: abrir, cerrar y cambiar estado.
La fachada queda como una capa fina que llama a esos servicios.

### 5.3 Los condicionales (se quedan solo si el producto los necesita)

**Abstract Factory — condicional.**
Está bien para dos familias: Nacional y Universitaria, cada una con validador, encabezado y regla de escrutinio. Pero las piezas son pequeñas y sin estado. Si mañana solo tienes dos familias y no crecen, un `ElectionPolicy` con Strategy sería más simple. **Mi recomendación:** mantenla porque ya está y no estorba, pero no agregues productos artificiales solo para justificarla. Si aparece una tercera familia real (municipal, consejo estudiantil, etc.), se gana su lugar.

**Bridge — condicional.**
Bridge vale la pena cuando hay **dos dimensiones que varían**: tipo de boletín y canal de envío. Hoy solo la consola es real; archivo y memoria son de test. Si tu roadmap incluye webhook, correo, Telegram o integración con la Registraduría, mantenlo. Si no, un `Notifier` con una sola implementación es suficiente. **No agregues canales solo para que el patrón tenga sentido.**

**Composite — condicional, pero con potencial.**
La jerarquía País → Departamento → Puesto → Mesa es correcta para un sistema electoral. El problema es que hoy el voto no guarda `station_id`, así que el árbol solo sirve para contar mesas y listar IDs. Si implementas resultados por mesa (algo que un sistema electoral real necesita), el Composite se vuelve genuinamente útil. **Mi recomendación:** conéctalo al voto y al escrutinio; si no vas a hacerlo, elimínalo.

### 5.4 Los que hoy sobran (o hay que arreglar)

**Singleton — sobra como patrón, no como idea.**
Tener una configuración única está bien. Lo que sobra es el **Singleton global** con `reset_for_testing()` en el camino de producción. Ese reset:
- Hace que los tests dependan del orden.
- Te impide tener dos elecciones simultáneas.
- Reinicia el estado sin querer al cambiar de modo.

**Qué hacer:** crear un objeto `Settings` una vez al arrancar y pasarlo por inyección de dependencias (o dejarlo como módulo de configuración). Si mantienes la clase, quita el reset del flujo de producción y úsalo solo en tests. No lo presentes como “el patrón Singleton” si en realidad es un objeto de configuración.

**Prototype — hoy no paga su costo.**
Solo se usa para clonar dos plantillas de mesa al arrancar. Una función `seed_stations()` con dos llamadas sería más simple y más legible. El patrón se gana su lugar cuando:
- El usuario puede crear plantillas desde la UI.
- Hay muchas mesas y quieres clonar configuraciones.
- Las plantillas tienen objetos complejos que no quieres reconstruir.

Si no vas a construir eso, **elimínalo** o déjalo como módulo experimental. No es que esté mal implementado; es que no resuelve un dolor actual.

**Flyweight — hoy no ahorra memoria.**
El patrón dice: comparte lo pesado y común; guarda aparte lo único. En tu código, el catálogo de candidatos comparte metadatos, pero cada `CandidateBallot` **vuelve a copiar** `candidate_name` y `party_name`. Entonces:
- No ahorras las cadenas duplicadas.
- Con 3 candidatos, el problema de memoria no existe.
- La justificación de “millones de votos” no se cumple.

**Dos caminos:**
1. **Arreglarlo:** la papeleta guarda solo `candidate_id`; el nombre y el partido se resuelven del pool al mostrar el voto. Ahí sí hay ahorro.
2. **Eliminarlo:** si el catálogo de candidatos se queda como una lista simple, el Flyweight no aporta y se puede quitar sin dolor.

Mi recomendación: si quieres conservar el aprendizaje, hazlo bien (opción 1). Si quieres simplificar el producto, elimínalo (opción 2). Lo que no deberías hacer es mantenerlo con la justificación actual, porque no es cierta.

**Código muerto que conviene quitar o mover:**
- `TallyReportDirector`: no se usa. O lo usas para un flujo real, o lo eliminas.
- `AuditAlertBulletin`: se importa pero no se instancia. Elimínalo hasta que existan alertas reales.
- `FileTransmissionChannel` y `MemoryAuditSinkTransmissionChannel`: son canales de test. Muévelos a `tests/support/` o márcalos como tales; no los presentes como producción.
- `JsonCensusAdapter` y `CsvCensusAdapter`: si no vas a importar censos, muévelos a `experimental/` o déjalos solo para tests. Si sí vas a importar, son útiles.
- `Singleton.reset_for_testing()`: quítalo del arranque de producción.
- Imports sin usar y tipos inconsistentes: limpieza de bajo riesgo.

### 5.5 Qué patrones nuevos sí valen la pena (y en qué orden)

No metas diez patrones de golpe. Para tu producto local, estos son los que realmente te van a servir:

| Necesidad | Patrón o técnica | Para qué | Cuándo |
|---|---|---|---|
| Ciclo de vida de la elección | **State** | Evitar reabrir una elección cerrada; pasar de borrador a abierta, cerrada, escrutada y certificada. | Fase 1 |
| Persistencia | **Repository + Unit of Work** | Aislar la base de datos y permitir cambiar SQLite por PostgreSQL sin tocar el dominio. | Fase 1 |
| Validación del voto | **Chain of Responsibility** | Encadenar comprobaciones: elección abierta, votante habilitado, no votó, candidato válido, mesa correcta. | Fase 1 |
| Reglas de escrutinio | **Strategy** | Mayoría absoluta, mayoría simple, segunda vuelta, desempate; configurables por elección. | Fase 2 |
| Auditoría | **Command** | Cada acción crítica como un objeto auditable, con actor, fecha y resultado. | Fase 2 |
| Transmisión confiable | **Outbox + Retry** | No perder boletines si el canal falla. | Cuando haya un canal real |
| Dashboard en vivo | **Observer / SSE** | Actualizar sin polling cada 5 segundos. | Cuando el dashboard sea pesado |
| Lectura de resultados | **CQRS** | Separar el modelo de escritura del de lectura. | Cuando haya muchos votos |

**Orden recomendado:** State → Repository → Chain → Strategy. Los demás pueden esperar.

### 5.6 No organices el código por patrón

Tu estructura actual por módulos de dominio (`census`, `voting`, `tally`) está bien. **No la cambies a carpetas por patrón** (`singleton/`, `factory/`, `decorator/`). Los patrones son detalles de implementación; el dominio es lo que debe mandar.

Una estructura objetivo, sin reescribir de golpe:

```text
src/
  core/            # configuración, logging, base de datos
  domain/          # entidades y reglas puras (sin FastAPI, sin SQLAlchemy)
  application/     # casos de uso: emitir voto, abrir urna, escrutar
  infrastructure/  # repositorios SQLite, criptografía, canales
  presentation/    # FastAPI y plantillas
```

Puedes llegar ahí gradualmente: primero extrae servicios de la fachada, luego mueve la persistencia a `infrastructure`, luego separa el dominio puro. **No hagas un “big bang” de reescritura.**

---

## 6. Plan de mejora de patrones (orden de refactor)

Este es el orden que menos riesgo tiene. Cada paso se puede hacer y probar por separado.

### Paso 1 — Limpieza de bajo riesgo (1-2 días)

- Eliminar `TallyReportDirector` o usarlo en un flujo real.
- Eliminar `AuditAlertBulletin` hasta que existan alertas.
- Mover canales de test a `tests/support/`.
- Quitar imports sin usar.
- Corregir tipos inconsistentes (`List[str] = (...)`).
- Quitar `reset_for_testing()` del arranque de producción.
- Documentar qué adaptadores son reales y cuáles son experimentales.

**Riesgo:** bajo. **Test:** los 13 tests siguen pasando.

### Paso 2 — Fachada delgada + servicios (3-5 días)

- Crear `VoteService`, `TallyService`, `CensusService`, `DashboardService`, `ElectionService`.
- Mover la lógica de `VotingSystemFacade` a esos servicios.
- Dejar la fachada como coordinadora.
- La API deja de acceder a `_facade`, `_config`, `_family_factory`; usa métodos públicos.

**Riesgo:** medio. **Test:** mismos endpoints, mismos resultados.

### Paso 3 — Estado de la elección (State) (3-5 días)

- Crear `ElectionState` con estados y transiciones válidas.
- Prohibir cambiar de modo con la urna abierta.
- Prohibir reabrir una elección cerrada sin operación explícita.
- Auditar cada transición.
- Validar `mode` con un enum.

**Riesgo:** medio. **Test:** no se puede abrir dos veces, no se puede votar cerrada, no se puede reabrir sin autorización.

### Paso 4 — Validación del voto (Chain) (3-5 días)

- Cadena de validadores: elección abierta → elector habilitado → no votó → candidato válido → mesa correcta.
- El cliente envía solo `candidate_id`.
- El servidor aplica siempre las capas de seguridad.
- Respuestas claras: 400/403/409/422.

**Riesgo:** medio. **Test:** candidato inexistente, voto sin firmas, doble voto, elector inhabilitado.

### Paso 5 — Persistencia (Repository + Unit of Work) (1-2 semanas)

- Crear repositorios para censo, participación, votos y actas.
- Restricción única `(election_id, voter_id)`.
- Transacción atómica para emitir voto.
- Persistir acta y recibo.
- Migraciones con Alembic.
- SQLite con WAL y backups; PostgreSQL cuando haga falta.

**Riesgo:** alto, pero es el paso que más te acerca a un producto real. **Test:** reiniciar el servidor no permite revotar; el acta sobrevive.

### Paso 6 — Conectar Composite y mesa (3-5 días)

- El voto guarda `station_id`/`terminal_id`.
- El escrutinio agrega por mesa y por jurisdicción.
- El acta muestra desglose real.
- `allowed_ballot_types` e `is_active` se validan de verdad.

**Riesgo:** medio. **Test:** resultados por mesa suman el total.

### Paso 7 — Decidir Flyweight, Prototype, Bridge y Abstract Factory (1-3 días)

- Flyweight: arreglar (papeleta guarda `candidate_id`) o eliminar.
- Prototype: mantener solo si hay plantillas configurables; si no, reemplazar por seed.
- Bridge: mantener si hay 2+ canales reales; si no, simplificar.
- Abstract Factory: mantener si habrá más familias; si no, evaluar Strategy.

**Riesgo:** bajo. **Test:** comportamiento idéntico.

### Paso 8 — Verificabilidad (opcional, 2-4 semanas)

- Ed25519, acta firmada, Merkle tree, recibo verificable, verificador independiente.
- Esto es investigación y diseño, no solo código. Hazlo cuando el resto esté estable.

---

## 7. Estrategia local-first (tu caso)

### 7.1 La decisión

**Ahora:** local, en tu máquina, con `python3 -m src.main`.
**Después:** nube, solo cuando los fundamentos estén sólidos y entiendas los riesgos.

Esto es una decisión válida y madura. No es “miedo a la nube”; es **secuenciar el aprendizaje**. La nube no arregla una aplicación insegura: la expone más rápido.

### 7.2 Qué significa “local” en seguridad

Local reduce el perímetro, pero no lo elimina. Aun en tu máquina:

- Un XSS en el panel admin puede robar el token y ejecutar acciones.
- Otro usuario de la máquina o un malware puede leer la base de datos.
- Un error puede borrar `e_voting.db`.
- Un archivo con datos personales puede filtrarse por un backup o un repositorio.
- Una dependencia comprometida puede ejecutar código.

**Frase para recordar:** *local es un perímetro más pequeño, no un perímetro inexistente.*

### 7.3 Modelo de amenaza local (simple)

| Amenaza | ¿Aplica en local? | Qué hacer |
|---|---|---|
| Alguien entra a tu sesión de admin | Sí, si dejas el navegador abierto | Login, bloqueo de pantalla, cookie con vencimiento |
| XSS en el panel | Sí | Escapar HTML, CSP, no token en JS |
| Pérdida de la base de datos | Sí | Backups automáticos, no borrar a mano |
| Malware en la máquina | Sí | Disco cifrado, antivirus, no instalar dependencias raras |
| Alguien lee el censo | Sí, si hay PII real | Datos sintéticos, cifrado en reposo, permisos de archivo |
| Acceso desde la red | No, si escuchas en `127.0.0.1` | No usar `0.0.0.0`, no abrir el puerto en el router |
| Ataque masivo de Internet | No, si no está expuesto | No publicar el puerto; si algún día lo haces, TLS, WAF, rate limit |

### 7.4 Checklist de seguridad local

- [ ] `.env` fuera de git, con permisos `600`.
- [ ] `SECRET_KEY` aleatoria y distinta de la de ejemplo.
- [ ] Sin tokens hardcodeados en código, HTML ni documentación.
- [ ] Login de administrador con contraseña hasheada (Argon2id).
- [ ] `/admin`, `/api/census/voters` y `/api/security/audit-log` requieren autenticación.
- [ ] Validación server-side del candidato y de la elección.
- [ ] Voto atómico y persistente.
- [ ] Sin documento en la auditoría de emisión de voto.
- [ ] HTML escapado; CSP; sin `onclick` inline.
- [ ] Tests con base de datos temporal, no con la base real.
- [ ] Backups de `e_voting.db` antes de cambios grandes.
- [ ] Datos sintéticos; nada de personas reales.
- [ ] Servidor escuchando en `127.0.0.1`, no en `0.0.0.0`.
- [ ] Un solo worker mientras el estado viva en memoria.
- [ ] `reload=False` para pruebas serias (el reload reinicia el estado).
- [ ] Dependencias auditadas (`pip-audit`).
- [ ] Disco cifrado (FileVault, LUKS o BitLocker).
- [ ] Logs sin PII.

### 7.5 Cómo ejecutarlo (runbook local)

```bash
# 1. Activar el entorno
source venv/bin/activate

# 2. Variables de entorno (cuando exista .env)
# cp .env.example .env
# chmod 600 .env

# 3. Arrancar
python3 -m src.main
```

**Importante:** no uses `python src/main.py`. Al ejecutar un script, Python pone `src/` como primer path y `import src.core...` falla. La forma correcta es `python3 -m src.main`, que ejecuta el módulo desde la raíz del proyecto. Corrige `docs/project_state.md`, que documenta la forma que falla.

### 7.6 Qué cambiar en `src/main.py` (sin reescribirlo)

- **Host:** mantener `127.0.0.1`; nunca `0.0.0.0` por ahora.
- **Reload:** usar una variable `DEV_RELOAD` (por defecto `false` para pruebas serias; `true` solo para desarrollo).
- **Workers:** uno solo mientras el estado esté en memoria. No uses `--workers 4`.
- **Auto-apertura:** hoy el arranque abre la urna con una sesión de admin fabricada. Para un producto, eso debe ser una acción explícita del administrador. Agrega `AUTO_OPEN_POLLS=false` por defecto.
- **Secretos:** cargar desde `.env`, no desde constantes.
- **Base de datos:** permitir `DATABASE_URL` para usar una base de test distinta.
- **Logs:** configurar logging a archivo/consola, no `print`.

### 7.7 Backups (importante en local)

No copies `e_voting.db` con `cp` mientras la aplicación está escribiendo. Usa la API de backup de SQLite:

```python
import sqlite3
from pathlib import Path
from datetime import datetime

src = sqlite3.connect("e_voting.db")
dst_path = Path("backups") / f"e_voting_{datetime.now():%Y%m%d_%H%M%S}.db"
dst_path.parent.mkdir(exist_ok=True)
dst = sqlite3.connect(dst_path)
src.backup(dst)
dst.close()
src.close()
print("Backup:", dst_path)
```

Hazlo antes de cada cambio de esquema o de cada prueba grande. En local, un backup es tu red de seguridad.

### 7.8 Cloud-ready sin nube: qué hacer ahora para no sufrir después

| Tema | Ahora (local) | Después (nube) |
|---|---|---|
| Configuración | `.env` + objeto `Settings` | Secrets Manager / SSM |
| Base de datos | SQLite con WAL y backups | PostgreSQL gestionado |
| Migraciones | Alembic desde el inicio | Alembic en CI/CD |
| Sesiones | Cookie firmada local | Redis/DB + OIDC |
| Archivos | Disco local | S3/GCS |
| Logs | Archivo/consola estructurada | CloudWatch/OpenTelemetry |
| Despliegue | `python3 -m src.main` | Docker + reverse proxy + TLS |
| Auth | Login local | OIDC/MFA |
| Rate limit | Middleware local | WAF/API Gateway |
| Observabilidad | `/health` + logs | Métricas, trazas, alertas |
| Tests | pytest local | CI |
| Secretos | `.env` | KMS/Vault |

**Regla:** si una decisión local te obliga a reescribir para la nube, probablemente no es una buena decisión local. Por eso: configuración por entorno, repositorios, migraciones y logs estructurados desde ahora.

### 7.9 Cuándo sí pasar a la nube

No lo hagas hasta que se cumplan estas condiciones:

- [ ] Autenticación y autorización reales.
- [ ] Sin secretos en el código.
- [ ] Base de datos con migraciones y backups probados.
- [ ] Aplicación sin estado crítico en memoria (o con estado compartido).
- [ ] Logs y health checks.
- [ ] Rate limiting.
- [ ] TLS y reverse proxy.
- [ ] Threat model y revisión de seguridad.
- [ ] Plan de rollback.
- [ ] Datos sintéticos o base legal para datos reales.

Si no cumples eso, la nube solo hará que los problemas sean más visibles y más caros.

---

## 8. Roadmap por fases (local)

### Fase 0 — Hardening local (1 semana)

Objetivo: que la demo local no tenga agujeros evidentes.

- [ ] Login de admin.
- [ ] Sin token hardcodeado.
- [ ] Censo y auditoría protegidos.
- [ ] Validación server-side del candidato.
- [ ] Voto siempre firmado por el servidor.
- [ ] Voto atómico (lock o BD).
- [ ] Sin documento en la auditoría de voto.
- [ ] HTML escapado + CSP.
- [ ] Tests aislados con base temporal.
- [ ] Documentación corregida.

**Definición de terminado:** los tests P0 pasan; ningún endpoint devuelve PII sin auth; un candidato inventado se rechaza; dos votos concurrentes no se aceptan; un `<img onerror>` se muestra como texto.

### Fase 1 — Persistencia y estado (2 semanas)

- [ ] Modelo de datos: elección, candidato, votante, participación, voto, acta, auditoría.
- [ ] Migraciones con Alembic.
- [ ] Restricción única `(election_id, voter_id)`.
- [ ] Transacción atómica de voto.
- [ ] Persistencia de acta y recibo.
- [ ] Máquina de estados de la elección.
- [ ] Sesión de elector de un solo uso.
- [ ] Tests de reinicio y concurrencia.

**Definición de terminado:** reiniciar el servidor no permite revotar; el acta sobrevive; no se puede reabrir una elección cerrada.

### Fase 2 — Escrutinio real y auditoría (2 semanas)

- [ ] Voto con `station_id`/`terminal_id`.
- [ ] Resultados por mesa y por jurisdicción (Composite conectado).
- [ ] Una sola función de conteo, por `candidate_id`.
- [ ] Tipos de voto: candidato, blanco, nulo, referendo.
- [ ] Reglas de escrutinio con Strategy y desempate.
- [ ] Auditoría persistente con hash chain.
- [ ] Panel de auditoría con filtros y paginación.
- [ ] Tests de suma y consistencia.

**Definición de terminado:** los resultados por mesa suman el total; el acta coincide con el dashboard; toda acción crítica queda auditada.

### Fase 3 — Verificabilidad (opcional, 2-4 semanas)

- [ ] Firmas Ed25519.
- [ ] Acta firmada.
- [ ] Merkle tree de papeletas.
- [ ] Código de retorno verificable.
- [ ] Verificador independiente.
- [ ] Documentación del protocolo.

**Definición de terminado:** un tercero puede verificar el acta y un recibo sin acceder a la base de datos.

### Fase 4 — Cloud readiness (cuando toque)

- [ ] Dockerfile + compose.
- [ ] PostgreSQL.
- [ ] Reverse proxy + TLS.
- [ ] Secrets manager.
- [ ] CI/CD.
- [ ] Observabilidad.
- [ ] Backups y restore drills.
- [ ] Threat model y DPIA.
- [ ] Load tests.

**No empieces esta fase antes de terminar la Fase 1.** La nube amplifica los errores; no los corrige.

### Qué hacer esta semana (si quieres empezar ya)

1. Crear `.env.example` y leer configuración desde entorno.
2. Implementar login de admin (aunque sea simple) y proteger `/admin`.
3. Validar el candidato en el servidor y firmar siempre.
4. Agregar un lock al voto y un test de concurrencia.
5. Quitar el documento de la auditoría de emisión.
6. Escapar el HTML del panel admin.
7. Aislar los tests con una base temporal.
8. Corregir este documento y `project_state.md` para usar `python3 -m src.main`.

---

## 9. Calidad: pruebas, herramientas y hábitos

### 9.1 Tests que de verdad importan

No midas solo cobertura. Mide **invariantes**:

- `test_no_puede_votar_dos_veces_concurrente`
- `test_no_puede_votar_candidato_inexistente`
- `test_voto_siempre_lleva_firma`
- `test_admin_sin_token_devuelve_401`
- `test_censo_requiere_autenticacion`
- `test_xss_se_renderiza_como_texto`
- `test_no_puede_votar_si_urna_cerrada`
- `test_no_puede_reabrir_eleccion_cerrada`
- `test_persistencia_tras_reinicio`
- `test_resultados_por_mesa_suman_total`

### 9.2 Aislar los tests

Hoy los tests importan `src.main` y usan la base real. Eso contamina `e_voting.db` y hace que los tests dependan del orden. Cambia a:

- Una base temporal por test (`tmp_path` o `DATABASE_URL=sqlite:///./test.db`).
- Un fixture que cree el esquema y lo borre al final.
- Sin `import src.main` con bootstrap global; usa una fábrica de aplicación.
- Datos de prueba sintéticos y mínimos.

### 9.3 Herramientas recomendadas

- `ruff` para lint y formato.
- `mypy` o `pyright` para tipos.
- `pytest` + `pytest-cov` con cobertura de ramas.
- `pip-audit` para dependencias.
- `pre-commit` para que no se suba código sin pasar las comprobaciones.
- `alembic` para migraciones.
- `structlog` o `logging` estándar para logs.
- `argon2-cffi` para contraseñas.
- `cryptography` para Ed25519 cuando llegue la Fase 3.
- `slowapi` o un middleware propio para rate limiting.
- `docker` y `docker compose` solo cuando pases a la nube.

### 9.4 Documentación que conviene escribir

- `docs/adr/ADR-001-local-first.md`: por qué local y no nube.
- `docs/adr/ADR-002-sqlite-ahora-postgres-despues.md`.
- `docs/adr/ADR-003-autenticacion-sesiones.md`.
- `docs/adr/ADR-004-secreto-del-voto.md`.
- `docs/threat_model.md`: qué proteges y de quién.
- `docs/runbook.md`: cómo arrancar, respaldar y recuperar.
- `docs/pattern_decisions.md`: este documento o una versión resumida.

Los ADR son útiles incluso en un proyecto personal: dentro de seis meses no recordarás por qué elegiste SQLite o HMAC en lugar de Ed25519.

### 9.5 Hábitos

- Un cambio pequeño, un test, un commit.
- No mezclar refactor y feature en el mismo commit.
- Backup antes de tocar la base.
- No agregar un patrón sin un problema real.
- No decir “producción” hasta que los P0 estén cerrados.
- Documentar las limitaciones conocidas; es más profesional que esconderlas.

---

## 10. Decisiones de producto que debes tomar

| Decisión | Opción A | Opción B | Mi recomendación |
|---|---|---|---|
| ¿Simulador o elección real? | Simulador para aprender | Elección real con requisitos legales | **Simulador por ahora**. Etiquétalo como tal. |
| ¿Un solo usuario o varios? | Solo tú, en local | Varios en red local | **Solo tú**. Si abres a LAN, necesitas TLS y auth. |
| ¿Datos reales? | Censo real | Datos sintéticos | **Sintéticos**. No uses PII de personas reales. |
| ¿Verificabilidad? | HMAC + auditoría local | Ed25519 + Merkle + verificador | **HMAC para aprender; Ed25519 cuando sea producto.** |
| ¿Multi-elección? | Una elección a la vez | Varias simultáneas | **Una a la vez** hasta que el Singleton desaparezca. |
| ¿Nube? | Ahora | Después de Fase 1 | **Después de Fase 1**. Local-first, cloud-ready. |

---

## 11. Cómo contar esto en tu portafolio (sin mentir)

**Pitch honesto:**

> “Prototipo local-first de votación electrónica con arquitectura de patrones GoF, FastAPI, SQLAlchemy y SQLite. Implementa 12 patrones, censo persistente, cabina de votación, dashboard y acta de escrutinio. Actualmente estoy en la fase de hardening de seguridad: autenticación real, voto atómico, aislamiento de identidad y verificación. No está certificado para elecciones reales; es un laboratorio personal para aprender arquitectura y seguridad.”

**Lo que sí puedes destacar:**
- Implementación real de 12 patrones, no solo diagramas.
- Diseño modular y UI completa.
- Uso de SQLite/SQLAlchemy y FastAPI.
- Conciencia de los trade-offs de seguridad.
- Capacidad de identificar y priorizar deuda técnica.

**Lo que no deberías decir:**
- “Está listo para producción.”
- “Es seguro” sin threat model.
- “Cifra los votos” (no los cifra).
- “Tiene firma digital” (es HMAC).
- “Es inmutable” (la bitácora está en memoria).

La honestidad no te quita valor; te da credibilidad. Un entrevistador senior valora más a alguien que sabe qué le falta que a alguien que lo niega.

---

## 12. Anexos

### A. Checklist P0 (para imprimir o copiar)

- [ ] Autenticación real del elector.
- [ ] Login real de administrador.
- [ ] Sin tokens hardcodeados.
- [ ] Censo y auditoría protegidos.
- [ ] Validación server-side del candidato.
- [ ] Capas de seguridad decididas por el servidor.
- [ ] Voto atómico y persistente.
- [ ] Sin documento en la auditoría de emisión.
- [ ] HTML escapado y CSP.
- [ ] Tests aislados con base temporal.
- [ ] Documentación corregida.
- [ ] `python3 -m src.main` como comando oficial.

### B. Comandos útiles

```bash
# Activar entorno
source venv/bin/activate

# Ejecutar la app
python3 -m src.main

# Tests
pytest -q

# Tests con cobertura
pytest --cov=src --cov-report=term-missing

# Lint (cuando lo agregues)
ruff check .
ruff format .

# Tipos (cuando lo agregues)
mypy src

# Auditoría de dependencias
pip-audit
```

### C. Estructura objetivo (gradual)

```text
src/
  core/
    config.py
    logging.py
    database.py
  domain/
    election.py
    ballot.py
    voter.py
    tally.py
  application/
    vote_service.py
    tally_service.py
    census_service.py
    election_service.py
  infrastructure/
    repositories/
    crypto/
    transmission/
  presentation/
    api.py
    templates/
```

### D. Lecturas y temas para aprender antes de la nube

- **Autenticación:** OWASP Authentication Cheat Sheet, OIDC, cookies `HttpOnly`, Argon2.
- **Autorización:** RBAC, principio de menor privilegio.
- **Seguridad web:** OWASP Top 10, CSP, CSRF, XSS.
- **Bases de datos:** transacciones, aislamiento, migraciones, backups.
- **Criptografía aplicada:** firmas Ed25519, HMAC, Merkle trees, gestión de claves.
- **Sistemas electorales:** end-to-end verifiability, risk-limiting audits, threat models.
- **Cloud:** 12-factor app, Docker, reverse proxy, TLS, secrets manager, observabilidad.
- **Operación:** logging, métricas, alertas, incident response, restore drills.

### E. Frases para recordar

- “Un patrón que no resuelve un problema real es decoración.”
- “Local es un perímetro más pequeño, no un perímetro inexistente.”
- “La nube no arregla una aplicación insegura; la expone más rápido.”
- “Si no puedes verificar el resultado, no tienes un sistema electoral; tienes una encuesta.”
- “No organices el código por patrón; organízalo por dominio.”
- “Primero el invariante, después la pantalla.”

---

**Fin del documento.**
