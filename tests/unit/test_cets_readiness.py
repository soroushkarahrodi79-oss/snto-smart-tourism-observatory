"""Contracts for the CETS Fase I readiness report (v3.0, institutional pack).

The non-negotiables under test:

* ``REAL`` is the evidence ceiling — no row can ever claim external/field
  validation, because the campaign (#26) has not run (ADR-003/ADR-004).
* The principles SNTO does **not** address are emitted, not hidden: a readiness
  document that silently dropped them would overstate coverage.
* Coverage (declared editorial position) and evidence class (computed from live
  state) stay independent — data availability never rewrites coverage.
* The blank field-observation template counts as **zero** measured plots, so the
  validation gate cannot be passed by the template's mere existence.
"""
from __future__ import annotations

from src.platform.evidence import EvidenceClass
from src.reporting.cets_readiness import (
    Coverage,
    EvidenceSignals,
    build_cets_readiness,
    count_measured_field_plots,
    render_cets_readiness_markdown,
    resolve_signals,
)

# Signals with nothing available — the honest floor.
_NO_DATA = EvidenceSignals(
    satellite_real=False,
    mobility_real=False,
    socioeconomic_series=False,
    field_measured_plots=0,
    scm_real_zones=0,
)
# Everything available, including measured field plots and real SCM zones.
_ALL_DATA = EvidenceSignals(
    satellite_real=True,
    mobility_real=True,
    socioeconomic_series=True,
    field_measured_plots=30,
    scm_real_zones=12,
)


def _build(signals: EvidenceSignals) -> dict:
    return build_cets_readiness(
        territory_name="Territorio de prueba",
        park="pnsg",
        report_date="2026-07-25",
        signals=signals,
    )


def _all_rows(report: dict) -> list[dict]:
    return report["components"] + report["principles"]


# ── The validation ceiling ────────────────────────────────────────────────────

def test_no_row_ever_reaches_a_validated_state_even_with_field_plots() -> None:
    """Measured plots raise evidence to REAL at most — never a validation claim."""
    report = _build(_ALL_DATA)
    statuses = {r["evidence_class"] for r in _all_rows(report)}
    # EvidenceClass has no "validated" tier by design; assert we stay inside it.
    assert statuses <= {s.value for s in EvidenceClass}
    assert EvidenceClass.REAL.value in statuses


def test_validation_caveat_is_always_present_regardless_of_signals() -> None:
    for signals in (_NO_DATA, _ALL_DATA):
        report = _build(signals)
        assert "#26" in report["validation_note"]
        assert "validado en campo" in report["validation_note"]


def test_field_row_is_missing_until_the_campaign_runs() -> None:
    report = _build(_NO_DATA)
    row = next(r for r in report["components"] if r["key"] == "plan_accion_validacion")
    assert row["evidence_class"] == EvidenceClass.MISSING.value
    assert "no se ha ejecutado" in row["evidence_note"]


def test_blank_field_template_counts_as_zero_measured_plots() -> None:
    """Pins the #26 gate: the shipped template has plots but no measurements."""
    assert count_measured_field_plots() == 0


def test_missing_field_file_counts_as_zero_not_an_error(tmp_path) -> None:
    assert count_measured_field_plots(tmp_path / "does_not_exist.csv") == 0


# ── Declared limits are never hidden ─────────────────────────────────────────

def test_out_of_scope_principles_are_emitted() -> None:
    report = _build(_ALL_DATA)
    out = [
        r for r in report["principles"]
        if r["coverage"] == Coverage.OUT_OF_SCOPE.value
    ]
    # Principles 4 (visitor experience), 6 (products), 7 (training).
    assert {r["key"] for r in out} == {
        "p04_experiencia", "p06_productos", "p07_formacion",
    }


def test_out_of_scope_rows_appear_in_the_rendered_limits_section() -> None:
    md = render_cets_readiness_markdown(_build(_ALL_DATA))
    assert "Límites declarados" in md
    assert "4 · Ofrecer una experiencia turística de alta calidad" in md


def test_out_of_scope_rows_carry_no_fabricated_module_or_evidence() -> None:
    report = _build(_ALL_DATA)
    for row in report["principles"]:
        if row["coverage"] == Coverage.OUT_OF_SCOPE.value:
            assert row["snto_module"] == "—"
            assert row["indicator"] == "—"
            assert row["evidence_class"] == EvidenceClass.MISSING.value


# ── Coverage is declared, evidence is computed ────────────────────────────────

def test_coverage_is_independent_of_data_availability() -> None:
    """The editorial position must not shift when data appears or vanishes."""
    poor = {r["key"]: r["coverage"] for r in _all_rows(_build(_NO_DATA))}
    rich = {r["key"]: r["coverage"] for r in _all_rows(_build(_ALL_DATA))}
    assert poor == rich


def test_evidence_class_does_shift_with_data_availability() -> None:
    poor = {r["key"]: r["evidence_class"] for r in _all_rows(_build(_NO_DATA))}
    rich = {r["key"]: r["evidence_class"] for r in _all_rows(_build(_ALL_DATA))}
    assert poor != rich


def test_satellite_rows_are_missing_without_a_real_series() -> None:
    report = _build(_NO_DATA)
    row = next(
        r for r in report["components"] if r["key"] == "diagnostico_conservacion"
    )
    assert row["evidence_class"] == EvidenceClass.MISSING.value


