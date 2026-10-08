"""Tests for h2star.inverse: the acceptability-map engine and DOE targets.

The central test here is the spot check. A grid engine that transposed an index
or applied a stale override would still produce a smooth, plausible contour
plot, and no amount of staring at the figure would reveal it. The only defence
is to rebuild a handful of nodes from scratch, outside the loop, and demand
bitwise equality -- not agreement to a tolerance, because the recomputation
runs the identical code path on identical inputs, so any difference at all is a
real defect rather than a numerical one.
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from h2star import envelope, inverse, system
from tests.conftest import DOE_TARGETS_YAML

#: A small, fast grid for tests that only need the engine's structure.
_NX, _NY = 7, 5


@pytest.fixture(scope="session")
def doe_2025():
    """The DOE 2025 system targets, loaded from the committed YAML."""
    return inverse.load_doe_targets(DOE_TARGETS_YAML, "2025")


@pytest.fixture(scope="session")
def small_map(ax21_material, engineering_params, doe_2025):
    """A small (n_max, alpha) acceptability map at the baseline envelope."""
    return inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "alpha",
        np.linspace(40.0, 160.0, _NX),
        np.linspace(2000.0, 6000.0, _NY),
        operating_point=envelope.OperatingPoint(P_full=100.0e5, T_full=80.0),
        targets=doe_2025,
    )


# --------------------------------------------------------------------------
# DOE targets
# --------------------------------------------------------------------------


def test_doe_targets_load_with_the_published_values(doe_2025):
    """The 2025 tier is 5.5 wt% gravimetric and 40 g/L volumetric, system."""
    assert doe_2025.gc == pytest.approx(0.055)
    assert doe_2025.vc == pytest.approx(0.040)
    assert doe_2025.label == "DOE 2025"
    assert "energy.gov" in doe_2025.citation


def test_doe_targets_file_parses_as_yaml():
    """The targets file is machine-readable, not only human-readable.

    It was committed on Day 1 with an indentation error that made it
    unparseable, and the error survived four months because nothing loaded it.
    This test is the reason that cannot recur silently.
    """
    with open(DOE_TARGETS_YAML) as fh:
        data = yaml.safe_load(fh)
    assert set(data) >= {"source", "targets"}


@pytest.mark.parametrize(
    ("tier", "gc", "vc"),
    [("2020", 0.045, 0.030), ("2025", 0.055, 0.040), ("ultimate", 0.065, 0.050)],
)
def test_every_published_tier_loads(tier, gc, vc):
    """All three target tiers are readable and carry the published numbers."""
    targets = inverse.load_doe_targets(DOE_TARGETS_YAML, tier)
    assert targets.gc == pytest.approx(gc)
    assert targets.vc == pytest.approx(vc)


def test_unknown_tier_raises():
    """Asking for a tier the table does not have is an error, not a default."""
    with pytest.raises(ValueError, match="not present"):
        inverse.load_doe_targets(DOE_TARGETS_YAML, "2099")


def test_targets_without_provenance_are_refused(tmp_path):
    """Targets with no source title or URL do not load, like material files."""
    path = Path(tmp_path) / "no_source.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "source": {"publisher": "someone"},
                "targets": {
                    "gravimetric_capacity_kgH2_per_kg_system": {"2025": 0.055},
                    "volumetric_capacity_kgH2_per_L_system": {"2025": 0.040},
                },
            }
        )
    )
    with pytest.raises(ValueError, match="source title or URL"):
        inverse.load_doe_targets(path, "2025")


# --------------------------------------------------------------------------
# The acceptability map
# --------------------------------------------------------------------------


def test_map_shape_and_axis_orientation(small_map):
    """x varies across columns, y down rows, as the docstring promises."""
    assert small_map["GC"].shape == (_NY, _NX)
    assert small_map["VC"].shape == (_NY, _NX)
    assert small_map["feasible"].shape == (_NY, _NX)
    assert small_map["x_values"].size == _NX
    assert small_map["y_values"].size == _NY
    assert small_map["param_x"] == "n_max"
    assert small_map["param_y"] == "alpha"


def test_three_random_nodes_recompute_exactly(small_map, ax21_material,
                                              engineering_params):
    """The mandatory sanity ritual: rebuild random nodes outside the loop.

    Indices are drawn from the evaluable nodes only, so the check exercises the
    numeric path rather than agreeing that two ``nan`` values are both ``nan``.
    """
    rows, cols = np.nonzero(small_map["evaluable"])
    assert rows.size >= 3, "need at least three evaluable nodes to spot-check"
    rng = np.random.default_rng(20261008)
    picks = rng.choice(rows.size, size=3, replace=False)
    indices = [(int(rows[k]), int(cols[k])) for k in picks]

    for record in inverse.spot_check(
        small_map, ax21_material, engineering_params, indices
    ):
        assert record["matches"], record
        assert record["dGC"] == 0.0
        assert record["dVC"] == 0.0


def test_node_matches_a_hand_driven_system_evaluation(small_map,
                                                      ax21_material,
                                                      engineering_params):
    """One node, rebuilt through SystemDesign directly, with no map code.

    ``spot_check`` reuses the module's own evaluator, so it would not catch a
    fault shared by both paths. This drives :mod:`h2star.system` by hand
    instead, which is the independent check.
    """
    from dataclasses import replace

    from h2star.isotherm import ModifiedDA

    i, j = 1, 2
    material = replace(
        ax21_material,
        n_max=float(small_map["x_values"][j]),
        alpha=float(small_map["y_values"][i]),
    )
    point = small_map["operating_point"]
    design = system.SystemDesign(
        material,
        ModifiedDA(material),
        engineering_params,
        point.P_full,
        point.T_full,
        point.P_empty,
        point.T_empty,
    )
    budget = design.evaluate(system.size_for_usable(design))

    assert budget["GC"] == small_map["GC"][i, j]
    assert budget["VC"] == small_map["VC"][i, j]
    assert budget["m_sys"] == small_map["m_sys"][i, j]


def test_feasible_mask_is_exactly_the_two_targets_met(small_map, doe_2025):
    """Feasibility is both targets at once, and never a non-evaluable node."""
    expected = (
        (small_map["GC"] >= doe_2025.gc)
        & (small_map["VC"] >= doe_2025.vc)
        & small_map["evaluable"]
    )
    np.testing.assert_array_equal(small_map["feasible"], expected)
    assert not np.any(small_map["feasible"] & ~small_map["evaluable"])
    assert small_map["n_feasible"] == int(small_map["feasible"].sum())
    assert small_map["n_evaluated"] == int(small_map["evaluable"].sum())


def test_overpacked_materials_are_unevaluable_not_infeasible(ax21_material,
                                                             engineering_params,
                                                             doe_2025):
    """A negative void volume means "no such material", not "misses target".

    Packing beyond ``1 / (1/rho_skel + v_a)`` leaves no room for the gas, and
    the tank layer refuses it. Those nodes must come back nan and unevaluable,
    kept distinct from nodes that are physically fine but below target.
    """
    impossible = 1.0 / (1.0 / ax21_material.rho_skel + ax21_material.v_a)
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "rho_bulk",
        np.array([71.6]),
        np.array([300.0, impossible * 1.5]),
        targets=doe_2025,
    )
    assert result["evaluable"][0, 0]
    assert not result["evaluable"][1, 0]
    assert np.isnan(result["GC"][1, 0])
    assert not result["feasible"][1, 0]


def test_capacity_rises_with_limiting_uptake(ax21_material, engineering_params,
                                             doe_2025):
    """More limiting uptake means more capacity, all else equal.

    Physical sanity on the swept axis: a sorbent that holds more hydrogen per
    kilogram needs less of itself to meet the mission, so the system gets
    lighter and the gravimetric capacity rises monotonically.
    """
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "alpha",
        np.array([40.0, 70.0, 100.0, 130.0, 160.0]),
        np.array([3080.0]),
        targets=doe_2025,
    )
    row = result["GC"][0, :]
    assert np.all(np.diff(row) > 0.0)


def test_sweeping_an_unknown_parameter_raises(ax21_material,
                                              engineering_params, doe_2025):
    """Only the material parameter vector may be swept."""
    with pytest.raises(ValueError, match="not a sweepable"):
        inverse.acceptability_map(
            ax21_material,
            engineering_params,
            "citation",
            "alpha",
            [1.0],
            [2.0],
            targets=doe_2025,
        )


def test_sweeping_one_parameter_against_itself_raises(ax21_material,
                                                      engineering_params,
                                                      doe_2025):
    """A parameter against itself is a line, not a region."""
    with pytest.raises(ValueError, match="must differ"):
        inverse.acceptability_map(
            ax21_material,
            engineering_params,
            "n_max",
            "n_max",
            [1.0],
            [2.0],
            targets=doe_2025,
        )


def test_point_evaluator_rejects_unknown_overrides(ax21_material,
                                                   engineering_params):
    """An override outside the parameter vector is a bug, not a silent no-op."""
    with pytest.raises(ValueError, match="not a sweepable"):
        inverse.evaluate_material_point(
            ax21_material,
            engineering_params,
            {"name": "not a parameter"},
            envelope.OperatingPoint(P_full=100.0e5, T_full=80.0),
        )


def test_base_material_is_not_mutated_by_the_sweep(ax21_material,
                                                   engineering_params,
                                                   doe_2025):
    """Sweeping builds variants; the reference material is left untouched."""
    before = (ax21_material.n_max, ax21_material.alpha, ax21_material.rho_bulk)
    inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "alpha",
        np.array([50.0, 90.0]),
        np.array([2500.0, 4500.0]),
        targets=doe_2025,
    )
    after = (ax21_material.n_max, ax21_material.alpha, ax21_material.rho_bulk)
    assert before == after


def test_variants_keep_the_reference_citation(ax21_material,
                                              engineering_params):
    """A swept variant inherits provenance; it does not become uncited."""
    from dataclasses import replace

    variant = replace(ax21_material, n_max=120.0)
    assert variant.citation == ax21_material.citation
    assert variant.n_max == 120.0


# --------------------------------------------------------------------------
# Regressions from the 2026-10-08 adversarial review.
# --------------------------------------------------------------------------


def test_unphysical_parameters_are_never_reported_feasible(ax21_material,
                                                           engineering_params,
                                                           doe_2025):
    """A negative density must not come back as a material meeting targets.

    The review found that ``SWEEPABLE_PARAMETERS`` validated parameter *names*
    but nothing validated parameter *values*, so a node at negative n_max and
    negative packing density inverted the sign of the sorbent mass, shrank the
    system mass denominator, and produced GC = 0.99 kg/kg -- which the
    feasibility mask duly marked as clearing every DOE target. A map is not
    allowed to report that, whatever a caller asks for.
    """
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "rho_bulk",
        np.array([-50.0, 71.6]),
        np.array([-300.0, 300.0]),
        targets=doe_2025,
    )
    assert not result["evaluable"][0, 0]
    assert not result["feasible"][0, 0]
    assert np.isnan(result["GC"][0, 0])
    assert result["feasible"].sum() == 0
    assert result["reason_counts"], "a rejected node must record a reason"


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"n_max": -1.0}, "n_max must be finite and positive"),
        ({"n_max": float("nan")}, "n_max must be finite and positive"),
        ({"v_a": 0.0}, "v_a must be finite and positive"),
        ({"rho_bulk": 3000.0}, "must exceed rho_bulk"),
        ({"alpha": -1.0e6}, "characteristic energy"),
    ],
)
def test_each_domain_violation_is_named(ax21_material, engineering_params,
                                        overrides, fragment):
    """Rejections say which parameter was wrong, not merely that one was."""
    budget, reason = inverse.evaluate_material_point_with_reason(
        ax21_material,
        engineering_params,
        overrides,
        envelope.OperatingPoint(P_full=100.0e5, T_full=80.0),
    )
    assert budget is None
    assert fragment in reason


def test_reference_material_is_inside_its_own_domain(ax21_material):
    """The shipped AX-21 parameters pass the domain check at the envelope."""
    assert inverse.material_domain_error(ax21_material, (80.0, 160.0)) is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"gc": 5.5, "vc": 40.0},        # weight percent and g/L, not SI
        {"gc": -0.055, "vc": 0.040},    # negative
        {"gc": 0.055, "vc": 0.0},       # zero
        {"gc": float("nan"), "vc": 0.040},
    ],
)
def test_targets_reject_values_that_are_not_system_capacities(kwargs):
    """A target in the wrong unit would empty the map instead of looking wrong."""
    with pytest.raises(ValueError):
        inverse.Targets(label="x", citation="c", **kwargs)


def test_targets_require_a_citation():
    """Targets carry provenance, like every other number in the repository."""
    with pytest.raises(ValueError, match="non-empty citation"):
        inverse.Targets(gc=0.055, vc=0.040, label="x", citation="   ")


def test_map_axes_do_not_alias_the_caller_arrays(ax21_material,
                                                 engineering_params, doe_2025):
    """Mutating the result must not reach back into the caller's input."""
    x_input = np.array([60.0, 100.0])
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "alpha",
        x_input,
        np.array([3080.0]),
        targets=doe_2025,
    )
    result["x_values"][0] = -999.0
    assert x_input[0] == 60.0


