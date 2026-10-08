"""Tests for h2star.uq, including Gate V4.1.

Gate V4.1 is the pre-registered check that the propagation machinery reproduces
a case with a closed-form answer, and it is marked ``validation`` so the suite
itself certifies it. Its tolerances are those declared in
``docs/validation_plan.md`` on 2026-10-08 and are not to be widened here: the
4-sigma bound and the 1% interval bands were fixed before this module existed,
and the git history of that file is the proof.

The rest of the module tests the loader's refusals. Most of them check that an
undefended or malformed specification is rejected rather than defaulted, which
matters more than it might appear: a declared range is a scientific claim about
how much a quantity could differ, and an undefended one is indistinguishable
from a guess once it has been propagated into a published interval.
"""

import math
from pathlib import Path

import numpy as np
import pytest
import yaml
from scipy.stats import norm

from h2star import envelope, inverse, uq

#: Repository root, resolved from this file. Not imported from tests.conftest:
#: that import only resolves when the repository root happens to be on
#: sys.path, which `python -m pytest` arranges and a bare `pytest` does not.
REPO_ROOT = Path(__file__).resolve().parents[1]

UNCERTAINTY_YAML = REPO_ROOT / "data" / "uncertainty.yaml"
DOE_TARGETS_YAML = REPO_ROOT / "data" / "targets" / "doe_targets.yaml"

#: The baseline envelope used throughout, from manual 2.4F.
BASELINE = envelope.OperatingPoint(P_full=100.0e5, T_full=80.0)


@pytest.fixture(scope="module")
def spec():
    """The committed uncertainty specification."""
    return uq.UncertaintySpec.from_yaml(UNCERTAINTY_YAML)


@pytest.fixture(scope="module")
def doe_2025():
    """DOE 2025 system targets."""
    return inverse.load_doe_targets(DOE_TARGETS_YAML, "2025")


def _write(tmp_path, data, name="spec.yaml"):
    """Write a specification dict to a temporary YAML file."""
    path = Path(tmp_path) / name
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


def _minimal_scalar(**overrides):
    """A valid scalar entry, for mutating in rejection tests."""
    entry = {
        "distribution": "uniform",
        "unit": "kg",
        "low": 8.0,
        "high": 24.0,
        "status": "MODELING ASSUMPTION",
        "_source": "nominal from engineering.yaml",
        "_justification": "declared band",
    }
    entry.update(overrides)
    return entry


# --------------------------------------------------------------------------
# Gate V4.1 — the pre-registered analytic propagation check.
# --------------------------------------------------------------------------


@pytest.mark.validation
def test_gate_v4_1_monte_carlo_matches_analytic_linear_gaussian():
    """Gate V4.1: the propagation reproduces a closed-form linear-Gaussian case.

    A linear functional of a correlated Gaussian input has an exactly known
    mean and variance. The input covariance is deliberately non-diagonal, so a
    propagation that ignored input correlation would fail this test rather than
    passing it by luck.

    The four criteria and their tolerances are pre-registered in
    docs/validation_plan.md (V4.1, 2026-10-08): a 4-sigma bound on the mean, a
    4/sqrt(2N) bound on the standard-deviation ratio, and 1% relative on the
    68% and 95% interval endpoints. The factor 4 rather than 3 was declared in
    advance and for a stated reason: four criteria are checked on every push,
    and a 3-sigma bound would fail spuriously about once in a hundred runs.
    """
    n = 100_000
    seed = 0
    mu = np.array([2.0, -1.0, 0.5])
    sigma = np.array(
        [[1.0, 0.6, -0.3], [0.6, 2.0, 0.4], [-0.3, 0.4, 0.5]]
    )
    c = np.array([1.5, -2.0, 3.0])

    mean_analytic = float(c @ mu)
    sd_analytic = float(math.sqrt(c @ sigma @ c))

    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(mu, sigma, size=n)
    samples = {f"x{i}": draws[:, i] for i in range(3)}

    values = uq.propagate(
        lambda d: sum(c[i] * d[f"x{i}"] for i in range(3)), samples
    )
    summary = uq.summarize(values)

    # (1) mean within 4 standard errors
    assert abs(summary["mean"] - mean_analytic) <= 4.0 * sd_analytic / math.sqrt(n)

    # (2) standard deviation ratio within 4/sqrt(2N)
    assert abs(summary["std"] / sd_analytic - 1.0) <= 4.0 / math.sqrt(2 * n)

    # (3) and (4) interval endpoints within 1% relative
    for probabilities, key in (
        ((0.16, 0.84), "interval_68"),
        ((0.025, 0.975), "interval_95"),
    ):
        analytic = tuple(
            mean_analytic + norm.ppf(p) * sd_analytic for p in probabilities
        )
        for got, want in zip(summary[key], analytic):
            assert abs(got / want - 1.0) <= 0.01, (key, got, want)


