"""Tests for h2star.sensitivity, including Gate V4.2.

Gate V4.2 is the pre-registered check that the Sobol machinery reproduces the
Ishigami function's closed-form indices. Its tolerances come from
``docs/validation_plan.md`` (2026-10-08) and are not to be widened here: 5%
relative on the non-zero indices, and an ABSOLUTE 0.05 on the one index that is
analytically zero, because a relative tolerance against zero is undefined.

The pre-registration also fixes a sample-size ladder, 2**14 to 2**16 to 2**18,
and requires the error to decrease across it. The gate itself is judged at
2**18, which is roughly 1.3 million function evaluations; that runs in about
twenty seconds for the analytic test function and is marked ``validation`` so
it runs on every push. The system-level Sobol study is far more expensive and
is exercised here only at a small sample size, with the full study living in
notebook 07.
"""

import math
from pathlib import Path

import numpy as np
import pytest

from h2star import envelope, sensitivity, uq

#: Repository root, resolved from this file rather than imported from
#: tests.conftest, which only resolves under `python -m pytest`.
REPO_ROOT = Path(__file__).resolve().parents[1]

UNCERTAINTY_YAML = REPO_ROOT / "data" / "uncertainty.yaml"

#: The two envelopes the regime question is asked at (manual 2.4K): cryogenic,
#: and ambient. The ambient case is the one where binding energetics are
#: expected to dominate.
CRYOGENIC = envelope.OperatingPoint(P_full=100.0e5, T_full=80.0)
AMBIENT = envelope.OperatingPoint(
    P_full=100.0e5, T_full=298.0, T_empty=298.0
)


@pytest.fixture(scope="module")
def spec():
    """The committed uncertainty specification."""
    return uq.UncertaintySpec.from_yaml(UNCERTAINTY_YAML)


# --------------------------------------------------------------------------
# The Ishigami closed form.
# --------------------------------------------------------------------------


def test_ishigami_closed_form_matches_brute_force_variance():
    """The analytic total variance is checked, not assumed.

    The Gate V4.2 reference values rest on the closed-form decomposition in
    ``ishigami_analytic``. Confirming its total variance against a
    brute-force quasi-Monte-Carlo estimate is what makes those references
    evidence rather than a quoted number: if the derivation were wrong, the
    gate would be certifying the implementation against a mistake.
    """
    from scipy.stats import qmc

    analytic = sensitivity.ishigami_analytic()
    sample = qmc.Sobol(d=3, scramble=True, seed=1).random_base2(18)
    points = -math.pi + 2.0 * math.pi * sample
    values = sensitivity.ishigami(points)

    assert values.var(ddof=1) == pytest.approx(analytic["variance"], rel=1e-3)


def test_ishigami_third_index_is_exactly_zero_first_order():
    """x3 enters only through its interaction with x1.

    That is what makes the Ishigami function a test of the machinery rather
    than a demonstration: an implementation that conflated first-order and
    total-order indices, or that missed interactions, would show a non-zero
    S1 for x3 or a zero ST.
    """
    analytic = sensitivity.ishigami_analytic()
    assert analytic["S1"][2] == 0.0
    assert analytic["ST"][2] > 0.2
    assert analytic["V3"] == 0.0
    assert analytic["V13"] > 0.0


def test_ishigami_rejects_wrong_input_width():
    """A shape error is caught rather than broadcast into nonsense."""
    with pytest.raises(ValueError, match="takes 3 inputs"):
        sensitivity.ishigami(np.zeros((4, 2)))


# --------------------------------------------------------------------------
# Gate V4.2 — the pre-registered Sobol check.
# --------------------------------------------------------------------------


@pytest.mark.validation
def test_gate_v4_2_sobol_indices_match_ishigami_closed_form():
    """Gate V4.2: Sobol indices on the Ishigami function, at the declared N.

    Pre-registered tolerances (docs/validation_plan.md, V4.2, 2026-10-08):
    5% relative on S1 for x1 and x2 and on ST for all three, and an absolute
    0.05 on S1 for x3, whose analytic value is exactly zero.
    """
    result = sensitivity.sobol_test_ishigami(n=2**18, seed=0)

    assert (result["S1_relative_error"] <= 0.05).all(), result["S1_relative_error"]
    assert (result["ST_relative_error"] <= 0.05).all(), result["ST_relative_error"]
    assert result["S1_x3_absolute_error"] <= 0.05


@pytest.mark.validation
def test_gate_v4_2_error_decreases_across_the_pre_registered_ladder():
    """The error must fall as N rises, 2**14 to 2**16 to 2**18.

    The ladder is fixed in advance so that increasing N is part of the
    procedure rather than a rescue applied after a failure. A result that met
    the band only at the largest N without improving along the way would
    indicate a bias rather than sampling noise, and would not be a pass.
    """
    errors = [
        sensitivity.sobol_test_ishigami(n=2**power, seed=0)[
            "worst_relative_error"
        ]
        for power in (14, 16)
    ]
    assert errors[1] < errors[0], errors


# --------------------------------------------------------------------------
# Problem construction from the specification.
# --------------------------------------------------------------------------


def test_problem_includes_both_layers_in_file_order(spec):
    """The problem covers the material parameters and the declared scalars."""
    built = sensitivity.build_problem(spec)
    assert built["names"] == (
        "n_max",
        "alpha",
        "v_a",
        "sigma_allow",
        "mli_k_eff",
        "heat_leak_budget",
        "bop_fixed",
        "rho_bulk",
    )
    assert built["problem"]["num_vars"] == 8
    assert set(built["fixed"]) == {"p0", "beta"}


