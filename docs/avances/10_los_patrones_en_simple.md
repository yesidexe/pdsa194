# Los 12 patrones explicados en simple

> Documento personal de estudio.
> No memorices diagramas: entiende **qué problema resuelve cada patrón** y **dónde vive en el código**.

---

## 0. Cómo leer esto

Cada patrón tiene la misma estructura:

1. **Problema de la vida real.**
2. **Idea del patrón.**
3. **Dónde está en el proyecto.**
4. **Cómo funciona, paso a paso.**
5. **Por qué se eligió.**
6. **Límite o crítica honesta.**
7. **Frase para exponerlo en un minuto.**

No todos los patrones aportan lo mismo. Al final hay una tabla con el veredicto de cada uno.

---

## 1. Singleton — una sola configuración para toda la jornada

**Problema de la vida real:** si cada módulo tuviera su propia copia del estado de la urna, uno podría creer que está abierta y otro que está cerrada.

**Idea:** garantizar una única instancia de la configuración y un punto de acceso común.

**Dónde está:** `src/core/config.py`, clase `ElectoralConfigManager`.

**Cómo funciona:**
- `__new__` crea la instancia solo si no existe.
- `_lock` evita que dos hilos la creen a la vez.
- `_initialized` evita que una segunda llamada sobrescriba los datos.
- `open_voting` y `close_voting` cambian el estado de la urna.

**Por qué se eligió:** la jornada tiene un estado global (abierta/cerrada) y una configuración común (institución, título, límite de votos).

**Límite honesto:** el Singleton crea estado global y acopla los tests. Además, impide tener dos elecciones realmente simultáneas en el mismo proceso. En una versión futura conviene inyectar un objeto `Settings` o un `ElectionContext` en lugar de usar una instancia global.

**Frase para exponer:**
> “Singleton garantiza que todos los módulos vean la misma configuración de la jornada; lo usamos para el estado de la urna, pero reconocemos que es un estado global y que una arquitectura multiproceso necesitaría otra solución.”

---

## 2. Factory Method — cada tipo de papeleta tiene su creador

**Problema de la vida real:** si el código hiciera `if tipo == candidato: ... elif tipo == blanco: ...`, cada nuevo tipo de voto obligaría a modificar la lógica central.

**Idea:** definir un creador abstracto y dejar que cada subclase decida qué papeleta construir.

**Dónde está:** `src/modules/voting/ballot_factory.py`.

**Cómo funciona:**
- `Ballot` es el producto abstracto.
- `CandidateBallot`, `ReferendumBallot` y `BlankBallot` son productos concretos.
- `BallotCreator` declara `create_ballot`.
- `CandidateBallotCreator`, `ReferendumBallotCreator` y `BlankBallotCreator` crean su producto.
- `issue_ballot` usa el producto sin conocer la clase concreta.

**Por qué se eligió:** agregar un nuevo tipo de voto no debería tocar la cabina ni el conteo; solo se agrega un creador y un producto.

**Límite honesto:** en la interfaz solo se usan candidato y blanco; el referendo existe en el dominio pero no tiene pantalla. Es un punto de extensión real, no una necesidad urgente de la demo.

**Frase para exponer:**
> “Factory Method separa la creación de la papeleta de su uso. Si mañana agregamos voto nulo o voto por lista, creamos un creador nuevo y no tocamos la cabina.”

---

## 3. Abstract Factory — familias coherentes de elección

**Problema de la vida real:** una elección nacional y una universitaria no solo cambian el título: cambian el tipo de documento, el encabezado y la regla de escrutinio. Si se mezclan piezas, el sistema queda incoherente.

**Idea:** una fábrica abstracta produce una familia completa de objetos relacionados.

**Dónde está:** `src/modules/election/election_factory.py`.

**Cómo funciona:**
- `ElectoralFamilyFactory` declara `create_validator`, `create_header` y `create_tally_rule`.
- `NationalElectionFactory` produce validador de cédula, encabezado de la República y mayoría absoluta.
- `UniversityElectionFactory` produce validador de carnet, encabezado de la universidad y mayoría simple.

**Por qué se eligió:** garantiza que todos los componentes de una modalidad pertenezcan a la misma familia.

**Límite honesto:** con solo dos familias y productos pequeños, también se podría resolver con una configuración y Strategy. Se mantiene porque ya está implementado y porque una tercera modalidad real lo justificaría.

**Frase para exponer:**
> “Abstract Factory no crea un objeto: crea una familia coherente. Si cambiamos de Nacional a Universitaria, cambian el validador, el membrete y la regla de escrutinio al mismo tiempo.”

---

## 4. Builder — construir el acta paso a paso