@pytest.mark.validation
def test_gate_v4_1_would_fail_if_correlation_were_ignored():
    """The V4.1 case is a real test: the diagonal surrogate misses the variance.

    If the input covariance were treated as diagonal, the propagated standard
    deviation would be wrong by far more than the gate's tolerance. Asserting
    that here is what makes the gate above evidence rather than decoration.
    """
    sigma = np.array(
        [[1.0, 0.6, -0.3], [0.6, 2.0, 0.4], [-0.3, 0.4, 0.5]]
    )
    c = np.array([1.5, -2.0, 3.0])

    sd_full = math.sqrt(c @ sigma @ c)
    sd_diagonal = math.sqrt(c @ np.diag(np.diag(sigma)) @ c)

    assert abs(sd_diagonal / sd_full - 1.0) > 0.05


# --------------------------------------------------------------------------
# The committed specification.
# --------------------------------------------------------------------------


def test_committed_spec_loads_with_the_pre_registered_structure(spec):
    """The shipped specification matches what the pre-registration declares."""
    assert spec.material is not None
    assert spec.material.parameters == ("n_max", "alpha", "v_a")
    assert set(spec.material.fixed) == {"p0", "beta"}
    assert spec.material.fixed["p0"] == pytest.approx(1.47e9)
    assert spec.material.fixed["beta"] == pytest.approx(18.9)
    assert spec.scalar_names == (
        "sigma_allow",
        "mli_k_eff",
        "heat_leak_budget",
        "bop_fixed",
        "rho_bulk",
    )
    assert set(spec.excluded) == {
        "performance_factor",
        "composite_density",
        "liner_areal_mass",
    }


def test_material_covariance_is_the_fixed_p0_gate_v2_fit(spec):
    """The seed is the fixed-p0 conditional covariance, recomputed from data.

    The pre-registration forbids seeding from the unconstrained fit, whose
    optimizer stopped at an active bound. This recomputes the fit from the
    committed digitized isotherm and checks the specification carries that
    covariance and not another.
    """
    import csv

    from h2star import fitting, isotherm

    material = isotherm.Material.from_yaml(
        REPO_ROOT / "data" / "materials" / "ax21.yaml"
    )
    pressures, uptakes = [], []
    with open(REPO_ROOT / "data" / "validation" / "ax21_digitized.csv") as fh:
        rows = csv.reader(line for line in fh if not line.startswith("#"))
        next(rows)
        for row in rows:
            if row:
                pressures.append(float(row[0]) * 1.0e6)
                uptakes.append(float(row[1]))

    fit = fitting.fit_modified_da(
        np.array(pressures), 77.0, np.array(uptakes), material, fix_p0=True
    )
    np.testing.assert_allclose(spec.material.mean, fit.popt, rtol=1e-6)
    np.testing.assert_allclose(spec.material.covariance, fit.cov, rtol=1e-6)


def test_every_spec_entry_carries_a_justification(spec):
    """No range is propagated without a defence of its width."""
    assert spec.material.justification.strip()
    assert spec.material.citation.strip()
    for scalar in spec.engineering:
        assert scalar.justification.strip(), scalar.name
        assert scalar.citation.strip(), scalar.name
        assert scalar.status.strip(), scalar.name


def test_assumptions_are_labelled_as_assumptions(spec):
    """A declared band must not read as a measured one.

    Three of the five engineering ranges are modeling assumptions. The
    distinction is carried in the data so that a reader of the results can see
    which spreads are sourced.
    """
    status = {scalar.name: scalar.status for scalar in spec.engineering}
    assert "ASSUMPTION" in status["sigma_allow"]
    assert "ASSUMPTION" in status["mli_k_eff"]
    assert "ASSUMPTION" in status["rho_bulk"]
    assert "SOURCED" in status["heat_leak_budget"]
    assert "SOURCED" in status["bop_fixed"]


def test_packing_density_band_is_one_sided(spec):
    """rho_bulk cannot exceed the laboratory bulk density, and the file says so.

    The asymmetry is the physical content of that entry: a bed packed into a
    real vessel achieves at most the measured bulk density. A symmetric band
    here would assert a mechanism that does not exist.
    """
    rho = next(s for s in spec.engineering if s.name == "rho_bulk")
    assert rho.params["high"] == pytest.approx(300.0)
    assert rho.params["low"] < 300.0