def test_spot_check_uses_the_mission_the_map_was_built_with(ax21_material,
                                                            engineering_params,
                                                            doe_2025):
    """An audit must not fail because it assumed a different mission.

    The map records ``target_usable_kg``; ``spot_check`` defaults to it. Before
    this, a map built at 4.0 kg and audited with the 5.6 kg default reported a
    mismatch that read as a map defect but was an argument error.
    """
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "alpha",
        np.array([80.0, 120.0]),
        np.array([3080.0]),
        targets=doe_2025,
        target_usable_kg=4.0,
    )
    assert result["target_usable_kg"] == 4.0
    for record in inverse.spot_check(
        result, ax21_material, engineering_params, [(0, 0), (0, 1)]
    ):
        assert record["matches"], record


def test_spot_check_detects_a_corrupted_node(ax21_material,
                                             engineering_params, doe_2025):
    """The audit must fail when the stored value is wrong. Otherwise it is theatre."""
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "alpha",
        np.array([80.0, 120.0]),
        np.array([3080.0]),
        targets=doe_2025,
    )
    result["GC"][0, 1] *= 1.10
    records = inverse.spot_check(
        result, ax21_material, engineering_params, [(0, 0), (0, 1)]
    )
    assert records[0]["matches"]
    assert not records[1]["matches"]
    assert records[1]["dGC"] > 0.0


