"""Phase 6.7d per-asset provenance and lineage contracts."""

from __future__ import annotations

from dataclasses import replace

from src.platform.calibration import CalibrationResult
from src.platform.evidence import EvidenceClass
from src.platform.lineage import build_lineage_profile, build_lineage_profiles
from src.platform.methodology import DataType
from src.territorial.fixtures import build_pnsg_territory


def _asset():
    return build_pnsg_territory()[0]


def test_curated_ehs_is_not_promoted_to_observed() -> None:
    asset = _asset()
    calibration = CalibrationResult(
        asset_id=asset.asset_id,
        curated_ehs=asset.ehs,
        satellite_ehs=asset.ehs + 20,
        matched_trails=["Senda de prueba"],
        n_trails=1,
        delta=20,
        flag="mas_sano",
    )

    record = build_lineage_profile(asset, calibration, ["2026-06-01"]).records[0]

    assert record.evidence_class is EvidenceClass.CALIBRATED
    assert record.epistemic_type is DataType.ESTIMATED
    assert record.observed_at is None


def test_conservative_satellite_override_uses_real_scene_date() -> None:
    asset = replace(_asset(), ehs=42.0)
    calibration = CalibrationResult(
        asset_id=asset.asset_id,
        curated_ehs=60.0,
        satellite_ehs=42.0,
        matched_trails=["Senda real"],
        n_trails=1,
        delta=-18.0,
        flag="mas_degradado",
    )

    record = build_lineage_profile(
        asset,
        calibration,
        ["2026-05-10", "2026-06-12"],
    ).records[0]

    assert record.evidence_class is EvidenceClass.REAL
    assert record.epistemic_type is DataType.CALCULATED
    assert record.observed_at == "2026-06-12"
    assert "Senda real" in record.source


def test_missing_scene_date_is_not_replaced_by_report_date() -> None:
    asset = replace(_asset(), ehs=42.0)
    calibration = CalibrationResult(
        asset_id=asset.asset_id,
        curated_ehs=60.0,
        satellite_ehs=42.0,
        matched_trails=["Senda real"],
        n_trails=1,
        delta=-18.0,
        flag="mas_degradado",
    )

    profile = build_lineage_profile(asset, calibration, [])

    assert profile.records[0].observed_at is None
    assert profile.dated_records == 0
    assert profile.missing_dates == len(profile.records)


def test_derived_decision_inherits_calibrated_input_class() -> None:
    profile = build_lineage_profile(_asset())
    by_name = {record.datum: record for record in profile.records}

    assert by_name["TPI"].evidence_class is EvidenceClass.CALIBRATED
    assert by_name["Decisión recomendada"].evidence_class is EvidenceClass.CALIBRATED
    assert "None" not in by_name["Decisión recomendada"].value
    assert "estimados" in by_name["TPI"].caveat


def test_profiles_preserve_ranked_asset_order() -> None:
    assets = build_pnsg_territory()[:3]
    profiles = build_lineage_profiles(assets, {})

    assert [profile.asset_id for profile in profiles] == [
        asset.asset_id for asset in assets
    ]
    assert all(len(profile.records) == 8 for profile in profiles)
