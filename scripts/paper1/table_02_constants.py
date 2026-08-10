"""
scripts/paper1/table_02_constants.py
====================================
Paper-1 Table T2: every constant that drives a scientific output, with its
**live value pulled from the code** (never hand-copied, so it cannot drift),
its code location, its evidential basis, and whether a sensitivity analysis is
required. This is the ``docs/paper1/FIGURE_PLAN.md`` T2 draft made drift-proof
and is unusual on purpose — most remote-sensing papers do not declare which of
their constants are literature-derived and which are expert guesses.

The **value** and **location** are derived from the code; the **basis** and
**sensitivity** columns are the curated Phase 0 audit §4 editorial judgement.
``tests/unit/test_paper1_table_constants.py`` asserts the emitted values match
the live constants, so a code change that moves a constant fails CI until the
table is regenerated.

Outputs (docs/paper1/tables/):
  table_02_constants.csv · table_02_constants.md · *.provenance.json
"""
from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.paper1._figutil import build_provenance, write_sidecar  # noqa: E402

_OUT_DIR = _ROOT / "docs" / "paper1" / "tables"
_ETL_BUFFER_FILE = _ROOT / "etl_raster_intersection.py"


def _etl_constant(name: str) -> float:
    """Read a module-level numeric constant from the ETL script via AST (no import)."""
    tree = ast.parse(_ETL_BUFFER_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    if isinstance(node.value, ast.Constant):
                        return node.value.value
    raise KeyError(f"{name} not found in {_ETL_BUFFER_FILE.name}")


def build_rows() -> list[dict]:
    """Build the table rows with live values. Order = Phase 0 §4."""
    from src.config import constants as C
    import src.spatial_causality.analyzer as scm
    from src.validation.confusion import FIELD_DEGRADED_THRESHOLD
    from src.validation.field import SOIL_COMPACTION_MAX_MPA

    # (label, value, location, basis, sensitivity_required)
    spec = [
        ("EHS_P_BASE", C.EHS_P_BASE, "src/config/constants.py::EHS_P_BASE",
         "Expert", True),
        ("EHS_P_FLOOR", C.EHS_P_FLOOR, "src/config/constants.py::EHS_P_FLOOR",
         "Expert", True),
        ("EHS_W_NDVI", C.EHS_W_NDVI, "src/config/constants.py::EHS_W_NDVI",
         "Expert", True),
        ("EHS_W_NDMI", C.EHS_W_NDMI, "src/config/constants.py::EHS_W_NDMI",
         "Expert", True),
        ("EHS_DENSE_CANOPY_NDVI_THRESHOLD", C.EHS_DENSE_CANOPY_NDVI_THRESHOLD,
         "src/config/constants.py::EHS_DENSE_CANOPY_NDVI_THRESHOLD",
         "Saturation literature (qualitative)", True),
        ("EHS_W_NDVI_DENSE", C.EHS_W_NDVI_DENSE,
         "src/config/constants.py::EHS_W_NDVI_DENSE", "Expert", True),
        ("EHS_W_NDMI_DENSE", C.EHS_W_NDMI_DENSE,
         "src/config/constants.py::EHS_W_NDMI_DENSE", "Expert", True),
        ("UPSLOPE_M", _etl_constant("UPSLOPE_M"),
         "etl_raster_intersection.py::UPSLOPE_M", "Wemple et al. (2001), qualitative", True),
        ("DOWNSLOPE_M", _etl_constant("DOWNSLOPE_M"),
         "etl_raster_intersection.py::DOWNSLOPE_M", "Wemple et al. (2001), qualitative", True),
        ("BUFFER_M (symmetric fallback)", _etl_constant("BUFFER_M"),
         "etl_raster_intersection.py::BUFFER_M", "Convention", False),
        ("CORE_OUTER_M", scm.CORE_OUTER_M,
         "src/spatial_causality/analyzer.py::CORE_OUTER_M",
         "Marion & Leung (2001) — cited", False),
        ("NEAR_OUTER_M", scm.NEAR_OUTER_M,
         "src/spatial_causality/analyzer.py::NEAR_OUTER_M", "Expert", True),
        ("SCM _SIG_LOCALIZED", scm._SIG_LOCALIZED,
         "src/spatial_causality/analyzer.py::_SIG_LOCALIZED",
         "Uncited heuristic", True),
        ("SCM _SIG_LANDSCAPE", scm._SIG_LANDSCAPE,
         "src/spatial_causality/analyzer.py::_SIG_LANDSCAPE",
         "Uncited heuristic", True),
        ("SCM _CORR_LANDSCAPE", scm._CORR_LANDSCAPE,
         "src/spatial_causality/analyzer.py::_CORR_LANDSCAPE",
         "Uncited heuristic", True),
        ("SCM _CORR_LOCALIZED", scm._CORR_LOCALIZED,
         "src/spatial_causality/analyzer.py::_CORR_LOCALIZED",
         "Uncited heuristic", True),
        ("FIELD_DEGRADED_THRESHOLD", FIELD_DEGRADED_THRESHOLD,
         "src/validation/confusion.py::FIELD_DEGRADED_THRESHOLD",
         "Uncited round number — must be calibrated out-of-sample", True),
        ("SOIL_COMPACTION_MAX_MPA", SOIL_COMPACTION_MAX_MPA,
         "src/validation/field.py::SOIL_COMPACTION_MAX_MPA",
         "Root-restriction range, qualitative (censoring)", True),
    ]
    return [
        {"constant": name, "value": value, "code_location": loc,
         "basis": basis, "sensitivity_required": "yes" if sens else "no"}
        for name, value, loc, basis, sens in spec
    ]


_FIELDNAMES = ["constant", "value", "code_location", "basis", "sensitivity_required"]


def _write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        w.writeheader()
        w.writerows(rows)


def _write_md(rows: list[dict], path: Path, commit: str) -> None:
    lines = [
        "# Table T2 — Constants driving scientific output (Paper 1)",
        "",
        "Values pulled **live from the code** (drift-proof); basis and "
        "sensitivity are the Phase 0 audit §4 editorial judgement. "
        "No constant may change without owner approval, a before/after "
        "comparison and a methodological rationale (change control).",
        "",
        f"_Generated by `scripts/paper1/table_02_constants.py` at commit `{commit}`._",
        "",
        "| Constant | Value | Code location | Basis | Sensitivity analysis |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['constant']}` | {r['value']} | `{r['code_location']}` | "
            f"{r['basis']} | {r['sensitivity_required']} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def render() -> Path:
    rows = build_rows()
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = _OUT_DIR / "table_02_constants.csv"
    md_path = _OUT_DIR / "table_02_constants.md"

    prov = build_provenance(
        {"constants": _ROOT / "src" / "config" / "constants.py",
         "analyzer": _ROOT / "src" / "spatial_causality" / "analyzer.py",
         "etl_buffers": _ETL_BUFFER_FILE},
        params={"n_constants": len(rows)},
    )
    _write_csv(rows, csv_path)
    _write_md(rows, md_path, prov["commit_hash"])
    write_sidecar(csv_path, prov)
    return csv_path


if __name__ == "__main__":
    out = render()
    print(f"Table T2 → {out} ({len(build_rows())} constants)")
