"""Tests for h2star.envelope: operating-point optimization and forward maps.

Two kinds of test live here, and the distinction matters.

The synthetic tests replace the system evaluation with an analytic surface
whose optimum is known in closed form. They check the *optimizer wrapper* --
the box reparameterization of the empty-state temperature, the constraint
handling, the polish-acceptance logic, the bound flagging -- independently of
whether the physics underneath is right. An optimizer that cannot find a
paraboloid's peak will not find anything useful on a real surface either.

The physical tests run the real system model on AX-21. They do not assert a
hoped-for optimum; they assert internal consistency: that the capacities
reported at the optimum are exactly what a direct evaluation at that operating
point returns, and that any constraint imposed actually holds there.
"""

from pathlib import Path

import numpy as np
import pytest

from h2star import envelope, isotherm, system

#: Repository root, resolved from this file. Deliberately NOT imported from
#: ``tests.conftest``: that import only resolves when the repository root
#: happens to be on ``sys.path``, which ``python -m pytest`` arranges and a
#: bare ``pytest`` does not. CI runs the bare form, so the import passed
#: locally and failed there.
REPO_ROOT = Path(__file__).resolve().parents[1]
AX21_YAML = REPO_ROOT / "data" / "materials" / "ax21.yaml"
ENGINEERING_YAML = REPO_ROOT / "data" / "engineering.yaml"

#: Interior optimum of the synthetic surface, in (Pa, K, K).
_SYNTH_P = 110.0e5
_SYNTH_TF = 90.0
_SYNTH_TE = 150.0


def _synthetic_budget(gc, vc):
    """A budget dict carrying only the keys the optimizer reads."""
    return {
        "GC": gc,
        "VC": vc,
        "V_internal": 0.1,
        "m_sys": 80.0,
        "m_usable": 5.6,
        "V_sys": 0.15,
    }


def _make_synthetic(vc_fn):
    """Build a drop-in ``evaluate_envelope`` over a known paraboloid.

    GC peaks at (``_SYNTH_P``, ``_SYNTH_TF``, ``_SYNTH_TE``) with a strictly
    negative-definite quadratic, so the maximizer is unique and interior to the
    default bounds. ``vc_fn`` supplies the volumetric capacity as a function of
    the same three coordinates, so a test can make the constraint bind.
    """

    def fake(material, iso, eng, P_full, T_full, P_empty, T_empty,
             target_usable_kg=5.6):
        gc = (
            0.080
            - 1.0e-16 * (P_full - _SYNTH_P) ** 2
            - 2.0e-6 * (T_full - _SYNTH_TF) ** 2
            - 2.0e-6 * (T_empty - _SYNTH_TE) ** 2
        )
        return _synthetic_budget(gc, vc_fn(P_full, T_full, T_empty))

    return fake


def test_synthetic_optimum_is_recovered(monkeypatch):
    """The optimizer finds a known interior maximum in all three variables."""
    monkeypatch.setattr(
        envelope, "evaluate_envelope", _make_synthetic(lambda p, tf, te: 0.050)
    )
    result = envelope.optimize_envelope(None, None, None, seed=3)

    assert result.P_full == pytest.approx(_SYNTH_P, rel=5.0e-3)
    assert result.T_full == pytest.approx(_SYNTH_TF, rel=5.0e-3)
    assert result.T_empty == pytest.approx(_SYNTH_TE, rel=5.0e-3)
    assert result.GC == pytest.approx(0.080, rel=1.0e-4)
    # An interior optimum must not be flagged as sitting on a bound.
    assert result.at_bound == ()


def test_synthetic_constraint_is_respected_at_the_returned_point(monkeypatch):
    """A binding volumetric constraint holds at the optimum and costs GC."""
    # VC falls as the full-state pressure rises, so requiring VC >= 0.050
    # forbids the unconstrained optimum's pressure and pushes it down.
    monkeypatch.setattr(
        envelope,
        "evaluate_envelope",
        _make_synthetic(lambda p, tf, te: 0.080 - 4.0e-9 * p),
    )
    unconstrained = envelope.optimize_envelope(None, None, None, seed=3)
    constrained = envelope.optimize_envelope(
        None, None, None, vc_target=0.050, seed=3
    )

    assert constrained.vc_feasible
    assert constrained.VC >= 0.050 - 1.0e-9
    assert constrained.GC <= unconstrained.GC
    assert constrained.P_full < unconstrained.P_full


def test_unevaluable_points_do_not_crash_the_optimizer(monkeypatch):
    """Operating points the model refuses are skipped, not propagated."""

    def fake(material, iso, eng, P_full, T_full, P_empty, T_empty,
             target_usable_kg=5.6):
        if T_full < 80.0:
            raise ValueError("synthetic sizing failure below 80 K")
        return _synthetic_budget(0.080 - 2.0e-6 * (T_full - 95.0) ** 2, 0.050)

    monkeypatch.setattr(envelope, "evaluate_envelope", fake)
    result = envelope.optimize_envelope(None, None, None, seed=1)
    assert result.T_full == pytest.approx(95.0, rel=5.0e-3)


