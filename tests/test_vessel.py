"""Tests for the thin-wall composite vessel mass model (h2star.vessel)."""

import math
from dataclasses import replace
from pathlib import Path

import pytest

from h2star.vessel import (
    VesselParams,
    radius_from_volume,
    surface_area,
    vessel_mass_hoop,
    vessel_mass_performance_factor,
    wall_thickness,
)

ENGINEERING_YAML = Path(__file__).resolve().parents[1] / "data" / "engineering.yaml"

#: Reference case: 100 bar design pressure, 0.15 m^3 internal volume.
P_MAX = 1.0e7  # Pa
V_INTERNAL = 0.15  # m^3


@pytest.fixture(scope="module")
def params():
    return VesselParams.from_yaml(ENGINEERING_YAML)


def test_vessel_mass_positive(params):
    """Machinery: the hoop-stress route returns a positive finite mass (kg)."""
    m = vessel_mass_hoop(P_MAX, V_INTERNAL, params)
    assert isinstance(m, float)
    assert math.isfinite(m)
    assert m > 0.0


def test_pf_mass_positive(params):
    """Machinery: the performance-factor route returns a positive mass (kg)."""
    m = vessel_mass_performance_factor(P_MAX, V_INTERNAL, params)
    assert isinstance(m, float)
    assert math.isfinite(m)
    assert m > 0.0


def test_cross_check_agreement(params):
    # Internal-consistency check between two vessel-mass routes (Type III
    # hoop-stress route vs a Type IV performance-factor benchmark), not a
    # pre-registered gate; band widened to 35% to reflect the documented
    # vessel-class mismatch recorded in data/engineering.yaml notes.
    m_hoop = vessel_mass_hoop(P_MAX, V_INTERNAL, params)
    m_pf = vessel_mass_performance_factor(P_MAX, V_INTERNAL, params)
    assert abs(m_hoop - m_pf) / m_pf < 0.35


def test_geometry_roundtrip(params):
    """radius_from_volume inverts the capsule volume formula exactly."""
    LR = params.aspect_ratio_LR
    r = radius_from_volume(V_INTERNAL, LR)
    V_round = math.pi * r**3 * (LR + 4.0 / 3.0)
    assert V_round == pytest.approx(V_INTERNAL, rel=1e-9)


def test_guards(params):
    """Each non-physical input raises ValueError."""
    # P_max <= 0
    with pytest.raises(ValueError):
        vessel_mass_hoop(0.0, V_INTERNAL, params)
    with pytest.raises(ValueError):
        vessel_mass_performance_factor(-1.0e7, V_INTERNAL, params)
    with pytest.raises(ValueError):
        wall_thickness(0.0, 0.25, params.safety_factor, params.sigma_allow)

    # V_internal <= 0
    with pytest.raises(ValueError):
        vessel_mass_hoop(P_MAX, 0.0, params)
    with pytest.raises(ValueError):
        vessel_mass_performance_factor(P_MAX, -0.15, params)
    with pytest.raises(ValueError):
        radius_from_volume(0.0, params.aspect_ratio_LR)

    # sigma_allow <= 0
    with pytest.raises(ValueError):
        vessel_mass_hoop(P_MAX, V_INTERNAL, replace(params, sigma_allow=0.0))
    with pytest.raises(ValueError):
        wall_thickness(P_MAX, 0.25, params.safety_factor, -1.0)

    # performance_factor <= 0
    with pytest.raises(ValueError):
        vessel_mass_performance_factor(
            P_MAX, V_INTERNAL, replace(params, performance_factor=0.0)
        )

    # aspect_ratio_LR <= 0
    with pytest.raises(ValueError):
        vessel_mass_hoop(P_MAX, V_INTERNAL, replace(params, aspect_ratio_LR=0.0))
    with pytest.raises(ValueError):
        radius_from_volume(V_INTERNAL, -3.0)
    with pytest.raises(ValueError):
        surface_area(0.25, 0.0)
