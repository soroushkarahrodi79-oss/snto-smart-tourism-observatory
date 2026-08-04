"""Phase 0.5A — import isolation for the root DB scripts.

The eight root scripts below historically called ``load_dotenv()`` at module
scope, which mutated ``os.environ`` for the whole process the moment any test
imported them. That defeated ``Settings(_env_file=None)`` isolation and could
surface a developer's real ``.env`` credentials in an assertion diff.

The fix moved ``load_dotenv()`` (and the DB-global refresh) into a private
``_load_runtime_db_config()`` helper that runs only from ``main()`` — i.e. only
on direct execution, never on import.

This module proves two independent properties for every script, each in a
**fresh subprocess** so a module already cached in the parent test session's
``sys.modules`` cannot mask the behaviour (and so importing these GDAL/rasterio
-backed modules cannot disturb the parent pytest process's output capture):

* **A — import is dotenv-side-effect-free.** ``dotenv.load_dotenv`` is replaced
  with a bomb that raises if called, then the module is imported. Import must not
  call it, and must not mutate any relevant DB environment key.
* **B — runtime refresh still works.** The module's ``load_dotenv`` is replaced
  with a fake that injects unmistakably fake DB values, ``_load_runtime_db_config()``
  is called, and the module globals must reflect those fake values. This guards
  against forgetting the ``global`` declaration (which would silently make the
  refresh a no-op) and proves direct execution can still load configuration.

No real credential is ever used, asserted, or printed here.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# tests/unit/this_file.py -> tests/unit -> tests -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODULES = [
    "calculate_delta_ehs",
    "tis_engine",
    "db_production_seeder",
    "etl_raster_intersection",
    "etl_tourist_traffic",
    "get_bounding_box",
    "run_scm_operational",
    "seed_pnsg_trails",
]

# Runs in a fresh interpreter (argv: <project_root> <module_name>). Exits 0 only
# when importing the module neither calls load_dotenv nor mutates the relevant DB
# environment keys; a raised bomb (exit 1) or ENV mutation (exit 2) fails it.
_IMPORT_PROBE = r"""
import os
import sys
import importlib

root, mod_name = sys.argv[1], sys.argv[2]
if root not in sys.path:
    sys.path.insert(0, root)

RELEVANT = (
    "SNTO_DB_HOST", "SNTO_DB_PORT", "SNTO_DB_NAME",
    "SNTO_DB_USER", "SNTO_DB_PASS", "SNTO_DATABASE_URL",
)
before = {k: os.environ.get(k) for k in RELEVANT}

import dotenv

def _bomb(*args, **kwargs):
    raise AssertionError("load_dotenv() was invoked at import time")

# Patched before the target imports, so its `from dotenv import load_dotenv`
# binds the bomb.
dotenv.load_dotenv = _bomb

importlib.import_module(mod_name)

if {k: os.environ.get(k) for k in RELEVANT} != before:
    sys.stderr.write("ENV_MUTATED\n")
    sys.exit(2)

sys.exit(0)
"""

# Runs in a fresh interpreter. Replaces the module's load_dotenv with a fake that
# injects unmistakably fake DB values, calls _load_runtime_db_config(), and exits
# 0 only if every module global picked up the fake value. On mismatch it reports
# per-field booleans (never the values) and exits 3.
_REFRESH_PROBE = r"""
import os
import sys
import importlib

root, mod_name = sys.argv[1], sys.argv[2]
if root not in sys.path:
    sys.path.insert(0, root)

FAKE = {
    "SNTO_DB_HOST": "example.invalid",
    "SNTO_DB_PORT": "5599",            # non-default (default 5432): observable
    "SNTO_DB_NAME": "fake-db",
    "SNTO_DB_USER": "fake-user",
    "SNTO_DB_PASS": "FAKE-NOT-A-SECRET",
}
for k in FAKE:
    os.environ.pop(k, None)

mod = importlib.import_module(mod_name)

def _fake_load_dotenv(*args, **kwargs):
    os.environ.update(FAKE)
    return True

mod.load_dotenv = _fake_load_dotenv
mod._load_runtime_db_config()

checks = {
    "host": mod.DB_HOST == "example.invalid",
    "port": mod.DB_PORT == 5599,
    "name": mod.DB_NAME == "fake-db",
    "user": mod.DB_USER == "fake-user",
    "pass": mod.DB_PASS == "FAKE-NOT-A-SECRET",
}
if not all(checks.values()):
    # Report booleans only — never the underlying values.
    sys.stderr.write("REFRESH_MISMATCH " + " ".join(
        f"{k}={v}" for k, v in checks.items()) + "\n")
    sys.exit(3)

sys.exit(0)
"""


def _run_probe(program: str, mod_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", program, str(PROJECT_ROOT), mod_name],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("mod_name", MODULES)
def test_import_does_not_invoke_load_dotenv(mod_name: str) -> None:
    """A — importing the module must not call load_dotenv or mutate DB env keys."""
    result = _run_probe(_IMPORT_PROBE, mod_name)
    # stderr only ever carries our sentinels or a traceback naming the bomb —
    # never an environment value — so it is safe to surface in the message.
    assert result.returncode == 0, (
        f"importing {mod_name!r} called load_dotenv() or mutated DB env keys "
        f"(exit={result.returncode}); stderr={result.stderr.strip()!r}"
    )


@pytest.mark.parametrize("mod_name", MODULES)
def test_runtime_refresh_updates_db_globals(mod_name: str) -> None:
    """B — _load_runtime_db_config() refreshes the module globals from the env."""
    result = _run_probe(_REFRESH_PROBE, mod_name)
    # stderr on mismatch reports per-field booleans only, never any value.
    assert result.returncode == 0, (
        f"_load_runtime_db_config() did not refresh globals for {mod_name!r} "
        f"(exit={result.returncode}); stderr={result.stderr.strip()!r}"
    )
