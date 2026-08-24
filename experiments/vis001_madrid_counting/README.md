# VIS-001 — Madrid Visual Counting Benchmark

A small, isolated, preregistered computer-vision **feasibility experiment**.

It is not a product, not a platform, not a dashboard, and not an SNTO feature.
Nothing under `src/`, `app.py`, `/api/v2`, `mobile/` or the deployment imports
anything here, and nothing here writes to the SNTO database.

## The question

> Can an off-the-shelf foundation object-detection model, with **zero** local
> fine-tuning, produce sufficiently reliable counts of selected mobility objects
> from real public Madrid traffic-camera imagery to justify further work on a
> Visual Evidence Layer?

That is the entire scope. The full contract — sample design, frozen thresholds,
decision gate, privacy constraints, non-goals — is in
**[`PREREGISTRATION.md`](PREREGISTRATION.md)**, written before any result
existed. Read that first; this file is only the operating manual.

## Operating principle

The camera is a **sensor**, not an intelligence system. The permitted chain is:

```
IMAGE → DETECTION → MEASUREMENT → HUMAN GROUND TRUTH → EVALUATION → VERDICT
```

VIS-001 never steps from an image to tourism pressure, carrying capacity,
ecological degradation, visitor behaviour or tourist-versus-resident identity.
The model's output is a derived prediction; it is never ground truth.

## Current status

| Axis | State |
| --- | --- |
| Implementation | Complete — pipeline, metrics, gate, tests |
| Preregistration | Frozen, gate version 1.0 |
| Data acquired | **None.** See *Blocker* below |
| Human ground truth | **None** — annotation cannot begin without frames |
| Baseline run | Not executed — no images to run on |
| Verdict | **NO VERDICT — MISSING EVIDENCE** |

### Blocker: the official Madrid sources are unreachable from this environment

`datos.madrid.es`, `informo.madrid.es` and the DGT national access point
(`nap.dgt.es`) are all refused at the network egress proxy (`403` to `CONNECT`)
in the environment where this experiment was implemented. That is an
organisation-level network policy, not a fault in the source or in this code.

Per the protocol's stop conditions, VIS-001 **stops the data claim, not the
implementation**. The acquisition pipeline ships and is reproducible; it has
simply never had a reachable source to run against. No frame was invented, no
mirror was substituted, and no generic internet imagery was used in place of
official Madrid data.

The frozen manifest at `data/sample_manifest.csv` is therefore **header-only**.
That is deliberate: it states the schema without asserting a single row of
evidence that does not exist.

## Frozen parameters

| | |
| --- | --- |
| Model | RF-DETR Small (`rfdetr.RFDETRSmall`), published zero-shot COCO checkpoint |
| Fine-tuning | Forbidden in VIS-001 |
| Classes | `person`, `bicycle`, `car`, `bus` — exactly four, no additions after results |
| Confidence threshold | 0.35 |
| Evaluation IoU | 0.50 |
| Sample | 8 cameras × 20 frames = 160 |
| Evaluation set | 10 images × 8 cameras = 80, seed `20260824` |
| Gate version | 1.0 |

## Setup

The CV stack is **experiment-local**. It is deliberately absent from the
repository's `requirements.txt` so SNTO's CI never installs PyTorch.

```bash
python -m venv .venv-vis001
. .venv-vis001/bin/activate
pip install --extra-index-url https://download.pytorch.org/whl/cpu \
    -r experiments/vis001_madrid_counting/requirements.txt
```

CPU is fully supported and is what the 160-image sample is sized for. A CUDA
device is used opportunistically if `torch` finds one, but none is required.

The pure metric, manifest, annotation and gate logic needs **none** of this — it
is standard library only and runs in the repository's ordinary test suite.

## Commands

Run them in this order. Each refuses to proceed on evidence that does not exist.

```bash
# 1. Verify the official source: reachability, licence text, declared image URLs.
#    Writes data/source_resolution.json. Nothing is downloaded here.
python experiments/vis001_madrid_counting/scripts/resolve_sources.py

# 2. Acquire frames. One pass = one frame per camera. Refuses to run unless
#    step 1 reported RESOLVED. Frames land in data/raw/ (git-ignored).
python experiments/vis001_madrid_counting/scripts/acquire_frames.py --once
python experiments/vis001_madrid_counting/scripts/acquire_frames.py \
    --samples 20 --interval-seconds 300

# 3. Freeze the 80-image evaluation set (stratified, seed 20260824).
python experiments/vis001_madrid_counting/scripts/select_eval_set.py
python experiments/vis001_madrid_counting/scripts/select_eval_set.py --check

# 4. Validate blind human annotations (produced externally — see
#    data/annotations/README.md).
python experiments/vis001_madrid_counting/scripts/validate_annotations.py

# 5. Run the frozen zero-shot baseline. Needs the CV stack.
python experiments/vis001_madrid_counting/scripts/run_baseline.py --eval-set-only

# 6. Evaluate and apply the gate.
python experiments/vis001_madrid_counting/scripts/evaluate.py
```

