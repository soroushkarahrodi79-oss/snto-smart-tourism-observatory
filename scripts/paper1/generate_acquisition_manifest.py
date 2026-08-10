"""
scripts/paper1/generate_acquisition_manifest.py
=================================================
Manage the Paper-1 satellite acquisition manifest
(``docs/paper1/SATELLITE_FIELD_MATCHING_PLAN.md``, Backlog B-06).

Three modes:

  --init                  Write a fresh PLANNED-stage manifest (frozen
                           matching-plan constants, no acquisition window yet)
                           to clean_assets/paper1/acquisition_manifest.json.
  --validate               Report schema/consistency problems for the
                           committed manifest and exit non-zero on failure.
  --check <scenes.json>    Compare the committed manifest's declared
                           scene_ids against a JSON array of scene IDs an
                           extraction run actually used; exit non-zero on any
                           mismatch.

Never invents an acquisition window or scene IDs: --init always produces a
PLANNED manifest. Fixing the window and scenes is a separate, later step, run
once the target field season (docs/paper1/DATA_ACQUISITION_TRIAGE.md, open
item 4) is decided.

Uso:
    python scripts/paper1/generate_acquisition_manifest.py --init
    python scripts/paper1/generate_acquisition_manifest.py --validate
    python scripts/paper1/generate_acquisition_manifest.py --check scenes.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.validation import (
    check_against_extraction,
    load_manifest,
    new_planned_manifest,
    validate_manifest,
    write_manifest,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_MANIFEST_PATH = _ROOT / "clean_assets" / "paper1" / "acquisition_manifest.json"


def _init() -> None:
    m = new_planned_manifest(
        notes="Frozen matching-plan constants per SATELLITE_FIELD_MATCHING_PLAN.md "
              "§2. Acquisition window not yet fixed — pending the target field "
              "season decision (DATA_ACQUISITION_TRIAGE.md open item 4). "
              "Sampling frame restricted to the Comunidad de Madrid-administered "
              "sector of PNSG (PNSG_RESEARCH_AUTHORIZATION_REQUEST.md §1)."
    )
    errors = validate_manifest(m)
    if errors:
        log.error("Generated manifest failed its own validation: %s", errors)
        sys.exit(1)
    write_manifest(m, _MANIFEST_PATH)
    log.info("Manifest (status=%s) → %s", m.status.value, _MANIFEST_PATH)


def _validate() -> None:
    if not _MANIFEST_PATH.exists():
        log.error("No manifest at %s — run --init first.", _MANIFEST_PATH)
        sys.exit(1)
    m = load_manifest(_MANIFEST_PATH)
    errors = validate_manifest(m)
    if errors:
        log.error("Manifest invalid (status=%s):", m.status.value)
        for e in errors:
            log.error("  - %s", e)
        sys.exit(1)
    log.info("Manifest valid (status=%s).", m.status.value)


def _check(scenes_path: Path) -> None:
    if not _MANIFEST_PATH.exists():
        log.error("No manifest at %s — run --init first.", _MANIFEST_PATH)
        sys.exit(1)
    m = load_manifest(_MANIFEST_PATH)
    extracted = json.loads(scenes_path.read_text(encoding="utf-8"))
    report = check_against_extraction(m, extracted)
    log.info(report.summary)
    if not report.ok:
        sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--init", action="store_true",
                   help="Write a fresh PLANNED-stage manifest and exit.")
    p.add_argument("--validate", action="store_true",
                   help="Validate the committed manifest and exit.")
    p.add_argument("--check", type=Path, default=None, metavar="SCENES_JSON",
                   help="Compare the manifest's scene_ids against a JSON array "
                        "of scene IDs an extraction run actually used.")
    args = p.parse_args()

    if args.init:
        _init()
    elif args.validate:
        _validate()
    elif args.check is not None:
        _check(args.check)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
