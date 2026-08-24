#!/usr/bin/env python3
"""Resolve the official Madrid camera source and build the camera manifest.

This script establishes the *provenance* half of VIS-001 (§6 of the protocol).
It does not download frames. It answers the questions that must be answered
before any frame is downloaded, and it does so from two distinct official
documents, because neither alone is sufficient:

* **The KML** (``informo.madrid.es/informo/tmadrid/CCTV.kml``) is the
  authoritative camera list. Cameras are read out of its ``<Placemark>``
  structure — id, published name, coordinates, image endpoint. It ships no
  licence header.
* **The open-data catalogue page** (``datos.madrid.es``) carries the licence and
  terms-of-use statement. Provenance is verified against it.

Cameras are **never** identified by scanning a page for anything that ends in
``.jpg``. A URL becomes a camera endpoint only when the KML attaches it to a
specific Placemark that also has coordinates, so every row of the camera
manifest is traceable to one entry in the official dataset. A blind regex over
arbitrary HTML would happily return a logo, a legend icon or a banner.

Writes:
    data/source_resolution.json   provenance record (git-ignored: environment-specific)
    data/camera_manifest.csv      the frozen camera population, from the KML

Usage:
    python experiments/vis001_madrid_counting/scripts/resolve_sources.py
    python experiments/vis001_madrid_counting/scripts/resolve_sources.py --timeout 60
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vis001 import config  # noqa: E402
from vis001.cameras import (  # noqa: E402
    KmlParseError,
    parse_kml,
    validate_camera_manifest,
    write_camera_manifest,
)

#: The official endpoints, in the two roles described above. Third-party
#: mirrors are deliberately absent: the protocol forbids using one while the
#: official source exists.
CANDIDATE_SOURCES: tuple[dict[str, str], ...] = (
    {
        "key": "informo_cctv_kml",
        "role": "camera_list",
        "url": config.MADRID_CCTV_KML_URL,
        "note": "Authoritative KML camera list published by the municipal "
                "traffic portal. Parsed structurally into the camera manifest.",
    },
    {
        "key": "datos_madrid_dataset_trafico_camaras",
        "role": "licence_and_terms",
        "url": config.MADRID_DATASET_PAGE_URL,
        "note": "Open data catalogue page for 'Tráfico. Cámaras'. Primary "
                "licence / terms-of-use statement the KML does not carry.",
    },
    {
        "key": "datos_gob_es_trafico_camaras_rdf",
        "role": "licence_and_terms",
        "url": config.MADRID_DATASET_NATIONAL_FALLBACK_URL,
        "note": "National open-data catalogue (datos.gob.es) RDF/XML entry for "
                "the SAME Ayuntamiento de Madrid dataset. Licence / metadata "
                "FALLBACK ONLY, consulted when the municipal catalogue page "
                "times out. Never a camera source or camera-list substitute "
                "(protocol deviation PD-001).",
    },
    {
        "key": "datos_madrid_kml_mirror",
        "role": "camera_list_alternate",
        "url": "https://datos.madrid.es/egob/catalogo/"
               "202088-0-trafico-camaras.kml",
        "note": "The same KML distribution served from the catalogue. Used "
                "only if the informo.madrid.es endpoint is unavailable; still "
                "an official Ayuntamiento de Madrid endpoint, not a mirror.",
    },
)

#: Licence-bearing phrases the Madrid catalogue uses. Matching one records the
#: surrounding text verbatim; it never *asserts* a licence on its own.
_LICENCE_HINTS = (
    "condiciones de uso",
    "aviso legal",
    "licencia",
    "reutilización",
    "terms of use",
    "creative commons",
)


def probe(url: str, *, timeout: int) -> dict[str, object]:
    """Fetch a URL and describe what came back, including how it failed."""
    request = urllib.request.Request(
        url,
        headers={
            # Identify the client honestly. A scientific benchmark has no
            # reason to disguise itself as a browser.
            "User-Agent": (
                "SNTO-VIS001/1.0 (research feasibility benchmark; "
                "contact via project repository)"
            ),
            "Accept": "*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            return {
                "reachable": True,
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type", ""),
                "content_length_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "final_url": response.geturl(),
                "error": None,
                "_payload": payload,
            }
    except urllib.error.HTTPError as exc:
        return {
            "reachable": True,
            "http_status": exc.code,
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "content_length_bytes": None,
            "sha256": None,
            "final_url": url,
            "error": f"HTTP {exc.code} {exc.reason}",
            "_payload": b"",
        }
    except Exception as exc:  # noqa: BLE001 - network/DNS/TLS/proxy all count
        return {
            "reachable": False,
            "http_status": None,
            "content_type": None,
            "content_length_bytes": None,
            "sha256": None,
            "final_url": url,
            "error": f"{type(exc).__name__}: {exc}",
            "_payload": b"",
        }


def extract_licence_snippets(payload: bytes, *, limit: int = 4) -> list[str]:
    """Record verbatim any licence-looking sentence, without interpreting it.

    The snippets are evidence for a human to read. This script never concludes
    "the licence permits X".
    """
    text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    snippets: list[str] = []
    lowered = text.lower()
    for hint in _LICENCE_HINTS:
        start = lowered.find(hint)
        if start < 0:
            continue
        window = text[max(0, start - 120) : start + 320].strip()
        if window and window not in snippets:
            snippets.append(window)
        if len(snippets) >= limit:
            break
    return snippets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout", type=int, default=30, help="per-request timeout in seconds"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=config.SOURCE_RESOLUTION_PATH,
        help="where to write the provenance record",
    )
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    licence_snippets: list[str] = []
    cameras: list = []
    camera_source = ""
    kml_errors: list[str] = []

    for candidate in CANDIDATE_SOURCES:
        print(f"probing {candidate['key']} … ", end="", flush=True)
        outcome = probe(candidate["url"], timeout=args.timeout)
        payload = outcome.pop("_payload")
        outcome["cameras_parsed"] = 0

        if outcome["reachable"] and outcome["http_status"] == 200:
            if candidate["role"].startswith("camera_list") and not cameras:
                try:
                    parsed = parse_kml(payload, source_document=candidate["url"])
                except KmlParseError as exc:
                    kml_errors.append(f"{candidate['key']}: {exc}")
                    print(f"OK ({outcome['http_status']}) but not usable KML: {exc}")
                    results.append({**candidate, **outcome})
                    continue
                cameras = parsed
                camera_source = candidate["url"]
                outcome["cameras_parsed"] = len(parsed)

            if candidate["role"] == "licence_and_terms":
                for snippet in extract_licence_snippets(payload):
                    if snippet not in licence_snippets:
                        licence_snippets.append(snippet)

            print(f"OK ({outcome['http_status']}, {outcome['cameras_parsed']} cameras)")
        else:
            print(f"FAILED ({outcome['error']})")

        results.append({**candidate, **outcome})

    manifest_problems = validate_camera_manifest(cameras) if cameras else []
    licence_verified = bool(licence_snippets)

    if cameras and not manifest_problems and licence_verified:
        status = "RESOLVED"
        summary = (
            f"{len(cameras)} cameras parsed structurally from the official KML "
            f"({camera_source}), and the catalogue page's terms-of-use text was "
            "retrieved for the record."
        )
    elif cameras and not manifest_problems:
        status = "PARTIAL"
        summary = (
            f"{len(cameras)} cameras parsed from the official KML, but the "
            "catalogue page carrying the licence / terms of use could not be "
            "retrieved. Provenance is incomplete: a human must confirm the "
            "terms before any frame is acquired."
        )
    elif cameras:
        status = "PARTIAL"
        summary = (
            f"{len(cameras)} cameras parsed, but the camera manifest failed "
            f"validation with {len(manifest_problems)} problem(s)."
        )
    else:
        status = "UNRESOLVED"
        summary = (
            "No camera could be parsed from an official Madrid KML. VIS-001 "
            "stops here rather than substituting another image source or "
            "guessing camera endpoints from page markup: the experiment is "
            "defined over the official Madrid open data."
        )

    record = {
        "experiment_id": config.EXPERIMENT_ID,
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "summary": summary,
        "camera_discovery_method": (
            "structural KML <Placemark> parsing (name, Point/coordinates, and "
            "the image endpoint attached to that Placemark). Image URLs are "
            "never harvested by scanning arbitrary HTML."
        ),
        "camera_source_document": camera_source,
        "cameras_parsed": len(cameras),
        "camera_manifest_problems": manifest_problems,
        "kml_parse_errors": kml_errors,
        "candidates": results,
        "licence_snippets_verbatim": licence_snippets,
        "licence_verified_from_dataset_page": licence_verified,
        "licence_conclusion": (
            "NOT ESTABLISHED BY THIS SCRIPT — a human must read the verbatim "
            "snippets above and the catalogue's terms-of-use page before any "
            "image is redistributed. VIS-001 commits no imagery to git in any "
            "case."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if cameras:
        written = write_camera_manifest(config.CAMERA_MANIFEST_PATH, cameras)
        print(f"\ncamera manifest: {config.CAMERA_MANIFEST_PATH} ({written} cameras)")
    else:
        print(
            "\ncamera manifest NOT written: no camera was parsed, and VIS-001 "
            "does not ship a fabricated camera list."
        )

    print(f"status: {status}")
    print(summary)
    for problem in manifest_problems:
        print(f"  - {problem}")
    print(f"provenance: {args.output}")
    return 0 if status == "RESOLVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
