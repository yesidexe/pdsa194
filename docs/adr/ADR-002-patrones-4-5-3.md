# ADR-002 — Doce patrones, cuatro/cinco/tres

**Estado:** aceptado.

## Contexto

La primera versión concentraba 5 patrones creacionales, 7 estructurales y 0 de
comportamiento. El estado de la jornada, la validación del elector y la auditoría
estaban dentro de la fachada y del Proxy, no como colaboradores explícitos. Esa
distribución no representaba las responsabilidades reales del dominio.

## Decisión

El portafolio queda en **12 patrones: 4 creacionales, 5 estructurales y 3 de
comportamiento**.

- Se retiran **Prototype** (solo dos mesas fijas), **Bridge** (un solo canal real)
  y **Composite** (el voto no guarda `station_id`, no hay resultados por mesa).
- Se agregan **State** (ciclo de vida persistente), **Chain of Responsibility**
  (cinco validaciones del elector) y **Observer** (auditoría a varios sumideros).
- **Strategy** no se duplica: `TallyRule` ya es una familia de algoritmos.

## Consecuencias

- El catálogo refleja responsabilidades del producto, no una cuota de patrones.
- Los patrones retirados se documentan como evaluados y descartados, con el
  motivo y la condición que los haría volver.
- El código baja en complejidad accidental; el comportamiento visible se conserva.
