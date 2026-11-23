"""Configuración común de pruebas.

Se usa una base SQLite separada (``test_e_voting.db``) para no contaminar la
base de demostración. Cada prueba arranca con la base recreada y el sistema
reconstruido, de modo que el orden de ejecución no altere el resultado.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEST_DB = ROOT / "test_e_voting.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["ADMIN_USER"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-admin"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["AUTO_OPEN_POLLS"] = "true"

for suffix in ("", "-wal", "-shm"):
    candidate = Path(str(TEST_DB) + suffix)
    if candidate.exists():
        candidate.unlink()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def fresh_environment():
    """Recrea la base y reconstruye el sistema antes de cada prueba."""
    from src.core.database import reset_database
    from src.main import bootstrap_electoral_system, system_holder

    reset_database()
    system_holder.current_mode = "national"
    system_holder.proxy = bootstrap_electoral_system("national")
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from src.main import app

    return TestClient(app)


@pytest.fixture
def admin_client(client):
    response = client.post(
        "/api/admin/login",
        json={"username": "admin", "password": "test-admin"},
    )
    assert response.status_code == 200, response.text
    return client


def pytest_sessionfinish(session, exitstatus):
    try:
        from src.core.database import engine

        engine.dispose()
    except Exception:
        pass
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(TEST_DB) + suffix)
        if candidate.exists():
            candidate.unlink()
