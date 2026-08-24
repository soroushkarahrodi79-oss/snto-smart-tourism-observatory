# VIS-001 — Preregistration

**Experiment id:** VIS-001
**Title:** Madrid Visual Counting Benchmark
**Gate version:** 1.0
**Preregistered:** 2026-08-24, before any evaluation result existed.

This document is the scientific contract for VIS-001. Every threshold below was
fixed before any image was scored. **No threshold in this document may be
changed after evaluation results have been observed.** If a preregistered rule
must change for a technical reason, it is recorded as a numbered protocol
deviation in the final section *before* the formal evaluation is re-run. History
is never rewritten to make a result pass.

---

## 1. Research question

> Can an off-the-shelf foundation object-detection model, with zero local
> fine-tuning, produce sufficiently reliable counts of selected mobility objects
> from real public Madrid traffic-camera imagery to justify further work on a
> Visual Evidence Layer?

That is the whole question. VIS-001 answers it and nothing adjacent to it.

## 2. Operating principle

The camera is treated as a **sensor**, not as an intelligence system. The only
permitted inferential chain is:

```
IMAGE → DETECTION → MEASUREMENT → HUMAN GROUND TRUTH → EVALUATION → VERDICT
```

VIS-001 does **not** step from an image to tourism pressure, carrying capacity,
ecological degradation, thermal comfort, visitor behaviour, or tourist-versus-
resident identity. Those are interpretations this experiment does not establish
and may not imply.

The model's output is a **derived prediction**. It is never ground truth.

## 3. Sample design

| Parameter | Value |
| --- | --- |
| Camera locations | 8 |
| Frames per camera | 20 |
| Total target frames | 160 |
| Camera list | `https://informo.madrid.es/informo/tmadrid/CCTV.kml` (authoritative) |
| Licence / terms | The `datos.madrid.es` catalogue page for "Tráfico. Cámaras" |
| Third-party mirrors | Not permitted while the official source exists |

### Camera discovery — structural, not scraped

Cameras are read out of the KML's `<Placemark>` structure: published name,
`<Point>` coordinates, and the image endpoint attached to that Placemark (from
`<ExtendedData>`, or from the `<description>` balloon parsed as HTML **scoped to
that one Placemark**). A Placemark without both coordinates and an image
endpoint is dropped, never completed from a guess.

Cameras are **never** identified by scanning a page for anything ending in
`.jpg` or `.png`. A blind regex over arbitrary markup returns logos, legend
icons and banners with equal confidence, and none of them is a camera. Every row
of the camera manifest is therefore traceable to one entry in the official
dataset. Provenance is verified against the catalogue page as well as the KML,
because the KML ships no licence header.

The camera manifest records, per camera: `camera_id`, `camera_name`,
`latitude`, `longitude`, `image_url`, `source_document`. It is frozen before
selection.

### Camera selection — deterministic, geographic, pre-model

The eight benchmark cameras are chosen by a frozen procedure (version **1.0**),
run **before any inference**:

1. Compute the centroid of every camera published in the KML.
2. Assign each camera to one of eight 45° compass sectors around that centroid
   (N, NE, E, SE, S, SW, W, NW), with longitude scaled by `cos(latitude)` so a
   degree east covers the same ground as a degree north.
3. Within each sector, order by distance from the centroid, breaking ties by
   `camera_id`, and take the **median** camera. Not the nearest (which would
   concentrate all eight in the centre) and not the farthest (which would
   concentrate them on the ring road) — either collapses the scene variety the
   sectors exist to create.
4. Visit sectors in compass order; backfill an empty sector from the sector with
   the most unselected cameras, so a gap in published coverage does not silently
   yield seven cameras.

This replaces "the first eight sorted camera ids", which is **not** acceptable:
municipal ids track installation batches, so the lowest eight tend to sit on the
same few roads — one scene type, one mounting style, one background.

Every input is **published geographic metadata**. No image is opened, no model
is run, and no prediction is consulted, so the choice cannot be tuned — even
accidentally — to flatter RF-DETR. No camera may be previewed, scored or
rejected on the basis of how well the model does on it.

The eight are frozen to `data/selected_cameras.json`, with the camera manifest's
SHA-256, **before** `run_baseline.py` is ever run.

### Sample completeness is structural

The sample is complete only when **each** of the eight frozen cameras holds at
least 20 **unique** frames (unique by content hash: Madrid republishes a capture
roughly every five minutes, and byte-identical repeats add no observation).