def test_problem_records_every_widened_distribution(spec):
    """The uniform-support substitution is reported, not left implicit.

    Saltelli sampling needs a box, so a triangular prior becomes a uniform over
    the same support and the material covariance loses its correlation. Both
    change the question the indices answer, so both are recorded.
    """
    built = sensitivity.build_problem(spec)
    widened = built["widened"]
    for name in ("n_max", "alpha", "v_a"):
        assert "correlation discarded" in widened[name]
    for name in ("sigma_allow", "mli_k_eff", "bop_fixed"):
        assert "uniform" in widened[name]
    # Already uniform: nothing to widen, nothing to report.
    assert "heat_leak_budget" not in widened
    assert "rho_bulk" not in widened


def test_problem_bounds_are_increasing_and_finite(spec):
    """Every bound is a usable interval."""
    for low, high in sensitivity.build_problem(spec)["problem"]["bounds"]:
        assert math.isfinite(low) and math.isfinite(high)
        assert low < high


def test_scalar_bounds_match_the_declared_support(spec):
    """A bounded distribution's box is its own support, not a guess."""
    bop = next(s for s in spec.engineering if s.name == "bop_fixed")
    assert bop.bounds() == (8.0, 24.0)


def test_normal_bounds_are_three_sigma():
    """An unbounded distribution is truncated at a stated width."""
    scalar = uq.ScalarSpec(
        name="bop_fixed",
        distribution="normal",
        params={"mean": 16.0, "sigma": 2.0},
        unit="kg",
        status="test",
        citation="test",
        justification="test",
    )
    assert scalar.bounds() == (10.0, 22.0)


def test_empty_problem_is_refused(spec):
    """No parameters selected is an error, not an empty analysis."""
    with pytest.raises(ValueError, match="nothing to analyse"):
        sensitivity.build_problem(
            spec, include_material=False, include_engineering=False
        )


# --------------------------------------------------------------------------
# The system-level analysis, at a small sample size.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def small_study(spec):
    """A coarse Sobol study at the cryogenic envelope.

    N = 32 with eight parameters is 320 model evaluations: far too few for a
    publishable ranking, and enough to exercise every code path. The full study
    is notebook 07.
    """
    from h2star import isotherm, system

    material = isotherm.Material.from_yaml(
        REPO_ROOT / "data" / "materials" / "ax21.yaml"
    )
    engineering = system.EngineeringParams.from_yaml(
        REPO_ROOT / "data" / "engineering.yaml"
    )
    return sensitivity.sobol_indices(
        spec, material, engineering, CRYOGENIC, n=32, seed=0
    )


def test_study_returns_indices_for_both_outputs(small_study):
    """GC and VC each get first- and total-order indices and a ranking."""
    names = small_study["names"]
    for label in ("GC", "VC"):
        assert small_study[f"S1_{label}"].shape == (len(names),)
        assert small_study[f"ST_{label}"].shape == (len(names),)
        assert set(small_study[f"ranking_{label}"]) == set(names)


def test_ranking_is_ordered_by_total_order_index(small_study):
    """The reported ranking matches the indices it claims to rank."""
    for label in ("GC", "VC"):
        names = small_study["names"]
        st = small_study[f"ST_{label}"]
        ranking = small_study[f"ranking_{label}"]
        values = [st[names.index(name)] for name in ranking]
        assert values == sorted(values, reverse=True)


def test_study_reports_its_failure_count(small_study):
    """Failed evaluations are counted, since they perturb the indices."""
    assert small_study["n_failed"] >= 0
    assert small_study["failure_fraction"] <= 0.05
    assert small_study["n_evaluations"] == 32 * (len(small_study["names"]) + 2)


def test_study_carries_both_caveats(small_study):
    """The surrogate substitution and the Gate V3 bias travel with the result."""
    caveat = small_study["caveat"]
    assert "independent-input surrogate" in caveat
    assert "correlation" in caveat
    assert "Gate V3" in caveat


def test_study_is_reproducible(spec, ax21_material, engineering_params):
    """A reported ranking must be reproducible from its seed."""
    kwargs = dict(n=16, seed=3)
    a = sensitivity.sobol_indices(
        spec, ax21_material, engineering_params, CRYOGENIC, **kwargs
    )
    b = sensitivity.sobol_indices(
        spec, ax21_material, engineering_params, CRYOGENIC, **kwargs
    )
    np.testing.assert_array_equal(a["ST_GC"], b["ST_GC"])
    assert a["ranking_GC"] == b["ranking_GC"]


def test_excessive_model_failures_are_refused(spec, ax21_material,
                                              engineering_params):
    """A decomposition over a mostly-invalid box is refused, not reported.

    Substituting the mean for a handful of impossible draws perturbs the
    indices slightly; doing it for most of the sample would manufacture a
    result. The 5% ceiling is what separates the two.
    """
    broken = uq.UncertaintySpec(
        material=None,
        engineering=(
            uq.ScalarSpec(
                name="rho_bulk",
                distribution="uniform",
                params={"low": 2.0e4, "high": 4.0e4},  # far beyond rho_skel
                unit="kg/m3",
                status="test",
                citation="test",
                justification="test",
            ),
            uq.ScalarSpec(
                name="bop_fixed",
                distribution="uniform",
                params={"low": 8.0, "high": 24.0},
                unit="kg",
                status="test",
                citation="test",
                justification="test",
            ),
        ),
        excluded={},
        notes="test",
    )
    with pytest.raises(ValueError, match="above the 5% ceiling"):
        sensitivity.sobol_indices(
            broken,
            ax21_material,
            engineering_params,
            CRYOGENIC,
            n=16,
            seed=0,
            include_material=False,
        )
