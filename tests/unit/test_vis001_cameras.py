"""VIS-001 camera discovery and the frozen benchmark-camera selection.

These are the pre-data audit regressions. Each test names the loophole it
closes, because every one of them is a way a benchmark could look healthy while
measuring the wrong thing.
"""

from __future__ import annotations

import pytest
from vis001.cameras import (
    SECTOR_NAMES,
    SELECTION_PROCEDURE_VERSION,
    CameraRecord,
    KmlParseError,
    is_image_url,
    kml_namespaces,
    parse_kml,
    read_camera_manifest,
    select_cameras,
    validate_camera_manifest,
    write_camera_manifest,
)


def _kml(placemarks: str, ns: str = "http://www.opengis.net/kml/2.2") -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<kml xmlns="{ns}"><Document>{placemarks}</Document></kml>'
    ).encode("utf-8")


def _placemark(
    name: str = "PUERTA DEL SOL",
    lon: str = "-3.7038",
    lat: str = "40.4168",
    img: str = "https://informo.madrid.es/cameras/Camara01.jpg",
    extended: str = "",
) -> str:
    description = (
        f"<description><![CDATA[<div><img src=\"{img}\" width=\"320\"></div>]]>"
        "</description>"
        if img
        else ""
    )
    point = (
        f"<Point><coordinates>{lon},{lat},0</coordinates></Point>" if lon else ""
    )
    return f"<Placemark><name>{name}</name>{description}{extended}{point}</Placemark>"


# --------------------------------------------------------------------------
# Structural KML parsing (audit finding 1)
# --------------------------------------------------------------------------


def test_parses_camera_from_placemark_structure():
    cameras = parse_kml(_kml(_placemark()), source_document="kml")
    assert len(cameras) == 1
    camera = cameras[0]
    assert camera.camera_name == "PUERTA DEL SOL"
    assert camera.image_url == "https://informo.madrid.es/cameras/Camara01.jpg"
    assert camera.camera_id == "camara01"
    assert camera.source_document == "kml"


def test_kml_coordinates_are_lon_lat_not_lat_lon():
    """KML orders coordinates lon,lat — the single easiest thing to invert."""
    cameras = parse_kml(
        _kml(_placemark(lon="-3.7038", lat="40.4168")), source_document="kml"
    )
    assert cameras[0].latitude == "40.416800"
    assert cameras[0].longitude == "-3.703800"


@pytest.mark.parametrize("namespace", list(kml_namespaces()))
def test_parses_every_supported_kml_namespace(namespace):
    cameras = parse_kml(_kml(_placemark(), ns=namespace), source_document="kml")
    assert len(cameras) == 1


def test_image_url_may_come_from_extended_data():
    extended = (
        "<ExtendedData>"
        '<Data name="url"><value>https://informo.madrid.es/c/9.jpg</value></Data>'
        "</ExtendedData>"
    )
    cameras = parse_kml(
        _kml(_placemark(img="", extended=extended)), source_document="kml"
    )
    assert cameras[0].image_url == "https://informo.madrid.es/c/9.jpg"


def test_published_id_field_wins_over_the_url_stem():
    extended = (
        '<ExtendedData><Data name="codigo"><value>PM-0042</value></Data>'
        "</ExtendedData>"
    )
    cameras = parse_kml(_kml(_placemark(extended=extended)), source_document="kml")
    assert cameras[0].camera_id == "pm-0042"


def test_image_urls_outside_a_placemark_are_never_harvested():
    """The core finding: no blind scan of arbitrary markup.

    A logo and a legend icon sit in the Document body. Neither belongs to a
    camera, and a regex over the raw page would return both.
    """
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        "<name>Camaras</name>"
        "<description><![CDATA[<img src=\"https://madrid.es/logo.png\">"
        "<img src=\"https://madrid.es/legend.jpg\">]]></description>"
        + _placemark()
        + "</Document></kml>"
    ).encode("utf-8")
    cameras = parse_kml(payload, source_document="kml")
    assert len(cameras) == 1
    assert "logo" not in cameras[0].image_url
    assert "legend" not in cameras[0].image_url


def test_placemark_without_coordinates_is_dropped_not_completed():
    cameras = parse_kml(_kml(_placemark(lon="")), source_document="kml")
    assert cameras == []


def test_placemark_without_an_image_endpoint_is_dropped():
    cameras = parse_kml(_kml(_placemark(img="")), source_document="kml")
    assert cameras == []


def test_out_of_range_coordinates_are_rejected():
    cameras = parse_kml(
        _kml(_placemark(lon="-999", lat="500")), source_document="kml"
    )
    assert cameras == []


def test_duplicate_camera_ids_are_collapsed():
    """A KML listing a camera twice must not inflate the selection pool."""
    cameras = parse_kml(_kml(_placemark() + _placemark()), source_document="kml")
    assert len(cameras) == 1


def test_non_kml_payload_is_refused_rather_than_scraped():
    """Well-formed HTML full of image URLs is still refused: wrong root element.

    This is the guard against silently falling back to page-scraping when the
    KML endpoint returns an error page instead of a document.
    """
    html = b'<html><body><img src="https://x/cam.jpg"/></body></html>'
    with pytest.raises(KmlParseError, match="expected <kml>"):
        parse_kml(html, source_document="page")


