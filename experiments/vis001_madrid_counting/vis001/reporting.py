"""Render the VIS-001 report.

The report is structured so that a reader cannot mistake a measurement for an
interpretation. Four sections, always in this order and always present:

``Evidence``
    Only what was measured. Counts, versions, metrics. No adjectives.
``Interpretation``
    What those numbers suggest. Clearly separated, clearly hedged.
``Verdict``
    Exactly one of ADVANCE / LOCAL_FINE_TUNE / KILL_OR_REPOSITION — or the
    explicit statement that no verdict could be issued.
``Missing evidence`` and ``Limitations``
    What is absent, and what the experiment does not establish even when it
    succeeds.

An incomplete evaluation is never rendered as a partial pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from vis001.metrics import EvaluationResult, Verdict

#: Fixed limitation list (§22 of the protocol). These are properties of the
#: experimental design, not of any particular result, so they are emitted on
#: every report — including a report that ADVANCEs.
STANDING_LIMITATIONS: tuple[str, ...] = (
    "Camera counts are not tourism counts.",
    "A `person` detection does not mean a tourist.",
    "Vehicles do not imply visitors to a protected area.",
    "Static snapshots do not establish individual trajectories; nothing here "
    "tracks a person or a vehicle between frames.",
    "Camera geometry (height, angle, focal length) affects detectability.",
    "Occlusion affects counts; an object hidden behind another is not counted.",
    "Lighting, weather and time of day affect detection.",
    "Public Madrid traffic cameras are a technical benchmark domain. They are "
    "not evidence of direct transferability to Parque Nacional de la Sierra de "
    "Guadarrama, whose scenes, mounting geometry and object mix differ.",
    "VIS-001 does not establish ecological impact.",
    "VIS-001 does not establish carrying capacity.",
    "VIS-001 does not validate SNTO's satellite indicators.",
    "Transfer to FieldOS/SNTO would require a separate field-domain validation.",
)


def _fmt(value: float | None, digits: int = 3) -> str:
    """Format a metric, or say plainly that it is undefined.

    ``n/a`` is used rather than ``0`` so an undefined quantity is never read as
    a measured zero.
    """
    return "n/a" if value is None else f"{value:.{digits}f}"


def _fmt_int(value: int | None) -> str:
    return "n/a" if value is None else str(value)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def render_report(
    *,
    result: EvaluationResult | None,
    verdict: Verdict,
    run_manifest: dict[str, object] | None,
    sample_frames: int,
    sample_cameras: int,
    target_frames: int,
    target_cameras: int,
    annotated_images: int,
    eval_set_size: int,
    class_distribution: dict[str, int],
    missing_evidence: Sequence[str],
) -> str:
    """Build ``report.md`` as a string."""
    lines: list[str] = []
    add = lines.append

    add("# VIS-001 — Madrid Visual Counting Benchmark")
    add("")
    add(
        "Feasibility experiment. Not an SNTO feature, not a product, not a "
        "deployed capability."
    )
    add("")
    add(
        "> **Question.** Can an off-the-shelf foundation object detector, with "
        "zero local fine-tuning, count `person` / `bicycle` / `car` / `bus` "
        "reliably enough on real public Madrid traffic-camera imagery to "
        "justify further work on a Visual Evidence Layer?"
    )
    add("")

    # ---------------------------------------------------------------- Evidence
    add("## Evidence")
    add("")
    add("Measured facts only. Nothing in this section is an inference.")
    add("")
    add("### Sample")
    add("")
    add("| Quantity | Value | Preregistered target |")
    add("| --- | ---: | ---: |")
    add(f"| Frames acquired | {sample_frames} | {target_frames} |")
    add(f"| Cameras | {sample_cameras} | {target_cameras} |")
    add(
        f"| Images with blind human annotation | {annotated_images} "
        f"| {eval_set_size} |"
    )
    add("")

    if class_distribution:
        add("### Ground-truth class distribution")
        add("")
        add("| Class | Annotated objects |")
        add("| --- | ---: |")
        for name, count in class_distribution.items():
            add(f"| `{name}` | {count} |")
        add("")
    else:
        add("### Ground-truth class distribution")
        add("")
        add("No human annotations present, so there is no class distribution.")
        add("")

    add("### Model")
    add("")
    if run_manifest:
        add("| Field | Value |")
        add("| --- | --- |")
        for key in (
            "model_name",
            "model_package",
            "model_package_version",
            "checkpoint",
            "device",
            "confidence_threshold",
            "iou_threshold",
            "git_commit",
            "python_version",
            "platform",
            "timestamp_utc",
        ):
            if key in run_manifest:
                add(f"| `{key}` | {run_manifest[key]} |")
        add("")
    else:
        add(
            "No inference run has been executed, so there is no reproducibility "
            "manifest and no model output to report."
        )
        add("")

    add("### Metrics")
    add("")
    if result is None or result.overall_detection is None:
        add(
            "No metrics were computed. Detection and counting metrics require "
            "both model predictions and blind human ground truth over the "
            "frozen evaluation set; at least one is absent."
        )
        add("")
    else:
        overall = result.overall_detection
        counting = result.overall_counting
        add(
            f"Evaluation set: {result.images_evaluated} images across "
            f"{result.cameras_evaluated} cameras, "
            f"{result.ground_truth_boxes} ground-truth objects, "
            f"{result.predicted_boxes} predicted objects."
        )
        add("")
        add("**Detection, IoU ≥ 0.50, one-to-one matching**")
        add("")
        add("| Scope | TP | FP | FN | Precision | Recall | F1 |")
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        add(
            f"| **all classes** | {overall.true_positives} | "
            f"{overall.false_positives} | {overall.false_negatives} | "
            f"{_fmt(overall.precision)} | {_fmt(overall.recall)} | "
            f"{_fmt(overall.f1)} |"
        )
        for name, metrics in result.per_class_detection.items():
            add(
                f"| `{name}` | {metrics.true_positives} | "
                f"{metrics.false_positives} | {metrics.false_negatives} | "
                f"{_fmt(metrics.precision)} | {_fmt(metrics.recall)} | "
                f"{_fmt(metrics.f1)} |"
            )
        add("")
        add(f"Macro F1 (unweighted mean over classes): **{_fmt(result.macro_f1)}**")
        add("")
        add("**Counting**")
        add("")
        add(
            "| Scope | Frames | GT total | Predicted total | MAE | "
            "Mean signed error | WAPE |"
        )
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        if counting is not None:
            add(
                f"| **all classes** | {counting.frames} | "
                f"{counting.total_ground_truth} | {counting.total_predicted} | "
                f"{_fmt(counting.mae)} | {_fmt(counting.bias)} | "
                f"{_fmt(counting.wape)} |"
            )
        for name, metrics in result.per_class_counting.items():
            add(
                f"| `{name}` | {metrics.frames} | {metrics.total_ground_truth} | "
                f"{metrics.total_predicted} | {_fmt(metrics.mae)} | "
                f"{_fmt(metrics.bias)} | {_fmt(metrics.wape)} |"
            )
        add("")
        add("**Counting by camera**")
        add("")
        add("| Camera | Frames | GT total | Predicted total | MAE | WAPE |")
        add("| --- | ---: | ---: | ---: | ---: | ---: |")
        for camera, metrics in result.per_camera_counting.items():
            add(
                f"| `{camera or '(unknown)'}` | {metrics.frames} | "
                f"{metrics.total_ground_truth} | {metrics.total_predicted} | "
                f"{_fmt(metrics.mae)} | {_fmt(metrics.wape)} |"
            )
        add("")

    # ---------------------------------------------------------- Interpretation
    add("## Interpretation")
    add("")
    if verdict.verdict is None:
        add(
            "No interpretation of model performance is offered, because no "
            "model performance was measured. The section below states exactly "
            "what is missing."
        )
    else:
        add(_interpretation_for(verdict, result))
    add("")

    # ----------------------------------------------------------------- Verdict
    add("## Verdict")
    add("")
    if verdict.verdict is None:
        add("**NO VERDICT — MISSING EVIDENCE**")
        add("")
        add(
            "The preregistered gate was not applied. An incomplete evaluation "
            "is not a result, and is never reported as one."
        )
    else:
        add(f"**{verdict.verdict}**")
        add("")
        add(f"Gate version `{verdict.gate_version}`.")
        add("")
        add("| Gate quantity | Measured | Frozen threshold |")
        add("| --- | ---: | ---: |")
        add(
            f"| macro F1 | {_fmt(verdict.macro_f1)} | "
            "≥ 0.80 to ADVANCE, < 0.65 kills |"
        )
        add(
            f"| counting WAPE | {_fmt(verdict.count_wape)} | "
            "≤ 0.20 to ADVANCE, > 0.35 kills |"
        )
        if verdict.failed_conditions:
            add("")
            add("Conditions not met:")
            add("")
            for condition in verdict.failed_conditions:
                add(f"- {condition}")
    add("")

    # -------------------------------------------------------- Missing evidence
    add("## Missing evidence")
    add("")
    if missing_evidence:
        for item in missing_evidence:
            add(f"- {item}")
    elif not verdict.blocking_reasons:
        add("None. Every input the preregistered gate requires is present.")
    add("")
    if verdict.blocking_reasons:
        add("**Why the gate was not applied:**")
        add("")
        for reason in verdict.blocking_reasons:
            add(f"- {reason}")
        add("")

    # ------------------------------------------------------------- Limitations
    add("## Limitations that hold regardless of the result")
    add("")
    for limitation in STANDING_LIMITATIONS:
        add(f"- {limitation}")
    add("")

    return "\n".join(lines) + "\n"


def _interpretation_for(verdict: Verdict, result: EvaluationResult | None) -> str:
    """One paragraph, matched to the verdict, with no upgrade of the claim."""
    if verdict.verdict == "ADVANCE":
        return (
            "The zero-shot baseline met every preregistered condition on this "
            "sample. That justifies scoping VIS-002 and further Visual "
            "Evidence Layer work. It does **not** mean the model is "
            "production-ready, and it says nothing about performance outside "
            "the eight benchmarked Madrid camera views."
        )
    if verdict.verdict == "LOCAL_FINE_TUNE":
        worst = _worst_slice(result)
        tail = (
            f" The largest single contributor to the error is {worst}."
            if worst
            else ""
        )
        return (
            "The baseline is promising in aggregate but misses at least one "
            "preregistered ADVANCE condition, and the failure is bounded rather "
            "than diffuse." + tail + " That makes a Madrid-specific labelled "
            "dataset plausibly worth building. No fine-tuning was performed in "
            "VIS-001, and none may be performed on this evaluation set without "
            "first retiring it."
        )
    return (
        "At least one major failure condition fired. On this evidence the "
        "off-the-shelf baseline is not a defensible foundation for a Visual "
        "Evidence Layer in its current form. The gate was not weakened to "
        "rescue the experiment; a negative result here is a successful VIS-001."
    )


def _worst_slice(result: EvaluationResult | None) -> str:
    """Name the weakest class or camera, when one is identifiable."""
    if result is None:
        return ""
    candidates: list[tuple[float, str]] = []
    for name, metrics in result.per_class_detection.items():
        if metrics.f1 is not None:
            candidates.append((metrics.f1, f"class `{name}` (F1 {metrics.f1:.3f})"))
    if not candidates:
        return ""
    candidates.sort()
    worst_f1, worst_label = candidates[0]

    camera_candidates = [
        (metrics.wape, camera)
        for camera, metrics in result.per_camera_counting.items()
        if metrics.wape is not None
    ]
    if camera_candidates:
        worst_wape, worst_camera = max(camera_candidates)
        if worst_wape > 0.35:
            return (
                f"{worst_label} and camera `{worst_camera}` "
                f"(counting WAPE {worst_wape:.3f})"
            )
    return worst_label if worst_f1 < 0.80 else ""
