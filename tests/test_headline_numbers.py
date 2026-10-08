"""The published numbers must keep coming out of the artifact.

This is a regression pin, not a gate, and the distinction is the reason the
file exists.

The validation gates assert their **pre-registered tolerances**, which is
correct and must never be tightened after the fact. But a pre-registered
tolerance is a floor, not a fingerprint: Gate V1's is "maximum relative density
error < 0.1%" against an observed 0.005%, so the EOS wrapper could degrade
twentyfold and still pass. An adversarial review pointed out that none of the
numbers H2STAR actually publishes was asserted anywhere — a grep for
``4.99166``, ``0.077671``, ``0.065215``, ``53.527`` or ``0.8756`` across the
whole repository returned nothing — so "the headline numbers reproduce" rested
on a session having checked them once.

These tests pin the observed values tightly. A change that moves a published
number now fails here, loudly, and whoever made it has to decide whether the
number or the text is wrong. The gates are untouched and keep their declared
tolerances.

The derivations live in ``scripts/report_headline_numbers.py`` and are imported
rather than repeated, so the command a clean room runs and the test CI runs
cannot drift apart. Claim C5's contour crossings are not here: they need a
33-node probability map at 1000 evaluations per node, which belongs to the
clean-room run (``--full``) rather than to every push.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "report_headline_numbers.py"

#: Published values, as ``docs/validation_plan.md`` and ``README.md`` state
#: them. The tolerance is 1e-6 relative: tight enough that any real change in
#: the model trips it, loose enough to survive the last bits of a floating
#: point sum reassociating on another platform.
RELATIVE_TOLERANCE = 1e-6

PUBLISHED = {
    "gate_v1_max_relative_density_error": 4.9916641302e-05,
    "gate_v3_gc_full": 0.07767099929091068,
    "gate_v3_vc_full": 0.036307715705179384,
    "gate_v4_2_worst_relative_error": 1.8851952766e-03,
    "ax21_baseline_capacity": 0.0652153968,
    "coherence_limit_fit": 104.923540,
    "coherence_limit_a_iso_4": 124.102063,
    "cnt_primary_n_max": 53.5273009898,
    "cnt_primary_capacity": 0.0571025626,
    "claim_c4_ratio": 0.8755994042,
}


def _load_report():
    spec = importlib.util.spec_from_file_location(
        "h2star_report_headline_numbers", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def report():
    return _load_report()


@pytest.fixture(scope="module")
def computed(report):
    """Every headline number, recomputed once for the module."""
    gc_full, vc_full = report.gate_v3_full_state_metrics()
    fit_limit, iso_limit = report.coherence_limits()
    n_max, capacity, ratio = report.cnt_primary_entry()
    return {
        "gate_v1_max_relative_density_error":
            report.gate_v1_max_relative_density_error(),
        "gate_v3_gc_full": gc_full,
        "gate_v3_vc_full": vc_full,
        "gate_v4_2_worst_relative_error":
            report.gate_v4_2_worst_relative_error(),
        "ax21_baseline_capacity": report.ax21_baseline_capacity(),
        "coherence_limit_fit": fit_limit,
        "coherence_limit_a_iso_4": iso_limit,
        "cnt_primary_n_max": n_max,
        "cnt_primary_capacity": capacity,
        "claim_c4_ratio": ratio,
    }


@pytest.mark.parametrize("name", sorted(PUBLISHED))
def test_headline_number_reproduces(name, computed):
    """Each published number comes back out of the artifact."""
    assert computed[name] == pytest.approx(
        PUBLISHED[name], rel=RELATIVE_TOLERANCE
    ), (
        f"{name} is published as {PUBLISHED[name]!r} and the artifact now "
        f"gives {computed[name]!r}. If the model changed on purpose, update "
        "this value, docs/validation_plan.md, docs/known_limitations.md, "
        "README.md and CHANGELOG.md together, and say in the changelog why "
        "the number moved."
    )


def test_every_published_number_is_covered(computed):
    """The two dicts must not drift apart."""
    assert set(computed) == set(PUBLISHED)


def test_gate_v3_is_still_a_failure(computed):
    """The documented FAIL must stay a FAIL at the published magnitude.

    Gate V3's own test asserts the pre-registered +/-15% band as a strict
    xfail. This asserts the *size* of the miss, which is what every limitation
    in the documentation is scaled against: "optimistic by about a factor of
    4.2" and "2.49x high" are quoted throughout, and if the miss shrank those
    statements would silently become wrong.
    """
    assert computed["gate_v3_gc_full"] / 0.0312 == pytest.approx(2.49, rel=0.01)
    assert computed["gate_v3_vc_full"] / 0.0194 == pytest.approx(1.87, rel=0.01)


def test_no_screened_cnt_entry_beats_ax21(computed):
    """Claim C4's relative form requires the ratio to stay below one.

    C4 was rewritten from an absolute shortfall to a ratio precisely because
    the Gate V3 bias puts absolute capacities above the DOE target. The claim
    that survives is "no entry passing the screen exceeds AX-21", so a ratio at
    or above 1.0 would falsify the published claim rather than improve it.
    """
    assert computed["claim_c4_ratio"] < 1.0
    assert computed["claim_c4_ratio"] == pytest.approx(0.88, abs=0.01)