**Problema de la vida real:** un acta tiene título, jurisdicción, mesas, votos, firmas, veredicto y sello. Un constructor con diez parámetros es difícil de leer y de usar sin equivocarse.

**Idea:** construir el objeto complejo por pasos, con métodos encadenables, y devolverlo al final.

**Dónde está:** `src/modules/tally/report_builder.py`.

**Cómo funciona:**
- `TallyReportBuilder` declara los pasos.
- `OfficialTallyReportBuilder` guarda el estado parcial.
- `set_header`, `add_table_batch`, `set_votes`, `add_officer_signature` y `set_winner_verdict` devuelven el builder.
- `build` calcula el total y genera el hash SHA-256.

**Por qué se eligió:** el acta es el objeto más complejo del sistema y debe quedar consolidada y con campos protegidos una vez construida.

**Límite honesto:** el `TallyReportDirector` existe pero no se usa; el flujo real llama al builder directamente. Se puede eliminar o usar para un boletín preliminar.

**Frase para exponer:**
> “Builder evita el constructor telescópico: armamos el acta por partes y al final la sellamos con SHA-256.”

---

## 5. Prototype — clonar mesas de votación

**Problema de la vida real:** crear muchas mesas parecidas desde cero obliga a repetir configuración y puede mezclar listas de jurados.

**Idea:** tener una plantilla y clonarla con copia profunda.

**Dónde está:** `src/modules/election/station_prototype.py`.

**Cómo funciona:**
- `VotingStation` implementa `clone` con `copy.deepcopy`.
- `StationPrototypeRegistry` guarda plantillas por clave.
- `spawn_station` clona la plantilla y le asigna nuevo ID, terminal y jurados.

**Por qué se eligió:** la copia profunda evita que dos mesas compartan la misma lista mutable de jurados o de tipos de papeleta.

**Límite honesto:** en la demo solo se clonan dos mesas al arrancar. Una función de configuración haría lo mismo. El patrón se justifica cuando el usuario puede crear plantillas y clonarlas desde la interfaz.

**Frase para exponer:**
> “Prototype nos permite partir de una mesa configurada y clonarla sin compartir listas mutables; hoy se usa al arrancar, y sería más valioso con un gestor de plantillas.”

---

## 6. Adapter — traducir censos de distintos formatos

**Problema de la vida real:** la Registraduría entrega CSV, la universidad entrega JSON y el sistema local usa SQLite. El dominio no debería llenarse de `if` para cada formato.

**Idea:** definir una interfaz común y envolver cada formato en un adaptador.

**Dónde está:** `src/modules/census/census_adapter.py`.

**Cómo funciona:**
- `ICensusRegistry` define el contrato: `is_eligible`, `get_voter_record`, `get_total_registered`, `get_total_eligible`, `authenticate`.
- `JsonCensusAdapter` y `CsvCensusAdapter` traducen archivos.
- `SqliteCensusAdapter` traduce la base local y además implementa la autenticación con PIN.

**Por qué se eligió:** la cabina habla con una interfaz, no con SQL. Cambiar la fuente no debería cambiar la cabina.

**Límite honesto:** el adaptador SQLite también escribe (registrar, habilitar), así que mezcla lectura y administración. En una versión futura conviene separar `ICensusQuery` de `ICensusAdmin`.

**Frase para exponer:**
> “Adapter es un traductor: el sistema siempre habla el mismo idioma, sin importar si el censo viene en CSV, JSON o SQLite.”

---

## 7. Bridge — separar el boletín del canal de envío

**Problema de la vida real:** hay varios tipos de boletín (preliminar, alerta, cierre) y varios canales (consola, archivo, memoria). Si se combinaran por herencia, tendríamos una clase por cada combinación.

**Idea:** separar la abstracción (qué se envía) del implementador (cómo se envía).

**Dónde está:** `src/modules/transmission/bulletin_bridge.py`.

**Cómo funciona:**
- `ElectoralBulletin` guarda un `ITransmissionChannel`.
- `PreliminaryBulletin`, `AuditAlertBulletin` y `OfficialClosingBulletin` construyen el payload.
- `ConsoleTransmissionChannel`, `FileTransmissionChannel` y `MemoryAuditSinkTransmissionChannel` lo transportan.
- El canal se puede cambiar en tiempo de ejecución.

**Por qué se eligió:** permite agregar un canal (webhook, correo) sin tocar los tipos de boletín, y viceversa.

**Límite honesto:** en producción solo se usa la consola; archivo y memoria son de test. Si no se agrega un segundo canal real, un `Notifier` simple bastaría.