A frame total of 160 **does not** by itself satisfy completeness. 160 frames
from two cameras, or spread 40/30/30/20/20/10/10/0, is a different sample that
happens to share a headline number, and it would destroy the per-camera
stratification the gate's camera rules rest on. Frames from a camera outside the
frozen eight also break completeness rather than padding it.

Required per-frame metadata: `image_id`, `camera_id`, `camera_name`,
`source_url`, `retrieved_at_utc`, `source_timestamp`, `latitude`, `longitude`,
`width`, `height`, `sha256`, `local_relative_path`, `licence_or_source_note`.
Fields the official source does not expose are left empty. They are never
inferred.

**If the 160-frame sample cannot be collected from currently accessible public
data, the data claim stops — the implementation does not.** The reproducible
acquisition pipeline still ships, and the result is reported as
`TARGET SAMPLE NOT YET COMPLETE`. Missing frames are never manufactured.

## 4. Target classes — frozen

```
person
bicycle
car
bus
```

Exactly four. **No fifth class may be added after results are seen.** The model
exposes ~80 more COCO classes; every one of them is discarded before the gate is
computed.

## 5. Model and inference parameters — frozen

| Parameter | Value |
| --- | --- |
| Model | RF-DETR Small (`rfdetr.RFDETRSmall`) |
| Weights | The published zero-shot COCO checkpoint |
| Fine-tuning | **Forbidden** in VIS-001 |
| Confidence threshold | **0.35** |
| Evaluation IoU threshold | **0.50** |
| Second architecture | Not introduced (no YOLO comparison in VIS-001) |

Inference runs locally against the open-source `rfdetr` package. No Roboflow API
credentials are used. CPU execution is supported; a GPU is used opportunistically
if present but is never required.

A threshold-sensitivity sweep **may** be computed and reported as a clearly
labelled **secondary diagnostic**. It is written to a separate file and can
never feed the gate. The formal verdict always uses 0.35.

## 6. Evaluation set

| Parameter | Value |
| --- | --- |
| Images per camera | 10 |
| Total | **exactly 80** |
| Stratification | Over exactly the eight frozen cameras |
| Random seed | **20260824** |

The draw visits the frozen cameras in the order they were frozen, sorts each
camera's frames by `image_id`, and samples with a single
`random.Random(20260824)`. It is byte-identical on any machine given the same
manifest and the same frozen cameras. Frames from an unselected camera are
ignored entirely, so a stray acquisition can neither dilute nor enlarge the set.
The manifest's SHA-256 is recorded alongside the drawn ids so that later drift
is detectable rather than silent.

**A formal verdict requires the evaluation set to be exactly 80 images: 10 from
each of the 8 frozen cameras.** 79 is not 80. A camera contributing 9 is not
back-filled from another camera — that would preserve the headline count while
breaking stratification. Any deviation forces **NO VERDICT**.

The remaining 80 frames stay **outside** the baseline evaluation. They may
become development or training candidates in a separate experiment.

> **Contamination rule.** Do not train on VIS-001 evaluation images later
> without explicitly retiring this evaluation set. A model fine-tuned on these
> 80 images can never again be benchmarked against them.

## 7. Ground truth

Ground truth is **human-created**. The model may not generate it.

Annotation is **blind**: the annotator sees no RF-DETR boxes, no overlays and no
model counts. Pre-labelling with model output is forbidden, because a human
correcting a model's boxes measures the human's agreement with the model, not
the model's agreement with reality.

Format: standard COCO detection JSON with `bbox`, `class`, `image_id`,
`annotation_id`. VIS-001 ships **no annotation application**; annotations are
produced in any external COCO-capable tool and dropped into
`data/annotations/`. A validator (`scripts/validate_annotations.py`) enforces:
referenced images exist in the manifest, classes are among the frozen four,
boxes have positive dimensions, boxes stay within the image bounds, annotation
ids are unique, and image ids are valid.

## 8. Metrics

### Detection, at IoU ≥ 0.50

`TP`, `FP`, `FN`, precision, recall, F1 — per class and overall.

**F1 is computed from counts**, not from precision and recall:

```
F1 = 2·TP / (2·TP + FP + FN)
```

The two forms are algebraically identical wherever both are defined, but the
count form stays defined when precision is not. That matters for one case that
must never be lost: `TP=0, FP=0, FN=10` — the model predicted no bus and there
were ten. Precision is undefined there, so the harmonic-mean form returns
`null` and the class leaves the gate. That is a **measured total detection
failure** and scores `F1 = 0.0`, eligible for the normal gate. A model must
never be protected from a negative verdict by predicting nothing.

`F1` is `null` only for `TP=0, FP=0, FN=0` — no observations of any kind.
Precision and recall remain `null` where they are genuinely undefined; they are
diagnostic, and the gate does not read them.

