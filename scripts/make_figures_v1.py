"""Regenerate every v1.0 figure from the committed analysis records.

One command, fresh-clone safe (D10). Figures land in figures/v1/ as both PDF
(vector, for the manuscript) and PNG (for the README). Each figure addresses
the corresponding 2026-10-27 review item (minors 6-12) and the frozen
captions rules: sampling schemes stated, no undisclosed bands, no robustness
claims beyond the two-model demonstration, validity regions shaded.
"""

import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dataclasses import replace  # noqa: E402

from h2star import eos, isotherm  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
AN = os.path.join(ROOT, "data", "analysis")
FIG = os.path.join(ROOT, "figures", "v1")

plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.titlesize": 9,
    "axes.labelsize": 9, "legend.fontsize": 7.5, "figure.dpi": 300,
    "savefig.bbox": "tight", "lines.linewidth": 1.0,
})

POSTERIOR_MEDIAN = {
    "n_max": 61.9047, "alpha": 3561.96, "beta": 16.61,
    "log10_p0": 9.1509, "v_a": 1.15627e-3,
}


def savefig(fig, name):
    os.makedirs(FIG, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG, f"{name}.{ext}"))
    plt.close(fig)
    print("built", name)


def load_multiT():
    rows = []
    with open(os.path.join(ROOT, "data", "validation",
                           "ax21_fig1a_multiT.csv")) as fh:
        for r in csv.DictReader(fh):
            rows.append({k: (v if k == "quality" else float(v or "nan"))
                         for k, v in r.items()})
    return rows


def median_material():
    mat = isotherm.Material.from_yaml(
        os.path.join(ROOT, "data", "materials", "ax21.yaml"))
    th = POSTERIOR_MEDIAN
    return replace(mat, n_max=th["n_max"], alpha=th["alpha"],
                   beta=th["beta"], p0=10 ** th["log10_p0"], v_a=th["v_a"])


def f1_eos_error():
    """F1 (minor 6): EOS relative error vs pressure, per isotherm."""
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    for T, marker in ((77, "o"), (100, "s"), (160, "^"), (298, "x")):
        path = os.path.join(ROOT, "data", "validation", f"nist_h2_{T}K.csv")
        P, rho = [], []
        with open(path) as fh:
            for line in fh:
                if line.startswith("#") or line.startswith("pressure"):
                    continue
                a, b = line.strip().split(",")
                P.append(float(a))
                rho.append(float(b))
        P = np.array(P) * 1e5  # file stores bar
        rho = np.array(rho)  # kg/m^3
        model = np.array([eos.density(p, float(T)) for p in P])
        rel = model / rho - 1.0
        ax.plot(P / 1e6, rel * 1e5, marker, ms=3, lw=0.7, ls="-",
                label=f"{T} K")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("Pressure (MPa)")
    ax.set_ylabel(r"relative density error ($\times 10^{-5}$)")
    ax.legend(ncol=4, frameon=False)
    savefig(fig, "F1_eos_relative_error")


def f2_fit():
    """F2 (minor 7): multi-T data + posterior-median fit, linear & log P."""
    rows = load_multiT()
    mat = median_material()
    iso = isotherm.ModifiedDA(mat)
    temps = sorted({r["temperature_K"] for r in rows})
    cmap = plt.get_cmap("viridis")
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), sharey=True)
    for ax, logx in zip(axes, (False, True)):
        for i, T in enumerate(temps):
            if T < 50:
                continue  # subcritical: excluded from fits (EOS floor at 30K)
            sel = [r for r in rows if r["temperature_K"] == T]
            P = np.array([r["pressure_MPa"] for r in sel])
            n = np.array([r["n_excess_molkg"] for r in sel])
            sn = np.array([r["sigma_n_molkg"] for r in sel])
            c = cmap(i / max(len(temps) - 1, 1))
            ax.errorbar(P, n, yerr=sn, fmt="o", ms=2.2, color=c, lw=0.6,
                        elinewidth=0.5,
                        label=f"{T:.0f} K" if not logx else None)
            Pg = np.logspace(np.log10(0.002), np.log10(6.0), 200) \
                if logx else np.linspace(0.002, 6.0, 200)
            ax.plot(Pg, iso.n_excess(Pg * 1e6, T), color=c, lw=0.8)
        if logx:
            ax.set_xscale("log")
            ax.set_xlabel("Pressure (MPa), log scale")
        else:
            ax.set_xlabel("Pressure (MPa)")
    axes[0].set_ylabel("Excess adsorption (mol/kg)")
    axes[0].legend(ncol=2, frameon=False)
    fig.suptitle("AX-21 H$_2$ excess isotherms (dual-digitized, reconciled; "
                 "posterior-median fit); resolution 0.0049 MPa, "
                 "0.062 mol/kg per pixel", fontsize=8)
    savefig(fig, "F2_multiT_fit")


