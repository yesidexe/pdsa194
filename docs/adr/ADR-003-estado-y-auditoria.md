# ADR-003 — Estado de la jornada y auditoría persistentes

**Estado:** aceptado.

## Contexto

`is_open` vivía en memoria y `is_tallied` en SQLite. La bitácora del Proxy era una
lista en memoria que se perdía al reiniciar, y el acta se devolvía una sola vez
sin persistirse.

## Decisión

- El estado de la jornada se guarda en `election_state.status` con cuatro estados:
  `DRAFT`, `OPEN`, `CLOSED`, `TALLIED`.
- La auditoría se guarda en `audit_events`, append-only, con `prev_hash` y
  `event_hash` (SHA-256). La verificación recalcula la cadena.
- El acta se persiste en `tally_reports`, con su payload y hash, y se puede
  consultar y descargar en JSON/CSV.
- La migración mínima de SQLite agrega `status` a bases existentes y conserva el
  histórico. La migración formal con Alembic queda pendiente.

## Consecuencias

- La jornada no puede reabrirse después del acta sin un reset explícito.
- La auditoría sobrevive al reinicio y detecta alteraciones, pero no es un WORM
  ni una firma asimétrica: un administrador con acceso a la base puede reescribir
  la cadena completa. Se documenta como límite.
- El reset deja la jornada en `DRAFT`; el administrador debe abrirla de nuevo.
