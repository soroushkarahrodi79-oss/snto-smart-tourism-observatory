"""Zero-shot RF-DETR Small inference, plus the reproducibility manifest.

Every heavy import (``rfdetr``, ``torch``, ``supervision``, ``PIL``) happens
*inside* a function. Importing this module costs nothing but the standard
library, so the repository's ordinary CI can lint and test the surrounding logic
without installing a 900 MB deep-learning stack or downloading model weights.

No fine-tuning happens here, and none may be added to VIS-001: the whole point
of the experiment is to measure an off-the-shelf checkpoint. Detections are
filtered to the four frozen target classes and to the frozen confidence
threshold before anything downstream sees them.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


class InferenceUnavailable(RuntimeError):
    """Raised when the CV stack or its weights are not available.

    Deliberately loud: a missing model is a *stop condition* for VIS-001, not
    something to paper over with a fallback detector or cached numbers.
    """


# --------------------------------------------------------------------------
# Reproducibility manifest (§12 of the protocol)
# --------------------------------------------------------------------------


@dataclass
class RunManifest:
    """Everything needed to reproduce an inference run, or to prove you cannot.

    A model result reported without this block is not a result: there would be
    no way to tell which checkpoint, which threshold and which exact bytes
    produced it.
    """

    experiment_id: str
    git_commit: str
    python_version: str
    platform: str
    timestamp_utc: str
    model_name: str
    model_package: str
    model_package_version: str
    checkpoint: str
    device: str
    confidence_threshold: float
    iou_threshold: float
    class_allowlist: list[str]
    random_seed: int
    number_of_images: int
    image_sha256: dict[str, str] = field(default_factory=dict)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


def git_commit(repo_root: Path | None = None) -> str:
    """Current HEAD, or ``"unknown"`` when git is unavailable.

    Never fabricated: an unknown commit is recorded as unknown so the reader
    knows the run cannot be tied back to a tree state.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root) if repo_root else None,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def package_version(package: str) -> str:
    from importlib import metadata

    try:
        return metadata.version(package)
    except Exception:  # noqa: BLE001 - any resolution failure means "unknown"
        return "unknown"


def build_run_manifest(
    *,
    experiment_id: str,
    model_name: str,
    model_package: str,
    checkpoint: str,
    device: str,
    confidence_threshold: float,
    iou_threshold: float,
    class_allowlist: Sequence[str],
    random_seed: int,
    image_sha256: dict[str, str],
    repo_root: Path | None = None,
) -> RunManifest:
    return RunManifest(
        experiment_id=experiment_id,
        git_commit=git_commit(repo_root),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        model_name=model_name,
        model_package=model_package,
        model_package_version=package_version(model_package),
        checkpoint=checkpoint,
        device=device,
        confidence_threshold=confidence_threshold,
        iou_threshold=iou_threshold,
        class_allowlist=list(class_allowlist),
        random_seed=random_seed,
        number_of_images=len(image_sha256),
        image_sha256=dict(sorted(image_sha256.items())),
    )


# --------------------------------------------------------------------------
# Detector
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RawDetection:
    """One model output, before class filtering."""

    class_name: str
    class_id: int
    box: tuple[float, float, float, float]  # xyxy, pixels
    confidence: float


def detect_device() -> str:
    """Report the accelerator opportunistically. CPU is always acceptable."""
    try:
        import torch
    except ImportError:
        return "unknown"
    if torch.cuda.is_available():
        return f"cuda:{torch.cuda.get_device_name(0)}"
    return "cpu"


def load_detector() -> Any:
    """Instantiate RF-DETR Small.

    The constructor downloads the published COCO checkpoint on first use and
    caches it. A failure here is a stop condition, not something to work around.
    """
    try:
        from rfdetr import RFDETRSmall
    except ImportError as exc:
        raise InferenceUnavailable(
            "rfdetr is not installed in this environment.\n"
            "VIS-001 keeps the CV stack out of the repository's core "
            "requirements on purpose; install the experiment-local extras:\n"
            "  python -m pip install -r "
            "experiments/vis001_madrid_counting/requirements.txt"
        ) from exc

    try:
        return RFDETRSmall()
    except Exception as exc:  # noqa: BLE001 - weights download / init failure
        raise InferenceUnavailable(
            f"RF-DETR Small could not be initialised: {exc}\n"
            "The pretrained checkpoint is fetched from storage.googleapis.com on "
            "first use; if that host is unreachable, VIS-001 stops rather than "
            "substituting another model."
        ) from exc


