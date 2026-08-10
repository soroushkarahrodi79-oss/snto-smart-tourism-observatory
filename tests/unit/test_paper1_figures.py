"""Paper-1 figure/table generators (Backlog B-09).

Split by dependency: input-validation, provenance and the Table-T2 drift guard
run everywhere (geopandas/stdlib only); the actual figure renders are guarded by
``importorskip('matplotlib')`` because matplotlib is offline figure-tooling, not
a pinned runtime dependency.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.paper1 import _figutil
from scripts.paper1._figutil import (
    EVIDENCE_COLORS,
    MissingInput,
    build_provenance,
    require_inputs,
    sha256_file,
)

_ROOT = Path(__file__).resolve().parents[2]


# ── provenance / input validation (no matplotlib) ───────────────────────────

def test_require_inputs_raises_loudly_on_missing(tmp_path):
    present = tmp_path / "there.txt"
    present.write_text("x", encoding="utf-8")
    with pytest.raises(MissingInput) as exc:
        require_inputs({"present": present, "absent": tmp_path / "nope.geojson"})
    assert "nope.geojson" in str(exc.value)
    assert "there.txt" not in str(exc.value)  # only the missing one is named


def test_require_inputs_passes_when_all_present(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("x", encoding="utf-8")
    require_inputs({"a": p})  # no raise


def test_sha256_and_provenance_structure(tmp_path):
    p = tmp_path / "d.bin"
    p.write_bytes(b"hello")
    digest = sha256_file(p)
    assert digest == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    prov = build_provenance({"d": p}, params={"k": 1})
    assert prov["inputs"]["d"]["sha256"] == digest
    assert "generated_at" in prov and "commit_hash" in prov
    assert prov["params"] == {"k": 1}


def test_evidence_palette_is_hex_and_covers_classes():
    for cls in ("real", "calibrated", "simulated", "synthetic", "constant"):
        assert cls in EVIDENCE_COLORS
        v = EVIDENCE_COLORS[cls]
        assert v.startswith("#") and len(v) == 7


# ── Table T2: live-value correctness + committed-artifact drift guard ───────

def test_table_values_match_live_constants():
    from scripts.paper1.table_02_constants import build_rows
    from src.config import constants as C
    import src.spatial_causality.analyzer as scm
    from src.validation.confusion import FIELD_DEGRADED_THRESHOLD
    from src.validation.field import SOIL_COMPACTION_MAX_MPA

    by_name = {r["constant"]: r["value"] for r in build_rows()}
    assert by_name["EHS_P_BASE"] == C.EHS_P_BASE
    assert by_name["EHS_W_NDMI"] == C.EHS_W_NDMI
    assert by_name["SCM _SIG_LOCALIZED"] == scm._SIG_LOCALIZED
    assert by_name["SCM _CORR_LOCALIZED"] == scm._CORR_LOCALIZED
    assert by_name["FIELD_DEGRADED_THRESHOLD"] == FIELD_DEGRADED_THRESHOLD
    assert by_name["SOIL_COMPACTION_MAX_MPA"] == SOIL_COMPACTION_MAX_MPA
    # AST-read ETL buffer values.
    assert by_name["UPSLOPE_M"] == 15
    assert by_name["DOWNSLOPE_M"] == 60


def test_committed_table_csv_is_fresh():
    # The committed CSV must equal a fresh regeneration — the same discipline as
    # the acquisition-manifest --check: a constant change fails CI until the
    # table is regenerated.
    from scripts.paper1.table_02_constants import build_rows

    csv_path = _ROOT / "docs" / "paper1" / "tables" / "table_02_constants.csv"
    assert csv_path.exists(), "run scripts/paper1/table_02_constants.py"
    committed = {row["constant"]: row["value"]
                 for row in csv.DictReader(csv_path.open(encoding="utf-8"))}
    for r in build_rows():
        assert committed[r["constant"]] == str(r["value"]), (
            f"{r['constant']} drifted — regenerate table_02_constants")


def test_table_render_writes_csv_md_and_sidecar(tmp_path, monkeypatch):
    import scripts.paper1.table_02_constants as t2
    monkeypatch.setattr(t2, "_OUT_DIR", tmp_path)
    out = t2.render()
    assert out.exists()
    assert (tmp_path / "table_02_constants.md").exists()
    assert (tmp_path / "table_02_constants.csv.provenance.json").exists()


# ── Figure generators refuse to run on missing inputs (no matplotlib) ───────

def test_figure_01_fails_loudly_when_input_absent(tmp_path, monkeypatch):
    import scripts.paper1.figure_01_study_area as f1
    monkeypatch.setattr(f1, "_TRAILS", tmp_path / "missing_trails.geojson")
    with pytest.raises(MissingInput):
        f1.render()


# ── Figure renders (require matplotlib) ─────────────────────────────────────

def test_figure_01_renders_pdf_and_sidecar(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    import scripts.paper1.figure_01_study_area as f1
    if not f1._TRAILS.exists() or not f1._BOUNDARY.exists():
        pytest.skip("committed trail/boundary inputs absent in this checkout")
    monkeypatch.setattr(f1, "_OUT_DIR", tmp_path)
    out = f1.render()
    assert out.exists() and out.suffix == ".pdf"
    assert (tmp_path / "figure_01_study_area.png").exists()
    assert out.with_suffix(".pdf.provenance.json").exists()


def test_figure_02_renders_vector_and_sidecar(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib")
    import scripts.paper1.figure_02_pipeline as f2
    monkeypatch.setattr(f2, "_OUT_DIR", tmp_path)
    out = f2.render()
    assert out.exists() and out.suffix == ".pdf"
    assert (tmp_path / "figure_02_pipeline.svg").exists()
