"""Tests for the CNT case study: the inference chain and the consistency screen.

The case study converts a single reported uptake into a system prediction, and
every link in that conversion is an assumption rather than a measurement. These
tests pin the links that can be checked objectively: the weight-percent
convention against a paper's own internal cross-check, the back-solve against
the isotherm it inverts, and the consistency screen against the corpus.

The screen's verdicts are asserted explicitly. It rejects two entries, and they
are the two the experimental literature contests; it accepts four, and they are
the four with reversible isotherms and calibrated apparatus. That alignment was
not tuned -- the pore-volume limit was established before any CNT value was
read -- and asserting it here means a future change to the isotherm layer or the
densities cannot quietly move a rejection into acceptance.
"""

import math
from pathlib import Path

import pytest
import yaml

from h2star import envelope, inverse, isotherm, system, uq

REPO_ROOT = Path(__file__).resolve().parents[1]
CNT_YAML = REPO_ROOT / "data" / "materials" / "cnt_literature.yaml"
BASELINE = envelope.OperatingPoint(P_full=100.0e5, T_full=80.0)


@pytest.fixture(scope="module")
def corpus():
    """The CNT literature file."""
    with open(CNT_YAML) as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def limits(ax21_material):
    """The two pore-volume coherence limits, in mol/kg."""
    spec = uq.UncertaintySpec.from_yaml(
        REPO_ROOT / "data" / "uncertainty.yaml"
    )
    return {
        "fit": inverse.coherent_n_max_limit(
            ax21_material, inverse.fit_va_slope(spec.material)
        ),
        "physical": inverse.coherent_n_max_limit(
            ax21_material, inverse.V_LIQUID_H2_MOLAR
        ),
    }


def _infer(material, entry, basis):
    """Back-solve a limiting uptake from one corpus entry."""
    uptake = entry["uptake"]
    moles = (
        inverse.wt_percent_to_mass_ratio(uptake["value"]) / inverse.M_H2
    )
    return inverse.material_from_reported_uptake(
        material,
        moles,
        uptake["temperature_K"],
        uptake["pressure_MPa"] * 1.0e6,
        basis=basis,
    )


# --------------------------------------------------------------------------
# The weight-percent convention, settled from a primary source.
# --------------------------------------------------------------------------


def test_liu1999_internal_check_identifies_the_total_mass_convention():
    """The paper's own H/C ratio decides which wt% convention it used.

    Liu 1999 reports "4.2 weight percent, or a hydrogen to carbon atom ratio of
    0.52". Only one of the two conventions reproduces that, so the convention is
    determined by the source rather than assumed by us.
    """
    total = inverse.hydrogen_to_carbon_ratio(4.2, "of_total")
    sorbent = inverse.hydrogen_to_carbon_ratio(4.2, "of_sorbent")
    assert total == pytest.approx(0.52, abs=0.005)
    assert abs(sorbent - 0.52) > abs(total - 0.52)


def test_the_two_conventions_differ_more_at_high_uptake():
    """The convention matters little at 1 wt% and a great deal at 20.

    The relative difference between the two conventions is f/(1-f) for a
    fraction f, so it is about 1% at 1 wt% and 25% at 20 wt%. Small next to the
    corpus's factor-of-160 spread, but not negligible at the contested upper
    end.
    """
    for value in (1.0, 4.0, 20.0):
        fraction = value / 100.0
        total = inverse.wt_percent_to_mass_ratio(value, "of_total")
        sorbent = inverse.wt_percent_to_mass_ratio(value, "of_sorbent")
        assert total / sorbent - 1.0 == pytest.approx(
            fraction / (1.0 - fraction), rel=1e-12
        )
    assert inverse.wt_percent_to_mass_ratio(
        20.0, "of_total"
    ) / inverse.wt_percent_to_mass_ratio(20.0, "of_sorbent") == pytest.approx(
        1.25, rel=1e-12
    )


def test_total_mass_convention_rejects_a_hundred_percent():
    """100 wt% on a total-mass basis would be hydrogen with no sorbent."""
    with pytest.raises(ValueError, match="not physical"):
        inverse.wt_percent_to_mass_ratio(100.0, "of_total")


def test_unknown_convention_is_refused():
    """Only the two documented conventions are accepted."""
    with pytest.raises(ValueError, match="Unknown weight-percent"):
        inverse.wt_percent_to_mass_ratio(1.7, "per_mole")


# --------------------------------------------------------------------------
# The back-solve.
# --------------------------------------------------------------------------


