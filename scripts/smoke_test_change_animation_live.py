#!/usr/bin/env python3
"""
MANUAL / LIVE smoke test for the temporal GIF (Visual Change Explorer, ADR-015).

⚠️  This script makes REAL Google Earth Engine calls. It is **manual only** and
must **never** run in CI. It requires an explicit opt-in flag and refuses to run
without it. It reuses the production service (``run_change_animation``) — it does
**not** re-implement the animation pipeline.

What it exercises (with valid credentials + the feature flag on):
  ee.Initialize → registered territory → ee.Geometry.Rectangle → local frame
  planning → one masked S2 collection + a pre-visualised median composite per
  frame → ONE grouped scene-count getInfo → empty-frame removal (≥2 usable) →
  chronological visualised collection → getVideoThumbURL → bounded GIF download.

Safety:
  * prints only *safe metadata* (frame counts, byte size, status) — **never** the
    signed video URL and **never** credentials;
  * downloads at most one bounded (≤ 8 MiB) GIF into memory; writes it to disk
    ONLY when ``--output <path>`` is given (use a git-ignored path), and refuses
    to overwrite an existing file without ``--force``;
  * does not create EE assets, start exports, or download full-res rasters;
  * exits non-zero on failure, with a distinct code per failure class.

Usage (locally, with credentials already configured out-of-band)::

    export GEE_PROJECT_ID=<your-ee-project>
    # personal auth (`earthengine authenticate`) OR service account:
    #   export GEE_SERVICE_ACCOUNT=<svc-email> ; export GEE_KEY_FILE=<path.json>
    export SNTO_ENABLE_CHANGE_EXPLORER=true
    python scripts/smoke_test_change_animation_live.py --confirm-live-ee

By default it uses a **small conservative AOI inside PNSG** (override lives only
here, never in the production territory registry). Pass ``--full-bbox`` to use
the registered territory bbox. Defaults: PNSG, NDVI, 2023-07-01 → 2024-08-31,
max 8 frames, 256px, 2 FPS, cloud ≤ 20%.
"""
from __future__ import annotations

import argparse
import dataclasses
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
EXIT_INSUFFICIENT_FRAMES = 4
EXIT_CONFIG = 5
EXIT_AUTH = 6
EXIT_QUOTA = 7
EXIT_UNAVAILABLE = 8
EXIT_UNEXPECTED = 9
EXIT_GIF_DOWNLOAD = 10
EXIT_OUTPUT = 11

# A small, low-risk AOI well inside PNSG (Madrid/Segovia forested belt near
# Rascafría / Valsaín). Conservative for a first live request — this override is
# SMOKE-TEST ONLY and never touches src/config/territories.py.
_CONSERVATIVE_BBOX = (-3.95, 40.85, -3.85, 40.92)  # (W, S, E, N)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Live GIF smoke test (manual only).")
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
    p.add_argument("--start", default="2023-07-01", help="Period start (YYYY-MM-DD).")
    p.add_argument("--end", default="2024-08-31", help="Period end (YYYY-MM-DD).")
    p.add_argument("--max-frames", type=int, default=8)
    p.add_argument("--dimensions", type=int, default=256)
    p.add_argument("--fps", type=int, default=2)
    p.add_argument("--cloud", type=float, default=20.0)
    p.add_argument(
        "--output", default=None,
        help="Optional path to write the GIF (use a git-ignored dir). Off by default.",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Allow --output to overwrite an existing file.",
    )
    return p.parse_args()


def _safe_artifact_summary(artifact) -> dict:
    """Secret-free summary via the artifact's own metadata-only serialiser."""
    # AnimatedArtifact.to_dict() never includes the GIF bytes or any URL.
    return artifact.to_dict()


def main() -> int:
    args = _parse_args()
    if not args.confirm_live_ee:
        print(
            "REFUSED: this is a live Earth Engine smoke test. Re-run with "
            "--confirm-live-ee to acknowledge real EE calls.",
            file=sys.stderr,
        )
        return EXIT_REFUSED

    # Validate --output up front (before any EE call) so we never generate a GIF
    # we then refuse to write.
    out_path: Path | None = None
    if args.output:
        out_path = Path(args.output)
        if out_path.exists() and not args.force:
            print(
                f"OUTPUT ERROR: {out_path} exists; pass --force to overwrite.",
                file=sys.stderr,
            )
            return EXIT_OUTPUT

    # Imports deferred so --help / refusal never require the SDK.
    from src.analysis.change_detection.models import CompositeKind
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
    from src.services.change_animation_service import (
        ChangeAnimationRequest,
        GifDownloadError,
        InsufficientUsableFramesError,
        run_change_animation,
    )

    try:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)
    except ValueError as exc:
        print(f"INPUT ERROR: bad date: {exc}", file=sys.stderr)
        return EXIT_INPUT

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
        request = ChangeAnimationRequest(
            territory_id=args.territory, product=product, start=start, end=end,
            max_cloud_pct=args.cloud, dimensions=args.dimensions,
            max_frame_count=args.max_frames, frames_per_second=args.fps,
        )
    except (ValueError, TypeError) as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT

    print("── Live smoke test: temporal GIF ───────────────────────────────────")
    print(f"  territory   : {args.territory} ({aoi_note})")
    print(f"  bbox (WSEN) : {cfg.bbox_wgs84}")
    print(f"  period      : {start} → {end}")
    print(f"  product     : {product.value}")
    print(f"  max frames  : {args.max_frames}   dimensions: {args.dimensions}px "
          f"  fps: {args.fps}")
    print(f"  cloud ≤     : {args.cloud}%")
    print("  (running real Earth Engine calls — the video URL is never printed)")

    settings = Settings()  # reads env: flag + GEE_* + optional key file
    t0 = time.monotonic()
    try:
        artifact = run_change_animation(
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
    except InsufficientUsableFramesError as exc:
        print(f"INSUFFICIENT FRAMES: {exc}", file=sys.stderr)
        return EXIT_INSUFFICIENT_FRAMES
    except GifDownloadError as exc:
        print(f"GIF DOWNLOAD: {type(exc).__name__}", file=sys.stderr)
        return EXIT_GIF_DOWNLOAD
    except EarthEngineError as exc:
        print(f"EARTH ENGINE ERROR: {type(exc).__name__}", file=sys.stderr)
        return EXIT_UNEXPECTED
    except ValueError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT
    elapsed = time.monotonic() - t0

    import json

    summary = _safe_artifact_summary(artifact)
    print("── Result (safe metadata) ──────────────────────────────────────────")
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print(f"  first-run duration ≈ {elapsed:.1f}s")
    print(f"  GIF size ≈ {artifact.byte_size / 1024:.0f} KiB "
          f"(cap {8 * 1024} KiB)")

    if out_path is not None:
        try:
            out_path.write_bytes(artifact.gif_bytes)
        except OSError as exc:
            print(f"OUTPUT ERROR: {exc}", file=sys.stderr)
            return EXIT_OUTPUT
        print(f"  wrote GIF → {out_path} ({artifact.byte_size} bytes)")

    if artifact.frame_count < 2:  # defensive; the service already enforces ≥2
        print("UNEXPECTED: fewer than two usable frames slipped through.",
              file=sys.stderr)
        return EXIT_UNEXPECTED

    print(
        f"SMOKE TEST PASSED: GIF generated with {artifact.frame_count}/"
        f"{artifact.planned_frame_count} usable frames (URL withheld)."
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