def test_scope_caveat_is_part_of_the_specification(spec):
    """The spread-not-bias limit travels with the data, not just the docs."""
    notes = spec.notes.lower()
    assert "spread" in notes
    assert "bias" in notes
    assert "4.2" in spec.notes


# --------------------------------------------------------------------------
# Loader refusals.
# --------------------------------------------------------------------------


def test_entry_without_justification_is_refused(tmp_path):
    """An undefended range is refused, not defaulted."""
    entry = _minimal_scalar()
    del entry["_justification"]
    path = _write(tmp_path, {"engineering": {"bop_fixed": entry}})
    with pytest.raises(ValueError, match="_justification"):
        uq.UncertaintySpec.from_yaml(path)


def test_entry_without_source_is_refused(tmp_path):
    """A range with no provenance is refused."""
    entry = _minimal_scalar()
    del entry["_source"]
    path = _write(tmp_path, {"engineering": {"bop_fixed": entry}})
    with pytest.raises(ValueError, match="_source"):
        uq.UncertaintySpec.from_yaml(path)


def test_unknown_parameter_is_refused(tmp_path):
    """A range on a parameter the sampler cannot apply is a silent no-op risk."""
    path = _write(tmp_path, {"engineering": {"not_a_parameter": _minimal_scalar()}})
    with pytest.raises(ValueError, match="not a parameter the sampler"):
        uq.UncertaintySpec.from_yaml(path)


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"distribution": "beta"}, "expected one of"),
        ({"distribution": "uniform", "low": 24.0, "high": 8.0}, "low < high"),
        (
            {"distribution": "triangular", "low": 8.0, "mode": 30.0, "high": 24.0},
            "low <= mode <= high",
        ),
        (
            {"distribution": "normal", "mean": 16.0, "sigma": -1.0},
            "sigma > 0",
        ),
    ],
)
def test_malformed_distributions_are_refused(tmp_path, overrides, fragment):
    """An inconsistent distribution is rejected at load, not at sample time."""
    entry = _minimal_scalar(**overrides)
    for key in ("low", "high", "mode", "mean", "sigma"):
        if key in entry and key not in overrides and entry["distribution"] != "uniform":
            entry.pop(key, None)
    path = _write(tmp_path, {"engineering": {"bop_fixed": entry}})
    with pytest.raises(ValueError, match=fragment):
        uq.UncertaintySpec.from_yaml(path)


def test_exclusion_without_a_reason_is_refused(tmp_path):
    """An exclusion with no reason is indistinguishable from an omission."""
    path = _write(
        tmp_path,
        {
            "engineering": {"bop_fixed": _minimal_scalar()},
            "excluded": {"performance_factor": {"reason": "  "}},
        },
    )
    with pytest.raises(ValueError, match="no reason"):
        uq.UncertaintySpec.from_yaml(path)


def test_non_positive_definite_material_covariance_is_refused(tmp_path):
    """A covariance that is not positive definite cannot be sampled from."""
    path = _write(
        tmp_path,
        {
            "material": {
                "distribution": "multivariate_normal",
                "parameters": ["n_max", "alpha"],
                "mean": [67.8, 3266.0],
                "covariance": [[1.0, 2.0], [2.0, 1.0]],
                "_source": "s",
                "_justification": "j",
            }
        },
    )
    with pytest.raises(ValueError, match="positive definite"):
        uq.UncertaintySpec.from_yaml(path)


def test_declared_sigma_disagreeing_with_covariance_is_refused(tmp_path):
    """One of the two was edited without the other; that must not pass."""
    path = _write(
        tmp_path,
        {
            "material": {
                "distribution": "multivariate_normal",
                "parameters": ["n_max", "alpha"],
                "mean": [67.8, 3266.0],
                "covariance": [[4.0, 0.0], [0.0, 9.0]],
                "one_sigma": [2.0, 5.0],
                "_source": "s",
                "_justification": "j",
            }
        },
    )
    with pytest.raises(ValueError, match="one_sigma disagrees"):
        uq.UncertaintySpec.from_yaml(path)


def test_independent_marginal_material_sampling_is_refused(tmp_path):
    """The material layer must be joint; marginals would overstate the fit."""
    path = _write(
        tmp_path,
        {
            "material": {
                "distribution": "normal",
                "parameters": ["n_max"],
                "mean": [67.8],
                "covariance": [[1.0]],
                "_source": "s",
                "_justification": "j",
            }
        },
    )
    with pytest.raises(ValueError, match="multivariate_normal"):
        uq.UncertaintySpec.from_yaml(path)


