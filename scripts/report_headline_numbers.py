#!/usr/bin/env python3
"""Recompute every headline number H2STAR publishes, from the artifact.

    python3 scripts/report_headline_numbers.py           # the fast eight
    python3 scripts/report_headline_numbers.py --full    # plus claim C5, ~1 min

Manual Part VII requires the clean-room reproduction to show "the headline
numbers reproduced from the artifact rather than read from a record". This is
the command that does it: each number is derived here by calling the package,
so the clean room compares computed values against the table in
``docs/validation_plan.md`` instead of against a previous session's prose.

It exists because an adversarial review pointed out that none of these numbers
was pinned anywhere. The validation gates assert their *pre-registered
tolerances*, which is correct and must not change -- Gate V1's floor is 0.1%
against an observed 0.005%, so the EOS wrapper could degrade twentyfold and
still pass its gate. That is the gate working as declared; it is not a
regression check on the published value. ``tests/test_headline_numbers.py``
imports the functions below and pins the observed values tightly, which is a
different job from adjudicating a gate and is kept separate from it.

Claim C5's contour crossings need a 33-node probability map at 1000 system
evaluations per node -- about a minute, against the ten that the full 19x7 map
behind figure F6 takes. They sit behind ``--full`` because a minute is still
too long for every push.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"

sys.path.insert(0, str(REPO_ROOT / "src"))

from h2star import (  # noqa: E402
    envelope,
    eos,
    inverse,
    isotherm,
    sensitivity,
    system,
    uq,
)

#: Baseline comparison envelope: 100 bar, 80 K full state (manual 2.4K).
BASELINE = envelope.OperatingPoint(P_full=100.0e5, T_full=80.0)

#: Gate V3's sizing-only empty state, as ``tests/test_system_validation.py``
#: declares it. The gate reads full-state inventory; this state sizes the tank.
GATE_V3_P_EMPTY = 5.0e5
GATE_V3_T_EMPTY = 160.0

M3_TO_L = 1.0e3
BAR_TO_PA = 1.0e5


def _inputs():
    material = isotherm.Material.from_yaml(DATA / "materials" / "ax21.yaml")
    return {
        "material": material,
        "isotherm": isotherm.ModifiedDA(material),
        "engineering": system.EngineeringParams.from_yaml(
            DATA / "engineering.yaml"
        ),
        "spec": uq.UncertaintySpec.from_yaml(DATA / "uncertainty.yaml"),
    }


def gate_v1_max_relative_density_error():
    """Largest relative density error of the EOS wrapper against NIST.

    Taken over all four validation isotherms at every tabulated pressure,
    row by row at each row's exact pressure.
    """
    worst = 0.0
    for path in sorted((DATA / "validation").glob("nist_h2_*.csv")):
        temperature = float(
            re.search(r"nist_h2_(\d+)K\.csv$", path.name).group(1)
        )
        with open(path) as handle:
            rows = csv.reader(
                line for line in handle if not line.startswith("#")
            )
            next(rows)
            for row in rows:
                if not row:
                    continue
                reference = float(row[1])
                modelled = eos.density(float(row[0]) * BAR_TO_PA, temperature)
                worst = max(worst, abs(modelled - reference) / reference)
    return worst


def gate_v3_full_state_metrics():
    """``(GC_full, VC_full)`` at the HSECoE anchor's full state.

    The same derivation ``tests/test_system_validation.py`` uses: the numerator
    is the full-state inventory, not the usable swing, and the anchor's state
    is read from its YAML rather than written down here.
    """
    with open(DATA / "validation" / "hsecoe_reference.yaml") as handle:
        anchor = yaml.safe_load(handle)
    full_state = anchor["operating_full_state"]

    ctx = _inputs()
    design = system.SystemDesign(
        ctx["material"],
        ctx["isotherm"],
        ctx["engineering"],
        full_state["pressure_bar"] * BAR_TO_PA,
        full_state["temperature_K"],
        GATE_V3_P_EMPTY,
        GATE_V3_T_EMPTY,
    )
    budget = design.evaluate(system.size_for_usable(design))
    return (
        budget["m_h2_full"] / budget["m_sys"],
        budget["m_h2_full"] / (budget["V_sys"] * M3_TO_L),
    )


def gate_v4_2_worst_relative_error(power=14):
    """Worst relative Sobol-index error against the Ishigami closed form."""
    return sensitivity.sobol_test_ishigami(n=2 ** power, seed=0)[
        "worst_relative_error"
    ]


def ax21_baseline_capacity():
    """AX-21's system gravimetric capacity at the baseline envelope."""
    ctx = _inputs()
    budget = envelope.evaluate_envelope(
        ctx["material"], ctx["isotherm"], ctx["engineering"],
        *BASELINE.as_tuple(),
    )
    return budget["GC"]