**Matching algorithm** (fixed, because the verdict depends on it): predictions
are sorted by descending confidence, ties broken by input order. Each is matched
to the highest-IoU ground-truth box **not already claimed**; if that IoU is
≥ 0.50 the pair is a true positive and the ground-truth box leaves the pool,
otherwise the prediction is a false positive. Unclaimed ground-truth boxes are
false negatives.

This is one-to-one by construction: one prediction can never satisfy two
ground-truth boxes, and duplicate detections of the same object are counted as
false positives. That is the honest behaviour for a counting benchmark —
double-counting one pedestrian inflates the count and must be penalised.
Matching is greedy (COCO/Pascal-VOC convention), not a globally optimal
assignment, so the figures stay comparable with published detector results.

### Counting, per frame and aggregated

Absolute count error, MAE, mean signed error (bias), total ground-truth count,
total predicted count, and

```
WAPE = sum(abs(predicted_count - ground_truth_count)) / sum(ground_truth_count)
```

MAPE is **excluded**: traffic-camera frames legitimately contain zero objects of
a class, and MAPE divides by the per-frame truth.

Errors are reported sliced by **class** and by **camera**. Descriptive slices by
lighting or time condition may be reported where the metadata supports them, but
they never replace the primary gate.

### Undefined quantities

A metric whose denominator is zero is reported as `null`, never as `0`. A model
that made no prediction has not been shown to be imprecise; a frame set with no
ground truth has no counting error. Reporting those as zero would read as
"perfect" and is forbidden.

### Class coverage is mandatory, and is defined by ground-truth support

**All four target classes must be evaluable for a formal verdict.** A class is
evaluable when the frozen evaluation set contains at least one human-annotated
instance of it:

```
TP + FN > 0
```

Coverage is **not** defined as "F1 is not null". The three cases:

| Ground truth | Predictions | Outcome |
| --- | --- | --- |
| `> 0` | `0` | **Evaluable.** `F1 = 0`. A measured total miss, eligible for the normal gate — including KILL. |
| `0` | `0` | **Not evaluable.** Nothing was annotated, so nothing was asked of the model. |
| `0` | `> 0` | **Not evaluable.** False positives are reported diagnostically, but with no human positive there is nothing to assess detection against. |

Rows 2 and 3 give **NO VERDICT — INSUFFICIENT CLASS COVERAGE**, naming the
affected classes.

The undefined class is **never** silently dropped from the macro average. The
classes most likely to lack support (`bus`, `bicycle`) are precisely the rare
ones a counting benchmark most needs to have measured, so averaging the three
that worked would both redefine the metric mid-experiment and bias it upward.
A benchmark that never saw a bus has not measured three-quarters of the
question; it has failed to measure the question.

### Camera coverage is mandatory

The ADVANCE gate reads "every camera subgroup counting WAPE ≤ 0.35". That
condition applies to **all eight** frozen benchmark cameras.

A camera's WAPE is undefined when its ten frozen evaluation images hold zero
ground-truth objects of the four target classes, so the denominator of
`sum|pred − gt| / sum gt` is zero. Such a camera does **not** drop out of the
rule — dropping it would quietly rewrite a preregistered condition as "every
camera that happened to contain objects", which is a different and weaker rule.
A frozen camera missing from the results entirely is treated the same way:
silence is not coverage.

Instead the gate stops with **NO VERDICT — INSUFFICIENT CAMERA COVERAGE**,
naming the affected camera(s). No replacement metric is invented, no threshold
is added, and the camera is **never** redrawn after labels have been seen.

## 9. Decision gate — frozen

Precedence is fixed and total: **KILL is checked first, ADVANCE second,
LOCAL_FINE_TUNE is the residual.**

### A. ADVANCE — all four must hold

```
macro F1                      >= 0.80
overall counting WAPE         <= 0.20
every class F1                >= 0.65
every camera counting WAPE    <= 0.35
```

Meaning: the zero-shot baseline is promising enough to justify VIS-002 /
Visual Evidence Layer work. It does **not** mean the model is production-ready.

### B. LOCAL_FINE_TUNE — the residual band

Neither ADVANCE nor KILL. Typically: macro F1 in [0.65, 0.80), or WAPE in
(0.20, 0.35], or one class/camera carrying most of the error.

Meaning: a Madrid-specific labelled dataset may plausibly be worth building.
**No fine-tuning happens in VIS-001.**

### C. KILL_OR_REPOSITION — any one is sufficient

```
C1  macro F1                        <  0.65
C2  overall counting WAPE           >  0.35
C3  two or more target classes with F1 < 0.50
C4  camera counting WAPE spread (max - min) > 0.50
```