**Frase para exponer:**
> “Bridge evita la explosión combinatoria: el boletín no sabe si sale por consola o por archivo; solo pide a su canal que lo envíe.”

---

## 8. Composite — árbol de jurisdicciones y mesas

**Problema de la vida real:** un país tiene departamentos, un departamento tiene puestos y un puesto tiene mesas. Contar mesas no debería requerir un `if` distinto para cada nivel.

**Idea:** tratar una hoja y un grupo de hojas con la misma interfaz.

**Dónde está:** `src/modules/election/jurisdiction_composite.py`.

**Cómo funciona:**
- `ElectoralUnit` declara `count_stations`, `get_station_ids`, `display_hierarchy` y `find_unit`.
- `VotingStationLeaf` representa una mesa.
- `ElectoralJurisdictionComposite` contiene hijos y propaga las operaciones recursivamente.

**Por qué se eligió:** el mapa electoral es naturalmente un árbol y el acta necesita listar las mesas.

**Límite honesto:** hoy el Composite solo cuenta mesas y lista IDs; el voto no guarda `station_id`, así que no hay resultados por mesa. Se conectaría de verdad cuando el escrutinio sea por mesa.

**Frase para exponer:**
> “Composite trata igual una mesa y un país entero: si pido cuántas mesas hay, cada nivel responde sumando a sus hijos.”

---

## 9. Decorator — capas de seguridad sobre el voto

**Problema de la vida real:** un voto puede necesitar timestamp, firma y marca de agua. Si se crearan subclases para cada combinación, tendríamos `2^n` clases.

**Idea:** envolver el objeto base con capas que agregan comportamiento sin modificar la clase original.

**Dónde está:** `src/modules/voting/ballot_decorator.py`.

**Cómo funciona:**
- `BallotSecurityDecorator` implementa `Ballot` y envuelve otro `Ballot`.
- `TimestampSecurityDecorator` agrega el sello de tiempo.
- `DigitalSignatureDecorator` agrega el HMAC.
- `AuditWatermarkDecorator` agrega marca de agua y código de recibo.
- `get_security_metadata` acumula los metadatos de todas las capas.

**Por qué se eligió:** es el ejemplo más claro de composición sobre herencia. Cada capa se puede aplicar en cualquier orden.

**Límite honesto:** HMAC no es una firma digital asimétrica; sirve para detectar alteraciones, no para no repudio. Además, las capas las decide el servidor, no el cliente.

**Frase para exponer:**
> “Decorator envuelve el voto como una cebolla: cada capa agrega un sello y el objeto sigue siendo un voto.”

---

## 10. Facade — una puerta de entrada al subsistema

**Problema de la vida real:** la API necesitaría crear fábricas, adaptadores, decoradores y builders en cada endpoint. Eso acopla la presentación a los detalles internos.

**Idea:** ofrecer métodos de alto nivel que coordinen el subsistema.

**Dónde está:** `src/modules/facade/voting_facade.py`.

**Cómo funciona:**
- `setup_environment` recibe censo, familia, canal y árbol.
- `verify_voter` valida documento + PIN y voto único.
- `cast_secure_vote` valida candidato, decora y persiste.
- `close_and_generate_tally` cierra, cuenta y construye el acta.
- `get_dashboard_summary` arma los agregados.

**Por qué se eligió:** la API y la interfaz web no deberían conocer los detalles de creación y conteo.

**Límite honesto:** la fachada actual hace mucho (votación, conteo, dashboard, transmisión). En una versión futura se puede dividir en servicios más pequeños.

**Frase para exponer:**
> “Facade es la recepción del edificio: el cliente pide una operación y la fachada coordina a todos los especialistas.”

---

## 11. Flyweight — compartir datos de candidatos

**Problema de la vida real:** si cada voto guardara una copia completa de la ficha del candidato, se repetiría mucha información.

**Idea:** compartir el estado intrínseco (lo común) y guardar aparte el estado extrínseco (lo único de cada voto).

**Dónde está:** `src/modules/voting/candidate_flyweight.py`.

**Cómo funciona:**
- `CandidateMetadataFlyweight` es inmutable y contiene ID, nombre, partido, lema y color.
- `CandidateFlyweightFactory` devuelve la misma instancia para el mismo `candidate_id`.
- La papeleta guarda `candidate_id`; el nombre y el partido se resuelven desde el catálogo.

**Por qué se eligió:** el catálogo alimenta el tarjetón y la validación server-side sin duplicar la ficha en cada papeleta.

**Límite honesto:** con 4 candidatos el ahorro de memoria es irrelevante. El patrón se vuelve valioso en un catálogo grande o si se cachean objetos pesados. En esta versión es más una demostración de diseño que una optimización necesaria.

