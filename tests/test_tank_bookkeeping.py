"""Tests for the tank-inventory layer (h2star.tank)."""

import math
from pathlib import Path

import pytest

from h2star.isotherm import Material, ModifiedDA
from h2star.tank import total_h2_mass, total_h2_mass_via_excess, usable_h2

AX21_YAML = Path(__file__).resolve().parents[1] / "data" / "materials" / "ax21.yaml"

#: Representative internal volume of a tank, m^3.
V_INTERNAL = 0.15


@pytest.fixture(scope="module")
def material():
    return Material.from_yaml(AX21_YAML)


@pytest.fixture(scope="module")
def da(material):
    return ModifiedDA(material)


@pytest.mark.validation
@pytest.mark.parametrize("P", [1e5, 1e6, 5e6, 1e7])
@pytest.mark.parametrize("T", [80.0, 100.0, 160.0])
def test_dual_bookkeeping_routes_agree(material, da, P, T):
    """Absolute and excess bookkeeping give the same total mass (kg).

    The excess route subtracts ``rho_gas * v_a`` from the loading and adds the
    same gas back by counting the adsorbed-phase volume as gas-filled, so the
    two routes must agree to round-off.
    """
    m_abs = total_h2_mass(material, da, P, T, V_INTERNAL)
    m_exc = total_h2_mass_via_excess(material, da, P, T, V_INTERNAL)
    assert m_exc == pytest.approx(m_abs, rel=1e-9)


def test_total_h2_mass_is_positive_finite(material, da):
    """Machinery: total inventory at 10 MPa, 80 K is a positive finite float."""
    m = total_h2_mass(material, da, 1e7, 80.0, V_INTERNAL)
    assert isinstance(m, float)
    assert math.isfinite(m)
    assert m > 0.0


def test_usable_h2_is_positive(material, da):
    """Machinery: discharging 10 MPa/80 K to 0.5 MPa/160 K delivers mass."""
    delivered = usable_h2(
        material, da, full=(1e7, 80.0), empty=(5e5, 160.0), V_internal=V_INTERNAL
    )
    assert delivered > 0.0
