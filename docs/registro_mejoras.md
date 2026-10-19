# Registro de Mejoras y Ajustes del Sistema

Historial consolidado de mejoras estéticas, operativas y arquitectónicas implementadas en la plataforma de votación electrónica.

---

## 1. Requerimientos de Documentación y Pruebas
- [x] **Diagramas UML por cada patrón:** Incorporados formalmente con diagramas Mermaid en los documentos de los avances 1 al 8 para los 12 patrones (5 creacionales y 7 estructurales).
- [x] **Instrucciones completas de ejecución:** Detalladas en el `README.md` (configuración del entorno virtual, dependencias, Uvicorn/FastAPI y pruebas automatizadas).
- [x] **Pruebas y evidencias de funcionamiento:** Suite automatizada de 18 pruebas unitarias y de integración pasando al 100%, con base de test separada y 86% de cobertura de líneas.

---

## 2. Mejoras Estéticas y de Experiencia de Usuario (Inspiradas en la Urna Electrónica de Brasil)
- [x] **Encabezado fijo sin cortes:** Resuelto problema de corte de cabecera al hacer scroll o recargar página mediante fijación `sticky top-0 z-50` y normalización de márgenes en `dashboard.html`, `admin.html` e `index.html`.
- [x] **Cabina limpia y realista:** Remoción de términos internos o nombres de patrones entre paréntesis (`adapter`, `decorator`, etc.) y retiro de cédulas de prueba visibles en pantalla para ofrecer una experiencia de usuario real.
- [x] **Retroalimentación visual de Voto en Blanco:** Implementación de borde sólido de alto contraste, casilla marcada y etiqueta destacada de confirmación al seleccionar la opción en blanco.
- [x] **Limpieza del censo:** Remoción de campos innecesarios (como profesiones) en el censo, conservando nombres legales reales de ciudadanos y estudiantes.
- [x] **Aislamiento estricto de vistas por perfil:**
  - El elector, al pulsar *"Ver Resultados en Vivo"*, solo accede a gráficos y estadísticas públicas en `/dashboard` sin opciones administrativas.
  - Los controles sensibles (apertura/cierre de urnas, generación de actas de escrutinio, conmutación de tipo de elección y gestión del censo) quedaron aislados exclusivamente en el panel administrativo protegido `/admin`.
---

## 3. Escrutinio y Transmisión de Resultados en Vivo
- [x] **Consolidación en tiempo real desde la urna digital anónima:**
  - El endpoint `/api/dashboard` ahora provee el desglose exacto de sufragios por candidato (`votes_by_candidate_id`, `votes_by_candidate_name`), votos en blanco y votos nulos directamente desde la urna desacoplada.
  - Se corrigió `dashboard.html` para consumir directamente las métricas de la urna, eliminando la dependencia de la bitácora de auditoría y garantizando el secreto del sufragio.
  - Suite de 18 pruebas automatizadas pasando al 100%, con base de test separada y 86% de cobertura de líneas.

---

## 4. Iteración de endurecimiento local (estado actual)

- [x] **Autenticación básica de elector:** documento + PIN de demostración (`1234`), validado contra el censo.
- [x] **Login de administrador:** cuenta única, cookie `HttpOnly` firmada y rutas administrativas protegidas.
- [x] **Persistencia de la urna:** `voter_participation` y `ballot_records` en SQLite; el voto sobrevive a un reinicio.
- [x] **Voto atómico:** restricción única de participación y transacción; prueba de concurrencia con un solo ganador.
- [x] **Validación server-side:** el cliente solo envía `candidate_id`; el servidor resuelve nombre/partido y aplica siempre las capas de seguridad.
- [x] **Reset de jornada:** borra votos y participaciones de la elección activa, conserva el censo y no permite borrar votos individuales.
- [x] **Corrección de XSS:** el panel escapa los datos dinámicos y ya no incrusta el token en el JavaScript.
- [x] **Censo y auditoría protegidos:** requieren sesión de administrador.
- [x] **Dashboard corregido:** cuenta votos por `candidate_id` y calcula participación sobre electores habilitados.
- [x] **Documentación:** referencias externas eliminadas, README sintetizado, manual de uso con capturas y guía personal en `docs/avances/`.

## 5. Nuevas mejoras
- [ ] El estado de la urna o cabina de votación cuando desde el panel de admin le di cerrar en la cabina decia urna abierta. Pero en el dash si salia urna cerrada, también cambia el botón del dashboard o de los votos en vivo donde dice Emitir un Voto en Cabina, para que salga también tipo rojo y que no deje por que se cerró, o algo por el estilo, o sea, en conclusión que tengas mas control sobre cuando se cierra la urna.
- [ ] Requiere trabajo que se hagan actualizaciones en vivo? puede traer alguna desventaja? poque estaba mirando y aparte de que no se actualiza la urna en el punto anterior el titulo tampoco lo hace cuando cambio de CNE a UDI. Igual al bitacora y demás "eventos" que deban actualizarse por si solas sin darle en actualizar.

---

## 5. Próximas mejoras (roadmap funcional)

Esta sección es una lista de ideas para después de la entrega actual. Está ordenada por impacto y por dependencia técnica, no por dificultad.

### 5.1 Prioridad 1: resultados por mesa y participación

