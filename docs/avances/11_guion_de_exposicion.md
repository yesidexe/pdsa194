# Guion de exposición y demostración

> Documento personal. La idea es que puedas exponer sin leer, entendiendo el hilo.
> Duración objetivo: 10–15 minutos + preguntas.

---

## 1. Antes de empezar (checklist de 2 minutos)

- [ ] Servidor corriendo con `python3 -m src.main`.
- [ ] Base de demostración con censo y votos: `./venv/bin/python scripts/cast_demo_votes.py`.
- [ ] Navegador en `http://127.0.0.1:8000/`.
- [ ] Pestañas abiertas: cabina, dashboard, `/admin/login`.
- [ ] Saber el usuario `admin` y la contraseña de `.env`.
- [ ] Saber un documento y el PIN `1234`.
- [ ] Tener a mano el documento de este guion.

Si algo falla, no improvises una disculpa larga: di “lo reviso mientras seguimos” y continúa con la explicación conceptual.

---

## 2. Guion en 6 bloques

### Bloque 1 — Qué es y qué problema resuelve (1–2 min)

**Frase de apertura:**

> “Esto es un simulador local de votación electrónica. Permite identificar a un elector con documento y PIN, emitir un voto anónimo, sellarlo, guardarlo en una urna persistente y generar un acta de escrutinio. No es un sistema electoral certificado: es un laboratorio para aprender arquitectura, patrones y seguridad.”

**Problema:**

- Un sistema electoral debe cumplir dos cosas a la vez: **secreto del voto** e **integridad del resultado**.
- La mayoría de los CRUD no tienen ese conflicto. Aquí sí: si guardas “quién votó qué”, rompes el secreto; si no guardas nada, no puedes auditar.

**Qué muestra la demo:**

- Identificación con PIN.
- Voto validado por el servidor.
- Papeleta sellada.
- Persistencia en SQLite.
- Panel administrativo protegido.
- Reset de jornada sin borrar el censo.

---

### Bloque 2 — El recorrido de un voto (3–4 min)

**Mientras navegas, narra:**

1. **Identificación:** “El elector escribe su documento y el PIN de demostración. El sistema valida que exista en el censo, que esté habilitado y que no haya votado.”
2. **Tarjetón:** “El cliente solo envía el identificador del candidato. El nombre y el partido los resuelve el servidor desde el catálogo oficial.”
3. **Sellado:** “La papeleta se envuelve con tres capas: sello de tiempo, sello HMAC y marca de agua.”
4. **Persistencia:** “La participación y la papeleta se guardan en la misma transacción. La restricción única de participación impide el doble voto.”
5. **Comprobante:** “El elector recibe un código de recibo y el ID anónimo de su papeleta. El comprobante no lleva su documento.”
6. **Dashboard:** “El dashboard lee solo los agregados de la tabla de papeletas: no puede unir identidad con voto.”

**Punto clave para decir:**

> “La decisión más importante del diseño es separar la tabla de participación de la tabla de papeletas. Una sabe quién votó; la otra sabe qué se votó; no hay una clave que las una.”

---

### Bloque 3 — El panel administrativo (2 min)

**Muestra el login y explica:**

- Una sola cuenta local.
- La sesión se guarda en una cookie `HttpOnly`.
- El JavaScript del panel no ve el token.
- `/admin` redirige al login si no hay sesión.
- Censo, auditoría y control de urna exigen la misma cookie.

**Muestra, si el tiempo lo permite:**

- Censo con 41 electores por modalidad.
- Diferencia entre **Cerrar urna** (bloquea votos) y **Generar acta** (cierra, cuenta y sella).
- Botón **Reiniciar jornada**: borra votos y participaciones, conserva el censo. **No** borra el voto de una persona concreta, porque eso rompería el secreto.
- Generación del acta con sello SHA-256.

**Punto clave:**

> “El administrador puede ver quién votó y qué se votó por separado, pero no puede ver ‘Juan votó por X’. Esa separación es deliberada.”