def test_everything_unevaluable_raises(monkeypatch):
    """If no operating point evaluates, say so instead of returning nonsense."""

    def fake(*args, **kwargs):
        raise ValueError("synthetic total failure")

    monkeypatch.setattr(envelope, "evaluate_envelope", fake)
    with pytest.raises(ValueError, match="no evaluable operating point"):
        envelope.optimize_envelope(None, None, None, seed=1)


def test_bounds_reject_inverted_intervals():
    """A non-increasing or non-positive bound is a configuration error."""
    with pytest.raises(ValueError, match="0 < lo < hi"):
        envelope.EnvelopeBounds(P_full=(200.0e5, 20.0e5))
    with pytest.raises(ValueError, match="0 < lo < hi"):
        envelope.EnvelopeBounds(T_full=(0.0, 120.0))


def test_bounds_reject_empty_state_below_full_state():
    """The empty state is reached by warming, so it cannot be capped below."""
    with pytest.raises(ValueError, match="warming the bed"):
        envelope.EnvelopeBounds(T_full=(60.0, 120.0), T_empty_max=100.0)


def test_negative_vc_target_rejected():
    """A non-positive volumetric target is meaningless, not merely lax."""
    with pytest.raises(ValueError, match="strictly positive"):
        envelope.optimize_envelope(None, None, None, vc_target=0.0)


# --------------------------------------------------------------------------
# Physical tests: the real AX-21 system model.
# --------------------------------------------------------------------------


def test_optimum_capacities_match_a_direct_evaluation(ax21_material,
                                                      ax21_isotherm,
                                                      engineering_params,
                                                      ax21_envelope_optimum):
    """GC and VC at the reported optimum equal a direct evaluation there.

    This is the anti-bookkeeping-error test: the optimizer reports coordinates
    and capacities from the same cached budget, so if the two ever drifted
    apart -- a stale cache key, a reparameterization applied twice -- the
    reported optimum would describe a point that was never evaluated.
    """
    result = ax21_envelope_optimum
    direct = envelope.evaluate_envelope(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        result.P_full,
        result.T_full,
        result.P_empty,
        result.T_empty,
    )
    assert direct["GC"] == result.GC
    assert direct["VC"] == result.VC
    assert direct["V_internal"] == result.V_internal


def test_optimum_is_reproducible(ax21_material, ax21_isotherm,
                                 engineering_params):
    """The same seed gives the same answer; the optimizer is not stochastic."""
    kwargs = {"seed": 0, "maxiter": 8}
    a = envelope.optimize_envelope(
        ax21_material, ax21_isotherm, engineering_params, **kwargs
    )
    b = envelope.optimize_envelope(
        ax21_material, ax21_isotherm, engineering_params, **kwargs
    )
    assert (a.P_full, a.T_full, a.T_empty, a.GC) == (
        b.P_full,
        b.T_full,
        b.T_empty,
        b.GC,
    )


def test_ax21_optimum_sits_on_the_search_bounds(ax21_envelope_optimum):
    """For AX-21 the optimum is a corner, and the result says so.

    GC rises monotonically with full-state pressure and falls with full-state
    temperature over the whole default region, so the answer is set by the
    bounds rather than by an interior trade-off. That is a legitimate result
    and a reader needs to know it, which is what ``at_bound`` is for. If this
    test ever fails, the response is to look at why an interior optimum
    appeared, not to delete the assertion.
    """
    result = ax21_envelope_optimum
    assert "T_full@lower" in result.at_bound
    assert "P_full@upper" in result.at_bound
    assert "T_empty@upper" in result.at_bound


def test_forward_map_shape_and_orientation(ax21_material, ax21_isotherm,
                                           engineering_params):
    """The map is (temperature, pressure) and each cell is a real evaluation."""
    P = np.linspace(40.0e5, 160.0e5, 4)
    T = np.linspace(70.0, 100.0, 3)
    grid = envelope.forward_map(
        ax21_material, ax21_isotherm, engineering_params, P, T
    )
    assert grid["GC"].shape == (3, 4)
    assert grid["VC"].shape == (3, 4)
    assert not np.isnan(grid["GC"]).any()

    direct = envelope.evaluate_envelope(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        P[2],
        T[1],
        envelope.DEFAULT_P_EMPTY,
        160.0,
    )
    assert grid["GC"][1, 2] == direct["GC"]
    assert grid["VC"][1, 2] == direct["VC"]


def test_forward_map_refuses_a_reversed_swing(ax21_material, ax21_isotherm,
                                              engineering_params):
    """Rows whose full state is warmer than the empty state come back nan."""
    grid = envelope.forward_map(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        np.array([100.0e5]),
        np.array([80.0, 150.0]),
        T_empty=120.0,
    )
    assert not np.isnan(grid["GC"][0, 0])
    assert np.isnan(grid["GC"][1, 0])


