"""Integridad del registro de trazabilidad y multiplicadores (defensa académica).

Estos tests blindan la *fuente de verdad* que alimenta la pestaña 8 del observatorio y
el anexo ``docs/defensibilidad_academica.md``: si alguien añade una variable sin tipo,
deja un multiplicador sin justificación, o rompe la invariante de pesos convexos, la
suite lo detecta antes de que llegue a una defensa de TFM.
"""
from __future__ import annotations

from src.platform.methodology import (
    _PLAIN_TYPE_SUMMARY,
    MULTIPLIERS,
    TRACEABILITY,
    Confidence,
    DataType,
    counts_by_type,
    validate_registry,
)


def test_registry_passes_integrity() -> None:
    report = validate_registry()
    assert report.ok, f"Registro inconsistente: {report.errors}"


def test_every_trace_row_is_classified() -> None:
    for r in TRACEABILITY:
        assert isinstance(r.dtype, DataType)
        assert isinstance(r.confidence, Confidence)
        assert r.variable and r.source and r.formula


def test_all_four_data_types_present() -> None:
    # La narrativa de defensa exige las cuatro categorías observada/calculada/estimada/simulada.
    present = {r.dtype for r in TRACEABILITY}
    assert present == set(DataType), f"Faltan tipos: {set(DataType) - present}"


def test_plain_summary_covers_every_data_type() -> None:
    # F10 — el resumen Gestor de la pestaña 8 traduce cada DataType a lenguaje
    # llano. Si se añade un tipo nuevo sin su versión llana, este test lo frena.
    assert set(_PLAIN_TYPE_SUMMARY) == {d.label for d in DataType}
    for title, sub in _PLAIN_TYPE_SUMMARY.values():
        assert title and sub


def test_satellite_indices_are_observed_and_high_confidence() -> None:
    rows = {r.variable: r for r in TRACEABILITY}
    for name in ("NDVI", "NDMI"):
        assert rows[name].dtype is DataType.OBSERVED
        assert rows[name].confidence is Confidence.HIGH


def test_economic_proxy_outputs_are_simulated_low_confidence() -> None:
    # El corazón de la auditoría: nada del proxy económico puede figurar como observado.
    sim = {
        r.variable: r
        for r in TRACEABILITY
        if "escenario" in r.variable.lower() or "proxy" in r.variable.lower()
    }
    assert sim, "Se esperaban variables de escenario/proxy en la matriz."
    for r in sim.values():
        assert r.dtype in (DataType.SIMULATED, DataType.ESTIMATED)
        assert r.confidence is Confidence.LOW


def test_visitor_capacity_is_estimated_not_observed() -> None:
    row = next(r for r in TRACEABILITY if r.variable == "visitor_capacity_annual")
    assert row.dtype is DataType.ESTIMATED
    assert row.dtype is not DataType.OBSERVED


def test_multipliers_are_fully_documented() -> None:
    for m in MULTIPLIERS:
        assert m.name and m.value and m.origin
        assert m.justification and m.behavior and m.sensitivity


def test_high_sensitivity_multipliers_are_flagged() -> None:
    # Gasto/visitante, visitantes/empleo y factores de cierre son los que más mueven el
    # resultado económico: deben declarar sensibilidad Alta o Crítica.
    critical = [
        m for m in MULTIPLIERS
        if "visitante" in m.name.lower() or "cierre" in m.name.lower()
    ]
    assert critical
    for m in critical:
        assert any(k in m.sensitivity for k in ("Alta", "Crítica"))


def test_counts_by_type_matches_registry() -> None:
    counts = counts_by_type()
    assert sum(counts.values()) == len(TRACEABILITY)
    for key in ("Observada", "Calculada", "Estimada", "Simulada"):
        assert counts.get(key, 0) >= 1
