"""F6 — logging setup and reproducible run context."""
from __future__ import annotations

import json
import logging

from src.config.logging_setup import configure_logging, resolve_level
from src.config.run_context import RunContext, capture


def test_resolve_level_from_explicit_and_env(monkeypatch):
    assert resolve_level("DEBUG") == logging.DEBUG
    assert resolve_level(logging.WARNING) == logging.WARNING
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    assert resolve_level(None) == logging.ERROR
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert resolve_level(None) == logging.INFO  # default


def test_configure_logging_is_idempotent():
    root = configure_logging("INFO", force=True)
    n_before = len(root.handlers)
    configure_logging("INFO")          # second call must not stack handlers
    assert len(root.handlers) == n_before
    assert n_before >= 1


def test_capture_run_context_fields():
    ctx = capture("unit-test", territory="pnsg", years=[2021, 2022])
    assert isinstance(ctx, RunContext)
    assert ctx.tool == "unit-test"
    assert ctx.params["territory"] == "pnsg"
    assert ctx.git_sha  # 'unknown' or a real short sha, never empty
    assert ctx.timestamp_utc.endswith("+00:00")
    assert ctx.python_version.count(".") >= 2


def test_run_context_round_trips_to_json(tmp_path):
    ctx = capture("unit-test", mode="dry-run")
    path = ctx.write_json(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["tool"] == "unit-test"
    assert payload["params"]["mode"] == "dry-run"
    assert "git_sha" in payload and "timestamp_utc" in payload