def test_back_solve_reproduces_the_reported_point(ax21_material):
    """The solved material's isotherm passes through the reported point.

    This is the one link in the inference chain that is arithmetic rather than
    assumption, so it must be exact.
    """
    reported, temperature, pressure = 8.5784, 292.15, 12.20e6
    for basis in ("absolute", "excess"):
        material = inverse.material_from_reported_uptake(
            ax21_material, reported, temperature, pressure, basis=basis
        )
        da = isotherm.ModifiedDA(material)
        modelled = (
            da.n_absolute(pressure, temperature)
            if basis == "absolute"
            else da.n_excess(pressure, temperature)
        )
        assert float(modelled) == pytest.approx(reported, rel=1e-9)


def test_basis_ambiguity_moves_the_answer_substantially(ax21_material,
                                                        corpus):
    """Excess versus absolute is a factor-1.8 ambiguity, not a rounding issue.

    No paper in the corpus states its basis, so this ambiguity is irreducible
    from the literature. Pinning its size here keeps it from being described as
    a minor caveat.
    """
    entry = next(e for e in corpus["entries"] if e["key"] == "liu2010")
    absolute = _infer(ax21_material, entry, "absolute").n_max
    excess = _infer(ax21_material, entry, "excess").n_max
    assert excess / absolute == pytest.approx(1.78, rel=0.05)


def test_back_solve_rejects_an_unreachable_point(ax21_material):
    """A reported value the isotherm cannot deliver is an error, not a fit.

    This is what rejects qikun2002: 43.1 mol/kg at 0.14 MPa is outside what the
    D-A form can produce at that state for any limiting uptake.
    """
    with pytest.raises(ValueError, match="No limiting uptake"):
        inverse.material_from_reported_uptake(
            ax21_material, 43.133, 298.0, 0.14e6, basis="absolute"
        )


def test_back_solve_rejects_a_non_positive_uptake(ax21_material):
    """A non-positive reported uptake is a data error."""
    with pytest.raises(ValueError, match="must be positive"):
        inverse.material_from_reported_uptake(
            ax21_material, 0.0, 292.15, 12.2e6
        )


# --------------------------------------------------------------------------
# The corpus and the consistency screen.
# --------------------------------------------------------------------------


def test_corpus_records_what_the_papers_do_not_state(corpus):
    """Every entry's measurement basis is recorded as not stated.

    This is a finding about the literature, not a gap in our transcription: no
    paper in the corpus says whether its uptake is Gibbsian excess or absolute.
    If a future entry DOES state it, this test should be updated to exempt that
    entry rather than deleted.
    """
    assert len(corpus["entries"]) == 7
    for entry in corpus["entries"]:
        assert entry["uptake"]["basis"] == "not_stated", entry["key"]


def test_every_entry_carries_a_verbatim_quote_and_location(corpus):
    """Each number is traceable to the sentence it came from."""
    for entry in corpus["entries"]:
        uptake = entry["uptake"]
        assert uptake["quote"].strip(), entry["key"]
        assert uptake["quote_location"].strip(), entry["key"]
        assert entry["citation"].strip(), entry["key"]
        assert entry["provenance_note"].strip(), entry["key"]


def test_missing_dois_are_recorded_as_missing_not_invented(corpus):
    """Two papers print no DOI, and the file says so rather than supplying one."""
    without = {e["key"] for e in corpus["entries"] if e["doi"] is None}
    assert without == {"tibbetts2001", "qikun2002"}
    for entry in corpus["entries"]:
        if entry["doi"] is None:
            assert "not printed" in entry["doi_source"]


def test_chemisorption_entry_is_excluded_with_a_reason(corpus):
    """chen1999 is out of scope on the paper's own analysis, and says why."""
    entry = next(e for e in corpus["entries"] if e["key"] == "chen1999")
    assert "chemisorption" in entry["reproducibility_tier"]
    assert "dissociative hydrogenation" in entry["provenance_note"]
    assert "chen1999" in corpus["case_study"]["excluded_entries"]


def test_screen_rejects_the_two_contested_entries(ax21_material, corpus,
                                                  limits):
    """liu1999 and qikun2002 fail the pore-volume screen; the others pass.

    The screen is the pore-volume constraint from the Gate V4 record, fixed
    before any CNT value was read. That it rejects exactly the two entries the
    experimental literature contests -- and that liu1999's own authors later
    retracted -- is the case study's central result, so it is asserted rather
    than left to a figure.
    """
    verdicts = {}
    for entry in corpus["entries"]:
        if entry["key"] == "chen1999":
            continue
        try:
            n_max = _infer(ax21_material, entry, "absolute").n_max
            verdicts[entry["key"]] = n_max <= limits["physical"]
        except ValueError:
            verdicts[entry["key"]] = False

    assert verdicts["liu1999"] is False
    assert verdicts["qikun2002"] is False
    for key in ("liu2010", "takagi2004", "zhou2004", "tibbetts2001"):
        assert verdicts[key] is True, key


