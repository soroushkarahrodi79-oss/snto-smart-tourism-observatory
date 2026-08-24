"""VIS-001 frozen configuration.

Everything in this module is **preregistered** (see ``PREREGISTRATION.md``) and
was fixed *before* any evaluation result existed. Changing any value here after
results have been observed invalidates the formal gate: record a numbered
protocol deviation in ``PREREGISTRATION.md`` and re-run the evaluation instead.

This module imports only the standard library on purpose. The metric, manifest
and gate logic must stay testable in the repository's normal CI, which does not
install PyTorch or RF-DETR.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

EXPERIMENT_ID: Final[str] = "VIS-001"
EXPERIMENT_TITLE: Final[str] = "Madrid Visual Counting Benchmark"

#: Bumped only when a gate threshold or the verdict algebra changes. A result
#: is only comparable with another result carrying the same gate version.
GATE_VERSION: Final[str] = "1.0"

# --------------------------------------------------------------------------
# Frozen target classes (§4 of the protocol)
# --------------------------------------------------------------------------

#: The four COCO-style classes VIS-001 evaluates. No fifth class may be added
#: after results are seen. Any other class the model emits is discarded before
#: the gate is computed.
TARGET_CLASSES: Final[tuple[str, ...]] = ("person", "bicycle", "car", "bus")

#: Canonical COCO category ids for the target classes. RF-DETR's pretrained
#: COCO checkpoints emit raw (sparse) COCO category ids, so this is a lookup
#: table, not a contiguous index.
COCO_CATEGORY_IDS: Final[dict[str, int]] = {
    "person": 1,
    "bicycle": 2,
    "car": 3,
    "bus": 6,
}

# --------------------------------------------------------------------------
# Frozen model and inference parameters (§5 of the protocol)
# --------------------------------------------------------------------------

MODEL_NAME: Final[str] = "RF-DETR Small"
MODEL_ENTRYPOINT: Final[str] = "rfdetr.RFDETRSmall"
MODEL_PACKAGE: Final[str] = "rfdetr"

#: Zero-shot only. VIS-001 performs no fine-tuning of any kind.
FINE_TUNING_ALLOWED: Final[bool] = False

#: Detection confidence floor. Frozen at 0.35 before any result was observed.
#: A threshold sweep may be reported as a clearly labelled secondary
#: diagnostic, but the formal gate always uses this value.
CONFIDENCE_THRESHOLD: Final[float] = 0.35

#: IoU at which a prediction may be matched to a ground-truth box.
EVAL_IOU_THRESHOLD: Final[float] = 0.50

# --------------------------------------------------------------------------
# Frozen sample design (§7 and §10 of the protocol)
# --------------------------------------------------------------------------

TARGET_CAMERAS: Final[int] = 8
TARGET_FRAMES_PER_CAMERA: Final[int] = 20
TARGET_FRAMES: Final[int] = TARGET_CAMERAS * TARGET_FRAMES_PER_CAMERA  # 160

EVAL_IMAGES_PER_CAMERA: Final[int] = 10
EVAL_SET_SIZE: Final[int] = TARGET_CAMERAS * EVAL_IMAGES_PER_CAMERA  # 80

#: The sample is complete only when EACH of the eight selected cameras holds at
#: least TARGET_FRAMES_PER_CAMERA unique frames. A total of 160 frames spread
#: unevenly — 100 from one camera, 60 from another — is NOT complete: it would
#: destroy the per-camera stratification the gate's camera rules depend on.
#: Completeness is therefore structural, never a headline count.
REQUIRE_PER_CAMERA_QUOTA: Final[bool] = True

#: A formal verdict requires the evaluation set to be exactly EVAL_SET_SIZE
#: images, EVAL_IMAGES_PER_CAMERA from each of the eight selected cameras.
#: Anything less forces NO VERDICT.
REQUIRE_EXACT_EVAL_SET: Final[bool] = True

#: A formal verdict requires all four target classes to be evaluable. A class
#: whose F1 is undefined is NOT quietly dropped from the macro average — the
#: gate stops with NO VERDICT — INSUFFICIENT CLASS COVERAGE instead. Dropping
#: it would let a benchmark that never saw a bus report a macro F1 as though it
#: had measured all four.
REQUIRE_ALL_CLASSES_EVALUABLE: Final[bool] = True

#: Seed for the stratified evaluation-set draw. Fixed by the protocol.
RANDOM_SEED: Final[int] = 20260824

# --------------------------------------------------------------------------
# Frozen decision gate (§15 of the protocol)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class GateThresholds:
    """The preregistered decision thresholds.

    ``ADVANCE`` requires every ``advance_*`` condition to hold simultaneously.
    ``KILL_OR_REPOSITION`` fires if any ``kill_*`` condition holds and takes
    precedence over everything else. ``LOCAL_FINE_TUNE`` is the residual: the
    baseline is neither good enough to advance on nor bad enough to abandon.
    """

    # --- ADVANCE (all must hold) ---
    advance_min_macro_f1: float = 0.80
    advance_max_count_wape: float = 0.20
    advance_min_class_f1: float = 0.65
    advance_max_camera_wape: float = 0.35

    # --- KILL_OR_REPOSITION (any is sufficient) ---
    kill_below_macro_f1: float = 0.65
    kill_above_count_wape: float = 0.35
    kill_class_f1_below: float = 0.50
    #: Number of target classes below ``kill_class_f1_below`` that triggers a kill.
    kill_min_failing_classes: int = 2
    #: Operationalisation of "performance varies so strongly across ordinary
    #: camera views that aggregate performance is misleading": the spread
    #: between the best and worst camera counting WAPE. Preregistered so the
    #: qualitative clause cannot be reinterpreted after seeing results.
    kill_above_camera_wape_spread: float = 0.50


GATE: Final[GateThresholds] = GateThresholds()

# --------------------------------------------------------------------------
# Paths (all relative to this experiment; nothing is written outside it)
# --------------------------------------------------------------------------

EXPERIMENT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

DATA_DIR: Final[Path] = EXPERIMENT_ROOT / "data"
RAW_FRAMES_DIR: Final[Path] = DATA_DIR / "raw"
ANNOTATIONS_DIR: Final[Path] = DATA_DIR / "annotations"
OUTPUTS_DIR: Final[Path] = EXPERIMENT_ROOT / "outputs"

SOURCE_RESOLUTION_PATH: Final[Path] = DATA_DIR / "source_resolution.json"
CAMERA_MANIFEST_PATH: Final[Path] = DATA_DIR / "camera_manifest.csv"
SELECTED_CAMERAS_PATH: Final[Path] = DATA_DIR / "selected_cameras.json"
SAMPLE_MANIFEST_PATH: Final[Path] = DATA_DIR / "sample_manifest.csv"
EVAL_SET_PATH: Final[Path] = DATA_DIR / "eval_set.json"
GROUND_TRUTH_PATH: Final[Path] = ANNOTATIONS_DIR / "ground_truth_coco.json"

PREDICTIONS_PATH: Final[Path] = OUTPUTS_DIR / "predictions.jsonl"
RUN_MANIFEST_PATH: Final[Path] = OUTPUTS_DIR / "run_manifest.json"
METRICS_PATH: Final[Path] = OUTPUTS_DIR / "metrics.json"
VERDICT_PATH: Final[Path] = OUTPUTS_DIR / "verdict.json"
REPORT_PATH: Final[Path] = OUTPUTS_DIR / "report.md"

# --------------------------------------------------------------------------
# Official source endpoints (§6 of the protocol)
# --------------------------------------------------------------------------

#: The authoritative camera list: the municipal traffic portal's KML. This is
#: the document VIS-001 parses structurally to build the camera manifest.
MADRID_CCTV_KML_URL: Final[str] = "https://informo.madrid.es/informo/tmadrid/CCTV.kml"

#: The open-data catalogue page for "Tráfico. Cámaras". Carries the licence and
#: terms-of-use statement; provenance is verified against it, not against the
#: KML alone, because the KML itself ships no licence header.
MADRID_DATASET_PAGE_URL: Final[str] = (
    "https://datos.madrid.es/dataset/202088-0-trafico-camaras"
)

#: Official national open-data catalogue entry for the SAME Ayuntamiento de
#: Madrid dataset ("Tráfico. Cámaras"), served as RDF/XML by datos.gob.es. It is
#: a licence/metadata **fallback only**, consulted when the municipal catalogue
#: page above times out (see protocol deviation PD-001 in ``PREREGISTRATION.md``).
#: It is NEVER an image source and NEVER a camera-list substitute: the
#: authoritative camera population is always ``MADRID_CCTV_KML_URL``.
MADRID_DATASET_NATIONAL_FALLBACK_URL: Final[str] = (
    "https://datos.gob.es/es/catalogo/l01280796-trafico-camaras1.xml"
)
# --------------------------------------------------------------------------
# Evidence semantics — experiment-local on purpose (§13 of the protocol)
# --------------------------------------------------------------------------

#: VIS-001 deliberately does NOT reuse ``src.platform.provenance.DataStatus``.
#: A real public camera image is a real *input*; it does not make an
#: algorithmic detection over it "REAL evidence". These three labels are local
#: to the experiment and are never written into SNTO's global enum.
EVIDENCE_RAW_INPUT: Final[str] = "REAL_PUBLIC_IMAGE"
EVIDENCE_HUMAN_REFERENCE: Final[str] = "HUMAN_ANNOTATION"
EVIDENCE_MODEL_OUTPUT: Final[str] = "MODEL_PREDICTION"