---

### Bloque 4 — Los patrones (3–4 min)

No expliques los 12 en detalle. Agrupa por problema:

**Creacionales:**

- **Singleton:** una configuración única de la jornada.
- **Factory Method:** cada tipo de papeleta tiene su creador.
- **Abstract Factory:** familias coherentes Nacional/Universitaria.
- **Builder:** el acta se arma paso a paso y se sella.
- **Prototype:** clonar mesas con copia profunda.

**Estructurales:**

- **Adapter:** el censo puede venir de SQLite, JSON o CSV.
- **Bridge:** el boletín se separa del canal de envío.
- **Composite:** país → departamento → puesto → mesa.
- **Decorator:** capas de seguridad sobre el voto.
- **Facade:** una puerta de entrada al subsistema.
- **Flyweight:** catálogo compartido de candidatos.
- **Proxy:** guardia de las operaciones administrativas.

**Frase de cierre del bloque:**

> “No los usé para llenar el diagrama. Algunos son claramente necesarios, como Factory Method, Builder, Adapter, Decorator y Proxy. Otros son puntos de extensión o demostraciones, como Prototype, Bridge, Composite y Flyweight. La documentación dice honestamente cuáles aportan hoy y cuáles se justifican a futuro.”

---

### Bloque 5 — Decisiones y límites (2 min)

**Decisiones:**

- Local-first: `python3 -m src.main`, `127.0.0.1`, un solo worker.
- Datos sintéticos.
- HMAC para aprender integridad, no como firma digital definitiva.
- Una elección activa a la vez.
- SQLite por simplicidad; PostgreSQL para producción.

**Límites honestos:**

- La autenticación del elector es básica (documento + PIN de demo).
- La bitácora está en memoria; se pierde al reiniciar.
- HMAC no es firma asimétrica ni no repudio.
- No hay verificación pública del recibo ni árbol de Merkle.
- No hay HTTPS, backups automáticos ni observabilidad de producción.
- No está certificado para elecciones reales.

**Frase:**

> “Prefiero decir con claridad qué no es. Es un simulador local con una arquitectura seria; no un sistema electoral listo para una elección real.”

---

### Bloque 6 — Cierre (1 min)

**Frase final:**

> “El proyecto me sirvió para entender que un sistema electoral no se diseña desde la pantalla, sino desde los invariantes: un elector vota una vez, el voto no se altera, el secreto se respeta y el resultado se puede auditar. La siguiente etapa es endurecer autenticación, persistir la auditoría y agregar verificación criptográfica.”

---

## 3. Demostración paso a paso

### 3.1 Cabina

1. Abrir `http://127.0.0.1:8000/`.
2. Escribir `10203040` y PIN `1234`.
3. Pulsar **Verificar elector**.
4. Elegir un candidato.
5. Pulsar **Confirmar y emitir sufragio**.
6. Mostrar el comprobante.

**Qué decir mientras carga:** “El sistema valida censo, PIN, estado de la urna y voto único.”

### 3.2 Segundo intento

1. Volver a la cabina.
2. Usar el mismo documento y PIN.
3. Mostrar el mensaje de rechazo.

**Qué decir:** “La restricción única de participación impide el doble voto. Si dos peticiones llegan al mismo tiempo, solo una gana.”

### 3.3 Dashboard

1. Abrir `http://127.0.0.1:8000/dashboard`.
2. Mostrar estado de urna, sufragios, censo habilitado, participación y desglose.

**Qué decir:** “El dashboard no lee identidades; lee solo papeletas anónimas.”

### 3.4 Panel administrativo

1. Abrir `http://127.0.0.1:8000/admin`.
2. Mostrar la redirección al login.
3. Iniciar sesión.
4. Mostrar censo, control de urna, reset y acta.

**Qué decir:** “El acceso está protegido con cookie HttpOnly; no hay token en el JavaScript.”

### 3.5 Reinicio de jornada