def f3_profiles():
    """F3 (new): profile likelihoods, 77 K vs multi-T (the headline)."""
    with open(os.path.join(AN, "identifiability_v1.json")) as fh:
        J = json.load(fh)
    fig, axes = plt.subplots(1, 5, figsize=(10.0, 2.4))
    labels = {"n_max": r"$n_{max}$ (mol/kg)", "alpha": r"$\alpha$ (J/mol)",
              "beta": r"$\beta$ (J/mol K)",
              "log10_p0": r"$\log_{10} P_0$ (Pa)",
              "v_a": r"$v_a$ (m$^3$/kg)"}
    for ax, p in zip(axes, ("n_max", "alpha", "beta", "log10_p0", "v_a")):
        for key, color, lab in (("single_isotherm_77K", "C1", "77 K only"),
                                ("multi_temperature", "C0", "60-298 K")):
            pr = J[key]["profiles"][p]
            obj0 = J[key]["objective"]
            ax.plot(pr["grid"], np.array(pr["objective"]) - obj0,
                    color=color, label=lab)
        ax.axhline(3.84, color="k", lw=0.5, ls="--")
        ax.set_ylim(0, 25)
        ax.set_xlabel(labels[p])
    axes[0].set_ylabel(r"$\Delta$ objective")
    axes[0].legend(frameon=False)
    fig.suptitle("Profile likelihoods: one isotherm leaves the parameters "
                 "loose; seven temperatures pin them", fontsize=9)
    savefig(fig, "F3_profiles")


def f4_anchor_table():
    """F4 (minor 8): anchor comparison as a table-figure with the E2 record."""
    rows = [
        ("E1 HexCell m_sys (kg)", "140.99", "140.99", "+0.0%", "calibrated"),
        ("E1 HexCell V_sys (L)", "287.70", "285.59", "-0.7%", "calibrated"),
        ("E2 H1 GC, type-3 200 bar", "0.0339", "0.0478", "+41.0%", "FAIL"),
        ("E2 H2 VC, type-3 200 bar", "0.0210", "0.0222", "+5.8%", "PASS"),
        ("E2 H3 m_sys (kg), 60 bar/40 K", "99.8", "99.6", "-0.2%", "PASS"),
        ("E2 H3 V_sys (L), 60 bar/40 K", "206.6", "184.7", "-10.6%", "PASS"),
        ("FY2011 GC (check)", "0.039", "0.0478", "+22.6%", "reported"),
        ("ST044-2012 GC (check)", "0.03665", "0.0478", "+30.4%", "reported"),
        ("ST044-2013 GC (check)", "0.0312", "0.0478", "+53.2%", "reported"),
    ]
    fig, ax = plt.subplots(figsize=(6.4, 2.8))
    ax.axis("off")
    tbl = ax.table(
        cellText=[list(r) for r in rows],
        colLabels=["Quantity", "Anchor", "Model", "Dev.", "Status"],
        loc="center", cellLoc="left")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    tbl.scale(1, 1.25)
    ax.set_title("Calibration (E1) and held-out gate (E2) against HSECoE "
                 "anchors; usable basis.\nGate E2 FAILED on H1 (pre-registered"
                 " 10.5281/zenodo.23931242): absolute-capacity claims dropped.",
                 fontsize=8)
    savefig(fig, "F4_anchors")