def test_unparseable_payload_raises():
    with pytest.raises(KmlParseError, match="not parseable XML"):
        parse_kml(b"{not xml at all", source_document="page")


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://x/cam.jpg", True),
        ("https://x/cam.JPEG", True),
        ("https://x/cam.png", True),
        ("https://x/cam.jpg?ts=1", True),
        ("https://x/cam.gif", False),
        ("https://x/camera", False),
        ("ftp://x/cam.jpg", False),
        ("/relative/cam.jpg", False),
        ("https://x/page.html?a=cam.jpg", False),
    ],
)
def test_image_url_recognition(url, expected):
    """A query string must not smuggle a non-image past the check."""
    assert is_image_url(url) is expected


# --------------------------------------------------------------------------
# Camera manifest (audit finding 2)
# --------------------------------------------------------------------------


def _camera(camera_id="c1", lat="40.4168", lon="-3.7038") -> CameraRecord:
    return CameraRecord(
        camera_id=camera_id,
        camera_name=f"CAM {camera_id}",
        latitude=lat,
        longitude=lon,
        image_url=f"https://informo.madrid.es/cameras/{camera_id}.jpg",
        source_document="https://informo.madrid.es/informo/tmadrid/CCTV.kml",
    )


def test_camera_manifest_round_trips(tmp_path):
    path = tmp_path / "camera_manifest.csv"
    cameras = [_camera("c1"), _camera("c2")]
    assert write_camera_manifest(path, cameras) == 2
    assert read_camera_manifest(path) == cameras


def test_camera_manifest_validation_accepts_a_good_row():
    assert validate_camera_manifest([_camera()]) == []


def test_camera_manifest_rejects_duplicates_and_bad_geometry():
    problems = validate_camera_manifest(
        [_camera("c1"), _camera("c1"), _camera("c2", lat="999")]
    )
    assert any("duplicate camera_id" in p for p in problems)
    assert any("latitude out of range" in p for p in problems)


def test_camera_manifest_rejects_a_non_image_endpoint():
    bad = CameraRecord("c1", "n", "40.0", "-3.0", "https://x/page.html", "kml")
    problems = validate_camera_manifest([bad])
    assert any("not an image endpoint" in p for p in problems)


def test_camera_manifest_rejects_missing_provenance():
    bad = CameraRecord("c1", "n", "40.0", "-3.0", "https://x/c.jpg", "")
    assert any("empty source_document" in p for p in validate_camera_manifest([bad]))


# --------------------------------------------------------------------------
# Frozen camera selection (audit finding 3)
# --------------------------------------------------------------------------


def _ring(count: int) -> list[CameraRecord]:
    """Cameras spread evenly around a circle, ids deliberately anti-correlated
    with position so that "first 8 sorted ids" and the real procedure differ."""
    import math

    cameras = []
    for index in range(count):
        angle = 2 * math.pi * index / count
        cameras.append(
            _camera(
                camera_id=f"cam{count - index:03d}",
                lat=f"{40.4168 + 0.05 * math.cos(angle):.6f}",
                lon=f"{-3.7038 + 0.05 * math.sin(angle):.6f}",
            )
        )
    return cameras


def test_selection_returns_exactly_eight():
    selection = select_cameras(_ring(64))
    assert len(selection.camera_ids) == 8
    assert selection.is_complete
    assert selection.procedure_version == SELECTION_PROCEDURE_VERSION


def test_selection_spans_all_eight_compass_sectors():
    """The point of the procedure: geographic spread, not id adjacency."""
    selection = select_cameras(_ring(64))
    assert set(selection.sector_of_camera.values()) == set(SECTOR_NAMES)


def test_selection_is_not_the_first_eight_sorted_ids():
    """The exact loophole replaced.

    Sorted ids follow installation batches, which cluster geographically.
    """
    cameras = _ring(64)
    first_eight_sorted = sorted(camera.camera_id for camera in cameras)[:8]
    selection = select_cameras(cameras)
    assert sorted(selection.camera_ids) != first_eight_sorted


def test_selection_is_deterministic():
    cameras = _ring(64)
    assert select_cameras(cameras).camera_ids == select_cameras(cameras).camera_ids


def test_selection_is_independent_of_input_order():
    cameras = _ring(64)
    forward = select_cameras(cameras).camera_ids
    backward = select_cameras(list(reversed(cameras))).camera_ids
    assert sorted(forward) == sorted(backward)


def test_selection_uses_no_imagery_and_no_model_output():
    """Every input is published geographic metadata.

    CameraRecord carries no pixel data and no score, so the procedure has
    nothing model-derived to key on even in principle.
    """
    field_names = {f.name for f in CameraRecord.__dataclass_fields__.values()}
    assert field_names == {
        "camera_id",
        "camera_name",
        "latitude",
        "longitude",
        "image_url",
        "source_document",
    }


def test_empty_sectors_are_reported_and_backfilled():
    """A gap in published coverage must not silently yield seven cameras."""
    import math

    # A tight arc: every camera falls in roughly the same direction.
    cameras = [
        _camera(
            camera_id=f"cam{index:03d}",
            lat=f"{40.4168 + 0.05 * math.cos(index * 0.01):.6f}",
            lon=f"{-3.7038 + 0.05 * math.sin(index * 0.01):.6f}",
        )
        for index in range(40)
    ]
    selection = select_cameras(cameras)
    assert len(selection.camera_ids) == 8
    assert selection.sectors_empty
    assert any("backfill" in sector for sector in selection.sector_of_camera.values())


def test_selection_on_too_few_cameras_is_incomplete_not_padded():
    selection = select_cameras(_ring(3))
    assert len(selection.camera_ids) == 3
    assert not selection.is_complete


def test_selection_on_no_cameras_is_empty():
    selection = select_cameras([])
    assert selection.camera_ids == ()
    assert not selection.is_complete
    assert selection.cameras_considered == 0
