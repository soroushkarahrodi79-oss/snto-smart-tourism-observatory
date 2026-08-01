# Test Baseline

Only safe, non-destructive, already-existing commands were run. **No failure was
repaired.** No test was added, modified, skipped, or deleted.

## 1. Environment

| Item | Value |
|---|---|
| Interpreter | `.venv\Scripts\python.exe`, CPython 3.12 |
| Platform | Windows 11, PowerShell |
| Working tree | `audit/2026-baseline-phase0` @ `ed25d0a` + 14 untracked files (12 OAPN CSVs, a UX PDF, `downgrade_preview.sql`) |
| Local `.env` present | **yes** — sets `SNTO_DB_*` (local Postgres) and `GEE_*`. Material to the failure below. |
| Test files | 111 under `tests/` |

## 2. Commands executed and results

### 2.1 Full suite

```bash
python -m pytest -q --no-header
```

```
1 failed, 1083 passed, 8 skipped, 1686 warnings in 49.48s
```

### 2.2 Full suite with coverage (mirrors the CI gate)

```bash
python -m pytest -q --no-header --cov=src --cov-report=term
```

```
TOTAL    10371 statements    1692 missed    84%
1 failed, 1083 passed, 8 skipped
```

**Coverage 84 %** against the CI gate of 80 % (`.github/workflows/ci.yml:90`).
The gate passes with ~4 points of headroom.

### 2.3 Targeted runs (to isolate the failure)

```bash
python -m pytest tests/persistence/test_settings_database_url.py::test_database_url_defaults_to_sqlite -q   # 1 passed
python -m pytest tests/persistence -q                                                                       # 109 passed, 8 skipped
python -m pytest tests/ui tests/persistence/test_settings_database_url.py -q                                # 32 passed
python -m pytest tests/unit tests/persistence/test_settings_database_url.py -q                              # 1 failed, 803 passed
python -m pytest tests/integration tests/persistence/test_settings_database_url.py -q                       # 1 failed, 105 passed
```

Then a per-file scan of `tests/unit/` paired with the failing test isolated the
two culprits exactly.

### 2.4 Runtime probes (read-only, no mutation)

```python
src.reporting.cets_readiness.resolve_signals('pnsg')
# {'satellite_real': True, 'mobility_real': False, 'socioeconomic_series': False,
#  'field_measured_plots': 0, 'scm_real_zones': 0}

src.platform.provenance.detect_scene_dates('pnsg')   # ['2025-08-10', '2026-04-10']
src.platform.provenance.snapshot_provenance('pnsg')  # status=REAL, n_scenes=2, MK justified=False
hash('pnsg-nat-001')  # differs between interpreter runs
```

## 3. The failure

```
FAILED tests/persistence/test_settings_database_url.py::test_database_url_defaults_to_sqlite

    assert settings.database_url == "sqlite:///data/outputs/snto.db"
E   AssertionError: assert 'postgresql+psycopg2://…@localhost:5432/snto'
                        == 'sqlite:///data/outputs/snto.db'
```

### Root cause (confirmed, not inferred)

`tests/unit/test_operational_ehs.py` imports `calculate_delta_ehs`, and
`tests/unit/test_tis_causal_budget.py` imports `tis_engine`. Both root-level
modules call **`load_dotenv()` at import time**:

- `calculate_delta_ehs.py:106` — *"carga .env antes de os.getenv() a nivel de módulo"*
- `tis_engine.py:52` — same

`load_dotenv()` writes `.env` values into **`os.environ` for the whole pytest
process**. `Settings(_env_file=None)` disables *dotenv file* reading but
pydantic-settings still reads `os.environ`, so the "defaults to SQLite"
assertion sees the developer's local Postgres URL.

Seven other root scripts share the pattern: `db_production_seeder.py`,
`etl_raster_intersection.py`, `etl_tourist_traffic.py`, `get_bounding_box.py`,
`run_scm_operational.py`, `seed_pnsg_trails.py`.

### Why CI does not catch it

GitHub Actions runners have no `.env` file, so `load_dotenv()` is a no-op there
and the test passes. **The failure is local-only and order-dependent** — which
makes it worse, not better: it means the test does not actually verify the
default it claims to verify, in any environment where a developer has configured
a database.

### Secondary concern

The assertion message printed the developer's **local database password** into
the test log. Any CI environment that did have a `.env` would leak it into build
output. (The password is not reproduced in this audit.)

## 4. Skipped tests (8)

All 8 are in `tests/persistence/test_managed_asset_geometry.py`, all with reason
`requires PostgreSQL/PostGIS`:

| Line | Count |
|---|---|
| 159, 201, 249, 287 | 1 each |
| 239 (parametrised) | 4 |

These run in CI's `postgres-integration` job against `postgis/postgis:16-3.4`.
Locally they skip because `SNTO_TEST_DATABASE_URL` is unset
(`tests/persistence/conftest.py:20`). This is correct, intentional behaviour.

## 5. Warnings (1 686)

Dominated by three recurring `DeprecationWarning` families — none is a failure,
all are forward-compatibility debt:

