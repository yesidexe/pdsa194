# ADR-001 — Local-first, sin despliegue en la nube

**Estado:** aceptado.

## Contexto

La plataforma es una aplicación de votación electrónica local-first en desarrollo.
No está certificada para elecciones reales, usa datos sintéticos y su modelo de
amenaza todavía no cubre una exposición pública.

## Decisión

La aplicación se ejecuta y opera en local. No se publica en un dominio ni
se despliega en un proveedor cloud. La arquitectura se mantiene "cloud-ready"
(configuración por entorno, migraciones, health checks, logs y backups), pero sin
operar infraestructura pública.

## Consecuencias

- Menor superficie de ataque y menos requisitos legales y operativos.
- La operación local depende del equipo donde se ejecute; el runbook y los
  backups son obligatorios.
- Si se despliega en el futuro, será un monolito modular con HTTPS, PostgreSQL,
  backups y monitoreo; no microservicios ni Kubernetes para este dominio.
