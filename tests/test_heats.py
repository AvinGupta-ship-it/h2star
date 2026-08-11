"""Tests for the isosteric heat of adsorption (h2star.heats)."""

import math
from pathlib import Path

import pytest

from h2star.heats import isosteric_heat, isosteric_heat_convergence
from h2star.isotherm import Material, ModifiedDA

AX21_YAML = Path(__file__).resolve().parents[1] / "data" / "materials" / "ax21.yaml"


@pytest.fixture(scope="module")
def da():
    return ModifiedDA(Material.from_yaml(AX21_YAML))


def test_isosteric_heat_positive_low_coverage(da):
    n = 0.1 * da.material.n_max
    q_st = isosteric_heat(da, n, 77.0)
    assert q_st > 0


def test_isosteric_heat_step_size_converges(da):
    n = 0.1 * da.material.n_max
    dTs = [5, 2, 1, 0.5]
    q = isosteric_heat_convergence(da, n, 77.0, dTs)
    # q[1] is dT=2, q[2] is dT=1.
    assert q[1] == pytest.approx(q[2], rel=0.01)


def test_isosteric_heat_matches_da_analytic():
    """Numerical q_st reproduces the closed-form D-A limit at 10% coverage.

    Machinery test (unmarked): the finite-difference inversion is checked
    against alpha*sqrt(ln(n_max/n)), the analytic q_st of the same D-A form.
    """
    mat = Material.from_yaml(AX21_YAML)
    da = ModifiedDA(mat)

    n = 0.10 * mat.n_max
    q_numerical = isosteric_heat(da, n, 77.0)
    q_analytic = mat.alpha * math.sqrt(math.log(mat.n_max / n))

    assert q_numerical == pytest.approx(q_analytic, rel=1e-4)


@pytest.mark.validation
def test_isosteric_heat_low_coverage_anchor():
    """Low-coverage q_st sits in the carbon literature band and falls with n.

    Bounds [4000, 7000] J/mol and the monotonic-decrease requirement are
    pre-registered in docs/validation_plan.md (Gate V2 isosteric-heat clause,
    2026-08-10); they are not tuned to the computed values.
    """
    mat = Material.from_yaml(AX21_YAML)
    da = ModifiedDA(mat)

    fracs = (0.05, 0.10, 0.15)
    qs = [isosteric_heat(da, frac * mat.n_max, 77.0) for frac in fracs]

    for frac, q in zip(fracs, qs, strict=True):
        assert 4000.0 <= q <= 7000.0, f"q_st = {q} J/mol at n/n_max = {frac}"

    # Strong sites fill first, so q_st decreases as loading rises.
    assert qs[0] > qs[1] > qs[2]