1. Pulsar **Reiniciar jornada**.
2. Escribir `REINICIAR`.
3. Mostrar que el dashboard queda en 0 y el censo sigue.

**Qué decir:** “El reset borra todos los votos, no el voto de una persona. Así se puede probar de nuevo sin romper el secreto.”

---

## 4. Preguntas probables y respuestas cortas

**¿Por qué no usaste una base de datos desde el principio?**
> El prototipo empezó en memoria para aprender los patrones. En esta iteración la urna y la participación ya están en SQLite; el siguiente paso es persistir la auditoría y usar PostgreSQL si crece.

**¿Cómo garantizas un voto por persona?**
> Con una restricción única `(election_type, document_id)` en `voter_participation` y una transacción que guarda participación y papeleta juntas. Probamos el caso concurrente.

**¿Cómo garantizas el secreto?**
> Separando identidad y papeleta en dos tablas sin relación, y sin guardar el documento en la papeleta ni en el evento de emisión. El administrador no tiene una vista que las una.

**¿HMAC no es una firma digital?**
> Correcto. HMAC es un sello con clave compartida. Sirve para detectar alteraciones; no da no repudio. Para producción se usaría Ed25519 y un verificador público.

**¿Qué pasa si se cae el servidor?**
> Los votos y participaciones están en SQLite; sobreviven. La bitácora en memoria se pierde. El siguiente paso es persistirla.

**¿Qué pasa si hay varios workers?**
> El estado de la jornada está en el Singleton de cada proceso; por eso se ejecuta con un solo worker. Para múltiples workers habría que llevar el estado a la base o a Redis.

**¿Por qué el PIN es 1234?**
> Es una credencial de demostración para no depender de un proveedor externo. En producción sería OTP, SSO o verificación presencial.

**¿Por qué hay patrones que no se usan?**
> Porque algunos son puntos de extensión y otros son demostraciones. La documentación distingue entre lo integrado y lo potencial; no digo que todos sean imprescindibles.

**¿Qué mejorarías primero?**
> Persistir la auditoría, agregar verificación de recibo con firma asimétrica, autenticación más fuerte y migrar a PostgreSQL con backups.

**¿Esto está listo para una elección real?**
> No. Es un simulador local. Un sistema real requiere certificación, auditoría externa, verificación de extremo a extremo, seguridad operativa y cumplimiento legal.

---

## 5. Si algo falla durante la demo

| Falla | Qué hacer |
|---|---|
| El servidor no responde | Reiniciar `python3 -m src.main`; verificar el puerto 8000. |
| El dashboard está en 0 | Ejecutar el script de votos de demostración o votar en vivo. |
| El elector ya votó | Usar otro documento o reiniciar la jornada. |
| El panel redirige al login | Iniciar sesión de nuevo; la cookie pudo vencer. |
| El acta no se genera | Verificar que haya votos y que la sesión siga activa. |
| Error de base bloqueada | Reintentar; SQLite no está pensado para alta concurrencia. |

**Frase de contingencia:**

> “La demo local depende de un proceso y una base SQLite; si algo falla, sigo con la explicación de arquitectura y muestro el código o las capturas.”

---

## 6. Frases que conviene memorizar

- “El secreto no se arregla con un `if`; se arregla separando identidad y papeleta.”
- “Un patrón que no resuelve un problema real es decoración.”
- “El cliente elige el candidato; el servidor decide si es válido y cómo se sella.”
- “La restricción única es la última línea de defensa contra el doble voto.”
- “Esto es un simulador local con arquitectura seria, no un sistema certificado.”
- “Lo importante no es que tenga 12 patrones, sino que el flujo tenga invariantes claros.”

---

## 7. Cierre para dejar buena impresión

> “Si tuviera que resumir el aprendizaje: un sistema electoral se diseña desde los invariantes, no desde la interfaz. Los patrones ayudan a organizar el código, pero no reemplazan el análisis de seguridad. Este proyecto me dejó una base funcional y, sobre todo, un mapa claro de lo que falta para acercarse a un sistema real.”