def f5_observable_map():
    """F5/F6 (minors 9-10, D4): requirement map in observables, two models."""
    with open(os.path.join(AN, "observable_map_v1.json")) as fh:
        M = json.load(fh)
    U = np.array(M["u_grid"])
    R = np.array(M["rho_grid"])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, (name, lab) in zip(
            axes, (("v1_component", "v1.0 component model"),
                   ("v02_lumped", "v0.2 lumped model (superseded)"))):
        GC = np.array(M["models"][name]["GC"])
        VC = np.array(M["models"][name]["VC"])
        feas = ((GC >= 0.055) & (VC >= 0.040)).astype(float)
        ax.contourf(R, U, feas, levels=[0.5, 1.5], colors=["#9ecae1"])
        cs = ax.contour(R, U, GC, levels=[0.045, 0.055, 0.065],
                        colors="k", linewidths=0.7)
        ax.clabel(cs, fmt="GC %.3f", fontsize=6)
        cs2 = ax.contour(R, U, VC, levels=[0.030, 0.040, 0.050],
                         colors="C3", linewidths=0.7)
        ax.clabel(cs2, fmt="VC %.3f", fontsize=6)
        pt = M["ax21_point"]
        ax.plot(pt["rho_pack"], pt["deliverable_uptake_abs_swing"], "k*",
                ms=9, label="AX-21 (posterior median)")
        ax.set_xlabel(r"packing density $\rho_{pack}$ (kg/m$^3$)")
        ax.set_title(lab, fontsize=8)
    axes[0].set_ylabel("deliverable uptake, full$\\to$empty (kg H$_2$/kg)")
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle("DOE-2025 feasibility in observable axes (shaded). No "
                 "probability band: axes are measured, not sampled "
                 "(conditionality rule). Two engineering models shown; the "
                 "boundary shift is the model-dependence the E2 FAIL "
                 "quantifies.", fontsize=7.5)
    savefig(fig, "F5_observable_map")


def f6_prediction_tightness():
    """F6 (new headline): loose parameters, tight predictions."""
    with open(os.path.join(AN, "identifiability_v1.json")) as fh:
        J = json.load(fh)
    prop = J["propagation_baseline_envelope_77K"]
    ok = [r for r in prop if "GC" in r]
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8))
    x = [r["log10_p0"] for r in ok]
    axes[0].plot(x, [r["n_max"] for r in ok], "o-", ms=3)
    axes[0].set_xlabel(r"$\log_{10} P_0$ (Pa)")
    axes[0].set_ylabel(r"profile $n_{max}$ (mol/kg)")
    axes[0].set_title("the 77 K ridge: parameters loose", fontsize=8)
    inr = [r for r in ok if r["in_frozen"]]
    axes[1].plot([r["log10_p0"] for r in ok], [r["GC"] for r in ok],
                 "o-", ms=3, label="all profile points")
    axes[1].plot([r["log10_p0"] for r in inr], [r["GC"] for r in inr],
                 "o", ms=4, color="C3", label="inside 95% region")
    axes[1].set_xlabel(r"$\log_{10} P_0$ (Pa)")
    axes[1].set_ylabel("system usable GC (kg/kg)")
    axes[1].set_title("predictions tight (frozen engineering model)",
                      fontsize=8)
    axes[1].legend(frameon=False, fontsize=6.5)
    savefig(fig, "F6_sloppiness")


def f7_shapley():
    """F7 (minor 11, M6 fix): Shapley effects + elasticities, separate."""
    with open(os.path.join(AN, "sensitivity_v1.json")) as fh:
        S = json.load(fh)
    players = S["shapley"]["players"]
    var = S["shapley"]["var_GC"]
    vals = np.array([S["shapley"]["GC"][p][0] for p in players]) / var
    errs = np.array([S["shapley"]["GC"][p][1] for p in players]) / var
    order = np.argsort(vals)[::-1][:10]
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    axes[0].barh(range(len(order)), vals[order], xerr=errs[order],
                 color="C0")
    axes[0].set_yticks(range(len(order)))
    axes[0].set_yticklabels([players[i] for i in order], fontsize=7)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Shapley share of Var(GC)")
    axes[0].set_title("attribution (joint posterior + declared inputs)",
                      fontsize=8)
    el = S["elasticities_nominal"]
    keys = sorted(el, key=lambda k: -abs(el[k]["GC"]))[:10]
    axes[1].barh(range(len(keys)), [el[k]["GC"] for k in keys], color="C2")
    axes[1].set_yticks(range(len(keys)))
    axes[1].set_yticklabels(keys, fontsize=7)
    axes[1].invert_yaxis()
    axes[1].set_xlabel(r"elasticity $\partial \ln GC / \partial \ln x$")
    axes[1].set_title("design leverage (separate, nominal point)", fontsize=8)
    fig.suptitle("Variance attribution vs design leverage, kept distinct "
                 "(N=20,000; permutation Shapley, dependent inputs)",
                 fontsize=8)
    savefig(fig, "F7_shapley_elasticity")


def main():
    f1_eos_error()
    f2_fit()
    f3_profiles()
    f4_anchor_table()
    f5_observable_map()
    f6_prediction_tightness()
    f7_shapley()
    print("all v1 figures built in", FIG)


if __name__ == "__main__":
    main()