def test_spot_check_distinguishes_a_nan_node_from_a_numeric_match(
    ax21_material, engineering_params, doe_2025
):
    """Agreeing that a node is impossible is flagged, not counted as equality."""
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "rho_bulk",
        np.array([71.6]),
        np.array([300.0, -300.0]),
        targets=doe_2025,
    )
    good, bad = inverse.spot_check(
        result, ax21_material, engineering_params, [(0, 0), (1, 0)]
    )
    assert good["matches"] and not good["nan_node"]
    assert bad["matches"] and bad["nan_node"]
    assert bad["reason"]


def test_spot_check_rejects_an_out_of_range_index(ax21_material,
                                                  engineering_params,
                                                  doe_2025):
    """An index outside the grid is an error with a message, not an IndexError
    raised from inside NumPy."""
    result = inverse.acceptability_map(
        ax21_material,
        engineering_params,
        "n_max",
        "alpha",
        np.array([80.0]),
        np.array([3080.0]),
        targets=doe_2025,
    )
    with pytest.raises(IndexError, match="outside the map grid"):
        inverse.spot_check(result, ax21_material, engineering_params, [(5, 5)])


def test_two_dimensional_axes_are_rejected(ax21_material, engineering_params,
                                           doe_2025):
    """A 2-D grid fails at the boundary with a clear message."""
    with pytest.raises(ValueError, match="one-dimensional"):
        inverse.acceptability_map(
            ax21_material,
            engineering_params,
            "n_max",
            "alpha",
            np.zeros((2, 2)),
            np.array([3080.0]),
            targets=doe_2025,
        )


def test_empty_targets_file_is_a_clear_error(tmp_path):
    """An unparseable or empty targets file names the problem."""
    path = Path(tmp_path) / "empty.yaml"
    path.write_text("")
    with pytest.raises(ValueError, match="did not parse into a mapping"):
        inverse.load_doe_targets(path, "2025")


def test_targets_file_without_a_capacity_table_is_a_clear_error(tmp_path):
    """A missing capacity table raises ValueError, not a bare KeyError."""
    path = Path(tmp_path) / "partial.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "source": {"title": "t", "url": "u"},
                "targets": {"gravimetric_capacity_kgH2_per_kg_system": {"2025": 0.055}},
            }
        )
    )
    with pytest.raises(ValueError, match="missing the capacity table"):
        inverse.load_doe_targets(path, "2025")
