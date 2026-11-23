# ADR-004 — Catálogo de candidatos administrable y congelado

**Estado:** aceptado.

## Contexto

La configuración de la jornada exige registrar candidatos y opciones. La versión
anterior los tenía hardcodeados en `main.py`; no había forma de administrarlos ni
de garantizar que la papeleta se congelara antes de votar.

## Decisión

- Los candidatos viven en la tabla `candidates`, por modalidad electoral.
- El administrador puede crearlos, editarlos y activarlos/desactivarlos desde el
  panel.
- No se permite editar la papeleta si la jornada está `OPEN` o `TALLIED`, ni en
  `CLOSED` si ya hay votos.
- No se borra un candidato: se desactiva. La papeleta guarda `selection`, así que
  el histórico sigue siendo legible.
- Abrir la urna exige al menos dos candidatos activos.
- El pool Flyweight se refresca después de cada cambio para que el tarjetón y la
  validación usen la misma ficha.

## Consecuencias

- La configuración queda cubierta con una operación real, no con datos de código.
- La lista oficial se puede congelar y auditar; cada cambio deja un evento.
- En una elección real, la carga debería venir de la autoridad electoral y no de
  un CRUD manual; el panel es la versión local de esa responsabilidad.
