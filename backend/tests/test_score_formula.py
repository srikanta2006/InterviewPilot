import pytest
from app.schemas.evaluation import calculate_weighted_score, RUBRIC_WEIGHTS


def test_score_formula_boundary_max():
    """All dimensions 5 out of 5 must produce exactly 100.0."""
    score = calculate_weighted_score(correctness=5, completeness=5, relevance=5, clarity=5)
    assert score == 100.0


def test_score_formula_boundary_zero():
    """All dimensions 0 out of 5 must produce exactly 0.0."""
    score = calculate_weighted_score(correctness=0, completeness=0, relevance=0, clarity=0)
    assert score == 0.0


def test_score_formula_agreed_rubric_weights():
    """
    Rubric weights:
    - Correctness: 30%
    - Completeness: 30%
    - Relevance: 20%
    - Clarity: 20%
    """
    assert RUBRIC_WEIGHTS["correctness"] == 30
    assert RUBRIC_WEIGHTS["completeness"] == 30
    assert RUBRIC_WEIGHTS["relevance"] == 20
    assert RUBRIC_WEIGHTS["clarity"] == 20

    # Only correctness 5, others 0 -> (5 * 30) / 5 = 30.0
    assert calculate_weighted_score(5, 0, 0, 0) == 30.0

    # Only completeness 5, others 0 -> (5 * 30) / 5 = 30.0
    assert calculate_weighted_score(0, 5, 0, 0) == 30.0

    # Only relevance 5, others 0 -> (5 * 20) / 5 = 20.0
    assert calculate_weighted_score(0, 0, 5, 0) == 20.0

    # Only clarity 5, others 0 -> (5 * 20) / 5 = 20.0
    assert calculate_weighted_score(0, 0, 0, 5) == 20.0


def test_score_formula_intermediate_values():
    # Correctness 4, Completeness 3, Relevance 5, Clarity 4
    # (4*30 + 3*30 + 5*20 + 4*20) / 5 = (120 + 90 + 100 + 80) / 5 = 390 / 5 = 78.0
    score = calculate_weighted_score(correctness=4, completeness=3, relevance=5, clarity=4)
    assert score == 78.0


@pytest.mark.parametrize("invalid_val", [-1, -5, 6, 10, 100])
def test_score_formula_invalid_range_raises_error(invalid_val):
    with pytest.raises(ValueError, match="must be an integer between 0 and 5"):
        calculate_weighted_score(invalid_val, 3, 3, 3)

    with pytest.raises(ValueError, match="must be an integer between 0 and 5"):
        calculate_weighted_score(3, invalid_val, 3, 3)

    with pytest.raises(ValueError, match="must be an integer between 0 and 5"):
        calculate_weighted_score(3, 3, invalid_val, 3)

    with pytest.raises(ValueError, match="must be an integer between 0 and 5"):
        calculate_weighted_score(3, 3, 3, invalid_val)

