"""S5 identifiability analysis (pre-registration section 6). Produces
data/analysis/identifiability_v1.json with: the multi-temperature optimum,
profile likelihoods for every parameter (multi-T and 77 K-only), the frozen
and overdispersion-inflated 95% intervals, the Fisher eigenvalue spectrum,
the bound-removal sensitivity for log10_p0, the low-temperature (35-45 K,
near-critical) sensitivity — the JSON key keeps its original name
"subcritical_sensitivity" for record stability, though only 30 K is truly
subcritical (Tc = 33.145 K) — and
the propagation of the profile region to system predictions under the frozen
v1.0 engineering model (usable GC/VC at the baseline envelope)."""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from h2star import engineering as eng  # noqa: E402
from h2star import identifiability as ident  # noqa: E402
from h2star import isotherm  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data", "validation", "ax21_fig1a_multiT.csv")
OUT = os.path.join(ROOT, "data", "analysis", "identifiability_v1.json")

GRIDS = {
    "log10_p0": np.round(np.arange(6.78, 12.001, 0.25), 3),
    "n_max": np.round(np.concatenate([
        np.arange(20, 100, 5), np.arange(100, 301, 20)]), 1),
    "alpha": np.round(np.arange(1500, 8001, 250), 1),
    "beta": np.round(np.arange(0, 50.1, 2.5), 1),
    "v_a": np.round(np.arange(1e-4, 3.01e-3, 1e-4), 6),
}


def run_profiles(base, D, label):
    r0 = ident.fit(base, *D)
    obj0 = r0["objective"]
    out = {"optimum": {k: float(v) for k, v in r0["theta"].items()},
           "objective": obj0, "n_points": int(len(D[0])),
           "dof": int(len(D[0]) - 5), "profiles": {}}
    s2 = obj0 / out["dof"]
    out["overdispersion_s2"] = float(s2)
    for p, grid in GRIDS.items():
        prof = ident.profile(base, *D, param=p, grid=grid,
                             theta_opt=r0["theta"])
        objs = [o for _, o, _ in prof]
        lo_f, hi_f = ident.profile_crossing(
            base, *D, param=p, theta_opt=r0["theta"], obj0=obj0)
        lo_s, hi_s = ident.profile_crossing(
            base, *D, param=p, theta_opt=r0["theta"], obj0=obj0,
            threshold=3.84 * s2)
        out["profiles"][p] = {
            "grid": [float(v) for v, _, _ in prof],
            "objective": [float(o) for o in objs],
            "interval_frozen": [lo_f, hi_f],
            "interval_s2_inflated": [lo_s, hi_s],
        }
        print(f"[{label}] {p}: frozen 95% [{lo_f:.5g}, {hi_f:.5g}]  "
              f"s2-inflated [{lo_s:.5g}, {hi_s:.5g}]")
    w, V = ident.fisher_spectrum(base, r0["theta"], *D)
    out["fisher_eigenvalues"] = [float(x) for x in w]
    out["fisher_eigenvectors"] = [[float(x) for x in col] for col in V.T]
    return out, r0


def propagate(base, prof_p0, obj0, s2):
    """System usable GC/VC across the log10_p0 profile region (frozen model,
    type-3 AX-21 at the baseline envelope 100 bar/80 K -> 5 bar/160 K)."""
    p = eng.EngineeringParamsV1.from_yaml(
        os.path.join(ROOT, "data", "engineering_v1.yaml"))
    rows = []
    for v, obj, theta in prof_p0:
        mat = isotherm.Material.from_yaml(
            os.path.join(ROOT, "data", "materials", "ax21.yaml"))
        from dataclasses import replace
        mat = replace(mat, n_max=theta["n_max"], alpha=theta["alpha"],
                      beta=theta["beta"], p0=10 ** v, v_a=theta["v_a"])
        iso = isotherm.ModifiedDA(mat)
        d = eng.SystemDesignV1(mat, iso, p, "type3", 100e5, 80.0, 5e5, 160.0)
        try:
            b = eng.evaluate_sized(d)
            rows.append({"log10_p0": float(v), "objective": float(obj),
                         "in_frozen": bool(obj <= obj0 + 3.84),
                         "in_s2": bool(obj <= obj0 + 3.84 * s2),
                         "n_max": float(theta["n_max"]),
                         "GC": b["GC"], "VC": b["VC"]})
        except Exception as e:  # noqa: BLE001 - record, never hide
            rows.append({"log10_p0": float(v), "error": str(e)[:120]})
    return rows


