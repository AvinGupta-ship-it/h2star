"""Tests for the system-level mass/volume budget (h2star.system).

Reference case: AX-21 in the H2STAR reference vessel, over the envelope
100 bar / 80 K (full) to 5 bar / 160 K (empty). All values SI except VC,
which is kg per litre.
"""

from pathlib import Path

import pytest

from h2star.isotherm import Material, ModifiedDA
from h2star.system import EngineeringParams, SystemDesign, size_for_usable
from h2star.vessel import radius_from_volume, surface_area

_ROOT = Path(__file__).resolve().parents[1]
ENGINEERING_YAML = _ROOT / "data" / "engineering.yaml"
AX21_YAML = _ROOT / "data" / "materials" / "ax21.yaml"

#: Reference operating envelope.
P_FULL = 1.0e7  # Pa (100 bar)
T_FULL = 80.0  # K
P_EMPTY = 5.0e5  # Pa (5 bar)
T_EMPTY = 160.0  # K

#: Reference internal volume for the fixed-size budget tests.
V_REFERENCE = 0.15  # m^3

#: Target usable hydrogen mass for the sizing test.
TARGET_USABLE = 5.6  # kg


@pytest.fixture(scope="module")
def design():
    """A :class:`SystemDesign` for AX-21 on the reference envelope."""
    material = Material.from_yaml(AX21_YAML)
    return SystemDesign(
        material=material,
        isotherm=ModifiedDA(material),
        engineering=EngineeringParams.from_yaml(ENGINEERING_YAML),
        P_full=P_FULL,
        T_full=T_FULL,
        P_empty=P_EMPTY,
        T_empty=T_EMPTY,
    )


@pytest.fixture(scope="module")
def budget(design):
    """The system budget at the reference internal volume."""
    return design.evaluate(V_REFERENCE)


def test_budget_components_positive(budget):
    """Every mass and volume term in the budget is strictly positive."""
    mass_keys = (
        "m_h2_full",
        "m_usable",
        "m_sorbent",
        "m_vessel",
        "m_insulation",
        "m_bop",
        "m_sys",
    )
    volume_keys = ("V_internal", "V_shell", "V_insulation", "V_sys")
    for key in mass_keys:
        assert budget[key] > 0.0, f"{key} = {budget[key]} kg is not positive"
    for key in volume_keys:
        assert budget[key] > 0.0, f"{key} = {budget[key]} m^3 is not positive"


def test_gc_in_unit_interval(budget):
    """Gravimetric capacity is a physical fraction: 0 < GC < 1."""
    assert 0.0 < budget["GC"] < 1.0


def test_sizing_reproduces_target(design):
    """size_for_usable inverts the usable-mass curve to 1e-6 relative."""
    V = size_for_usable(design, TARGET_USABLE)
    assert V > 0.0
    m_usable = design.evaluate(V)["m_usable"]
    assert abs(m_usable - TARGET_USABLE) / TARGET_USABLE < 1.0e-6


def test_vc_positive(budget):
    """Volumetric capacity (kg per litre) is strictly positive."""
    assert budget["VC"] > 0.0


def test_insulation_thickness_positive(design, budget):
    """The solved MLI blanket thickness, V_insulation / A, is positive."""
    LR = design.vessel_params.aspect_ratio_LR
    A = surface_area(radius_from_volume(V_REFERENCE, LR), LR)  # m^2
    t_ins = budget["V_insulation"] / A  # m
    assert t_ins > 0.0
