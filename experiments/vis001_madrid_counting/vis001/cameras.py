"""Camera discovery from the official Madrid KML, and the frozen camera choice.

Two responsibilities, both of which must happen **before** any image is scored:

1. **Parse the official KML structurally.** Each camera is a ``<Placemark>``
   carrying a name, a ``<Point>`` and an image endpoint. Cameras are read out of
   that structure — never by scanning a page for anything that looks like a
   ``.jpg``. A URL is only accepted as a camera image when it is attached to a
   specific Placemark, so every row in the camera manifest is traceable to one
   entry in the official dataset.

2. **Select the eight benchmark cameras deterministically, before inference.**
   The procedure below uses only published geographic metadata. It never opens
   an image, never runs the model, and never sees a prediction, so it cannot be
   tuned — even accidentally — to favour RF-DETR.

Standard library only: this module must stay testable in ordinary CI.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import asdict, dataclass, fields
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree

#: KML 2.2 and the older 2.0/2.1 namespaces Madrid has published over time.
_KML_NAMESPACES = (
    "http://www.opengis.net/kml/2.2",
    "http://earth.google.com/kml/2.2",
    "http://earth.google.com/kml/2.1",
    "http://earth.google.com/kml/2.0",
)

#: Image extensions accepted for a camera endpoint. Checked against the URL
#: *path*, so a query string cannot smuggle in a non-image.
_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")

#: Field names inside <ExtendedData> that may carry a camera identifier.
_ID_FIELD_NAMES = (
    "id", "cod", "codigo", "código", "camera_id", "idcamara", "id_camara",
)

#: Field names inside <ExtendedData> that may carry the image endpoint.
_URL_FIELD_NAMES = ("url", "img", "image", "imagen", "urlimagen", "url_imagen", "foto")

CAMERA_MANIFEST_COLUMNS: tuple[str, ...] = (
    "camera_id",
    "camera_name",
    "latitude",
    "longitude",
    "image_url",
    "source_document",
)


class KmlParseError(ValueError):
    """Raised when the payload is not a KML document we can read."""


@dataclass(frozen=True)
class CameraRecord:
    """One camera as published by the official Madrid dataset.

    Every field comes from the KML. Nothing here is inferred: a camera without
    coordinates or without an image endpoint is dropped rather than completed
    from a guess, because it could not be used as a benchmark camera anyway.
    """

    camera_id: str
    camera_name: str
    latitude: str
    longitude: str
    image_url: str
    source_document: str

    @property
    def lat(self) -> float:
        return float(self.latitude)

    @property
    def lon(self) -> float:
        return float(self.longitude)

    def as_row(self) -> dict[str, str]:
        return asdict(self)


# --------------------------------------------------------------------------
# KML parsing
# --------------------------------------------------------------------------


class _ImageSrcCollector(HTMLParser):
    """Collect ``<img src>`` values from one Placemark's description CDATA.

    Madrid puts the camera's image endpoint inside an HTML balloon in the
    Placemark ``<description>``. Reading it with a real HTML parser, scoped to a
    single Placemark, keeps the URL attributable to that camera. This is the
    opposite of scanning a whole page for anything ending in ``.jpg``, which
    would happily pick up a logo, a legend icon or an unrelated banner.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        for name, value in attrs:
            if name.lower() == "src" and value:
                self.sources.append(value.strip())


def _localname(tag: str) -> str:
    """Strip the namespace so parsing survives Madrid changing KML versions."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _child_text(element: ElementTree.Element, name: str) -> str:
    for child in element:
        if _localname(child.tag) == name:
            return (child.text or "").strip()
    return ""


def is_image_url(url: str) -> bool:
    """True when the URL's *path* ends in an accepted image suffix."""
    if not url.lower().startswith(("http://", "https://")):
        return False
    path = url.split("?", 1)[0].split("#", 1)[0]
    return path.lower().endswith(_IMAGE_SUFFIXES)


