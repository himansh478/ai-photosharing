import pytest
import numpy as np
from backend.services.matching_service import MatchingService


def test_cosine_similarity_identical():
    svc = MatchingService()
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    sim = svc._cosine_similarity(a, b)
    assert pytest.approx(sim, rel=1e-3) == 1.0


def test_cosine_similarity_orthogonal():
    svc = MatchingService()
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    sim = svc._cosine_similarity(a, b)
    assert pytest.approx(sim, rel=1e-3) == 0.0
