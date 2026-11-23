"""Respuestas de descarga reutilizables para actas y auditoría."""
from __future__ import annotations

import csv
import io
import json
from typing import Any, Iterable, List

from fastapi import Response


def json_attachment(filename: str, payload: Any) -> Response:
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def csv_attachment(filename: str, header: List[str], rows: Iterable[Iterable[Any]]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