def _coco_name_for(class_id: int) -> str:
    """Resolve a COCO category id to its name, without guessing.

    Prefers RF-DETR's own table so the mapping always matches the checkpoint
    actually loaded; falls back to the four ids VIS-001 cares about.
    """
    try:
        from rfdetr.assets.coco_classes import COCO_CLASSES
    except ImportError:
        COCO_CLASSES = {1: "person", 2: "bicycle", 3: "car", 6: "bus"}
    return COCO_CLASSES.get(class_id, "")


def detections_from_supervision(result: Any) -> list[RawDetection]:
    """Normalise a ``supervision.Detections`` object into plain tuples.

    RF-DETR attaches human-readable names in ``data["class_name"]`` and, for
    pretrained COCO checkpoints, emits raw (sparse) COCO category ids in
    ``class_id``. The name is preferred when present; the id table is the
    fallback. Neither path invents a label — an unresolvable class becomes ``""``
    and is dropped by the allowlist filter.
    """
    boxes = result.xyxy
    confidences = result.confidence
    class_ids = result.class_id
    names = None
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        names = data.get("class_name")

    detections: list[RawDetection] = []
    for index in range(len(boxes)):
        class_id = int(class_ids[index]) if class_ids is not None else -1
        if names is not None and index < len(names):
            class_name = str(names[index])
        else:
            class_name = _coco_name_for(class_id)
        x1, y1, x2, y2 = (float(value) for value in boxes[index])
        detections.append(
            RawDetection(
                class_name=class_name,
                class_id=class_id,
                box=(x1, y1, x2, y2),
                confidence=(
                    float(confidences[index]) if confidences is not None else 0.0
                ),
            )
        )
    return detections


def filter_detections(
    detections: Iterable[RawDetection],
    *,
    allowed_classes: Sequence[str],
    confidence_threshold: float,
) -> list[RawDetection]:
    """Apply the two frozen filters: the class allowlist and the threshold.

    Classes outside the frozen four are discarded here and never reach the gate,
    even though the model emits eighty more of them.
    """
    allowed = set(allowed_classes)
    return [
        detection
        for detection in detections
        if detection.class_name in allowed
        and detection.confidence >= confidence_threshold
    ]


def infer_image(
    detector: Any,
    image_path: Path,
    *,
    threshold: float,
) -> list[RawDetection]:
    """Run the model on one image and return normalised detections.

    ``threshold`` is passed to the model so it does its own cheap pruning; the
    caller still re-applies the frozen threshold via :func:`filter_detections`,
    which keeps the gate's filter independent of the model's internal semantics.
    """
    from PIL import Image

    with Image.open(image_path) as handle:
        image = handle.convert("RGB")
        result = detector.predict(image, threshold=threshold)
    return detections_from_supervision(result)


def prediction_record(
    *,
    image_id: str,
    camera_id: str,
    detection: RawDetection,
) -> dict[str, object]:
    """One line of ``predictions.jsonl``.

    ``evidence`` is stamped on every row so a prediction can never be read back
    as an observation. It is an experiment-local label and is deliberately not
    SNTO's global ``DataStatus``.
    """
    from vis001 import config

    x1, y1, x2, y2 = detection.box
    return {
        "image_id": image_id,
        "camera_id": camera_id,
        "class_name": detection.class_name,
        "class_id": detection.class_id,
        "bbox_xyxy": [round(value, 2) for value in (x1, y1, x2, y2)],
        "confidence": round(detection.confidence, 4),
        "evidence": config.EVIDENCE_MODEL_OUTPUT,
    }
