"""VIS-001 provenance regressions for protocol deviation PD-001.

PD-001 (2026-08-25) added an official licence-metadata *fallback*
(`datos.gob.es`) after the municipal `datos.madrid.es` source timed out
repeatedly. These tests pin the exact shape of that change so it can never drift
into something it was explicitly forbidden from becoming:

* the authoritative camera source stays the Informo Madrid KML;
* the municipal canonical catalogue stays the *primary* licence source;
* `datos.gob.es` is a licence/metadata fallback ONLY — never a camera source;
* the three documents (config, experiment.yaml, PREREGISTRATION.md) agree;
* no frozen numeric parameter moved.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from vis001 import config

EXPERIMENT_ROOT = (
    Path(__file__).resolve().parents[2] / "experiments" / "vis001_madrid_counting"
)
PREREGISTRATION = EXPERIMENT_ROOT / "PREREGISTRATION.md"
EXPERIMENT_YAML = EXPERIMENT_ROOT / "experiment.yaml"

INFORMO_KML = "https://informo.madrid.es/informo/tmadrid/CCTV.kml"
DATOS_MADRID = "https://datos.madrid.es/dataset/202088-0-trafico-camaras"
DATOS_GOB_ES = "https://datos.gob.es/es/catalogo/l01280796-trafico-camaras1.xml"


def _flattened(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


@pytest.fixture(scope="module")
def prereg_text() -> str:
    return _flattened(PREREGISTRATION)


@pytest.fixture(scope="module")
def yaml_text() -> str:
    return _flattened(EXPERIMENT_YAML)


@pytest.fixture(scope="module")
def resolver():
    """Import scripts/resolve_sources.py by path (it is not a package module)."""
    path = EXPERIMENT_ROOT / "scripts" / "resolve_sources.py"
    spec = importlib.util.spec_from_file_location("vis001_resolve_sources", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# The camera source is unchanged
# --------------------------------------------------------------------------


def test_informo_kml_endpoint_is_unchanged():
    assert config.MADRID_CCTV_KML_URL == INFORMO_KML


def test_camera_list_in_yaml_is_still_only_the_informo_kml(yaml_text):
    assert f"camera_list: {INFORMO_KML}" in yaml_text


# --------------------------------------------------------------------------
# Licence sources: municipal primary, national fallback
# --------------------------------------------------------------------------


def test_municipal_catalogue_remains_the_primary_licence_source():
    assert config.MADRID_DATASET_PAGE_URL == DATOS_MADRID


def test_datos_gob_es_fallback_constant_is_exact():
    assert config.MADRID_DATASET_NATIONAL_FALLBACK_URL == DATOS_GOB_ES


def test_experiment_yaml_distinguishes_primary_from_fallback(yaml_text):
    assert DATOS_MADRID in yaml_text
    assert DATOS_GOB_ES in yaml_text
    assert "primary:" in yaml_text
    assert "fallback:" in yaml_text
    assert "fallback_scope: licence_metadata_only" in yaml_text
    # The primary URL must be introduced as the primary, the fallback as fallback.
    assert yaml_text.index(DATOS_MADRID) < yaml_text.index(DATOS_GOB_ES)


def test_datos_gob_es_is_described_as_licence_metadata_fallback_only(
    yaml_text, resolver
):
    assert "licence_metadata_only" in yaml_text

    candidates = {c["key"]: c for c in resolver.CANDIDATE_SOURCES}
    fallback = candidates["datos_gob_es_trafico_camaras_rdf"]
    assert fallback["url"] == DATOS_GOB_ES
    assert fallback["role"] == "licence_and_terms"
    assert "FALLBACK ONLY" in fallback["note"]


# --------------------------------------------------------------------------
# datos.gob.es must NEVER be a camera source
# --------------------------------------------------------------------------


def test_datos_gob_es_is_never_a_camera_source(resolver):
    for candidate in resolver.CANDIDATE_SOURCES:
        if candidate["url"] == DATOS_GOB_ES:
            assert not candidate["role"].startswith("camera_list")
    camera_urls = {
        c["url"]
        for c in resolver.CANDIDATE_SOURCES
        if c["role"].startswith("camera_list")
    }
    assert DATOS_GOB_ES not in camera_urls
    assert INFORMO_KML in camera_urls


def test_fallback_is_ordered_after_the_municipal_licence_source(resolver):
    keys = [c["key"] for c in resolver.CANDIDATE_SOURCES]
    assert "datos_madrid_dataset_trafico_camaras" in keys
    assert "datos_gob_es_trafico_camaras_rdf" in keys
    assert keys.index("datos_gob_es_trafico_camaras_rdf") > keys.index(
        "datos_madrid_dataset_trafico_camaras"
    )


# --------------------------------------------------------------------------
# PREREGISTRATION.md records PD-001, and A1/A2 are untouched
# --------------------------------------------------------------------------


def test_preregistration_records_pd_001(prereg_text):
    assert "## Protocol deviations" in prereg_text
    assert "PD-001 — Official licence-metadata fallback (2026-08-25)" in prereg_text
    # The empty-state placeholder must be gone.
    assert "None recorded." not in prereg_text
    # The three facts that make PD-001 legitimate.
    assert "357 cameras" in prereg_text
    assert DATOS_GOB_ES in prereg_text
    assert "CC BY 4.0" in prereg_text
    assert "provenance substitution only" in prereg_text


def test_pd_001_records_that_no_frozen_parameter_changed(prereg_text):
    pd = prereg_text.split("PD-001 — Official licence-metadata fallback")[1]
    assert "zero image frames had been acquired" in pd
    assert "no camera-selection rule" in pd
    assert "gate version" in pd
    assert "status = RESOLVED` is never forced by hand" in pd


def test_a1_and_a2_amendments_are_left_unchanged(prereg_text):
    assert "A1 — Pre-data audit corrections" in prereg_text
    assert "A2 — Pre-data statistical correctness" in prereg_text
    # PD-001 lives under deviations, after both amendments.
    assert prereg_text.index("A2 — Pre-data") < prereg_text.index("PD-001 —")


# --------------------------------------------------------------------------
# No frozen numeric parameter moved
# --------------------------------------------------------------------------


def test_no_frozen_numeric_parameter_changed():
    assert config.GATE_VERSION == "1.0"
    assert config.CONFIDENCE_THRESHOLD == 0.35
    assert config.EVAL_IOU_THRESHOLD == 0.50
    assert config.TARGET_CAMERAS == 8
    assert config.TARGET_FRAMES_PER_CAMERA == 20
    assert config.TARGET_FRAMES == 160
    assert config.EVAL_IMAGES_PER_CAMERA == 10
    assert config.EVAL_SET_SIZE == 80
    assert config.RANDOM_SEED == 20260824
    assert config.TARGET_CLASSES == ("person", "bicycle", "car", "bus")
    gate = config.GATE
    assert (gate.advance_min_macro_f1, gate.advance_max_count_wape) == (0.80, 0.20)
    assert (gate.advance_min_class_f1, gate.advance_max_camera_wape) == (0.65, 0.35)
    assert (gate.kill_below_macro_f1, gate.kill_above_count_wape) == (0.65, 0.35)
    assert (gate.kill_class_f1_below, gate.kill_min_failing_classes) == (0.50, 2)
    assert gate.kill_above_camera_wape_spread == 0.50


# --------------------------------------------------------------------------
# A licence-bearing fallback payload satisfies the existing snippet mechanism
# offline — no network, no new extraction path.
# --------------------------------------------------------------------------


def test_fallback_rdf_payload_satisfies_licence_snippet_mechanism(resolver):
    """The datos.gob.es RDF/XML declares CC BY 4.0, which the *existing*
    licence-snippet extractor already recognises. No new parsing was added."""
    payload = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<rdf:RDF xmlns:dcterms="http://purl.org/dc/terms/">'
        b"<dcterms:license>Creative Commons Attribution 4.0 International "
        b"(CC BY 4.0)</dcterms:license>"
        b"<dcterms:rights>Condiciones de uso: reutilizaci\xc3\xb3n permitida"
        b"</dcterms:rights>"
        b"</rdf:RDF>"
    )
    snippets = resolver.extract_licence_snippets(payload)
    assert snippets, "the CC BY 4.0 declaration should yield a licence snippet"
    # This is exactly the flag the resolver reads to decide licence verification.
    assert bool(snippets) is True


def test_empty_payload_does_not_fabricate_licence_evidence(resolver):
    """Fail-closed: no snippet means no licence verification."""
    assert resolver.extract_licence_snippets(b"") == []