def canonical_image_endpoint(url: str) -> str:
    """Stable identity for a camera image endpoint: scheme + host + path only.

    Madrid's official KML puts a volatile cache/version token in the image
    URL's query string (``?v=51444``), which changes on essentially every
    catalogue refresh without the camera itself changing. Stripping the query
    string and fragment gives an identity that is stable across that churn,
    while still distinguishing one camera's endpoint from another's — only the
    path is compared, never normalised away.

    ``https://informo.madrid.es/cameras/Camara05324.jpg?v=51444`` and
    ``…Camara05324.jpg?v=76738`` canonicalise to the same value;
    ``…Camara05324.jpg`` and ``…Camara09999.jpg`` do not.
    """
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _extended_data(placemark: ElementTree.Element) -> dict[str, str]:
    """Flatten ``<ExtendedData>`` into ``{lowercased name: value}``.

    Handles both the ``<Data name=…><value>`` and ``<SimpleData name=…>`` forms.
    """
    collected: dict[str, str] = {}
    for element in placemark.iter():
        local = _localname(element.tag)
        name = (element.get("name") or "").strip().lower()
        if not name:
            continue
        if local == "Data":
            value = _child_text(element, "value")
        elif local == "SimpleData":
            value = (element.text or "").strip()
        else:
            continue
        if value:
            collected[name] = value
    return collected


def _image_url_for(placemark: ElementTree.Element, extended: dict[str, str]) -> str:
    """Resolve the camera's image endpoint from this Placemark alone."""
    for key in _URL_FIELD_NAMES:
        candidate = extended.get(key, "")
        if is_image_url(candidate):
            return candidate

    description = _child_text(placemark, "description")
    if description:
        collector = _ImageSrcCollector()
        collector.feed(description)
        for candidate in collector.sources:
            if is_image_url(candidate):
                return candidate
    return ""


def _coordinates_for(placemark: ElementTree.Element) -> tuple[str, str]:
    """Return ``(latitude, longitude)`` as strings, or ``("", "")``.

    KML orders coordinates ``lon,lat[,alt]`` — the reverse of the usual
    lat/lon convention, which is the single easiest thing to get wrong here.
    """
    for element in placemark.iter():
        if _localname(element.tag) != "coordinates":
            continue
        raw = (element.text or "").strip()
        if not raw:
            continue
        first = raw.split()[0]
        parts = first.split(",")
        if len(parts) < 2:
            continue
        try:
            lon, lat = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            continue
        return (f"{lat:.6f}", f"{lon:.6f}")
    return ("", "")


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-").lower()
    return cleaned[:48]


def _camera_id_for(
    name: str, image_url: str, extended: dict[str, str], ordinal: int
) -> str:
    """Derive a stable camera id, preferring what the source itself publishes.

    Order: an explicit id field in ``ExtendedData`` → the image URL's filename
    stem → a slug of the published name → the Placemark's ordinal position. The
    ordinal is the last resort precisely because it is the only one that is not
    a property of the camera, and it is recorded as such.
    """
    for key in _ID_FIELD_NAMES:
        value = extended.get(key, "").strip()
        if value:
            return _slug(value) or value
    if image_url:
        stem = Path(image_url.split("?", 1)[0]).stem
        if stem:
            return _slug(stem)
    if name:
        slug = _slug(name)
        if slug:
            return slug
    return f"placemark-{ordinal:04d}"


def parse_kml(payload: bytes, *, source_document: str) -> list[CameraRecord]:
    """Extract cameras from an official KML document.

    A Placemark becomes a camera only when it has **both** usable coordinates
    and an image endpoint attributable to it. Placemarks missing either are
    skipped: they cannot serve as benchmark cameras, and filling in the gap
    would be fabrication.

    Duplicate camera ids are de-duplicated, first occurrence winning, so a KML
    that lists a camera twice does not inflate the population the selection
    procedure draws from.
    """
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise KmlParseError(f"payload is not parseable XML: {exc}") from exc

    if _localname(root.tag) != "kml":
        raise KmlParseError(
            f"root element is <{_localname(root.tag)}>, expected <kml>. "
            "VIS-001 reads cameras out of the official KML structure and will "
            "not fall back to scraping a page for image-looking URLs."
        )

    cameras: list[CameraRecord] = []
    seen: set[str] = set()
    ordinal = 0
    for element in root.iter():
        if _localname(element.tag) != "Placemark":
            continue
        ordinal += 1

        extended = _extended_data(element)
        name = _child_text(element, "name")
        image_url = _image_url_for(element, extended)
        latitude, longitude = _coordinates_for(element)
        if not image_url or not latitude:
            continue

        camera_id = _camera_id_for(name, image_url, extended, ordinal)
        if camera_id in seen:
            continue
        seen.add(camera_id)

        cameras.append(
            CameraRecord(
                camera_id=camera_id,
                camera_name=name,
                latitude=latitude,
                longitude=longitude,
                image_url=image_url,
                source_document=source_document,
            )
        )
    return cameras


