"""VIS-001 preregistration integrity and CI safety.

Two jobs:

1. The frozen numbers exist in three places — ``vis001/config.py``,
   ``experiment.yaml`` and ``PREREGISTRATION.md``. If someone changes a
   threshold in one after seeing a result, these tests fail loudly instead of
   letting the three drift apart quietly. That is the whole point of a
   preregistration.
2. The repository's ordinary CI must stay healthy without PyTorch or RF-DETR
   installed, so nothing importable from the metric/manifest/annotation layer
   may pull in the CV stack.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from vis001 import config

EXPERIMENT_ROOT = (
    Path(__file__).resolve().parents[2] / "experiments" / "vis001_madrid_counting"
)
PREREGISTRATION = EXPERIMENT_ROOT / "PREREGISTRATION.md"
EXPERIMENT_YAML = EXPERIMENT_ROOT / "experiment.yaml"


def _flattened(path: Path) -> str:
    """Collapse whitespace so a line-wrapped phrase still matches.

    The preregistration is prose wrapped at 80 columns, so "person
    re-identification" can straddle a newline. Searching the flattened text
    asserts the *statement* is present, not that it happened to fit on one line.
    """
    return " ".join(path.read_text(encoding="utf-8").split())


@pytest.fixture(scope="module")
def prereg_text() -> str:
    return _flattened(PREREGISTRATION)


@pytest.fixture(scope="module")
def yaml_text() -> str:
    return _flattened(EXPERIMENT_YAML)


# --------------------------------------------------------------------------
# The frozen constants
# --------------------------------------------------------------------------


def test_target_classes_are_exactly_the_frozen_four():
    assert config.TARGET_CLASSES == ("person", "bicycle", "car", "bus")


def test_coco_ids_match_the_frozen_classes():
    assert set(config.COCO_CATEGORY_IDS) == set(config.TARGET_CLASSES)
    assert config.COCO_CATEGORY_IDS == {"person": 1, "bicycle": 2, "car": 3, "bus": 6}


def test_thresholds_are_frozen():
    assert config.CONFIDENCE_THRESHOLD == 0.35
    assert config.EVAL_IOU_THRESHOLD == 0.50


def test_sample_design_is_frozen():
    assert config.TARGET_CAMERAS == 8
    assert config.TARGET_FRAMES_PER_CAMERA == 20
    assert config.TARGET_FRAMES == 160
    assert config.EVAL_IMAGES_PER_CAMERA == 10
    assert config.EVAL_SET_SIZE == 80
    assert config.RANDOM_SEED == 20260824


def test_fine_tuning_is_forbidden():
    assert config.FINE_TUNING_ALLOWED is False


def test_gate_thresholds_are_frozen():
    gate = config.GATE
    assert (gate.advance_min_macro_f1, gate.advance_max_count_wape) == (0.80, 0.20)
    assert (gate.advance_min_class_f1, gate.advance_max_camera_wape) == (0.65, 0.35)
    assert (gate.kill_below_macro_f1, gate.kill_above_count_wape) == (0.65, 0.35)
    assert (gate.kill_class_f1_below, gate.kill_min_failing_classes) == (0.50, 2)
    assert gate.kill_above_camera_wape_spread == 0.50


def test_gate_thresholds_are_immutable():
    """Frozen means frozen: a stray assignment cannot silently move the bar."""
    with pytest.raises(Exception):
        config.GATE.advance_min_macro_f1 = 0.10  # type: ignore[misc]


# --------------------------------------------------------------------------
# Three-way agreement
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0.35", "0.50", "0.80", "0.20", "0.65", "20260824"])
def test_frozen_values_appear_in_the_preregistration(prereg_text, value):
    assert value in prereg_text


@pytest.mark.parametrize("value", ["0.35", "0.50", "0.80", "0.20", "0.65", "20260824"])
def test_frozen_values_appear_in_experiment_yaml(yaml_text, value):
    assert value in yaml_text


@pytest.mark.parametrize("name", ["person", "bicycle", "car", "bus"])
def test_classes_are_named_in_both_documents(prereg_text, yaml_text, name):
    assert name in prereg_text
    assert name in yaml_text


def test_documents_declare_the_same_gate_version(prereg_text, yaml_text):
    assert config.GATE_VERSION == "1.0"
    assert f"**Gate version:** {config.GATE_VERSION}" in prereg_text
    assert f'gate_version: "{config.GATE_VERSION}"' in yaml_text


def test_report_headings_promised_by_the_preregistration_exist(prereg_text):
    assert "NO VERDICT — MISSING EVIDENCE" in prereg_text


def test_model_is_rf_detr_small_everywhere(prereg_text, yaml_text):
    assert config.MODEL_NAME == "RF-DETR Small"
    assert "RF-DETR Small" in prereg_text
    assert "RF-DETR Small" in yaml_text


def test_no_second_architecture_is_introduced(prereg_text, yaml_text):
    """A YOLO comparison is a future experiment, not this one."""
    assert "no YOLO comparison in VIS-001" in prereg_text
    assert "a second detector architecture as a comparison baseline" in yaml_text


# --------------------------------------------------------------------------
# Privacy boundary
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        "face recognition",
        "person re-identification",
        "emotion detection",
        "licence-plate recognition",
        "persistent individual tracking",
    ],
)
def test_privacy_prohibitions_are_declared(prereg_text, yaml_text, forbidden):
    assert forbidden in prereg_text
    assert forbidden in yaml_text


def test_no_biometric_or_identity_code_exists_in_the_experiment():
    """The prohibition is enforced against the source, not just documented.

    Only the implementation is scanned: the preregistration and README name
    these techniques precisely in order to forbid them.
    """
    banned = (
        "face_recognition",
        "facenet",
        "arcface",
        "insightface",
        "reid",
        "deepsort",
        "bytetrack",
        "easyocr",
        "pytesseract",
        "paddleocr",
    )
    sources = list((EXPERIMENT_ROOT / "vis001").rglob("*.py"))
    sources += list((EXPERIMENT_ROOT / "scripts").rglob("*.py"))
    assert sources, "expected the experiment to have source files"
    for path in sources:
        text = path.read_text(encoding="utf-8").lower()
        for term in banned:
            assert term not in text, f"{path.name} references {term!r}"


# --------------------------------------------------------------------------
# Evidence semantics
# --------------------------------------------------------------------------


def test_vis001_does_not_reuse_snto_data_status():
    """A real image does not make a prediction over it REAL evidence."""
    assert config.EVIDENCE_MODEL_OUTPUT == "MODEL_PREDICTION"
    assert config.EVIDENCE_RAW_INPUT == "REAL_PUBLIC_IMAGE"
    assert config.EVIDENCE_HUMAN_REFERENCE == "HUMAN_ANNOTATION"

    # The prohibition is on *using* SNTO's enum, not on naming it. Several
    # docstrings mention DataStatus precisely to say VIS-001 does not touch it,
    # so the check targets imports and attribute access rather than the word.
    sources = list((EXPERIMENT_ROOT / "vis001").rglob("*.py"))
    for path in sources:
        text = path.read_text(encoding="utf-8")
        assert "from src.platform.provenance" not in text
        assert "import DataStatus" not in text
        assert "DataStatus." not in text, f"{path.name} uses SNTO's DataStatus enum"


def test_experiment_does_not_import_snto_production_code():
    """VIS-001 is isolated: nothing here couples to src/, app.py or the API."""
    sources = list((EXPERIMENT_ROOT / "vis001").rglob("*.py"))
    sources += list((EXPERIMENT_ROOT / "scripts").rglob("*.py"))
    for path in sources:
        text = path.read_text(encoding="utf-8")
        assert "import src." not in text, f"{path.name} imports SNTO production code"
        assert "from src." not in text, f"{path.name} imports SNTO production code"


# --------------------------------------------------------------------------
# CI safety
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module",
    ["vis001.config", "vis001.manifest", "vis001.annotations", "vis001.metrics",
     "vis001.reporting", "vis001.inference"],
)
def test_modules_import_without_the_cv_stack(module):
    """Importing any VIS-001 module must not drag in torch or rfdetr.

    Run in a subprocess so the assertion is about what the import *actually*
    loads, not about what some earlier test happened to leave in sys.modules.
    """
    code = (
        "import sys, importlib;"
        f"importlib.import_module({module!r});"
        "heavy = [name for name in ('torch', 'rfdetr', 'supervision', 'cv2') "
        "if name in sys.modules];"
        "print(','.join(heavy))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(EXPERIMENT_ROOT),
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "", (
        f"{module} pulled in a heavy dependency: {completed.stdout.strip()}"
    )


def test_core_requirements_do_not_carry_the_cv_stack():
    """The CV dependencies stay experiment-local; SNTO's CI must not install them."""
    core = (Path(__file__).resolve().parents[2] / "requirements.txt").read_text(
        encoding="utf-8"
    )
    for package in ("rfdetr", "supervision", "torch", "opencv"):
        assert package not in core.lower()

    local = (EXPERIMENT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "rfdetr" in local
