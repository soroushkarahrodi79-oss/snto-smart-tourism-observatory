"""VIS-001 report rendering.

The report is the artifact a human reads to decide whether to fund VIS-002, so
these tests are mostly about what it must *refuse* to say: no invented metric,
no soft pass, no dropped limitation.
"""

from __future__ import annotations

from vis001.config import GATE, GATE_VERSION
from vis001.metrics import (
    CountingMetrics,
    DetectionMetrics,
    EvaluationResult,
    Verdict,
    decide,
)
from vis001.reporting import STANDING_LIMITATIONS, render_report

_CLASSES = ("person", "bicycle", "car", "bus")


def _blank_report(**overrides) -> str:
    kwargs = {
        "result": None,
        "verdict": Verdict(
            verdict=None,
            gate_version=GATE_VERSION,
            macro_f1=None,
            count_wape=None,
            blocking_reasons=("no human ground truth is present",),
        ),
        "run_manifest": None,
        "sample_frames": 0,
        "sample_cameras": 0,
        "target_frames": 160,
        "target_cameras": 8,
        "annotated_images": 0,
        "eval_set_size": 80,
        "class_distribution": {},
        "missing_evidence": ["No frames have been acquired."],
    }
    kwargs.update(overrides)
    return render_report(**kwargs)


def _good_result() -> EvaluationResult:
    detection = DetectionMetrics(90, 5, 5, 0.947, 0.947, 0.947)
    counting = CountingMetrics(80, 100, 98, 0.3, -0.025, 0.05)
    return EvaluationResult(
        images_evaluated=80,
        cameras_evaluated=8,
        ground_truth_boxes=100,
        predicted_boxes=98,
        per_class_detection={name: detection for name in _CLASSES},
        per_class_counting={name: counting for name in _CLASSES},
        per_camera_counting={f"cam{i}": counting for i in range(8)},
        overall_detection=detection,
        overall_counting=counting,
        macro_f1=0.947,
    )


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------


def test_report_has_the_four_required_sections():
    report = _blank_report()
    headings = ("## Evidence", "## Interpretation", "## Verdict", "## Missing evidence")
    for heading in headings:
        assert heading in report


def test_evidence_precedes_interpretation_which_precedes_the_verdict():
    report = _blank_report()
    assert report.index("## Evidence") < report.index("## Interpretation")
    assert report.index("## Interpretation") < report.index("## Verdict")


# --------------------------------------------------------------------------
# Missing evidence never becomes a result
# --------------------------------------------------------------------------


def test_no_verdict_is_stated_explicitly():
    report = _blank_report()
    assert "**NO VERDICT — MISSING EVIDENCE**" in report
    assert "ADVANCE" not in report.split("## Verdict")[1].split("## Missing")[0]


def test_missing_evidence_is_listed_verbatim():
    report = _blank_report(
        missing_evidence=[
            "No verdict issued: only 31/80 preregistered evaluation images "
            "currently have blind human annotations."
        ]
    )
    assert "only 31/80 preregistered evaluation images" in report


def test_blocking_reasons_reach_the_report():
    report = _blank_report()
    assert "no human ground truth is present" in report


def test_absent_metrics_render_as_not_available_not_zero():
    report = _blank_report()
    assert "No metrics were computed." in report
    assert "0.000" not in report


def test_incomplete_sample_is_reported_against_the_target():
    report = _blank_report(sample_frames=42, sample_cameras=3)
    assert "| Frames acquired | 42 | 160 |" in report
    assert "| Cameras | 3 | 8 |" in report


def test_no_interpretation_is_offered_without_a_measurement():
    report = _blank_report()
    interpretation = report.split("## Interpretation")[1].split("## Verdict")[0]
    assert "no model performance was measured" in interpretation


# --------------------------------------------------------------------------
# A real verdict
# --------------------------------------------------------------------------


def test_advance_report_carries_metrics_and_the_verdict():
    result = _good_result()
    verdict = decide(result, thresholds=GATE, gate_version=GATE_VERSION)
    report = render_report(
        result=result,
        verdict=verdict,
        run_manifest={
            "model_name": "RF-DETR Small",
            "confidence_threshold": 0.35,
            "git_commit": "abc123",
        },
        sample_frames=160,
        sample_cameras=8,
        target_frames=160,
        target_cameras=8,
        annotated_images=80,
        eval_set_size=80,
        class_distribution={"person": 40, "bicycle": 10, "car": 40, "bus": 10},
        missing_evidence=[],
    )
    assert "**ADVANCE**" in report
    assert "RF-DETR Small" in report
    assert "0.947" in report
    assert "Every input the preregistered gate requires is present." in report


def test_advance_does_not_claim_production_readiness():
    result = _good_result()
    verdict = decide(result, thresholds=GATE, gate_version=GATE_VERSION)
    report = render_report(
        result=result,
        verdict=verdict,
        run_manifest=None,
        sample_frames=160,
        sample_cameras=8,
        target_frames=160,
        target_cameras=8,
        annotated_images=80,
        eval_set_size=80,
        class_distribution={},
        missing_evidence=[],
    )
    assert "does **not** mean the model is production-ready" in report


def test_kill_report_does_not_hedge():
    result = _good_result()
    result.macro_f1 = 0.40
    verdict = decide(result, thresholds=GATE, gate_version=GATE_VERSION)
    report = render_report(
        result=result,
        verdict=verdict,
        run_manifest=None,
        sample_frames=160,
        sample_cameras=8,
        target_frames=160,
        target_cameras=8,
        annotated_images=80,
        eval_set_size=80,
        class_distribution={},
        missing_evidence=[],
    )
    assert "**KILL_OR_REPOSITION**" in report
    assert "not a defensible foundation" in report
    assert "a negative result here is a successful VIS-001" in report


# --------------------------------------------------------------------------
# Limitations
# --------------------------------------------------------------------------


def test_every_standing_limitation_is_emitted_even_on_a_pass():
    result = _good_result()
    verdict = decide(result, thresholds=GATE, gate_version=GATE_VERSION)
    report = render_report(
        result=result,
        verdict=verdict,
        run_manifest=None,
        sample_frames=160,
        sample_cameras=8,
        target_frames=160,
        target_cameras=8,
        annotated_images=80,
        eval_set_size=80,
        class_distribution={},
        missing_evidence=[],
    )
    assert verdict.verdict == "ADVANCE"
    for limitation in STANDING_LIMITATIONS:
        assert limitation in report


def test_the_scientific_boundaries_are_stated():
    report = _blank_report()
    for claim in (
        "Camera counts are not tourism counts.",
        "VIS-001 does not establish carrying capacity.",
        "VIS-001 does not validate SNTO's satellite indicators.",
    ):
        assert claim in report


def test_guadarrama_transferability_is_explicitly_disclaimed():
    assert any("Guadarrama" in item for item in STANDING_LIMITATIONS)
    assert "Guadarrama" in _blank_report()