C4 is the preregistered operationalisation of "performance varies so strongly
across ordinary camera views that aggregate performance is misleading". It is
stated numerically here precisely so the qualitative clause cannot be
reinterpreted after seeing results. Cameras whose evaluated frames contain zero
ground-truth objects have an undefined WAPE and are excluded from C4 and from
the ADVANCE camera ceiling.

**The gate is not weakened to rescue the experiment.** A negative result that is
honestly obtained is a successful VIS-001.

### No verdict

The gate is **not applied** — verdict `null`, blocking reasons listed
explicitly, report stating **NO VERDICT — MISSING EVIDENCE** — whenever any of
the following holds:

* the eight benchmark cameras are not frozen;
* the sample is structurally incomplete (§3);
* the evaluation set is not exactly 80 images, 10 per frozen camera;
* the frozen evaluation set is not fully annotated;
* predictions are absent;
* any of the four target classes has no human-annotated positive, which is
  reported as **NO VERDICT — INSUFFICIENT CLASS COVERAGE**;
* any of the eight frozen benchmark cameras has an undefined counting WAPE,
  which is reported as **NO VERDICT — INSUFFICIENT CAMERA COVERAGE**;
* macro F1 or WAPE is undefined.

Note what is **not** on this list: a class the model missed entirely. That is a
measured result, and it goes to the gate.

An incomplete evaluation is never converted into a positive result.

## 10. Evidence semantics

Three distinct things, never conflated:

| Layer | What it is | VIS-001 label |
| --- | --- | --- |
| Raw input | A real public Madrid camera image | `REAL_PUBLIC_IMAGE` |
| Human annotation | A human reference observation of the objects visible in it | `HUMAN_ANNOTATION` |
| Model prediction | A derived algorithmic inference | `MODEL_PREDICTION` |

A real image does **not** make the prediction over it "REAL evidence".

These labels are **experiment-local**. VIS-001 does not touch, extend or reuse
SNTO's global `DataStatus` enum (`src/platform/provenance.py`).

## 11. Privacy constraints

VIS-001 is **object counting only**. The software must never attempt to
determine identity. The following are forbidden and are not implemented:

face identification · face recognition · face embeddings · person
re-identification · age inference · gender inference · ethnicity inference ·
emotion detection · tourist-vs-resident classification · licence-plate
recognition · OCR · persistent individual tracking

No biometric inference of any kind. Raw imagery and any annotated preview that
draws boxes around people stay local and are excluded from git.

## 12. Non-goals

VIS-001 does not build: a dashboard, a camera-management platform, a backend,
authentication, a database, cloud infrastructure, Kubernetes, a Roboflow cloud
deployment, a training platform, an annotation UI, a data-labelling platform,
real-time streaming, ByteTrack or any temporal tracking, alerts, agents, LLM
interpretation, or multimodal agents.

It is not integrated into `app.py`, the Streamlit UI, `/api/v2`,
PostgreSQL/PostGIS, the mobile app, forecasting, LAC/ROS, GEE, the Sentinel-2
pipeline, reporting, CETS, PRUG, or any production deployment.

## 13. Limitations that hold regardless of the result

- Camera counts are not tourism counts.
- `person` does not mean tourist.
- Vehicles do not imply visitors to a protected area.
- Static snapshots do not establish individual trajectories.
- Camera geometry affects detectability.
- Occlusion affects counts.
- Lighting affects detection.
- Public Madrid traffic cameras are a **technical benchmark domain**, not
  evidence of direct transferability to Parque Nacional de la Sierra de
  Guadarrama.
- VIS-001 does not establish ecological impact.
- VIS-001 does not establish carrying capacity.
- VIS-001 does not validate SNTO's satellite indicators.
- Transfer to FieldOS/SNTO requires a separate field-domain validation.

## 14. Stop conditions

VIS-001 stops and reports rather than fabricating if: the official image source
cannot be verified; usage or licensing conditions are materially unclear; image
URLs cannot be resolved; fewer images exist than expected; human annotations are
absent; RF-DETR cannot be installed; model weights cannot be obtained; or a
required external service needs credentials that are not present.

A stop is reported as: **BLOCKER · EVIDENCE · WHAT WAS COMPLETED · MINIMUM NEXT
HUMAN ACTION**.

Official Madrid data is never silently replaced with random internet images.

---

## Amendments

Numbered and dated. An amendment is only legitimate **before** the data it
governs exists; once a result has been observed, a change to this document is a
protocol deviation instead (next section) and must be recorded as one.

