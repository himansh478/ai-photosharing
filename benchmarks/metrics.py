"""Accuracy arithmetic for the benchmark. Pure Python, so it is easy to test and to trust.

Terms, for one guest searching one event:
  * true positive  - a photo shown to the guest that they really are in
  * false positive - a photo shown to the guest that they are NOT in (a privacy problem)
  * false negative - a photo they are in that was not shown (a missed photo)
"""


def cosine(a, b):
    """Cosine similarity of two embeddings."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def best_similarity(selfie_embedding, photo_embeddings):
    """How strongly a selfie matches a photo: its best match among the photo's faces."""
    return max((cosine(selfie_embedding, e) for e in photo_embeddings), default=0.0)


def confusion(scores, truth, threshold):
    """Count outcomes for one guest.

    scores: {photo: similarity}; truth: set of photos the guest really is in.
    """
    shown = {photo for photo, score in scores.items() if score >= threshold}
    return {
        'tp': len(shown & truth),
        'fp': len(shown - truth),
        'fn': len(truth - shown),
    }


def summarise(counts):
    """Precision, recall and F1 from summed tp/fp/fn counts."""
    tp, fp, fn = counts['tp'], counts['fp'], counts['fn']
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {**counts, 'precision': precision, 'recall': recall, 'f1': f1}


def sweep(per_guest, thresholds):
    """Evaluate every threshold over all guests.

    per_guest: list of (scores, truth) pairs, one per selfie.
    Returns {threshold: summary}.
    """
    results = {}
    for threshold in thresholds:
        total = {'tp': 0, 'fp': 0, 'fn': 0}
        for scores, truth in per_guest:
            for key, value in confusion(scores, truth, threshold).items():
                total[key] += value
        results[threshold] = summarise(total)
    return results


def best_threshold(results, min_precision):
    """The threshold with the highest recall among those that keep precision at or above the bar.

    Wrong photos shown to a guest are worse than missed ones, so precision is the constraint
    and recall is what gets maximised. Returns None if no threshold is precise enough.
    """
    eligible = [(summary['recall'], threshold) for threshold, summary in results.items()
                if summary['precision'] >= min_precision]
    return max(eligible)[1] if eligible else None