# --------------------------------------------------------------------------
# Sampling and propagation behaviour.
# --------------------------------------------------------------------------


def test_material_sampling_reports_its_truncation(spec, ax21_material):
    """Rejected draws are counted and the discard fraction is reported.

    The pre-registration requires the truncation to be named as a limitation
    when the discard fraction exceeds 1%. The measured fraction for this
    covariance is far below that, but the machinery must report it either way
    rather than silently truncating.
    """
    rng = np.random.default_rng(0)
    sample = uq.sample_material(
        spec.material, ax21_material, 500, BASELINE, rng
    )
    assert sample.values.shape == (500, 3)
    assert sample.n_drawn >= 500
    assert 0.0 <= sample.discard_fraction < uq.DISCARD_REPORTING_THRESHOLD
    assert sample.truncation_material is False
    assert sample.n_rejected == sum(sample.rejection_reasons.values())


def test_material_sampling_rejects_rather_than_clips(ax21_material):
    """Draws outside the domain are discarded, not pushed onto the boundary.

    Clipping would pile probability mass on the domain edge and report a
    spurious spike there. This uses a deliberately wide covariance so that a
    substantial fraction of draws is invalid, then checks that no accepted
    sample sits at a bound and that the rejections were recorded.
    """
    wide = uq.MaterialSpec(
        parameters=("n_max", "alpha", "v_a"),
        mean=np.array([67.8, 3266.0, 1.4e-3]),
        covariance=np.diag([400.0, 4.0e6, 1.0e-6]),
        fixed={},
        status="test",
        citation="test",
        justification="test",
    )
    rng = np.random.default_rng(1)
    sample = uq.sample_material(wide, ax21_material, 200, BASELINE, rng)
    assert sample.n_rejected > 0
    assert sample.rejection_reasons
    assert (sample.values[:, 0] > 0.0).all()
    assert (sample.values[:, 2] > 0.0).all()


def test_impossible_specification_fails_loudly(ax21_material):
    """A distribution almost entirely outside the domain raises, not spins."""
    hopeless = uq.MaterialSpec(
        parameters=("n_max",),
        mean=np.array([-1.0e6]),
        covariance=np.array([[1.0]]),
        fixed={},
        status="test",
        citation="test",
        justification="test",
    )
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="outside the physical domain"):
        uq.sample_material(hopeless, ax21_material, 10, BASELINE, rng)


def test_overrides_route_to_the_right_object(ax21_material, engineering_params):
    """A sampled value reaches the material, the engineering block or the vessel."""
    material, engineering = uq.apply_overrides(
        ax21_material,
        engineering_params,
        {
            "n_max": 80.0,
            "rho_bulk": 280.0,
            "bop_fixed": 20.0,
            "sigma_allow": 1.7e9,
        },
    )
    assert material.n_max == 80.0
    assert material.rho_bulk == 280.0
    assert engineering.bop_fixed == 20.0
    assert engineering.vessel.sigma_allow == 1.7e9
    # The originals are untouched.
    assert ax21_material.n_max == pytest.approx(71.6)
    assert engineering_params.bop_fixed == pytest.approx(16.0)


def test_unknown_override_is_refused(ax21_material, engineering_params):
    """An override that matches nothing is a bug, not a silent no-op."""
    with pytest.raises(ValueError, match="neither a known engineering"):
        uq.apply_overrides(
            ax21_material, engineering_params, {"not_a_field": 1.0}
        )


def test_system_capacities_returns_nan_for_an_impossible_draw(
    ax21_material, engineering_params
):
    """One impossible draw yields nan rather than aborting a whole sample."""
    gc, vc = uq.system_capacities(
        ax21_material,
        engineering_params,
        {"n_max": -10.0},
        BASELINE,
    )
    assert math.isnan(gc) and math.isnan(vc)


def test_propagate_rejects_ragged_samples():
    """Sample arrays of different lengths are a caller error."""
    with pytest.raises(ValueError, match="same length"):
        uq.propagate(lambda d: d["a"], {"a": np.zeros(3), "b": np.zeros(4)})


def test_propagate_rejects_empty_samples():
    """Nothing to propagate is an error, not an empty result."""
    with pytest.raises(ValueError, match="nothing to propagate"):
        uq.propagate(lambda d: 0.0, {})