**Frase para exponer:**
> “Flyweight comparte lo que no cambia: la ficha del candidato se guarda una vez y cada voto solo referencia su ID.”

---

## 12. Proxy — un guardia delante de las operaciones sensibles

**Problema de la vida real:** abrir la urna, cerrarla o generar el acta no puede hacerlo cualquiera. Si esas comprobaciones se repitieran en cada endpoint, el código se ensuciaría.

**Idea:** un sustituto que intercepta la operación, valida permisos, audita y delega.

**Dónde está:** `src/modules/security/access_proxy.py`.

**Cómo funciona:**
- `ElectoralAccessProxy` envuelve la fachada.
- `open_polls`, `close_polls`, `close_and_generate_tally` y `reset_election` exigen rol de administrador o jurado según corresponda.
- Cada intento se registra en la bitácora.
- Si el permiso falla, lanza `PermissionError`.

**Por qué se eligió:** centraliza la protección y la auditoría en un solo lugar.

**Límite honesto:** el Proxy confía en el rol de la `UserSession`; la autenticación real (contraseña y cookie) vive en `presentation/auth.py`. La bitácora está en memoria, no es persistente ni inmutable.

**Frase para exponer:**
> “Proxy es el guardia de la puerta: revisa el permiso, deja registro y solo entonces deja pasar la operación.”

---

## 13. Cómo se conectan los patrones (historia de 30 segundos)

1. El **Proxy** protege la operación.
2. La **Fachada** coordina el caso de uso.
3. El **Adapter** valida el censo.
4. La **Abstract Factory** elige la familia de la elección.
5. El **Factory Method** crea la papeleta.
6. El **Decorator** la sella.
7. El **Flyweight** aporta el catálogo de candidatos.
8. La **Restricción única** de la base garantiza un voto por elector.
9. El **Builder** arma el acta.
10. El **Bridge** transmite el boletín.
11. El **Composite** organiza las mesas.
12. El **Singleton** mantiene la configuración de la jornada.

No es una lista de patrones sueltos: es un flujo.

---

## 14. Veredicto honesto de cada patrón

| Patrón | ¿Aporta hoy? | Decisión |
|---|---|---|
| Singleton | Como idea de configuración, sí; como patrón global, no | Simplificar en el futuro |
| Factory Method | Sí | Mantener |
| Abstract Factory | Condicional | Mantener si crecen las familias |
| Builder | Sí | Mantener |
| Prototype | No hoy | Mantener solo si hay plantillas configurables |
| Adapter | Sí | Mantener |
| Bridge | Condicional | Mantener si hay 2+ canales reales |
| Composite | Condicional | Conectar al escrutinio por mesa |
| Decorator | Sí | Mantener |
| Facade | Sí, pero delgada | Refactorizar en el futuro |
| Flyweight | No por memoria; sí como catálogo | Mantener como catálogo, no como optimización |
| Proxy | Sí | Mantener |

---

## 15. Preguntas que te pueden hacer

**¿Por qué usaste Singleton?**
> Para que todos los módulos vean el mismo estado de la jornada. Es cómodo para una demo local; en producción habría que usar configuración inyectada o un estado compartido en base de datos.

**¿Por qué no usaste una base de datos para los votos desde el principio?**
> Porque el prototipo empezó en memoria para aprender los patrones. En esta iteración lo corregimos: la urna y la participación ya viven en SQLite.

**¿HMAC es una firma digital?**
> No. HMAC es un sello con clave compartida que detecta alteraciones. Una firma digital asimétrica, como Ed25519, permitiría verificar sin compartir la clave privada. HMAC se usa aquí con fines de aprendizaje.

**¿El administrador puede saber qué votó cada persona?**
> No en el modelo actual: la tabla de participación y la tabla de papeletas no se pueden unir. El administrador ve el censo, la participación y los agregados, pero no la relación entre identidad y voto.

**¿Qué pasa si dos personas votan al mismo tiempo con el mismo documento?**
> La restricción única de la base permite solo una participación. La otra petición recibe `409 Conflict`. Lo probamos con peticiones concurrentes.

**¿Por qué hay patrones que no se usan en la interfaz?**
> Porque el proyecto busca ser extensible. Algunos son puntos de extensión (Prototype, Bridge, Composite) y otros son demostraciones (Flyweight). La documentación distingue entre lo que está integrado y lo que es potencial.

**¿Qué falta para producción?**
> Autenticación fuerte, persistencia de la auditoría, firmas asimétricas, verificación pública, HTTPS, PostgreSQL, backups, monitoreo y un análisis legal. Este es un simulador local, no un sistema certificado.