Hoy el voto **no guarda la mesa**. Para poder filtrar por mesa, mostrar cuántas mesas han votado o saber qué candidato ganó en cada mesa, primero hay que agregar `station_id` (y opcionalmente `terminal_id`) a `ballot_records`.

Con eso se puede construir:

- **Participación por mesa:** votos emitidos / electores habilitados de esa mesa.
- **Mesas que ya reportaron:** cuántas mesas tienen al menos un voto.
- **Ganador por mesa:** candidato más votado en cada mesa.
- **Filtros del dashboard:** por modalidad, zona, mesa y candidato.
- **Tabla de detalle por mesa:** votos, blanco, participación y ganador.
- **Gráficas:** barras por mesa, barras apiladas por candidato y línea de avance de mesas.
- **Exportación:** CSV/PDF del detalle por mesa.

No se recomienda un mapa geográfico todavía: exigiría coordenadas, más usuarios y una capa de visualización que no aporta al objetivo actual. Un **heatmap de mesas** o un ranking por zona es más simple y más útil para la demo.

### 5.2 Prioridad 2: entidades y modelo relacional

El modelo actual es deliberadamente pequeño: censo, participación y papeletas. Para crecer sin repetir texto ni depender de valores hardcodeados, conviene normalizar:

| Tabla propuesta | Para qué |
|---|---|
| `institutions` | Universidad, Registraduría u otra entidad organizadora. |
| `elections` | Jornada concreta: título, tipo, estado, fecha de inicio/cierre. |
| `jurisdictions` | Árbol de país/departamento/puesto o sede/facultad. |
| `stations` | Mesas físicas, con jurisdicción, zona y terminal. |
| `contests` | Cargo o pregunta que se somete a votación. |
| `candidates` | Candidatos por contienda, con partido, color y orden en el tarjetón. |
| `voters` | Electores por institución y mesa. |
| `voter_participation` | Quién votó en cada elección. |
| `ballots` | Voto anónimo, con `station_id` y `contest_id`, sin documento. |
| `audit_events` | Eventos con actor, acción, fecha y hash encadenado. |
| `tally_reports` | Actas generadas, con payload y sello. |

La regla es: **normalizar solo lo que se va a consultar, filtrar o reutilizar**. Si se agregan tablas que nadie consulta, solo se suma complejidad. Cada tabla nueva implica claves foráneas, migraciones y datos de prueba.

### 5.3 Prioridad 3: experiencia de usuario

- **Dashboard con pestañas:** Resumen, Por mesa, Por candidato, Participación.
- **Filtros persistentes** en la URL para poder compartir una vista.
- **Actualización en vivo** con SSE o WebSocket en lugar de polling cada 5 segundos.
- **Exportar** resultados y actas a CSV/PDF.
- **Modo oscuro** opcional, si se mantiene el contraste.
- **Animaciones sutiles** en cambios de estado y carga de tarjetas, respetando `prefers-reduced-motion`.
- **Accesibilidad:** etiquetas, foco visible, contraste y navegación por teclado.
- **Móvil:** tablas con scroll horizontal y filtros colapsables.

### 5.4 Prioridad 4: auditoría y verificabilidad

- Persistir `audit_events` en SQLite con encadenamiento de hashes.
- Guardar `tally_reports` para consultar actas anteriores.
- Sustituir HMAC por firmas Ed25519 para el acta.
- Agregar verificación de recibo por parte del votante.
- Publicar una raíz de Merkle de papeletas y un verificador independiente.
- Documentar el threat model y el protocolo de verificación.

### 5.5 Lo que NO conviene hacer todavía

- Un mapa geográfico completo: mucho esfuerzo para poca información nueva.
- Microservicios o Kubernetes: el sistema es un monolito local y no lo necesita.
- Multiusuario simultáneo real: el estado de la jornada sigue siendo local.
- Datos personales reales: el simulador debe seguir usando datos sintéticos.
- Más patrones de diseño solo para “completar” el catálogo: primero deben resolver un problema real.

### 5.6 Orden recomendado

1. Agregar `station_id` al voto y resultados por mesa (impacto alto, cambio acotado).
2. Crear `elections` y `candidates` en base de datos para dejar de hardcodear.
3. Normalizar instituciones, jurisdicciones y mesas.
4. Persistir auditoría y actas.
5. Verificabilidad criptográfica.
6. Migrar a PostgreSQL y preparar despliegue.

---

## 6. Apariencia y experiencia (iteración actual)

- **Diseño más sobrio:** encabezados sólidos, tarjetas blancas, bordes suaves y una paleta azul marino + acento.
- **Menos apretado:** más espaciado vertical, padding consistente y jerarquía tipográfica más clara.
- **Responsive:** cabina en una columna en móvil, stepper compacto, cabeceras con acciones que se envuelven y tablas con scroll horizontal.
- **Animaciones sutiles:** entrada de tarjetas, hover con elevación mínima, transiciones en botones e iconos y respeto por `prefers-reduced-motion`.
- **Notificaciones:** toasts en lugar de `alert()` para las acciones administrativas y los errores del voto.
- **Estados más claros:** la urna muestra “Abierta”, “Cerrada” o “Cerrada y escrutada”; el botón cambia entre “Abrir urna”, “Cerrar urna” y “Jornada escrutada”.
- **Evidencias:** capturas de cabina, login, móvil y panel administrativo en `avances/capturas/`.