def test_liu1999_exceeds_both_pore_volume_limits(ax21_material, corpus,
                                                 limits):
    """The rejection is not marginal: 163 mol/kg against limits of 105 and 124."""
    entry = next(e for e in corpus["entries"] if e["key"] == "liu1999")
    n_max = _infer(ax21_material, entry, "absolute").n_max
    assert n_max > limits["physical"]
    assert n_max > limits["fit"]
    assert n_max == pytest.approx(163.0, rel=0.02)


def test_no_accepted_entry_beats_ax21(ax21_material, ax21_isotherm,
                                      engineering_params, corpus):
    """Claim C4 as rewritten: every accepted CNT entry sits below AX-21.

    The relative form is used because the Gate V3 gap makes absolute system
    capacities optimistic -- this model puts AX-21 itself above the DOE
    gravimetric target. A ratio against AX-21 at the same envelope cancels a
    bias in the shared denominator, so the ordering survives where the levels
    do not.
    """
    reference = envelope.evaluate_envelope(
        ax21_material, ax21_isotherm, engineering_params,
        *BASELINE.as_tuple()
    )

    ratios = {}
    for key in ("liu2010", "takagi2004", "zhou2004", "tibbetts2001"):
        entry = next(e for e in corpus["entries"] if e["key"] == key)
        material = _infer(ax21_material, entry, "absolute")
        budget = envelope.evaluate_envelope(
            material, isotherm.ModifiedDA(material), engineering_params,
            *BASELINE.as_tuple()
        )
        ratios[key] = budget["GC"] / reference["GC"]

    assert all(ratio < 1.0 for ratio in ratios.values()), ratios
    assert ratios["liu2010"] == pytest.approx(0.88, abs=0.02)
    assert max(ratios.values()) < 0.95


def test_model_puts_ax21_above_the_doe_target(ax21_material, ax21_isotherm,
                                              engineering_params):
    """The reason C4 had to be rewritten, asserted so it cannot be forgotten.

    If this model's absolute capacities were trustworthy, AX-21 activated
    carbon would meet the DOE 2025 gravimetric target at this envelope. It does
    not in reality -- the HSECoE full-state figure is 0.0312 kg/kg -- so this is
    the Gate V3 optimism showing, and it is why the CNT claim is reported as a
    ratio rather than as a shortfall against the target.
    """
    targets = inverse.load_doe_targets(
        REPO_ROOT / "data" / "targets" / "doe_targets.yaml", "2025"
    )
    budget = envelope.evaluate_envelope(
        ax21_material, ax21_isotherm, engineering_params,
        *BASELINE.as_tuple()
    )
    assert budget["GC"] > targets.gc


# --------------------------------------------------------------------------
# The gap waterfall.
# --------------------------------------------------------------------------


def test_waterfall_decreases_monotonically(ax21_material, ax21_isotherm,
                                           engineering_params):
    """Each stage divides the same hydrogen by a larger mass, so value falls."""
    budget = envelope.evaluate_envelope(
        ax21_material, ax21_isotherm, engineering_params,
        *BASELINE.as_tuple()
    )
    waterfall = system.gap_waterfall(budget)
    values = waterfall["values"]
    assert all(b < a for a, b in zip(values, values[1:]))
    assert len(values) == len(system.GAP_STAGES)


def test_waterfall_ends_at_the_system_capacity(ax21_material, ax21_isotherm,
                                               engineering_params):
    """The last stage IS the system gravimetric capacity, not an approximation."""
    budget = envelope.evaluate_envelope(
        ax21_material, ax21_isotherm, engineering_params,
        *BASELINE.as_tuple()
    )
    waterfall = system.gap_waterfall(budget)
    assert waterfall["system_gc"] == pytest.approx(budget["GC"], rel=1e-12)


def test_waterfall_factor_is_the_ratio_of_its_ends(ax21_material,
                                                   ax21_isotherm,
                                                   engineering_params):
    """The headline loss factor is arithmetic on the stages, not a separate claim."""
    budget = envelope.evaluate_envelope(
        ax21_material, ax21_isotherm, engineering_params,
        *BASELINE.as_tuple()
    )
    waterfall = system.gap_waterfall(budget)
    assert waterfall["total_factor"] == pytest.approx(
        waterfall["values"][0] / waterfall["values"][-1], rel=1e-12
    )
    assert math.isfinite(waterfall["total_factor"])


def test_waterfall_refuses_an_incomplete_budget():
    """A missing mass term would make the decomposition silently wrong."""
    with pytest.raises(KeyError, match="missing mass terms"):
        system.gap_waterfall({"m_usable": 5.6, "m_sorbent": 30.0})