| Warning | Sites | Note |
|---|---|---|
| `asyncio.iscoroutinefunction` deprecated (removal in Python 3.16) | Starlette 0.37 internals, ~170 occurrences | Comes from the **pinned** `starlette>=0.37.2,<0.38` (`requirements.txt:26`), pinned because FastAPI 0.111 breaks with Starlette ≥ 1.x. A version-lock trap for the 3.16 migration. |
| `datetime.utcnow()` deprecated | `src/api/v2/field_verifications.py:68`, `src/persistence/services/field_verification_ingest.py:87` | Two real occurrences in project code. |
| misc pydantic / rasterio | scattered | — |

## 6. Static checks

Not re-run locally (they are CI jobs and this phase changes no code), but their
configuration was audited:

| Check | Configuration | Assessment |
|---|---|---|
| `ruff check` (blocking) | explicit allow-list of ~45 paths, `ci.yml:28-63` | The list is maintained by hand and grows with every PR. Everything outside it is report-only. |
| `ruff check src tests *.py` | `continue-on-error: true` | Encodes acknowledged lint debt. Unknown magnitude — no count is recorded anywhere. |
| `mypy src/persistence src/api/v2 src/config` | `continue-on-error: true` | The workflow comment records **~110 outstanding `--strict` errors**. `pyproject.toml:27` sets `strict = true` globally, so any future in-scope module inherits a failing baseline. |
| `sync_readme.py --check-version` | blocking | Good. |
| `build_dossier.py --check` | blocking | Excellent — prevented a documented 7× budget misstatement in an OAPN-facing document. |
| `export_openapi.py --check` | blocking | Good; contract embeds the package version, so it must be regenerated on release. |

## 7. Untested critical paths

Ranked by risk, all confirmed by absence of a corresponding test file or test name:

| # | Path | Why it matters |
|---|---|---|
| T-1 | `app.py` itself | Covered only by `py_compile` (`ci.yml:86`). The 4×14 tab dispatch, the asset route, the socio overlay and the `home_layer` gate have no behavioural test. `tests/ui/test_navigation.py` tests the *contract*, not the wiring. |
| T-2 | `src/platform/map_layers.py` geometry synthesis | No test pins `_jitter`/`_trail_path` determinism — which is why C-06's contradiction went unnoticed. A test asserting cross-process stability would have failed. |
| T-3 | `src/platform/provenance.py::snapshot_provenance` fallback | No test covers the "no scenes detected" branch that still returns `DataStatus.REAL`. |
| T-4 | `src/platform/dashboard.py` narrative strings | KPI *numbers* are tested (`test_dashboard_kpis_empty.py`); the causal **claims** in `what_it_means` / `recommended_action` are not asserted anywhere. C-01/C-02/C-03 are invisible to the suite. |
| T-5 | End-to-end Pipeline A | `calculate_delta_ehs` unit-tested; the full raster → GeoJSON run is not reproducible in CI (rasters git-ignored). |
| T-6 | ΔEHS temporal comparability | Nothing asserts that the two scenes are same-year, same-sensor, or correctly ordered. |
| T-7 | Streamlit rendering | No `AppTest`/smoke test renders the dashboard. A `NameError` in any tab reaches production. |
| T-8 | Migration application | `alembic upgrade head` is not exercised against a fresh Postgres in CI (the job runs the suite, which uses `create_all`-style fixtures). The production PostGIS migration remains unapplied and untested end-to-end. |

Coverage of 84 % is therefore **line coverage of the analytical core**, not
assurance over the delivered product: the dashboard shell, the map builders'
determinism, and every scientific claim string sit outside it.

## 8. Reproducibility problems

| # | Problem | Evidence |
|---|---|---|
| P-1 | Test outcome depends on the developer's `.env` and on test ordering | §3 |
| P-2 | Synthetic map geometry is not reproducible across processes | `hash()` salting, C-06 |
| P-3 | Pipeline A cannot be re-run from a fresh clone | rasters git-ignored; only 3 files tracked under `data/` |
| P-4 | `snapshot_provenance` silently substitutes `n_scenes = 2` when scenes are undetectable | `provenance.py:129` |
| P-5 | Last time-series pipeline run recorded `"mode": "dry-run"` and `"git_dirty": true` | `data/outputs/pnsg/run_context.json` |
| P-6 | 12 OAPN GEE CSVs untracked and un-ignored | `git status` |
| P-7 | Coverage threshold is enforced but the *shape* of coverage is not (no per-module floor) | `ci.yml:90` |
| P-8 | **Running the suite modifies tracked files.** 46 `.pyc` files are committed and `__pycache__/` is not git-ignored, so `git status` is dirty after any test run. This audit restored them with `git checkout -- "*.pyc"`. | `git ls-files "*.pyc"` |

## 9. Baseline verdict

The suite is **substantial and genuinely useful**: 1 083 passing tests, 84 %
coverage, a real-Postgres integration job, and three drift gates that protect
externally-facing documents. That is well above prototype norms.

Its blind spot is precise and consequential: **it verifies that the arithmetic is
stable, not that the statements are true.** Every Tier-1 finding in
`SCIENTIFIC_CLAIMS_REGISTER.md` passes the current suite.