def test_summarize_refuses_an_all_nan_distribution():
    """A distribution of nothing has no summary."""
    with pytest.raises(ValueError, match="No finite samples"):
        uq.summarize(np.full(10, np.nan))


def test_summarize_reports_failures_separately():
    """Failed draws are excluded from statistics and counted."""
    values = np.array([1.0, 2.0, 3.0, np.nan])
    summary = uq.summarize(values, target=2.0)
    assert summary["n"] == 4
    assert summary["n_finite"] == 3
    assert summary["n_failed"] == 1
    assert summary["median"] == pytest.approx(2.0)
    assert summary["p_meets_target"] == pytest.approx(2.0 / 3.0)


def test_half_sample_convergence_detects_a_drifting_sample():
    """The criterion fails when the two halves genuinely disagree."""
    rng = np.random.default_rng(0)
    steady = rng.normal(1.0, 0.05, size=4000)
    assert uq.half_sample_convergence(steady)["converged"]

    drifting = np.concatenate([
        rng.normal(1.0, 0.05, size=2000),
        rng.normal(2.0, 0.05, size=2000),
    ])
    assert not uq.half_sample_convergence(drifting)["converged"]


def test_half_sample_convergence_needs_enough_samples():
    """Two halves of one point each have no meaningful percentiles."""
    with pytest.raises(ValueError, match="at least 4 finite"):
        uq.half_sample_convergence(np.array([1.0, 2.0]))


# --------------------------------------------------------------------------
# End-to-end system propagation.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def propagated(spec, doe_2025):
    """A small but convergent system propagation at the baseline envelope."""
    from h2star import isotherm, system

    material = isotherm.Material.from_yaml(
        REPO_ROOT / "data" / "materials" / "ax21.yaml"
    )
    engineering = system.EngineeringParams.from_yaml(
        REPO_ROOT / "data" / "engineering.yaml"
    )
    return uq.propagate_system(
        spec, material, engineering, BASELINE, n=600, targets=doe_2025, seed=0
    )


def test_propagation_produces_summaries_and_convergence(propagated):
    """The result carries intervals, target probabilities and convergence."""
    assert propagated["GC"].shape == (600,)
    assert propagated["n_failed"] == 0
    for key in ("summary_GC", "summary_VC"):
        summary = propagated[key]
        assert summary["interval_68"][0] < summary["median"] < summary["interval_68"][1]
        assert summary["interval_95"][0] <= summary["interval_68"][0]
        assert summary["interval_95"][1] >= summary["interval_68"][1]
        assert 0.0 <= summary["p_meets_target"] <= 1.0
    assert propagated["convergence_GC"]["converged"]
    assert propagated["convergence_VC"]["converged"]


def test_propagation_carries_the_scope_caveat(propagated):
    """Every propagated result states that it is spread and not bias."""
    caveat = propagated["caveat"]
    assert "Gate V3" in caveat
    assert "4.2" in caveat
    assert "conditional on a" in caveat


def test_propagation_is_reproducible(spec, doe_2025, ax21_material,
                                     engineering_params):
    """The same seed gives the same distribution."""
    kwargs = dict(n=200, targets=doe_2025, seed=7)
    a = uq.propagate_system(
        spec, ax21_material, engineering_params, BASELINE, **kwargs
    )
    b = uq.propagate_system(
        spec, ax21_material, engineering_params, BASELINE, **kwargs
    )
    np.testing.assert_array_equal(a["GC"], b["GC"])
    np.testing.assert_array_equal(a["VC"], b["VC"])


def test_layers_can_be_propagated_separately(spec, doe_2025, ax21_material,
                                             engineering_params):
    """Material-only propagation is what claim C5 needs, and it is supported."""
    material_only = uq.propagate_system(
        spec, ax21_material, engineering_params, BASELINE, n=200, seed=0,
        include_engineering=False,
    )
    engineering_only = uq.propagate_system(
        spec, ax21_material, engineering_params, BASELINE, n=200, seed=0,
        include_material=False,
    )
    assert material_only["layers"] == ("material",)
    assert engineering_only["layers"] == ("engineering",)
    assert material_only["material_sample"] is not None
    assert engineering_only["material_sample"] is None
    for result in (material_only, engineering_only):
        assert result["summary_GC"]["std"] > 0.0


def test_propagating_no_layers_is_refused(spec, ax21_material,
                                          engineering_params):
    """There is nothing to propagate with both layers off."""
    with pytest.raises(ValueError, match="At least one of"):
        uq.propagate_system(
            spec, ax21_material, engineering_params, BASELINE,
            include_material=False, include_engineering=False,
        )