def coherence_limits():
    """``(fit, A-ISO-4)`` pore-volume limits on the limiting uptake, mol/kg."""
    ctx = _inputs()
    return (
        inverse.coherent_n_max_limit(
            ctx["material"], inverse.fit_va_slope(ctx["spec"].material)
        ),
        inverse.coherent_n_max_limit(
            ctx["material"], inverse.V_LIQUID_H2_MOLAR
        ),
    )


def cnt_primary_entry():
    """``(n_max, system GC, ratio to AX-21)`` for the best-provenanced entry."""
    ctx = _inputs()
    with open(DATA / "materials" / "cnt_literature.yaml") as handle:
        corpus = yaml.safe_load(handle)
    key = corpus["case_study"]["primary_entry"]
    entry = next(e for e in corpus["entries"] if e["key"] == key)

    candidate = inverse.material_from_corpus_entry(
        ctx["material"], entry, "absolute"
    )
    budget = envelope.evaluate_envelope(
        candidate, isotherm.ModifiedDA(candidate), ctx["engineering"],
        *BASELINE.as_tuple(),
    )
    return candidate.n_max, budget["GC"], budget["GC"] / ax21_baseline_capacity()


def c5_contour_crossings():
    """Claim C5's P = 0.05, 0.50, 0.95 crossings along alpha = 3080 J/mol.

    A 33-node sweep at 1000 system evaluations per node, on the line and at
    the resolution pre-registered for the metric. About a minute.
    """
    ctx = _inputs()
    targets = inverse.load_doe_targets(DATA / "targets" / "doe_targets.yaml",
                                       "2025")
    # conditional=False is the configuration the published C5 numbers come
    # from, and it is not the function's default. With the unswept parameters
    # conditioned on the node, every node on this row returns no valid sample
    # and the contours do not exist -- which an independent verifier had to
    # recover from notebook 07 rather than from the pre-registration. Stating
    # it here makes the published metric reproducible from the record.
    row = inverse.probability_map(
        ctx["spec"], ctx["material"], ctx["engineering"],
        "n_max", "alpha",
        np.linspace(90.0, 170.0, 33), [3080.0],
        targets=targets, n_samples=1000, seed=0, conditional=False,
    )
    return inverse.boundary_separation(row, 3080.0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full", action="store_true",
        help="also compute claim C5's contour crossings (about a minute)",
    )
    args = parser.parse_args(argv)

    print("H2STAR headline numbers, recomputed from the artifact")
    print("=" * 62)

    v1 = gate_v1_max_relative_density_error()
    print(f"Gate V1  max relative density error   {v1:.6e}   "
          f"(floor < 1e-3, PASS)")

    gc_full, vc_full = gate_v3_full_state_metrics()
    print(f"Gate V3  GC_full                      {gc_full:.6f} kg/kg  "
          f"(anchor 0.0312, documented FAIL)")
    print(f"Gate V3  VC_full                      {vc_full:.6f} kg/L   "
          f"(anchor 0.0194, documented FAIL)")

    v42 = gate_v4_2_worst_relative_error()
    print(f"Gate V4.2 worst rel. error @ 2^14     {100.0 * v42:.4f} %")

    print(f"AX-21    baseline system GC           {ax21_baseline_capacity():.6f} kg/kg")

    fit_limit, iso_limit = coherence_limits()
    print(f"Coherence limit (fit correlation)     {fit_limit:.4f} mol/kg")
    print(f"Coherence limit (A-ISO-4)             {iso_limit:.4f} mol/kg")

    n_max, gc, ratio = cnt_primary_entry()
    print(f"CNT primary inferred n_max            {n_max:.4f} mol/kg")
    print(f"CNT primary system GC                 {gc:.6f} kg/kg")
    print(f"Claim C4 ratio to AX-21               {ratio:.4f}x")

    if args.full:
        print("\nClaim C5 (expensive) ...", flush=True)
        c5 = c5_contour_crossings()
        print(f"Claim C5  P = 0.05 crossing           "
              f"{c5['x_at_low']:.4f} mol/kg")
        print(f"Claim C5  P = 0.50 crossing           "
              f"{c5['x_at_median']:.4f} mol/kg")
        print(f"Claim C5  P = 0.95 crossing           "
              f"{c5['x_at_high']:.4f} mol/kg")
        print(f"Claim C5  separation                  "
              f"{c5['separation']:.4f} mol/kg "
              f"({c5['separation_percent']:.2f}% of the median)")
    else:
        print("\nClaim C5's crossings need --full (about a minute).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
