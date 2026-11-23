"""Utilidades compartidas por las pruebas de integración."""
from __future__ import annotations


def reset_and_open(admin_client):
    """Deja la jornada nacional limpia y abierta."""
    reset = admin_client.post("/api/admin/reset-election")
    assert reset.status_code == 200, reset.text
    opened = admin_client.post("/api/election/open")
    assert opened.status_code == 200, opened.text
