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
| Preregistration | Frozen, gate version 1.0 (amendment A1: pre-data audit corrections) |
| Camera manifest | **Empty** — the KML is unreachable here. See *Blocker* below |
| Benchmark cameras frozen | **No** — cannot be selected from an empty manifest |
| Data acquired | **None** |
| Human ground truth | **None** — annotation cannot begin without frames |
| Baseline run | Not executed — no images to run on |
| Verdict | **NO VERDICT — MISSING EVIDENCE** |

### Blocker: the official Madrid sources are unreachable from this environment

`informo.madrid.es` (which serves the authoritative `CCTV.kml`),
`datos.madrid.es` and the DGT national access point (`nap.dgt.es`) are all
refused at the network egress proxy (`403` to `CONNECT`) in the environment
where this experiment was implemented. That is an organisation-level network
policy, not a fault in the source or in this code.

Per the protocol's stop conditions, VIS-001 **stops the data claim, not the
implementation**. The acquisition pipeline ships and is reproducible; it has
simply never had a reachable source to run against. No frame was invented, no
mirror was substituted, and no generic internet imagery was used in place of
official Madrid data.

Both `data/camera_manifest.csv` and `data/sample_manifest.csv` are therefore
**header-only**, and `data/selected_cameras.json` does not exist. That is
deliberate: they state the schema without asserting a single row of evidence
that does not exist. The eight benchmark cameras cannot be frozen from an empty
camera manifest, and every downstream step refuses to run without them.

## Frozen parameters

| | |
| --- | --- |
| Model | RF-DETR Small (`rfdetr.RFDETRSmall`), published zero-shot COCO checkpoint |
| Fine-tuning | Forbidden in VIS-001 |
| Classes | `person`, `bicycle`, `car`, `bus` — exactly four, no additions after results |
| Confidence threshold | 0.35 |
| Evaluation IoU | 0.50 |
| Camera list | `https://informo.madrid.es/informo/tmadrid/CCTV.kml`, parsed structurally |
| Licence / terms | Verified against the `datos.madrid.es` catalogue page |
| Camera selection | 8 compass sectors, median distance — procedure version 1.0 |
| Sample | ≥ 20 **unique** frames from **each** of the 8 frozen cameras |
| Evaluation set | **exactly** 10 × 8 = 80, seed `20260824` |
| Class coverage | all four classes evaluable, or NO VERDICT |
| Gate version | 1.0 |

### What forces NO VERDICT

The gate is never applied on partial structure. Any one of these is enough:

- the eight benchmark cameras are not frozen;
- a frozen camera holds fewer than 20 unique frames (**a matching total of 160
  spread unevenly does not count** — that is a different sample sharing a
  headline number);
- the evaluation set is not exactly 80 images, 10 from each frozen camera —
  79 is not 80, and a short camera is never back-filled from another;
- any of `person` / `bicycle` / `car` / `bus` is not evaluable → **NO VERDICT —
  INSUFFICIENT CLASS COVERAGE**. The undefined class is never dropped from the
  macro average;
- the evaluation set is not fully annotated, or predictions are absent.

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
# 1. Resolve the official source and build the camera manifest by parsing the
#    KML structurally. Verifies licence text against the catalogue page.
#    Writes data/source_resolution.json + data/camera_manifest.csv.
#    No imagery is downloaded here.
python experiments/vis001_madrid_counting/scripts/resolve_sources.py

# 2. Freeze the eight benchmark cameras (compass sectors, median distance).
#    Geographic metadata only — no imagery, no model. MUST run before step 5.
python experiments/vis001_madrid_counting/scripts/select_cameras.py
python experiments/vis001_madrid_counting/scripts/select_cameras.py --check

# 3. Acquire frames from exactly those eight. One pass = one frame per camera.
#    Frames land in data/raw/ (git-ignored); byte-identical repeats are skipped.
python experiments/vis001_madrid_counting/scripts/acquire_frames.py --once
python experiments/vis001_madrid_counting/scripts/acquire_frames.py \
    --samples 20 --interval-seconds 300

# 4. Freeze the 80-image evaluation set (10 per frozen camera, seed 20260824).
python experiments/vis001_madrid_counting/scripts/select_eval_set.py
python experiments/vis001_madrid_counting/scripts/select_eval_set.py --check

# 5. Validate blind human annotations (produced externally — see
#    data/annotations/README.md).
python experiments/vis001_madrid_counting/scripts/validate_annotations.py

# 6. Run the frozen zero-shot baseline. Needs the CV stack.
python experiments/vis001_madrid_counting/scripts/run_baseline.py --eval-set-only

# 7. Evaluate and apply the gate.
python experiments/vis001_madrid_counting/scripts/evaluate.py
```

Step 3 runs its passes in the **foreground** and exits. It never launches a
long-running background collector.

Steps 1–2 must complete before step 3: acquisition targets the frozen eight and
refuses to run against an unfrozen camera set. Step 2 must complete before step
6 — the whole point of freezing the cameras is that they are chosen before the
model has ever been run.

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
│   ├── camera_manifest.csv    ← cameras from the KML (header-only until resolved)
│   ├── sample_manifest.csv    ← frame chain of custody (header-only until acquired)
│   └── annotations/README.md  ← how to produce and place blind COCO ground truth
├── vis001/
│   ├── config.py              ← every frozen constant
│   ├── cameras.py             ← structural KML parsing + the frozen camera choice
│   ├── manifest.py            ← frame manifest, completeness, evaluation-set draw
│   ├── annotations.py         ← COCO ground-truth loading and validation
│   ├── inference.py           ← RF-DETR adapter (lazy imports) + run manifest
│   ├── metrics.py             ← IoU, matching, detection/counting metrics, the gate
│   └── reporting.py           ← report rendering
└── scripts/                   ← the seven commands above
```

## Tests

The pure logic runs in the repository's normal suite — no PyTorch, no weights,
no network:

```bash
python -m pytest tests/unit/ -k vis001 -q
```

They cover IoU, one-to-one matching, precision/recall/F1, count MAE and WAPE,
zero-ground-truth edge cases, manifest and annotation validation, the
reproducible evaluation split, and every branch of the verdict logic — including
its refusal to issue a verdict on incomplete evidence.

`test_vis001_cameras.py` and `test_vis001_structural_gates.py` are the pre-data
audit regressions. Each names the loophole it closes: image URLs harvested from
outside a Placemark, a KML served as an error page, cameras picked by sorted id,
160 frames from two cameras, 79 images passing as 80, a short camera
back-filled from another, and an undefined class quietly averaged away.

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