def test_gc_falls_with_full_state_temperature(ax21_material, ax21_isotherm,
                                              engineering_params):
    """Warming the full state costs capacity, monotonically, at fixed pressure.

    Physical sanity rather than a tuned number: adsorption falls with
    temperature, so a tank sized to the same mission needs more sorbent and
    more vessel, and the system capacity drops.
    """
    grid = envelope.forward_map(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        np.array([100.0e5]),
        np.array([60.0, 70.0, 80.0, 90.0, 100.0]),
    )
    column = grid["GC"][:, 0]
    assert np.all(np.diff(column) < 0.0)


def test_operating_point_defaults_match_the_manual_baseline():
    """The default empty state is the 5 bar / 160 K baseline of manual 2.4F."""
    point = envelope.OperatingPoint(P_full=100.0e5, T_full=80.0)
    assert point.P_empty == pytest.approx(5.0e5)
    assert point.T_empty == pytest.approx(160.0)
    assert point.as_tuple() == (100.0e5, 80.0, 5.0e5, 160.0)


def test_envelope_result_exposes_its_operating_point(ax21_envelope_optimum):
    """The optimum converts to an OperatingPoint the maps can consume."""
    result = ax21_envelope_optimum
    point = result.operating_point
    assert point.as_tuple() == (
        result.P_full,
        result.T_full,
        result.P_empty,
        result.T_empty,
    )


def test_fixtures_are_the_committed_reference_files():
    """Guard against a fixture silently pointing somewhere else."""
    assert AX21_YAML.name == "ax21.yaml"
    assert ENGINEERING_YAML.name == "engineering.yaml"
    material = isotherm.Material.from_yaml(AX21_YAML)
    assert material.name == "AX-21"
    params = system.EngineeringParams.from_yaml(ENGINEERING_YAML)
    assert params.bop_fixed == pytest.approx(16.0)


# --------------------------------------------------------------------------
# Regressions from the 2026-10-08 adversarial review.
# --------------------------------------------------------------------------


def test_forward_map_axes_do_not_alias_the_caller_arrays(ax21_material,
                                                         ax21_isotherm,
                                                         engineering_params):
    """The returned axes are copies, not views of the caller's arrays."""
    P = np.array([100.0e5])
    grid = envelope.forward_map(
        ax21_material, ax21_isotherm, engineering_params, P, np.array([80.0])
    )
    grid["P_full"][0] = -1.0
    assert P[0] == 100.0e5


def test_forward_map_rejects_a_two_dimensional_axis(ax21_material,
                                                    ax21_isotherm,
                                                    engineering_params):
    """A 2-D grid is caught at the boundary, not deep inside the loop."""
    with pytest.raises(ValueError, match="one-dimensional"):
        envelope.forward_map(
            ax21_material,
            ax21_isotherm,
            engineering_params,
            np.zeros((2, 2)),
            np.array([80.0]),
        )


def test_forward_map_reports_how_many_nodes_evaluated(ax21_material,
                                                      ax21_isotherm,
                                                      engineering_params):
    """An all-nan map is visible from the result rather than only in the plot.

    A negative pressure returns a map of nan instead of raising, because one
    impossible corner should not discard a good map. The count is what tells a
    caller the difference between that and a total failure.
    """
    bad = envelope.forward_map(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        np.array([-100.0e5]),
        np.array([80.0]),
    )
    assert bad["n_evaluated"] == 0
    assert not bad["evaluable"].any()

    good = envelope.forward_map(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        np.array([100.0e5]),
        np.array([80.0]),
    )
    assert good["n_evaluated"] == 1


def test_isothermal_swing_is_evaluated(ax21_material, ax21_isotherm,
                                       engineering_params):
    """T_empty == T_full is a pure pressure swing, a legitimate case.

    Manual 2.4F names the isothermal swing as the comparison case against the
    temperature-plus-pressure baseline, so it must not be filtered out with
    the genuinely impossible reversed swings.
    """
    grid = envelope.forward_map(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        np.array([100.0e5]),
        np.array([160.0]),
        T_empty=160.0,
    )
    assert grid["n_evaluated"] == 1
    assert np.isfinite(grid["GC"][0, 0])


def test_optimizer_failure_names_a_cause(ax21_material, ax21_isotherm,
                                         engineering_params):
    """"Nothing evaluated" must report why, not always blame the mission."""
    with pytest.raises(ValueError) as excinfo:
        envelope.optimize_envelope(
            ax21_material,
            ax21_isotherm,
            engineering_params,
            target_usable_kg=-1.0,
            seed=0,
            maxiter=3,
        )
    message = str(excinfo.value)
    assert "no evaluable operating point" in message
    assert "last failure was" in message


def test_mission_constant_has_one_definition():
    """The 5.6 kg mission is defined once and reused, not duplicated."""
    from h2star import constants

    assert envelope.DEFAULT_TARGET_USABLE_KG is constants.DEFAULT_TARGET_USABLE_KG
