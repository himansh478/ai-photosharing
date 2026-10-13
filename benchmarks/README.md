# Accuracy benchmark

Measures how well face matching works on your own events, so that changes to the model or
the threshold are decided by numbers instead of guesses.

## What you need to collect

For each kind of event (wedding, family function, pooja, garba), with the permission of the
people in the photos:

- 100–150 event photos
- one selfie each for 10–15 of the people in them
- a list of who is in which photo

Include the hard cases on purpose: night and coloured lights, motion blur, side faces,
covered heads, glasses, children, siblings, and large group photos.

Put them in a folder under `benchmarks/data/`, which git ignores, so these photos are never
committed:

```
benchmarks/data/garba-night/
    photos/IMG_001.jpg ...
    selfies/asha.jpg ...
    labels.json
```

`labels.json`:

```json
{
  "event_type": "garba",
  "photos": {
    "IMG_001.jpg": ["asha", "ravi"],
    "IMG_002.jpg": [],
    "IMG_003.jpg": ["asha"]
  },
  "selfies": {
    "asha.jpg": "asha",
    "ravi.jpg": "ravi"
  }
}
```

List every photo, with an empty list for photos that show none of the selfie people. A photo
missing from the list is ignored. A person named in a photo but without a selfie is fine.

## Running it

It needs the real face model, so run it where the full requirements are installed (the
Docker image, or any Linux machine with `pip install -r requirements-dev.txt`):

```
python -m benchmarks.evaluate benchmarks/data/garba-night benchmarks/data/pooja
```

To compare another model pack, first put its files under `models_cache/models/<pack name>/`
(InsightFace only downloads its own packs automatically), then:

```
python -m benchmarks.evaluate benchmarks/data/garba-night --model auraface
```

## Reading the result

For each threshold it prints:

- **precision**: of the photos shown to guests, how many were really theirs. Low precision
  means strangers' photos are being shown, which is a privacy problem.
- **recall**: of the photos a guest is really in, how many were found.

It then names the threshold with the highest recall that still keeps precision at 99% or
above (change with `--min-precision`). That value is what `SIMILARITY_THRESHOLD` should be
set to. The app's current default of 0.4 was chosen without measurement.

Results are saved under `benchmarks/results/` so the next run can be compared with this one.

The accuracy arithmetic is covered by `tests/test_benchmark_metrics.py`. The part that runs
the model has not been run on real photos yet, because no labelled dataset exists.
