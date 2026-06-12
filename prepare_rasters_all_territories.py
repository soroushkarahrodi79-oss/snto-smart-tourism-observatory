"""
SNTO — Batch Raster Preparation (all territories)
==================================================
Runs prepare_raster.py for every registered territory × season combination.

Scene convention (T30TVL tile):
  summer  ← S2A_MSIL2A_20250810  (August 2025)
  spring  ← S2B_MSIL2A_20260410  (April 2026)

Outputs are written to:
  data/clean_assets/<territory_key>/spring_raster.tif
  data/clean_assets/<territory_key>/summer_raster.tif

Usage
-----
    python prepare_rasters_all_territories.py
    python prepare_rasters_all_territories.py --territory pnsg
    python prepare_rasters_all_territories.py --dry-run
"""
from __future__ import annotations

import argparse
import io
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
RASTER_ROOT = ROOT / "data" / "raw_assets" / "raster_data"

SEP = "=" * 72
DIV = "-" * 72

# Map output season label → partial scene name (date-only substring is enough)
SEASON_SCENE_FRAGMENT: dict[str, str] = {
    "summer": "20250810",   # S2A August 2025
    "spring": "20260410",   # S2B April 2026
}


def _find_safe(folder: Path, date_fragment: str) -> Path | None:
    """Return the .SAFE directory whose name contains date_fragment, or None."""
    matches = [p for p in folder.iterdir() if p.is_dir() and date_fragment in p.name]
    return matches[0] if len(matches) == 1 else None


def _run_prepare(territory_key: str, raw_folder: Path, season: str, scene: Path, dry_run: bool) -> bool:
    cmd = [
        sys.executable, str(ROOT / "prepare_raster.py"),
        "--territory", territory_key,
        "--input",    str(scene),
        "--output",   f"{season}_raster.tif",
    ]
    print(f"\n  [{territory_key} / {season}]")
    print(f"    Scene  : {scene.name}")
    print(f"    Output : data/clean_assets/{territory_key}/{season}_raster.tif")
    if dry_run:
        print("    (dry-run — skipping execution)")
        return True
    result = subprocess.run(cmd, cwd=str(ROOT))
    return result.returncode == 0


def main() -> None:
    from src.config.territories import TERRITORIES

    parser = argparse.ArgumentParser(description="Batch raster preparation for all SNTO territories.")
    parser.add_argument("--territory", default=None, help="Limit to one territory key.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing.")
    args = parser.parse_args()

    keys = [args.territory] if args.territory else list(TERRITORIES)

    print(SEP)
    print("  SNTO — Batch Raster Preparation (all territories)")
    print(SEP)

    ok = err = 0
    for key in keys:
        cfg = TERRITORIES[key]
        raw_folder = RASTER_ROOT / cfg.raw_raster_folder
        if not raw_folder.is_dir():
            print(f"\n  [SKIP] {key}: raw folder not found: {raw_folder}")
            continue

        for season, fragment in SEASON_SCENE_FRAGMENT.items():
            scene = _find_safe(raw_folder, fragment)
            if scene is None:
                print(f"\n  [SKIP] {key}/{season}: no .SAFE scene matching '{fragment}' in {raw_folder}")
                continue
            success = _run_prepare(key, raw_folder, season, scene, args.dry_run)
            if success:
                ok += 1
            else:
                err += 1
                print(f"  [ERROR] {key}/{season} failed — see output above.")

    print()
    print(DIV)
    print(f"  Done.  {ok} succeeded, {err} failed.")
    print(DIV)
    if err:
        sys.exit(1)


if __name__ == "__main__":
    main()