def kml_namespaces() -> tuple[str, ...]:
    """The KML namespaces this parser has been checked against."""
    return _KML_NAMESPACES


# --------------------------------------------------------------------------
# Camera manifest I/O
# --------------------------------------------------------------------------


def write_camera_manifest(path: Path, cameras: Iterable[CameraRecord]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CAMERA_MANIFEST_COLUMNS))
        writer.writeheader()
        for camera in cameras:
            writer.writerow(camera.as_row())
            count += 1
    return count


def read_camera_manifest(path: Path) -> list[CameraRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if header != CAMERA_MANIFEST_COLUMNS:
            raise KmlParseError(
                f"{path}: unexpected columns.\n"
                f"  expected: {list(CAMERA_MANIFEST_COLUMNS)}\n"
                f"  found:    {list(header)}"
            )
        return [
            CameraRecord(
                **{
                    f.name: (row.get(f.name) or "").strip()
                    for f in fields(CameraRecord)
                }
            )
            for row in reader
        ]


def validate_camera_manifest(cameras: Sequence[CameraRecord]) -> list[str]:
    """Return every problem found. Empty list means the manifest is usable."""
    problems: list[str] = []
    seen: set[str] = set()
    for index, camera in enumerate(cameras):
        where = f"row {index + 1}"
        if not camera.camera_id:
            problems.append(f"{where}: empty camera_id")
        elif camera.camera_id in seen:
            problems.append(f"{where}: duplicate camera_id {camera.camera_id!r}")
        else:
            seen.add(camera.camera_id)

        if not is_image_url(camera.image_url):
            problems.append(f"{where}: image_url is not an image endpoint")
        if not camera.source_document:
            problems.append(f"{where}: empty source_document")

        for field_name in ("latitude", "longitude"):
            raw = getattr(camera, field_name)
            try:
                value = float(raw)
            except ValueError:
                problems.append(f"{where}: {field_name} not numeric: {raw!r}")
                continue
            limit = 90.0 if field_name == "latitude" else 180.0
            if not -limit <= value <= limit:
                problems.append(f"{where}: {field_name} out of range: {raw!r}")
    return problems


# --------------------------------------------------------------------------
# Frozen camera selection (§7 of the protocol)
# --------------------------------------------------------------------------

#: Bumped only if the selection procedure itself changes. A selected-camera set
#: is only comparable with another set produced by the same procedure version.
SELECTION_PROCEDURE_VERSION = "1.0"

#: Compass sectors, in the order they are filled.
SECTOR_NAMES: tuple[str, ...] = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def _centroid(cameras: Sequence[CameraRecord]) -> tuple[float, float]:
    return (
        sum(camera.lat for camera in cameras) / len(cameras),
        sum(camera.lon for camera in cameras) / len(cameras),
    )


def _bearing_sector(lat: float, lon: float, origin: tuple[float, float]) -> str:
    """Which 45° compass sector a camera falls in, seen from the centroid.

    Longitude is scaled by ``cos(latitude)`` so that a degree east covers the
    same ground distance as a degree north. Without it, Madrid's ~40° latitude
    would stretch the east-west axis by about 30% and skew every sector.
    """
    origin_lat, origin_lon = origin
    north = lat - origin_lat
    east = (lon - origin_lon) * math.cos(math.radians(origin_lat))
    if north == 0.0 and east == 0.0:
        return SECTOR_NAMES[0]
    # Bearing clockwise from north, shifted by half a sector so that due north
    # lands in the middle of sector "N" rather than on its boundary.
    bearing = (math.degrees(math.atan2(east, north)) + 360.0 + 22.5) % 360.0
    return SECTOR_NAMES[int(bearing // 45.0)]


def _distance(camera: CameraRecord, origin: tuple[float, float]) -> float:
    origin_lat, origin_lon = origin
    north = camera.lat - origin_lat
    east = (camera.lon - origin_lon) * math.cos(math.radians(origin_lat))
    return math.hypot(north, east)


@dataclass(frozen=True)
class CameraSelection:
    """The eight benchmark cameras, plus how they were chosen."""

    procedure_version: str
    camera_ids: tuple[str, ...]
    sector_of_camera: dict[str, str]
    cameras_considered: int
    sectors_empty: tuple[str, ...]

    @property
    def is_complete(self) -> bool:
        return len(self.camera_ids) == len(SECTOR_NAMES)


def select_cameras(
    cameras: Sequence[CameraRecord], *, count: int = len(SECTOR_NAMES)
) -> CameraSelection:
    """Choose ``count`` benchmark cameras deterministically, before inference.

    The procedure, frozen and stated in full because the whole benchmark rests
    on the eight cameras it picks:

    1. Compute the centroid of every camera published in the KML.
    2. Assign each camera to one of eight 45° compass sectors around that
       centroid (N, NE, E, SE, S, SW, W, NW).
    3. Within each sector, order cameras by distance from the centroid, then by
       ``camera_id`` to break ties, and take the **median** one. The median
       rather than the nearest or the farthest: the nearest would concentrate
       all eight in the city centre and the farthest would concentrate them on
       the ring road, and either would collapse the scene variety the sectors
       exist to create.
    4. Visit sectors in compass order. If a sector is empty, fill the slot from
       the sector that still has the most unselected cameras, again by median,
       so a gap in the published coverage does not silently yield seven cameras.

    Why this rather than "the first eight sorted ids": sorted ids follow the
    municipality's numbering, which tracks installation batches, so the first
    eight tend to be neighbouring cameras on the same few roads — one scene
    type, one mounting style, one background. Spreading across compass sectors
    of the city is a proxy for the pedestrian density, road type, camera height
    and background complexity the protocol asks to vary.

    Crucially, every input here is **published geographic metadata**. No image
    is opened, no model is run, and no prediction is consulted, so the choice
    cannot be tuned to flatter RF-DETR.
    """
    if not cameras:
        return CameraSelection(SELECTION_PROCEDURE_VERSION, (), {}, 0, SECTOR_NAMES)

    origin = _centroid(cameras)
    by_sector: dict[str, list[CameraRecord]] = {name: [] for name in SECTOR_NAMES}
    for camera in cameras:
        by_sector[_bearing_sector(camera.lat, camera.lon, origin)].append(camera)

    for sector in by_sector:
        by_sector[sector].sort(key=lambda c: (_distance(c, origin), c.camera_id))

    selected: list[CameraRecord] = []
    sector_of: dict[str, str] = {}
    empty: list[str] = []

    def take_median(sector: str) -> CameraRecord | None:
        pool = by_sector[sector]
        if not pool:
            return None
        return pool.pop(len(pool) // 2)

    for sector in SECTOR_NAMES:
        if len(selected) >= count:
            break
        chosen = take_median(sector)
        if chosen is None:
            empty.append(sector)
            continue
        selected.append(chosen)
        sector_of[chosen.camera_id] = sector

    # Backfill the slots left by empty sectors, always from the richest
    # remaining sector so the spread degrades as gracefully as it can.
    while len(selected) < count:
        richest = max(SECTOR_NAMES, key=lambda name: (len(by_sector[name]), name))
        chosen = take_median(richest)
        if chosen is None:
            break
        selected.append(chosen)
        sector_of[chosen.camera_id] = f"{richest} (backfill)"

    return CameraSelection(
        procedure_version=SELECTION_PROCEDURE_VERSION,
        camera_ids=tuple(camera.camera_id for camera in selected),
        sector_of_camera=sector_of,
        cameras_considered=len(cameras),
        sectors_empty=tuple(empty),
    )
