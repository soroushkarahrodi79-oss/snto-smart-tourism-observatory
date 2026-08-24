#!/usr/bin/env python3
"""Resolve and record the official Madrid traffic-camera image source.

This script establishes the *provenance* half of VIS-001. It does not download
frames; it answers the questions that must be answered before any frame is
downloaded (§6 of the protocol):

1. Which official endpoint publishes the cameras?
2. Is it reachable from this machine right now?
3. What licence or terms-of-use statement ships with it?
4. Are image URLs stable, or dynamically generated per request?

The candidate endpoints below are the entries in the Ayuntamiento de Madrid open
data catalogue. They are recorded here as *candidates*: this script's job is to
confirm or refute each one at runtime and write the result to
``data/source_resolution.json``. Nothing downstream may treat an unconfirmed
candidate as a verified source.

Camera identifiers and image URLs are deliberately NOT hardcoded. They are
parsed out of whatever the official catalogue actually serves, so the experiment
can never ship a fabricated camera list.

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

#: Candidate official endpoints, in preference order. Each is an entry point in
#: the Ayuntamiento de Madrid open data catalogue (datos.madrid.es) or the
#: municipal traffic portal it points at (informo.madrid.es). Third-party
#: mirrors are deliberately absent: the protocol forbids using one while the
#: official source exists.
CANDIDATE_SOURCES: tuple[dict[str, str], ...] = (
    {
        "key": "datos_madrid_dataset_trafico_camaras",
        "kind": "catalogue_page",
        "url": "https://datos.madrid.es/portal/site/egob/menuitem."
               "c05c1f754a33a9fbe4b2e4b284f1a5a0/"
               "?vgnextoid=8803c23866b93410VgnVCM1000000b205a0aRCRD",
        "note": "Catalogue page for the dataset 'Tráfico. Cámaras'. Carries the "
                "licence statement and links the distributions.",
    },
    {
        "key": "datos_madrid_kml_trafico_camaras",
        "kind": "distribution_kml",
        "url": "https://datos.madrid.es/egob/catalogo/"
               "202088-0-trafico-camaras.kml",
        "note": "KML distribution: camera positions, and the image URL each "
                "camera exposes. This is the authoritative list of cameras.",
    },
    {
        "key": "datos_madrid_dataset_calle30_camaras",
        "kind": "catalogue_page",
        "url": "https://datos.madrid.es/egob/catalogo/"
               "212166-0-trafico-calle30-camaras",
        "note": "Catalogue page for 'Tráfico Calle 30. Cámaras', a second "
                "camera set with its own terms.",
    },
    {
        "key": "informo_portal_root",
        "kind": "portal",
        "url": "https://informo.madrid.es/",
        "note": "Municipal traffic portal that hosts the camera image "
                "endpoints referenced by the KML.",
    },
)

#: Any absolute http(s) URL that looks like an image endpoint.
_IMAGE_URL_PATTERN = re.compile(
    r"https?://[^\s\"'<>]+?\.(?:jpe?g|png)(?:\?[^\s\"'<>]*)?", re.IGNORECASE
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


def extract_image_urls(payload: bytes) -> list[str]:
    """Pull image endpoints out of a catalogue payload (KML, HTML or JSON).

    Returns them de-duplicated and sorted. An empty list means the payload did
    not declare any — which is a finding, not a reason to invent one.
    """
    try:
        text = payload.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - unreadable payload declares nothing
        return []
    return sorted({match.group(0) for match in _IMAGE_URL_PATTERN.finditer(text)})


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
        help="where to write the resolution record",
    )
    args = parser.parse_args()

    results: list[dict[str, object]] = []
    all_image_urls: set[str] = set()
    licence_snippets: list[str] = []

    for candidate in CANDIDATE_SOURCES:
        print(f"probing {candidate['key']} … ", end="", flush=True)
        outcome = probe(candidate["url"], timeout=args.timeout)
        payload = outcome.pop("_payload")

        if outcome["reachable"] and outcome["http_status"] == 200:
            found = extract_image_urls(payload)
            all_image_urls.update(found)
            outcome["image_urls_declared"] = len(found)
            outcome["image_url_sample"] = found[:5]
            for snippet in extract_licence_snippets(payload):
                if snippet not in licence_snippets:
                    licence_snippets.append(snippet)
            print(f"OK ({outcome['http_status']}, {len(found)} image URLs)")
        else:
            outcome["image_urls_declared"] = 0
            outcome["image_url_sample"] = []
            print(f"FAILED ({outcome['error']})")

        results.append({**candidate, **outcome})

    resolved = any(
        entry["reachable"] and entry["http_status"] == 200 for entry in results
    )
    has_images = bool(all_image_urls)

    if resolved and has_images:
        status = "RESOLVED"
        summary = (
            f"{len(all_image_urls)} distinct image endpoints declared by the "
            "official catalogue."
        )
    elif resolved:
        status = "PARTIAL"
        summary = (
            "At least one official endpoint responded, but no image endpoint "
            "was declared in the payloads. The camera image URLs must be "
            "located manually before acquisition can proceed."
        )
    else:
        status = "UNRESOLVED"
        summary = (
            "No official Madrid endpoint could be reached from this machine. "
            "VIS-001 stops here rather than substituting another image source: "
            "the experiment is defined over official Madrid open data."
        )

    record = {
        "experiment_id": config.EXPERIMENT_ID,
        "resolved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "summary": summary,
        "candidates": results,
        "image_urls_discovered": sorted(all_image_urls),
        "licence_snippets_verbatim": licence_snippets,
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

    print()
    print(f"status: {status}")
    print(summary)
    print(f"written: {args.output}")
    return 0 if status == "RESOLVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