def main():
    base = isotherm.Material.from_yaml(
        os.path.join(ROOT, "data", "materials", "ax21.yaml"))
    D_multi = ident.load_dataset(DATA)
    D_77 = ident.load_dataset(DATA, temps=(77.0,))

    multi, r_multi = run_profiles(base, D_multi, "multi-T")
    single, _ = run_profiles(base, D_77, "77K-only")

    # Bound-removal sensitivity for log10_p0 (lower bound relaxed to 6.0)
    ident.BOUNDS["log10_p0"] = (6.0, 12.0)
    relaxed = ident.fit(base, *D_multi)
    ident.BOUNDS["log10_p0"] = (6.78, 12.0)
    sens_bound = {"theta": {k: float(v) for k, v in relaxed["theta"].items()},
                  "objective": float(relaxed["objective"])}

    # Subcritical sensitivity: add 35-45 K isotherms. The 30 K isotherm lies
    # below the repository's EOS validity floor (33.2 K, FM3 guard) and is
    # excluded from every fit; its 5 reconciled points are published in the
    # dataset for completeness.
    D_all = ident.load_dataset(
        DATA, temps=(35., 40., 45.) + ident.PRIMARY_TEMPS)
    r_all = ident.fit(base, *D_all)
    sens_sub = {"theta": {k: float(v) for k, v in r_all["theta"].items()},
                "objective": float(r_all["objective"]),
                "n_points": int(len(D_all[0]))}

    theta_opt = {k: float(v) for k, v in r_multi["theta"].items()}
    prof_p0 = ident.profile(
        base, *D_multi, param="log10_p0", grid=GRIDS["log10_p0"],
        theta_opt=theta_opt)
    prop = propagate(base, prof_p0, multi["objective"],
                     multi["overdispersion_s2"])

    # Headline sloppiness propagation: the SINGLE-isotherm (77 K) profile
    # region pushed through the same frozen engineering model.
    r77 = ident.fit(base, *D_77)
    prof77_p0 = ident.profile(
        base, *D_77, param="log10_p0", grid=GRIDS["log10_p0"],
        theta_opt={k: float(v) for k, v in r77["theta"].items()})
    prop77 = propagate(base, prof77_p0, single["objective"],
                       single["overdispersion_s2"])

    # --- Referee round 1 additions (2026-11-03) ---------------------------
    # (i) 77 K upper-bound sensitivity: the quoted single-isotherm n_max
    # interval is conditional on the frozen log10_p0 <= 12 bound. Raise the
    # bound to 14 and re-derive; direction strengthens non-identifiability.
    ident.BOUNDS["log10_p0"] = (6.78, 14.0)
    r77_b14 = ident.fit(base, *D_77)
    nlo14, nhi14 = ident.profile_crossing(
        base, *D_77, param="n_max", theta_opt=r77_b14["theta"],
        obj0=r77_b14["objective"])
    plo14, phi14 = ident.profile_crossing(
        base, *D_77, param="log10_p0", theta_opt=r77_b14["theta"],
        obj0=r77_b14["objective"])
    ident.BOUNDS["log10_p0"] = (6.78, 12.0)
    sens_77_bound14 = {
        "note": "77K-only refit with log10_p0 bound raised 12 -> 14; the "
                "frozen-bound interval is conditional on that bound "
                "(referee round-1 minor 1).",
        "theta": {k: float(v) for k, v in r77_b14["theta"].items()},
        "objective": float(r77_b14["objective"]),
        "n_max_interval_frozen": [nlo14, nhi14],
        "log10_p0_interval_frozen": [plo14, phi14],
    }

    # (ii) Propagation at the exact 77 K n_max frozen-interval endpoints
    # (the profile grid spans less than the full interval; referee minor 2).
    n_lo = single["profiles"]["n_max"]["interval_frozen"][0]
    n_hi = single["profiles"]["n_max"]["interval_frozen"][1]
    endpoint_prop = []
    for nv in (n_lo, n_hi):
        r_end = ident.fit(base, *D_77,
                          free=[k for k in ident.PARAM_ORDER if k != "n_max"],
                          fixed={"n_max": nv})
        th = r_end["theta"]
        from dataclasses import replace
        mat = replace(base, n_max=th["n_max"], alpha=th["alpha"],
                      beta=th["beta"], p0=10 ** th["log10_p0"], v_a=th["v_a"])
        iso = isotherm.ModifiedDA(mat)
        p_eng = eng.EngineeringParamsV1.from_yaml(
            os.path.join(ROOT, "data", "engineering_v1.yaml"))
        b = eng.evaluate_sized(eng.SystemDesignV1(
            mat, iso, p_eng, "type3", 100e5, 80.0, 5e5, 160.0))
        endpoint_prop.append({"n_max": float(nv),
                              "objective": float(r_end["objective"]),
                              "GC": b["GC"], "VC": b["VC"]})

    # (iii) Dense multi-T profile grids for plotting (F3): the headline
    # multi-T intervals are narrower than the coarse grids above, so F3
    # needs local grids that resolve the dip (referee minor 5).
    dense = {}
    for pname in ident.PARAM_ORDER:
        lo_i, hi_i = multi["profiles"][pname]["interval_frozen"]
        c = theta_opt[pname]
        half = max(hi_i - c, c - lo_i)
        gl, gh = c - 3.0 * half, c + 3.0 * half
        blo, bhi = ident.BOUNDS[pname]
        gl, gh = max(gl, blo), min(gh, bhi)
        grid = np.linspace(gl, gh, 13)
        prof_d = ident.profile(base, *D_multi, param=pname, grid=grid,
                               theta_opt=r_multi["theta"])
        dense[pname] = {
            "grid": [float(v) for v, _, _ in prof_d],
            "objective": [float(o) for _, o, _ in prof_d],
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({
            "dataset": "data/validation/ax21_fig1a_multiT.csv",
            "plan": "docs/preregistration_v1.0.md section 6 "
                    "(DOI 10.5281/zenodo.23931242)",
            "multi_temperature": multi,
            "single_isotherm_77K": single,
            "bound_removal_sensitivity": sens_bound,
            "subcritical_sensitivity": sens_sub,
            "propagation_baseline_envelope_multiT": prop,
            "propagation_baseline_envelope_77K": prop77,
            "sens_77K_upper_bound_14": sens_77_bound14,
            "propagation_77K_interval_endpoints": endpoint_prop,
            "profiles_dense_multiT": dense,
        }, fh, indent=1)
    print("wrote", OUT)

    for prop_, tag in ((prop, "multi-T"), (prop77, "77K-only")):
      for key, lab in (("in_frozen", "frozen"), ("in_s2", "s2")):
        gcs = [r["GC"] for r in prop_ if r.get(key)]
        vcs = [r["VC"] for r in prop_ if r.get(key)]
        if gcs:
            print(f"[{tag}] propagated over {lab} region (n={len(gcs)}): "
                  f"GC {min(gcs):.4f}-{max(gcs):.4f}, "
                  f"VC {min(vcs):.4f}-{max(vcs):.4f}")
        else:
            print(f"[{tag}] propagated over {lab} region: narrower than "
                  f"the 0.25-decade grid")


if __name__ == "__main__":
    main()
