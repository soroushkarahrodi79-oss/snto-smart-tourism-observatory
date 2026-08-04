#!/usr/bin/env python3
"""
MANUAL / LIVE smoke test for the Visual Change Explorer (ADR-015).

⚠️  This script makes REAL Google Earth Engine calls. It is **manual only** and
must **never** run in CI. It requires an explicit opt-in flag and refuses to run
without it. It reuses the production service (``run_change_explorer``) — it does
**not** re-implement the analysis pipeline.

What it exercises (with valid credentials + the feature flag on):
  ee.Initialize → registered territory → ee.Geometry.Rectangle → S2 filtering →
  SCL masking → per-scene NDVI → median composites → one combined quality getInfo
  per window → getThumbURL (before / after / dNDVI).

Safety:
  * prints only *safe metadata* (counts, fractions, status) — **never** thumbnail
    URLs and **never** credentials;
  * does not download rasters, create EE assets, or start exports;
  * exits non-zero on failure, with a distinct code per failure class.

Usage (locally, with credentials already configured out-of-band)::

    export GEE_PROJECT_ID=<your-ee-project>
    # personal auth (`earthengine authenticate`) OR service account:
    #   export GEE_SERVICE_ACCOUNT=<svc-email> ; export GEE_KEY_FILE=<path.json>
    export SNTO_ENABLE_CHANGE_EXPLORER=true
    python scripts/smoke_test_change_explorer_live.py --confirm-live-ee

By default it uses a **small conservative AOI inside PNSG** (override lives only
here, never in the production territory registry). Pass ``--full-bbox`` to use
the registered territory bbox. Optionally write a secret-free JSON summary with
``--summary-json data/change_explorer_smoke.json`` (``data/`` is git-ignored).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from datetime import date
from pathlib import Path

# Make the repo root importable when run as `python scripts/...` (matches the
# convention in scripts/build_dossier.py / export_openapi.py).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Exit codes (distinct per failure class).
EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_INPUT = 3
EXIT_NO_DATA = 4
EXIT_CONFIG = 5
EXIT_AUTH = 6
EXIT_QUOTA = 7
EXIT_UNAVAILABLE = 8
EXIT_UNEXPECTED = 9

# A small, low-risk AOI well inside PNSG (Madrid/Segovia forested belt near
# Rascafría / Valsaín). Conservative for a first live request — this override is
# SMOKE-TEST ONLY and never touches src/config/territories.py.
_CONSERVATIVE_BBOX = (-3.95, 40.85, -3.85, 40.92)  # (W, S, E, N)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Live smoke test (manual only).")
    p.add_argument(
        "--confirm-live-ee", action="store_true",
        help="REQUIRED opt-in: acknowledge this makes real Earth Engine calls.",
    )
    p.add_argument("--territory", default="pnsg", help="Registered territory id.")
    p.add_argument(
        "--full-bbox", action="store_true",
        help="Use the registered territory bbox instead of the conservative one.",
    )
    p.add_argument("--product", choices=["ndvi", "true_colour"], default="ndvi")
    p.add_argument("--dimensions", type=int, default=256)
    p.add_argument("--cloud", type=float, default=20.0)
    p.add_argument(
        "--summary-json", default=None,
        help="Optional path for a secret-free JSON summary (use a git-ignored dir).",
    )
    return p.parse_args()


def _safe_result_summary(result) -> dict:
    """Secret-free summary: booleans for artifacts, never URLs."""
    def _q(q):
        return {
            "scene_count": q.scene_count,
            "mean_scene_cloud_pct": q.mean_scene_cloud_pct,
            "valid_pixel_fraction": q.valid_pixel_fraction,
            "adequate_coverage": q.adequate_coverage,
            "warnings": list(q.warnings),
        }

    return {
        "territory_id": result.territory_id,
        "territory_name": result.territory_name,
        "product": result.product.value,
        "status": result.status.value,
        "before_window": result.request.before.to_dict(),
        "after_window": result.request.after.to_dict(),
        "cloud_threshold": result.request.max_cloud_pct,
        "dimensions": result.request.dimensions,
        "before_quality": _q(result.before_quality),
        "after_quality": _q(result.after_quality),
        "warnings": list(result.warnings),
        "artifacts_present": {
            "before": result.before_artifact is not None,
            "after": result.after_artifact is not None,
            "dndvi": result.dndvi_artifact is not None,
        },
        # Explicitly NO urls / no signed data.
    }


def main() -> int:
    args = _parse_args()
    if not args.confirm_live_ee:
        print(
            "REFUSED: this is a live Earth Engine smoke test. Re-run with "
            "--confirm-live-ee to acknowledge real EE calls.",
            file=sys.stderr,
        )
        return EXIT_REFUSED

    # Imports deferred so --help / refusal never require the SDK.
    from src.analysis.change_detection.models import CompositeKind, DateWindow
    from src.config import territories
    from src.config.settings import Settings
    from src.integrations.earth_engine.errors import (
        EarthEngineAuthError,
        EarthEngineConfigError,
        EarthEngineDisabledError,
        EarthEngineError,
        EarthEngineQuotaError,
        EarthEngineUnavailableError,
    )
    from src.services.change_explorer_service import (
        ChangeExplorerRequest,
        ResultStatus,
        run_change_explorer,
    )

    # Conservative, comparable summer windows from past years.
    before = DateWindow(date(2023, 7, 1), date(2023, 8, 31))
    after = DateWindow(date(2024, 7, 1), date(2024, 8, 31))
    product = (
        CompositeKind.NDVI if args.product == "ndvi" else CompositeKind.TRUE_COLOUR
    )

    try:
        base_cfg = territories.get(args.territory)
    except KeyError:
        print(f"INPUT ERROR: unknown territory {args.territory!r}.", file=sys.stderr)
        return EXIT_INPUT

    if args.full_bbox:
        cfg = base_cfg
        aoi_note = "registered bbox"
    else:
        cfg = dataclasses.replace(base_cfg, bbox_wgs84=_CONSERVATIVE_BBOX)
        aoi_note = "conservative smoke-test bbox (override; not persisted)"

    try:
        request = ChangeExplorerRequest(
            territory_id=args.territory, product=product, before=before,
            after=after, max_cloud_pct=args.cloud, dimensions=args.dimensions,
        )
    except (ValueError, TypeError) as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT

    print("── Live smoke test: Visual Change Explorer ─────────────────────────")
    print(f"  territory   : {args.territory} ({aoi_note})")
    print(f"  bbox (WSEN) : {cfg.bbox_wgs84}")
    print(f"  before      : {before.start} → {before.end}")
    print(f"  after       : {after.start} → {after.end}")
    print(f"  product     : {product.value}")
    print(f"  cloud ≤     : {args.cloud}%   dimensions: {args.dimensions}px")
    print("  (running real Earth Engine calls — no URLs will be printed)")

    settings = Settings()  # reads env: flag + GEE_* + optional key file
    t0 = time.monotonic()
    try:
        result = run_change_explorer(
            request, app_settings=settings, territory_resolver=lambda _t: cfg
        )
    except EarthEngineDisabledError:
        print(
            "CONFIG: feature flag off. Set SNTO_ENABLE_CHANGE_EXPLORER=true.",
            file=sys.stderr,
        )
        return EXIT_CONFIG
    except EarthEngineConfigError as exc:
        print(f"CONFIG: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except EarthEngineAuthError:
        print(
            "AUTH: Earth Engine authentication/permission failed. Check personal "
            "auth (`earthengine authenticate`) or the service-account key, and "
            "that the project is Earth Engine-registered.",
            file=sys.stderr,
        )
        return EXIT_AUTH
    except EarthEngineQuotaError:
        print("QUOTA: Earth Engine quota / rate limit hit.", file=sys.stderr)
        return EXIT_QUOTA
    except EarthEngineUnavailableError:
        print(
            "UNAVAILABLE: Earth Engine unavailable / network / SDK problem.",
            file=sys.stderr,
        )
        return EXIT_UNAVAILABLE
    except EarthEngineError as exc:
        print(f"EARTH ENGINE ERROR: {type(exc).__name__}", file=sys.stderr)
        return EXIT_UNEXPECTED
    except ValueError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT
    elapsed = time.monotonic() - t0

    summary = _safe_result_summary(result)
    print("── Result (safe metadata) ──────────────────────────────────────────")
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print(f"  first-run duration ≈ {elapsed:.1f}s")

    if args.summary_json:
        with open(args.summary_json, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False, default=str)
        print(f"  wrote secret-free summary → {args.summary_json}")

    if result.status is ResultStatus.NO_DATA:
        print(
            "NO DATA: no scenes / no valid pixels for the chosen windows. Widen "
            "the dates or raise the cloud threshold and retry.",
            file=sys.stderr,
        )
        return EXIT_NO_DATA

    ok = (
        result.before_artifact is not None
        and result.after_artifact is not None
        and result.dndvi_artifact is not None
    )
    if not ok:
        print("UNEXPECTED: data present but artifacts missing.", file=sys.stderr)
        return EXIT_UNEXPECTED

    print("SMOKE TEST PASSED: three artifacts generated (URLs withheld).")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
