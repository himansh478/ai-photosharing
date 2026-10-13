import math

from benchmarks.metrics import best_similarity, best_threshold, confusion, cosine, summarise, sweep


def close(a, b):
    # Plain math rather than pytest's approx, which inspects numpy, and on some
    # machines numpy is only a stand-in (see conftest.py).
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def test_cosine():
    assert close(cosine([1.0, 0.0], [1.0, 0.0]), 1.0)
    assert close(cosine([1.0, 0.0], [0.0, 1.0]), 0.0)
    assert close(cosine([3.0, 4.0], [6.0, 8.0]), 1.0)   # length does not matter
    assert cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_best_similarity_takes_the_closest_face_in_the_photo():
    assert close(best_similarity([1.0, 0.0], [[0.0, 1.0], [1.0, 0.0]]), 1.0)
    assert best_similarity([1.0, 0.0], []) == 0.0


def test_confusion_counts():
    scores = {'mine-found': 0.8, 'mine-missed': 0.3, 'stranger-shown': 0.6, 'stranger-hidden': 0.1}
    truth = {'mine-found', 'mine-missed'}
    assert confusion(scores, truth, threshold=0.5) == {'tp': 1, 'fp': 1, 'fn': 1}
    assert confusion(scores, truth, threshold=0.25) == {'tp': 2, 'fp': 1, 'fn': 0}
    assert confusion(scores, truth, threshold=0.9) == {'tp': 0, 'fp': 0, 'fn': 2}


def test_summarise():
    result = summarise({'tp': 8, 'fp': 2, 'fn': 8})
    assert close(result['precision'], 0.8)
    assert close(result['recall'], 0.5)
    assert close(result['f1'], 2 * 0.8 * 0.5 / 1.3)
    # Showing nothing is perfectly precise and finds nothing.
    assert summarise({'tp': 0, 'fp': 0, 'fn': 5})['precision'] == 1.0
    assert summarise({'tp': 0, 'fp': 0, 'fn': 5})['recall'] == 0.0


def test_sweep_adds_up_all_guests_and_picks_the_safest_useful_threshold():
    asha = ({'a1': 0.9, 'a2': 0.45, 'r1': 0.35}, {'a1', 'a2'})
    ravi = ({'a1': 0.1, 'a2': 0.5, 'r1': 0.7}, {'r1'})
    results = sweep([asha, ravi], [0.3, 0.4, 0.6])

    assert (results[0.3]['tp'], results[0.3]['fp'], results[0.3]['fn']) == (3, 2, 0)
    assert (results[0.4]['tp'], results[0.4]['fp'], results[0.4]['fn']) == (3, 1, 0)
    assert (results[0.6]['tp'], results[0.6]['fp'], results[0.6]['fn']) == (2, 0, 1)

    # Only 0.6 shows no wrong photo; with a looser bar the more complete 0.4 wins.
    assert best_threshold(results, min_precision=0.99) == 0.6
    assert best_threshold(results, min_precision=0.75) == 0.4
    assert best_threshold({0.3: results[0.3]}, min_precision=0.99) is None
