"""Measure face-matching accuracy and speed on labelled photos from real events.

    python -m benchmarks.evaluate benchmarks/data/garba-night benchmarks/data/pooja

Each dataset folder holds:
    photos/        event photos
    selfies/       one selfie per person to search for
    labels.json    who is in which photo (see benchmarks/README.md)

Prints precision and recall at a range of thresholds for every dataset, the threshold that
gives the most recall while staying above the precision bar, and photos processed per second.
Results are also written to benchmarks/results/ so a later run can be compared with this one.
"""
import argparse
import json
import os
import time

from benchmarks.metrics import best_similarity, best_threshold, sweep

THRESHOLDS = [round(0.20 + 0.05 * i, 2) for i in range(11)]   # 0.20 … 0.70
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')


def load_dataset(folder):
    with open(os.path.join(folder, 'labels.json'), encoding='utf-8') as f:
        labels = json.load(f)
    photos = {name: set(people) for name, people in labels['photos'].items()}
    selfies = dict(labels['selfies'])
    for sub, names in (('photos', photos), ('selfies', selfies)):
        for name in names:
            if not os.path.isfile(os.path.join(folder, sub, name)):
                raise FileNotFoundError(f'{folder}: labels.json mentions {sub}/{name}, which does not exist')
    unlabelled = [n for n in os.listdir(os.path.join(folder, 'photos'))
                  if n.lower().endswith(IMAGE_EXTENSIONS) and n not in photos]
    if unlabelled:
        print(f'  note: {len(unlabelled)} photos in {folder}/photos are not in labels.json and are ignored')
    return labels.get('event_type', 'other'), photos, selfies


def embed_dataset(engine, folder, photos, selfies):
    """Run the model over every photo and selfie. Returns embeddings and timing."""
    started = time.perf_counter()
    photo_embeddings = {
        name: [e.tolist() for e in engine.detect_and_embed(os.path.join(folder, 'photos', name))]
        for name in photos
    }
    photo_seconds = time.perf_counter() - started

    selfie_embeddings, no_face = {}, []
    for name in selfies:
        embedding = engine.get_user_embedding(os.path.join(folder, 'selfies', name))
        if embedding is None:
            no_face.append(name)
        else:
            selfie_embeddings[name] = embedding.tolist()
    return photo_embeddings, selfie_embeddings, no_face, photo_seconds


def evaluate(folder, engine, min_precision):
    event_type, photos, selfies = load_dataset(folder)
    photo_embeddings, selfie_embeddings, no_face, photo_seconds = embed_dataset(engine, folder, photos, selfies)

    per_guest = []
    for selfie, embedding in selfie_embeddings.items():
        person = selfies[selfie]
        scores = {photo: best_similarity(embedding, faces) for photo, faces in photo_embeddings.items()}
        truth = {photo for photo, people in photos.items() if person in people}
        per_guest.append((scores, truth))

    results = sweep(per_guest, THRESHOLDS)
    return {
        'dataset': os.path.basename(os.path.normpath(folder)),
        'event_type': event_type,
        'model': engine.model_version,
        'photos': len(photos),
        'faces_detected': sum(len(faces) for faces in photo_embeddings.values()),
        'selfies': len(selfies),
        'selfies_without_face': no_face,
        'photos_per_second': round(len(photos) / photo_seconds, 2) if photo_seconds else None,
        'thresholds': {str(t): r for t, r in results.items()},
        'recommended_threshold': best_threshold(results, min_precision),
    }


def print_report(report, min_precision):
    print(f"\n=== {report['dataset']} ({report['event_type']}) — model {report['model']} ===")
    print(f"{report['photos']} photos, {report['faces_detected']} faces, {report['selfies']} selfies, "
          f"{report['photos_per_second']} photos/second")
    if report['selfies_without_face']:
        print(f"No face found in selfies: {', '.join(report['selfies_without_face'])}")
    print('threshold  precision  recall   wrong photos shown  photos missed')
    for threshold, r in report['thresholds'].items():
        print(f"   {threshold:<8} {r['precision']:>7.1%}   {r['recall']:>6.1%}   {r['fp']:>12}   {r['fn']:>14}")
    recommended = report['recommended_threshold']
    if recommended is None:
        print(f'No threshold keeps precision at {min_precision:.0%} or above.')
    else:
        print(f'Highest recall with precision >= {min_precision:.0%}: threshold {recommended}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('datasets', nargs='+', help='dataset folders')
    parser.add_argument('--model', default=None, help='InsightFace model pack (default: FACE_MODEL_PACK)')
    parser.add_argument('--min-precision', type=float, default=0.99)
    args = parser.parse_args()

    from backend.config import Config
    from backend.models.face_engine import FaceEngine

    engine = FaceEngine(model_dir=Config.INSIGHTFACE_DIR, model_pack=args.model)
    engine.load()
    if not engine.is_ready():
        raise SystemExit(f'Could not load the face model: {engine.get_load_error()}')

    reports = [evaluate(folder, engine, args.min_precision) for folder in args.datasets]
    for report in reports:
        print_report(report, args.min_precision)

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, time.strftime(f'%Y%m%d-%H%M%S-{engine.model_version}.json'))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(reports, f, indent=2)
    print(f'\nSaved to {out_path}')


if __name__ == '__main__':
    main()
