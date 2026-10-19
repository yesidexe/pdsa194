"""Genera votos de demostración usando el mismo flujo HTTP de la cabina.

Uso:
    # Modo nacional (por defecto)
    ./venv/bin/python scripts/cast_demo_votes.py

    # Modo universitario
    ELECTION_MODE=university ./venv/bin/python scripts/cast_demo_votes.py

No inserta filas a mano: usa documento + PIN y la validación real. Si un elector
ya votó, lo informa y continúa. Sirve para que el dashboard tenga datos antes de
la exposición.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from src.main import app  # noqa: E402


NATIONAL_VOTERS = ["10203040", "50607080", "70809010", "80901020"] + [
    f"2000{idx:04d}" for idx in range(2, 16)
]
UNIVERSITY_VOTERS = ["EST-2024", "EST-9012", "EST-3341", "EST-5520"] + [
    f"EST-{1001 + idx}" for idx in range(2, 16)
]
NATIONAL_CANDIDATES = ["CAND-01", "CAND-02", "CAND-03", "CAND-04"]
UNIVERSITY_CANDIDATES = ["VOC-01", "VOC-02", "VOC-03", "VOC-04"]


def main() -> None:
    client = TestClient(app)
    mode = os.getenv("ELECTION_MODE", "national").lower().strip()
    is_university = mode == "university"
    voters = UNIVERSITY_VOTERS if is_university else NATIONAL_VOTERS
    candidates = UNIVERSITY_CANDIDATES if is_university else NATIONAL_CANDIDATES

    created = 0
    skipped = 0
    for index, document_id in enumerate(voters):
        if index % 6 == 5:
            payload = {
                "document_id": document_id,
                "pin": "1234",
                "ballot_type": "blank",
                "selection": {},
            }
        else:
            payload = {
                "document_id": document_id,
                "pin": "1234",
                "ballot_type": "candidate",
                "selection": {
                    "candidate_id": candidates[index % len(candidates)],
                },
            }
        response = client.post("/api/votes/cast", json=payload)
        if response.status_code == 200:
            created += 1
        elif response.status_code == 409:
            skipped += 1
        elif response.status_code == 403 and "no habilitado" in response.text.lower():
            skipped += 1
        else:
            print(f"  {document_id}: {response.status_code} {response.text[:120]}")

    dashboard = client.get("/api/dashboard").json()
    print(f"Votos nuevos: {created} (omitidos: {skipped})")
    print(f"Total en urna ({mode}): {dashboard['total_votes_cast']}")
    print(f"Participación: {dashboard['turnout_percentage']}%")


if __name__ == "__main__":
    main()