### A1 — Pre-data audit corrections (2026-08-24)

Recorded while **zero frames had been acquired, zero annotations existed and the
model had never been run**, so no result could have motivated any of it. Six
loopholes were closed:

1. **Camera discovery is structural.** Cameras are parsed from the official
   KML's `<Placemark>` structure at
   `https://informo.madrid.es/informo/tmadrid/CCTV.kml`, with provenance and
   licence verified against the `datos.madrid.es` catalogue page. The previous
   approach — harvesting anything ending in `.jpg` from page markup — is
   forbidden: it cannot distinguish a camera from a logo.
2. **A real camera manifest is frozen** from the KML (id, published name,
   coordinates, image endpoint, source document) before selection.
3. **Camera selection is a documented pre-model procedure** (§3, version 1.0):
   eight compass sectors, median distance within each. It replaces "the first
   eight sorted camera ids", which clusters geographically because ids track
   installation batches.
4. **Sample completeness is structural** — at least 20 unique frames from each
   of the eight frozen cameras. A matching frame total no longer satisfies it.
5. **The evaluation set must be exactly 80** — 10 from each frozen camera.
   Anything else forces NO VERDICT.
6. **All four target classes must be evaluable.** An undefined class F1 forces
   NO VERDICT — INSUFFICIENT CLASS COVERAGE instead of being dropped from the
   macro average.

**No scientific gate or threshold changed.** The model, the confidence
threshold (0.35), the IoU threshold (0.50), the four classes, the sample size
(8 × 20), the evaluation-set size (80), the seed (20260824) and every ADVANCE /
LOCAL_FINE_TUNE / KILL_OR_REPOSITION boundary are exactly as first registered.
Every correction makes the gate **harder** to satisfy, never easier: each one
adds a way to reach NO VERDICT that did not previously exist.

### A2 — Pre-data statistical correctness (2026-08-24)

Recorded, like A1, while **zero real frames had been acquired, zero human
annotations existed, and no formal RF-DETR evaluation result existed**. A1 is
left exactly as written; A2 is a separate, later amendment and does not revise
it. Three defects, all of the same shape — a *measured failure* being mistaken
for *absent evidence*, or an absent subgroup silently leaving a preregistered
rule:

1. **The zero-prediction F1 bug.** `GT = 10, predictions = 0` yielded an
   undefined F1 (precision is undefined with no predictions, and F1 was derived
   from precision and recall). The class then left the gate as "no evidence".
   F1 is now computed from counts, `2·TP / (2·TP + FP + FN)`, so that case
   scores `TP=0, FP=0, FN=10, recall=0, F1=0` and remains fully eligible for
   KILL / LOCAL_FINE_TUNE / ADVANCE. **A model must never be protected from a
   negative verdict merely because it predicted nothing.** Only
   `TP=FP=FN=0` stays undefined.
2. **Class coverage redefined on ground-truth support.** Coverage was tested as
   "F1 is not null", which collapsed the case above into "insufficient
   evidence". It is now `TP + FN > 0` — at least one human-annotated instance
   in the frozen evaluation set. `GT=0, predictions>0` is also insufficient:
   false positives are worth reporting, but with no human positive there is
   nothing to assess detection against.
3. **Camera coverage.** A frozen benchmark camera whose counting WAPE was
   undefined simply disappeared from the preregistered "every camera subgroup
   WAPE ≤ 0.35" condition, weakening it to "every camera that happened to
   contain objects". All eight frozen cameras must now have a defined WAPE, or
   the gate stops with **NO VERDICT — INSUFFICIENT CAMERA COVERAGE**, naming
   the affected camera(s). The preregistered metric is preserved rather than
   replaced: no substitute statistic is invented, no threshold is added, and no
   camera is redrawn after labels have been seen.

**No numeric threshold changed.** The model, the confidence threshold (0.35),
the IoU threshold (0.50), the four classes, the sample structure (8 × 20), the
evaluation-set size (80), the seed (20260824) and every ADVANCE /
LOCAL_FINE_TUNE / KILL_OR_REPOSITION boundary are exactly as first registered.

A2 differs from A1 in direction, and this is worth stating plainly. Every A1
correction made the gate strictly harder to satisfy. A2 does **both**: defect 1
makes a negative verdict *reachable* where it previously escaped into NO
VERDICT, while defects 2 and 3 add new routes to NO VERDICT. What unites them
is not severity but correctness — each closes a path by which the gate would
have reported something other than what was actually measured.

---

## Protocol deviations

Numbered, dated, and recorded **before** the affected evaluation is re-run.

*(None recorded. The gate has not yet been applied to any result.)*
