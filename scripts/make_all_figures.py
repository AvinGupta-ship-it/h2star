#!/usr/bin/env python3
"""Regenerate every H2STAR figure from the committed data, in one command.

    python3 scripts/make_all_figures.py [--quick] [--only F6] [--figures DIR]

Run from a fresh clone, this is the single-command reproducibility check that
manual Part VII requires: no notebook, no cached intermediate, nothing but the
package and the files under ``data/``.

All physics lives in the package. This script loads inputs, calls package
functions, and writes PNGs. It performs no modelling of its own, which is why a
figure it produces and a figure a notebook produces are the same figure rather
than two implementations that happen to agree.

The expensive one is F6. Its probability band is 1000 system evaluations per
grid node, each a Brent sizing solve, and the published grid takes roughly ten
minutes. ``--quick`` drops the sample count and coarsens the grid for a smoke
test; it does NOT reproduce the published figure and the script says so, both
on the console and in the figure's own title, so a quick-mode image cannot be
mistaken for the real one.
"""

import argparse
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot  # noqa: E402

import numpy as np  # noqa: E402

from h2star import (  # noqa: E402
    envelope,
    fitting,
    inverse,
    isotherm,
    sensitivity,
    system,
    uq,
    viz,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "data"

#: The baseline cryo-adsorption envelope (manual 2.4F).
BASELINE = envelope.OperatingPoint(P_full=100.0e5, T_full=80.0)

#: Ambient comparison envelope for the two-regime Sobol study (manual 2.4K).
AMBIENT = envelope.OperatingPoint(P_full=100.0e5, T_full=298.0, T_empty=298.0)

#: Published F6 grid and sample count, pre-registered as N >= 1000 per node.
F6_GRID = {
    "x": (70.0, 160.0, 19),
    "alpha": (2000.0, 5000.0, 7),
    "rho_bulk": (200.0, 500.0, 7),
    "n_samples": 1000,
}

#: Quick-mode substitute. Not the published figure.
F6_QUICK = {
    "x": (70.0, 160.0, 9),
    "alpha": (2000.0, 5000.0, 3),
    "rho_bulk": (200.0, 500.0, 3),
    "n_samples": 60,
}


def load_inputs():
    """Load every committed input the figures depend on."""
    material = isotherm.Material.from_yaml(DATA / "materials" / "ax21.yaml")
    return {
        "material": material,
        "isotherm": isotherm.ModifiedDA(material),
        "engineering": system.EngineeringParams.from_yaml(
            DATA / "engineering.yaml"
        ),
        "targets": inverse.load_doe_targets(
            DATA / "targets" / "doe_targets.yaml", "2025"
        ),
        "spec": uq.UncertaintySpec.from_yaml(DATA / "uncertainty.yaml"),
    }


def _nist_isotherms(ctx):
    """Model-versus-reference density pairs for every NIST validation table."""
    import csv
    import re

    from h2star import eos

    def temperature_of(path):
        return float(re.search(r"nist_h2_(\d+)K\.csv$", path.name).group(1))

    # Sorted by temperature, not by filename. A filename sort orders these
    # 100, 160, 298, 77 -- string order -- which put the legend of the
    # published F1 out of temperature sequence and drew the isotherms in that
    # order, so the overlay order of the scatter points was a property of how
    # the files happened to be named.
    isotherms = []
    for path in sorted((DATA / "validation").glob("nist_h2_*.csv"),
                       key=temperature_of):
        temperature = temperature_of(path)
        pressures, reference = [], []
        with open(path) as handle:
            rows = csv.reader(
                line for line in handle if not line.startswith("#")
            )
            next(rows)
            for row in rows:
                if row:
                    pressures.append(float(row[0]))
                    reference.append(float(row[1]))
        model = [
            eos.density(p * 1.0e5, temperature) for p in pressures
        ]
        isotherms.append(
            {"T": temperature, "nist": reference, "model": model}
        )
    return isotherms


def figure_f1(ctx, out):
    """F1 — EOS parity against the NIST reference tables (Gate V1)."""
    viz.eos_parity_plot(_nist_isotherms(ctx), savepath=out / "F1_eos_parity.png")


def _digitized_ax21():
    """The digitized AX-21 77 K excess points, in Pa and mol/kg."""
    import csv

    pressures, uptakes = [], []
    path = DATA / "validation" / "ax21_digitized.csv"
    with open(path) as handle:
        rows = csv.reader(line for line in handle if not line.startswith("#"))
        next(rows)
        for row in rows:
            if row:
                pressures.append(float(row[0]))
                uptakes.append(float(row[1]))
    return np.array(pressures), np.array(uptakes)


def figure_f2(ctx, out):
    """F2 — AX-21 isotherm: digitized data, published parameters, refit (Gate V2).

    The refit is the fixed-p0 one, which is the conditional fit the Gate V4
    pre-registration seeds the material uncertainty from. Showing the
    unconstrained refit here would draw a curve whose parameters the
    uncertainty layer deliberately does not use.
    """
    pressures_mpa, uptakes = _digitized_ax21()
    order = np.argsort(pressures_mpa)
    pressures_mpa, uptakes = pressures_mpa[order], uptakes[order]
    pressures_pa = pressures_mpa * 1.0e6

    curve_pa = np.linspace(0.05e6, 6.0e6, 400)
    published = ctx["isotherm"]

    refit = fitting.fit_modified_da(
        pressures_pa, 77.0, uptakes, ctx["material"], fix_p0=True
    )
    fitted = isotherm.ModifiedDA(refit.material)

    viz.plot_ax21_isotherm(
        P_data_mpa=pressures_mpa,
        n_excess_data=uptakes,
        P_curve_mpa=curve_pa / 1.0e6,
        n_excess_curve=published.n_excess(curve_pa, 77.0),
        n_absolute_curve=published.n_absolute(curve_pa, 77.0),
        residuals=uptakes - published.n_excess(pressures_pa, 77.0),
        rmse_value=float(
            isotherm.rmse(published.n_excess(pressures_pa, 77.0), uptakes)
        ),
        n_excess_fit=fitted.n_excess(curve_pa, 77.0),
        residuals_fit=uptakes - fitted.n_excess(pressures_pa, 77.0),
        rmse_fit=refit.rmse,
        fit_label="Refit, p0 fixed (this work)",
        savepath=out / "F2_ax21_isotherm.png",
    )


def figure_f3(ctx, out):
    """F3 — isosteric heat against the carbon band (Gate V2 part 3).

    ``plot_isosteric_heat`` draws onto an axis and returns it rather than
    owning a figure, so the figure and its saving are the caller's job here as
    they are in notebook 03.
    """
    figure, axis = matplotlib.pyplot.subplots(figsize=(7, 5))
    viz.plot_isosteric_heat(ctx["isotherm"], ax=axis)
    figure.tight_layout()
    figure.savefig(out / "F3_isosteric_heat.png", dpi=300)


def figure_f4(ctx, out):
    """F4 — system validation against the HSECoE anchor (Gate V3, a FAIL)."""
    import yaml

    with open(DATA / "validation" / "hsecoe_reference.yaml") as handle:
        anchor = yaml.safe_load(handle)

    state = anchor["operating_full_state"]
    design = system.SystemDesign(
        ctx["material"],
        ctx["isotherm"],
        ctx["engineering"],
        state["pressure_bar"] * 1.0e5,
        state["temperature_K"],
        5.0e5,
        160.0,
    )
    budget = design.evaluate(system.size_for_usable(design))
    results = anchor["reference_results"]

    viz.plot_system_validation(
        budget["m_h2_full"] / budget["m_sys"],
        budget["m_h2_full"] / (budget["V_sys"] * 1000.0),
        results["system_gravimetric_capacity_kg_per_kg"]["value"],
        results["system_volumetric_capacity_kg_per_L"]["value"],
        anchor["tolerance_pct"],
        savepath=out / "F4_system_validation.png",
    )


def figure_f5(ctx, out):
    """F5 — forward capacity maps over the full state."""
    grid = envelope.forward_map(
        ctx["material"],
        ctx["isotherm"],
        ctx["engineering"],
        np.linspace(20.0e5, 200.0e5, 37),
        np.linspace(60.0, 120.0, 31),
    )
    viz.plot_forward_maps(
        grid, targets=ctx["targets"], savepath=out / "F5_forward_maps.png"
    )


def figure_f6(ctx, out, quick=False):
    """F6 — the acceptability boundary as a Monte Carlo probability band."""
    settings = F6_QUICK if quick else F6_GRID
    x_lo, x_hi, x_n = settings["x"]
    x_values = np.linspace(x_lo, x_hi, x_n)

    panels = []
    for parameter in ("alpha", "rho_bulk"):
        lo, hi, count = settings[parameter]
        panels.append(
            inverse.probability_map(
                ctx["spec"],
                ctx["material"],
                ctx["engineering"],
                "n_max",
                parameter,
                x_values,
                np.linspace(lo, hi, count),
                operating_point=BASELINE,
                targets=ctx["targets"],
                n_samples=settings["n_samples"],
                seed=0,
                conditional=False,
            )
        )

    slope = inverse.V_LIQUID_H2_MOLAR
    limit = inverse.coherent_n_max_limit(ctx["material"], slope)
    curves = [
        {f"Pore volume exhausted (A-ISO-4): $n_{{\\mathrm{{max}}}}$ = {limit:.0f}":
            (limit, None)},
        {"Pore volume exhausted (A-ISO-4)":
            (x_values, inverse.coherent_rho_bulk_limit(
                ctx["material"], x_values, slope))},
    ]
    reference = {
        "AX-21 (reference)": {
            "n_max": ctx["material"].n_max,
            "alpha": ctx["material"].alpha,
            "rho_bulk": ctx["material"].rho_bulk,
        }
    }

    title = None
    if quick:
        title = (
            "Material acceptability as a probability band (F6) "
            "- QUICK MODE, NOT THE PUBLISHED FIGURE"
        )
    viz.plot_probability_maps(
        panels,
        coherence_curves=curves,
        reference_points=reference,
        title=title,
        savepath=out / "F6_acceptability_probability.png",
    )


def figure_f7(ctx, out, quick=False):
    """F7 — Sobol indices at the cryogenic and ambient envelopes."""
    n = 64 if quick else 512
    studies, labels = [], []
    for label, point in (
        ("Cryogenic: 80 K full, 160 K empty", BASELINE),
        ("Ambient: 298 K isothermal", AMBIENT),
    ):
        studies.append(
            sensitivity.sobol_indices(
                ctx["spec"],
                ctx["material"],
                ctx["engineering"],
                point,
                n=n,
                seed=0,
            )
        )
        labels.append(label)

    # F6 marks quick mode in its own title; F7 did not, so a coarsened F7 was
    # indistinguishable from the published one once the console warning had
    # scrolled away. Both now say so in the image.
    title = None
    if quick:
        title = (
            "Sobol indices by operating regime (F7) "
            "- QUICK MODE, NOT THE PUBLISHED FIGURE"
        )
    for output in ("GC", "VC"):
        viz.plot_sobol_indices(
            studies,
            labels,
            output=output,
            title=title,
            savepath=out / f"F7_sobol_{output.lower()}.png",
        )


def figure_f8(ctx, out):
    """F8 — the CNT cascade and the physical-consistency screen."""
    import yaml

    with open(DATA / "materials" / "cnt_literature.yaml") as handle:
        corpus = yaml.safe_load(handle)

    limit_fit = inverse.coherent_n_max_limit(
        ctx["material"], inverse.fit_va_slope(ctx["spec"].material)
    )
    limit_physical = inverse.coherent_n_max_limit(
        ctx["material"], inverse.V_LIQUID_H2_MOLAR
    )

    rows = []
    for entry in corpus["entries"]:
        if entry["key"] == "chen1999":
            continue
        try:
            n_max = inverse.material_from_corpus_entry(
                ctx["material"], entry, "absolute"
            ).n_max
            accepted = n_max <= limit_physical
            note = "" if accepted else "exceeds the pore-volume limit"
        except ValueError:
            n_max, accepted = None, False
            note = "no $n_{max}$ reproduces the reported point"
        rows.append((entry["key"], n_max, accepted, note))

    primary = next(
        e for e in corpus["entries"]
        if e["key"] == corpus["case_study"]["primary_entry"]
    )
    waterfalls = {}
    for basis in ("absolute", "excess"):
        candidate = inverse.material_from_corpus_entry(
            ctx["material"], primary, basis
        )
        budget = envelope.evaluate_envelope(
            candidate,
            isotherm.ModifiedDA(candidate),
            ctx["engineering"],
            *BASELINE.as_tuple(),
        )
        waterfalls[basis] = system.gap_waterfall(budget)

    viz.plot_cnt_gap(
        {
            "label": f"{primary['label']} ({primary['uptake']['value']} wt%)",
            "primary": waterfalls["absolute"],
            "alternate": waterfalls["excess"],
        },
        {
            "entries": rows,
            "limits": {
                "pore volume exhausted (fit correlation)": limit_fit,
                "pore volume exhausted (A-ISO-4)": limit_physical,
            },
            "reference": ("AX-21 activated carbon", ctx["material"].n_max),
        },
        savepath=out / "F8_cnt_gap.png",
    )


#: Every figure, in order, with the builders that take a quick-mode flag noted.
FIGURES = (
    ("F1", figure_f1, False),
    ("F2", figure_f2, False),
    ("F3", figure_f3, False),
    ("F4", figure_f4, False),
    ("F5", figure_f5, False),
    ("F6", figure_f6, True),
    ("F7", figure_f7, True),
    ("F8", figure_f8, False),
)


def main(argv=None):
    """Regenerate the requested figures and report what was written."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="coarsen F6 and F7 for a smoke test; does NOT reproduce the "
             "published figures",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="Fn",
        help="build only these figures (repeatable), e.g. --only F6",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=None,
        help="output directory (default: ./figures, or ./figures/quick with "
             "--quick)",
    )
    args = parser.parse_args(argv)

    requested = {name.upper() for name in (args.only or [])}
    known = {name for name, _, _ in FIGURES}
    unknown = requested - known
    if unknown:
        parser.error(f"unknown figure(s) {sorted(unknown)}; known: {sorted(known)}")

    # Quick mode must not be able to overwrite a published figure. It used to
    # write into figures/ like a real run, so a smoke test left two coarsened
    # PNGs sitting among the published ones under their published names. It
    # now writes to figures/quick/ unless an output directory is named
    # outright, and the console still says so.
    if args.figures is None:
        args.figures = (
            REPO_ROOT / "figures" / "quick" if args.quick
            else REPO_ROOT / "figures"
        )

    args.figures.mkdir(parents=True, exist_ok=True)
    if args.quick:
        print(f"QUICK MODE: F6 and F7 are coarsened. These are NOT the "
              f"published figures, and they are written to {args.figures} "
              f"rather than among them.\n")

    context = load_inputs()
    failures = []
    started = time.perf_counter()

    for name, builder, takes_quick in FIGURES:
        if requested and name not in requested:
            continue
        print(f"{name} ...", end=" ", flush=True)
        step = time.perf_counter()
        try:
            # viz pins the rendering parameters for its own drawing, but a
            # builder that assembles its own figure around a viz call -- F3
            # does -- would otherwise draw the figure-level text under
            # whatever font the host environment supplies. Applying the pin
            # here covers every builder, present and future, rather than
            # leaving each one to remember.
            with viz.figure_style():
                if takes_quick:
                    builder(context, args.figures, quick=args.quick)
                else:
                    builder(context, args.figures)
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            failures.append((name, exc))
            print(f"FAILED ({type(exc).__name__}: {exc})")
            continue
        matplotlib.pyplot.close("all")
        print(f"ok ({time.perf_counter() - step:.1f}s)")

    elapsed = time.perf_counter() - started
    print(f"\n{elapsed:.1f}s total, written to {args.figures}")

    if failures:
        print("\nFAILED:")
        for name, exc in failures:
            print(f"  {name}: {type(exc).__name__}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