def test_satellite_rows_are_real_with_a_committed_series() -> None:
    report = _build(_ALL_DATA)
    row = next(
        r for r in report["components"] if r["key"] == "diagnostico_conservacion"
    )
    assert row["evidence_class"] == EvidenceClass.REAL.value


def test_forecast_row_is_never_real() -> None:
    """Projection is simulated by construction, whatever else is available."""
    for signals in (_NO_DATA, _ALL_DATA):
        report = _build(signals)
        row = next(
            r for r in report["components"] if r["key"] == "estrategia_proyeccion"
        )
        assert row["evidence_class"] != EvidenceClass.REAL.value


# ── ADR-004: simulated must stay distinguishable from synthetic ──────────────

def test_simulated_rows_are_simulated_not_synthetic() -> None:
    """The whole reason this module uses EvidenceClass over DataStatus.

    ``DataStatus`` has no SIMULATED tier, so a model-derived projection would
    collapse into SYNTHETIC alongside demo mocks — the blurring ADR-004 forbids.
    """
    report = _build(_NO_DATA)
    for key in ("estrategia_proyeccion", "diagnostico_atribucion"):
        row = next(r for r in report["components"] if r["key"] == key)
        assert row["evidence_class"] == EvidenceClass.SIMULATED.value, (
            f"{key} must be 'simulated', never 'synthetic'"
        )


def test_scm_attribution_is_simulated_without_real_zones() -> None:
    """Attribution must not inherit the trend series' REAL status.

    The SCM runs its α-decay simulation unless real multi-scale zone exports
    exist, so with a real satellite series but no zones the row stays SIMULATED.
    """
    signals = EvidenceSignals(
        satellite_real=True,
        mobility_real=False,
        socioeconomic_series=False,
        field_measured_plots=0,
        scm_real_zones=0,
    )
    row = next(
        r for r in _build(signals)["components"]
        if r["key"] == "diagnostico_atribucion"
    )
    assert row["evidence_class"] == EvidenceClass.SIMULATED.value
    assert "decaimiento α" in row["evidence_note"]


def test_scm_attribution_becomes_real_once_zones_are_exported() -> None:
    row = next(
        r for r in _build(_ALL_DATA)["components"]
        if r["key"] == "diagnostico_atribucion"
    )
    assert row["evidence_class"] == EvidenceClass.REAL.value


def test_scm_zone_probe_counts_zero_for_a_missing_directory(tmp_path) -> None:
    from src.reporting.cets_readiness import count_real_scm_zone_exports

    assert count_real_scm_zone_exports(tmp_path / "nope") == 0


def test_scm_zone_probe_counts_exports(tmp_path) -> None:
    from src.reporting.cets_readiness import count_real_scm_zone_exports

    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("x", encoding="utf-8")
    assert count_real_scm_zone_exports(tmp_path) == 2


def test_curated_portfolio_rows_are_calibrated_never_real() -> None:
    report = _build(_ALL_DATA)
    row = next(r for r in report["components"] if r["key"] == "estrategia_priorizacion")
    assert row["evidence_class"] == EvidenceClass.CALIBRATED.value


def test_socioeconomic_degrades_to_calibrated_without_a_series() -> None:
    """A single curated snapshot is calibrated, not missing and not real."""
    report = _build(_NO_DATA)
    row = next(
        r for r in report["components"] if r["key"] == "diagnostico_socioeconomico"
    )
    assert row["evidence_class"] == EvidenceClass.CALIBRATED.value


# ── Structural integrity ─────────────────────────────────────────────────────

def test_summary_counts_agree_with_the_emitted_rows() -> None:
    report = _build(_ALL_DATA)
    rows = _all_rows(report)
    assert report["summary"]["requirements_assessed"] == len(rows)
    for coverage, n in report["summary"]["by_coverage"].items():
        assert n == sum(1 for r in rows if r["coverage"] == coverage)
    for status, n in report["summary"]["by_evidence_class"].items():
        assert n == sum(1 for r in rows if r["evidence_class"] == status)


def test_all_ten_principles_are_present() -> None:
    report = _build(_NO_DATA)
    assert len(report["principles"]) == 10


def test_report_keys_are_unique() -> None:
    keys = [r["key"] for r in _all_rows(_build(_NO_DATA))]
    assert len(keys) == len(set(keys))


def test_report_is_json_serialisable() -> None:
    import json

    json.dumps(_build(_ALL_DATA), ensure_ascii=False)


def test_scope_note_states_it_is_not_a_candidacy_dossier() -> None:
    report = _build(_ALL_DATA)
    assert "no la constituye" in report["scope_note"]
    md = render_cets_readiness_markdown(report)
    assert "No es un dosier de candidatura" in md


def test_markdown_reports_the_pending_campaign_when_no_plots_exist() -> None:
    md = render_cets_readiness_markdown(_build(_NO_DATA))
    assert "campaña #26 pendiente" in md


# ── Live resolution against the real repository ──────────────────────────────

def test_resolve_signals_finds_the_real_pnsg_satellite_series() -> None:
    """PNSG has a committed Mann-Kendall JSON, so this must resolve True."""
    assert resolve_signals("pnsg").satellite_real is True


def test_resolve_signals_reports_no_series_for_an_unknown_park() -> None:
    signals = resolve_signals("park_that_does_not_exist")
    assert signals.satellite_real is False


def test_resolve_signals_never_claims_field_validation_today() -> None:
    assert resolve_signals("pnsg").field_validated is False
