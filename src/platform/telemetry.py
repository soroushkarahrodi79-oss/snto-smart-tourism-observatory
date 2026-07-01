"""Telemetría de uso de vistas (F10 · Fase 5) — LOCAL y opt-in.

Registra *qué vista/audiencia* se usa, para priorizar de forma empírica dónde
profundizar el detalle en versiones posteriores. Es deliberadamente mínima y
respetuosa con la privacidad:

* **100 % local**: escribe un JSONL en disco; **nunca** hace red ni envía datos a
  terceros. El fichero vive bajo ``data/`` (ignorado por git), así que no sale
  del entorno.
* **sin PII**: cada evento es solo ``(timestamp UTC, modo de vista)``. No hay
  usuario, IP, sesión ni geolocalización.
* **opt-in**: desactivada por defecto; se activa con ``SNTO_TELEMETRY=1``.

Todo el módulo es **puro** (sin Streamlit) para poder testearlo sin levantar la
app. ``app.py`` solo llama a ``record_view`` cuando ``telemetry_enabled()``.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Bajo data/ (git-ignored): la telemetría no se versiona ni sale del entorno.
DEFAULT_LOG = Path("data/outputs/view_usage.jsonl")

_TRUTHY = {"1", "true", "yes", "on"}


def telemetry_enabled() -> bool:
    """True solo si ``SNTO_TELEMETRY`` está explícitamente activada (opt-in)."""
    return os.getenv("SNTO_TELEMETRY", "").strip().lower() in _TRUTHY


def record_view(
    mode: str,
    *,
    path: Path | None = None,
    now: datetime | None = None,
) -> bool:
    """Anexa un evento ``(ts UTC, modo)`` al log local. Devuelve True si escribió.

    Nunca lanza: si el disco falla, la telemetría no debe tumbar la app, así que
    captura el ``OSError`` y devuelve False. ``path``/``now`` son inyectables para
    tests deterministas.
    """
    log = path or DEFAULT_LOG
    ts = (now or datetime.now(timezone.utc)).isoformat()
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": ts, "view": mode}) + "\n")
        return True
    except OSError:
        return False


def load_events(path: Path | None = None) -> list[dict]:
    """Lee los eventos del log. Lista vacía si no existe; ignora líneas corruptas."""
    log = path or DEFAULT_LOG
    if not log.exists():
        return []
    events: list[dict] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def usage_summary(path: Path | None = None) -> dict[str, int]:
    """Recuento de eventos por modo de vista (para el panel de mantenimiento)."""
    counter: Counter[str] = Counter(
        e["view"] for e in load_events(path) if isinstance(e.get("view"), str)
    )
    return dict(counter)