Step 2 runs its passes in the **foreground** and exits. It never launches a
long-running background collector.

### Order matters

Run step 5 **after** annotation is complete, or on a machine the annotator does
not see. Ground truth must be produced blind (no model boxes, no overlays, no
counts) — a human correcting a model's output measures the human's agreement
with the model, not the model's agreement with reality.

## Outputs

`outputs/` is git-ignored.

| File | Contents |
| --- | --- |
| `predictions.jsonl` | One detection per line, after class and threshold filtering |
| `run_manifest.json` | Commit, versions, checkpoint, device, thresholds, per-image SHA-256 |
| `metrics.json` | Detection and counting metrics, sliced by class and camera |
| `verdict.json` | `ADVANCE` / `LOCAL_FINE_TUNE` / `KILL_OR_REPOSITION`, or `null` |
| `report.md` | Evidence · Interpretation · Verdict · Missing evidence · Limitations |

A metric with no evidence behind it is `null`. Never `0`.

## Layout

```
experiments/vis001_madrid_counting/
├── README.md                  ← you are here
├── PREREGISTRATION.md         ← the scientific contract; read this
├── experiment.yaml            ← machine-readable mirror of the frozen design
├── requirements.txt           ← experiment-local CV stack
├── .gitignore                 ← raw imagery, outputs and weights never committed
├── data/
│   ├── sample_manifest.csv    ← frame chain of custody (header-only until acquired)
│   └── annotations/README.md  ← how to produce and place blind COCO ground truth
├── vis001/
│   ├── config.py              ← every frozen constant
│   ├── manifest.py            ← manifest I/O, validation, evaluation-set draw
│   ├── annotations.py         ← COCO ground-truth loading and validation
│   ├── inference.py           ← RF-DETR adapter (lazy imports) + run manifest
│   ├── metrics.py             ← IoU, matching, detection/counting metrics, the gate
│   └── reporting.py           ← report rendering
└── scripts/                   ← the six commands above
```

## Tests

The pure logic runs in the repository's normal suite — no PyTorch, no weights,
no network:

```bash
python -m pytest tests/unit/test_vis001_metrics.py \
                 tests/unit/test_vis001_manifest.py \
                 tests/unit/test_vis001_annotations.py \
                 tests/unit/test_vis001_gate.py \
                 tests/unit/test_vis001_reporting.py \
                 tests/unit/test_vis001_preregistration.py -q
```

They cover IoU, one-to-one matching, precision/recall/F1, count MAE and WAPE,
zero-ground-truth edge cases, manifest and annotation validation, the
reproducible evaluation split, and every branch of the verdict logic — including
its refusal to issue a verdict on incomplete evidence.

`test_vis001_preregistration.py` additionally asserts that `config.py`,
`experiment.yaml` and `PREREGISTRATION.md` still agree on every frozen number,
that no biometric or tracking library appears anywhere in the source, and that
importing any VIS-001 module does not pull in `torch`, `rfdetr`, `supervision`
or `cv2`.

## Privacy

Object counting only. The software never attempts to determine identity: no face
recognition, no face embeddings, no person re-identification, no age, gender,
ethnicity or emotion inference, no licence-plate recognition, no OCR, no
persistent individual tracking, no tourist-versus-resident classification.

Raw camera imagery is never committed, and neither are annotated previews that
draw boxes around people. What is committed: code, manifests, hashes, the
annotation schema, aggregated metrics and the report.

## What VIS-001 does not establish

Even a clean `ADVANCE` would mean only that the zero-shot baseline is worth
building on. It would not mean the model is production-ready, and it would say
nothing about:

- tourism pressure — camera counts are not tourism counts, and `person` does not
  mean tourist;
- carrying capacity or Limits of Acceptable Change;
- ecological impact;
- the validity of SNTO's Sentinel-2 indicators;
- transferability to Parque Nacional de la Sierra de Guadarrama. Madrid traffic
  cameras are a **technical benchmark domain**: different scenes, different
  mounting geometry, different object mix. Transfer to FieldOS/SNTO would need
  its own field-domain validation.

## Success condition

Success is **not** a positive model result. Success is a reproducible,
privacy-bounded, preregistered experiment that can honestly determine whether
zero-shot computer vision is reliable enough to justify a Visual Evidence Layer.

A negative result is a successful VIS-001, provided the experiment proves it
honestly.
