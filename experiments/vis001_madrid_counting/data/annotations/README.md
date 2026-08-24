# VIS-001 ground truth — how to produce and place it

VIS-001 ships **no annotation application**. Building one is an explicit
non-goal: it is a data-labelling platform, not a feasibility experiment. Use any
external COCO-capable tool you already trust (CVAT, Label Studio, makesense.ai,
Roboflow Annotate, a COCO exporter from your own pipeline) and drop the result
here.

## The blind rule — read this first

Ground truth must be created **without the annotator ever seeing the model's
output**.

- ❌ No pre-labelled boxes from RF-DETR.
- ❌ No model overlays on the images.
- ❌ No model counts shown next to a frame.
- ❌ No "correct the model's boxes" workflow.

A human correcting a model's boxes measures the human's agreement with the
model. It does not measure the model's agreement with reality, which is the only
thing VIS-001 is trying to find out. Annotate the raw frames, cold.

Run `scripts/run_baseline.py` **after** annotation is complete, or on a machine
the annotator does not see. The order matters.

## What to annotate

Exactly four classes, and nothing else:

```
person   bicycle   car   bus
```

Annotate every instance of those four that a careful human can see in the frame,
including partially occluded ones. If you genuinely cannot tell whether
something is a car or a bus, leave a note in your tool and flag the frame — do
not guess, and do not split the difference.

A frame containing none of the four is still a valid annotation: it is a
**zero**, and zeros carry real information about false positives. Declare such a
frame in the COCO `images` array with no annotations referencing it. Skipping it
entirely makes it invisible to the evaluation.

## File to produce

```
data/annotations/ground_truth_coco.json
```

Standard COCO detection JSON:

```json
{
  "images": [
    { "id": "<manifest image_id>", "file_name": "<local_relative_path>",
      "width": 640, "height": 480 }
  ],
  "categories": [
    { "id": 1, "name": "person"  },
    { "id": 2, "name": "bicycle" },
    { "id": 3, "name": "car"     },
    { "id": 6, "name": "bus"     }
  ],
  "annotations": [
    { "id": 1, "image_id": "<manifest image_id>", "category_id": 1,
      "bbox": [x, y, width, height], "iscrowd": 0, "area": 0 }
  ]
}
```

Two things that commonly trip people up:

1. **`image_id` must be the manifest `image_id`**, not your tool's internal
   numeric id. That string is what the evaluation joins on. Many tools export
   integer ids — remap them on export, or the validator will reject every
   annotation as referencing an unknown image.
2. **`bbox` is COCO format**: `[x, y, width, height]` in pixels with a top-left
   origin — *not* `[x1, y1, x2, y2]`. Passing corner coordinates silently
   produces boxes that fail the bounds check or, worse, pass it while being
   wrong.

The category ids above match COCO's own sparse numbering. Any ids work as long
as the `name` is one of the four; the validator matches on name.

## Validate before you evaluate

```bash
python experiments/vis001_madrid_counting/scripts/validate_annotations.py
```

It checks that every referenced image is in the frame manifest, that classes are
among the frozen four, that boxes have positive dimensions and stay inside the
image, that annotation ids are unique, and that image ids are valid. It also
reports how much of the frozen 80-image evaluation set is covered.

## Which images to annotate

The frozen evaluation set — 80 images, 10 per camera, drawn with seed
`20260824`:

```bash
python experiments/vis001_madrid_counting/scripts/select_eval_set.py
cat experiments/vis001_madrid_counting/data/eval_set.json
```

Annotating images outside that set is not harmful — the gate ignores them — but
it is not what unblocks a verdict.

## Privacy

These frames may contain people who never consented to appear in a dataset.

- Raw imagery is **not** committed to git (see the experiment `.gitignore`).
- Neither are annotated previews that draw boxes around people.
- Annotate *what class an object is*, never *who a person is*. No face marking,
  no identity labels, no attributes (age, gender, ethnicity, emotion), no
  licence plates.

The committed artifacts are this schema, the manifests, the aggregated metrics
and the report — never the pixels.
