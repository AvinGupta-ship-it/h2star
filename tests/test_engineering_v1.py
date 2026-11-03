"""Tests for the v1.0 component-resolved engineering model."""

import math
import os

import pytest

from h2star import engineering as eng
from h2star import isotherm

ROOT = os.path.join(os.path.dirname(__file__), "..")
YAML = os.path.join(ROOT, "data", "engineering_v1.yaml")
AX21 = os.path.join(ROOT, "data", "materials", "ax21.yaml")
MOF5 = os.path.join(ROOT, "data", "materials", "mof5_hsecoe.yaml")


@pytest.fixture(scope="module")
def params():
    return eng.EngineeringParamsV1.from_yaml(YAML)


@pytest.fixture(scope="module")
def hexcell(params):
    mat = isotherm.Material.from_yaml(MOF5)
    return eng.SystemDesignV1(
        mat, isotherm.ModifiedDA(mat), params, "type1",
        100e5, 80.0, 5e5, 140.0)


@pytest.fixture(scope="module")
def ax21_t3(params):
    mat = isotherm.Material.from_yaml(AX21)
    return eng.SystemDesignV1(
        mat, isotherm.ModifiedDA(mat), params, "type3",
        200e5, 80.0, 5e5, 160.0)


def test_capsule_geometry_round_trip():
    V = 0.1884
    r = eng.capsule_radius(V, 4.0)
    back = math.pi * r**2 * (4.0 * r) + 4.0 / 3.0 * math.pi * r**3
    assert abs(back - V) < 1e-12


def test_netting_total_is_angle_independent(params):
    """Cylinder netting total t = 1.5 P r / sigma exactly, for any angle."""
    from dataclasses import replace
    r, Pd, Pf = 0.25, 1.25 * 200e5, 200e5
    totals = []
    for deg in (8.0, 12.0, 25.0):
        p = replace(params, t3_helical_angle=math.radians(deg))
        t_h, t_th = eng.type3_netting(Pd, Pf, r, p)
        totals.append(t_h + t_th)
    sigma = eng.type3_sigma_eff(Pf, params)
    sf_eff = params.t3_safety_factor / params.vent_ratio
    expect = 1.5 * sf_eff * Pd * r / sigma
    for t in totals:
        assert abs(t - expect) / expect < 1e-12


def test_type1_wall_matches_fedsm_backout(params):
    """sigma_design back-derived from FEDSM Table 5 reproduces 14.00 mm at
    the published geometry (within the capsule-radius convention)."""
    r = eng.capsule_radius(0.1884, 4.0)
    t = eng.type1_wall_thickness(params.vent_ratio * 100e5, r, params)
    assert abs(t - 0.0140) / 0.0140 < 2e-3


def test_e1_calibration_record(hexcell):
    """The frozen factors reproduce the E1 record exactly (regression)."""
    b = eng.evaluate_sized(hexcell)
    assert abs(b["m_sys"] - 140.99) < 0.02
    assert abs(b["V_sys"] * 1e3 - 285.59) < 0.05
    assert abs(b["t_wall"] * 1e3 - 13.59) < 0.02
    assert abs(b["GC"] - 0.03972) < 2e-5


def test_gate_e2_adjudication_record(ax21_t3, params):
    """Gate E2 numbers are reproducible from the frozen model (regression of
    the adjudicated record in docs/validation_plan.md; E2 itself ran once)."""
    b = eng.evaluate_sized(ax21_t3)
    assert abs(b["GC"] - 0.04780) < 5e-5
    assert abs(b["VC"] - 0.02221) < 5e-5
    mat = isotherm.Material.from_yaml(AX21)
    d = eng.SystemDesignV1(mat, isotherm.ModifiedDA(mat), params, "type1",
                           60e5, 40.0, 5e5, 110.0)
    b2 = eng.evaluate_sized(d)
    assert abs(b2["m_sys"] - 99.6) < 0.1
    assert abs(b2["V_sys"] * 1e3 - 184.7) < 0.2


def test_usable_basis(ax21_t3):
    """GC and VC are usable-basis; m_sys carries the full inventory."""
    V = eng.size_for_usable(ax21_t3)
    b = ax21_t3.evaluate(V)
    assert abs(b["m_usable"] - 5.6) < 1e-6
    assert abs(b["GC"] - b["m_usable"] / b["m_sys"]) < 1e-12
    assert b["m_sys"] > b["m_usable"] + b["m_sorbent"]


def test_design_pressure_rule(ax21_t3):
    assert abs(ax21_t3.P_design - 1.25 * 200e5) < 1e-6


def test_component_budget_sums(ax21_t3):
    V = eng.size_for_usable(ax21_t3)
    b = ax21_t3.evaluate(V)
    total = (b["m_h2_full"] + b["m_sorbent"] + b["m_hx"] + b["m_wall"]
             + b["m_ln2_channel"] + b["m_mli"] + b["m_shell"]
             + b["m_supports"] + b["m_bop"])
    assert abs(total - b["m_sys"]) < 1e-9
    assert abs(b["V_tank_outer"] + b["V_bop"] - b["V_sys"]) < 1e-12


def test_mli_sized_to_budget_type3(ax21_t3, params):
    V = eng.size_for_usable(ax21_t3)
    b = ax21_t3.evaluate(V)
    assert abs(b["Q_implied_W"] - params.mli_Q_type3) < 1e-9


def test_bad_vessel_type_rejected(params):
    mat = isotherm.Material.from_yaml(AX21)
    with pytest.raises(ValueError):
        eng.SystemDesignV1(mat, isotherm.ModifiedDA(mat), params, "type4",
                           100e5, 80.0, 5e5, 160.0)


def test_mati_family_check(params):
    """Secondary, non-binding E1 family check (validation_plan Part v1.0).

    MATI system of FEDSM2017-69411 Table 5: 0.32 g/cc compacted MOF-5
    (Table 2, committed YAML), E1-frozen factors, sized to 5.6 kg usable on
    the 100 bar/80 K -> 5 bar/140 K envelope. Pins the recomputed record
    (S8 re-derivation correction): m_sys +5.07%, V_sys -0.43%,
    t_wall -2.34%; and the sigma_design cross-check at the published
    internal volume, t = 13.79 mm.
    """
    mat = isotherm.Material.from_yaml(os.path.join(
        ROOT, "data", "materials", "mof5_compacted_hsecoe.yaml"))
    d = eng.SystemDesignV1(mat, isotherm.ModifiedDA(mat), params, "type1",
                           100e5, 80.0, 5e5, 140.0)
    b = eng.evaluate_sized(d)
    assert abs(100 * (b["m_sys"] / 141.59 - 1) - 5.07) < 0.01
    assert abs(100 * (b["V_sys"] * 1e3 / 246.03 - 1) - (-0.43)) < 0.01
    assert abs(100 * (b["t_wall"] * 1e3 / 13.06 - 1) - (-2.34)) < 0.01
    at_published_v = d.evaluate(0.1801)
    assert abs(at_published_v["t_wall"] * 1e3 - 13.79) < 0.01
