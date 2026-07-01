"""Tests for the isosteric heat of adsorption (h2star.heats)."""

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
