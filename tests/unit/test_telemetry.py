"""Telemetría de uso de vistas (F10 · Fase 5) — local, opt-in, sin PII.

Verifica el contrato del módulo puro sin levantar Streamlit: registro append-only,
lectura resiliente a líneas corruptas, recuento por vista y el gate opt-in.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.platform.telemetry import (
    load_events,
    record_view,
    telemetry_enabled,
    usage_summary,
)


def test_record_and_load_roundtrip(tmp_path: Path) -> None:
    log = tmp_path / "view_usage.jsonl"
    assert record_view("tribunal", path=log) is True
    assert record_view("gestor", path=log) is True
    events = load_events(log)
    assert [e["view"] for e in events] == ["tribunal", "gestor"]
    assert all("ts" in e for e in events)


def test_record_is_append_only(tmp_path: Path) -> None:
    log = tmp_path / "u.jsonl"
    record_view("tecnica", path=log)
    record_view("tecnica", path=log)
    assert len(load_events(log)) == 2


def test_load_events_missing_file_is_empty(tmp_path: Path) -> None:
    assert load_events(tmp_path / "nope.jsonl") == []


def test_load_events_skips_corrupt_lines(tmp_path: Path) -> None:
    log = tmp_path / "u.jsonl"
    log.write_text('{"ts":"t","view":"gestor"}\nNOT JSON\n\n', encoding="utf-8")
    events = load_events(log)
    assert [e["view"] for e in events] == ["gestor"]


def test_usage_summary_counts_by_view(tmp_path: Path) -> None:
    log = tmp_path / "u.jsonl"
    for m in ("tribunal", "tribunal", "gestor"):
        record_view(m, path=log)
    assert usage_summary(log) == {"tribunal": 2, "gestor": 1}


def test_record_uses_injected_timestamp(tmp_path: Path) -> None:
    log = tmp_path / "u.jsonl"
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    record_view("gestor", path=log, now=now)
    assert load_events(log)[0]["ts"] == now.isoformat()


def test_record_never_raises_on_bad_path(tmp_path: Path) -> None:
    # El "directorio" es en realidad un fichero: mkdir/open fallan → False, sin lanzar.
    clash = tmp_path / "afile"
    clash.write_text("x", encoding="utf-8")
    assert record_view("tecnica", path=clash / "sub" / "log.jsonl") is False


def test_telemetry_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("SNTO_TELEMETRY", raising=False)
    assert telemetry_enabled() is False


def test_telemetry_opt_in_truthy_values(monkeypatch) -> None:
    for val in ("1", "true", "YES", "on"):
        monkeypatch.setenv("SNTO_TELEMETRY", val)
        assert telemetry_enabled() is True
    for val in ("0", "false", "", "no"):
        monkeypatch.setenv("SNTO_TELEMETRY", val)
        assert telemetry_enabled() is False
