"""Post-adjudication BOP-anchor correction sensitivity (S8 audit, finding D2).

The S8 reference audit found that the ST001-2011 '16 kg miscellaneous
balance-of-system' anchor was recorded at the wrong abscissa: slide 26 states
16 kg miscellaneous weight and 10 L miscellaneous volume as fixed assumptions
of the MOF-5 on-board analysis, whose design point is 150 atm (152.0 bar)
storage with a 187.5 atm vent (slides 12, 26, 27) -- not a 100-bar system,
and the volume is stated (10 L), not unassigned.

Gate E2 was adjudicated ONCE on the model as frozen at E1 (anchors 16 kg/11 L
at 100 bar design-class, 30 kg/25 L at 350 bar). That record stands and is
never re-run. This script quantifies, post hoc and labelled as such, what the
corrected anchor placement does to the E1 calibration and the E2 held-out
comparisons:

* variant 'frozen'   : the adjudicated model, reproduced as a check;
* variant 'corrected': anchors at the sources' own storage pressures,
  (152 bar, 16 kg, 10 L) and (350 bar, 30 kg, 25 L), interpolated linearly in
  FULL (storage) pressure -- the coordinate in which both sources state their
  systems -- and the E1 factors re-solved by the frozen E1 procedure
  (c_bop_mass exact on m_sys; c_bop_vol exact on V_sys, clamped to its
  declared bounds; c_hx = 1);
* variant 'fixed'    : BOP mass/volume pressure-independent at 16 kg/10 L
  (the ST001 deck itself treats them as fixed assumptions), same re-solve.

Output: data/analysis/bop_anchor_sensitivity.json and a printed table for
docs/validation_plan.md. The adjudicated gate verdict is NOT changed by this
script under any variant it reports; if a variant had changed a verdict, that
would be reported here and in the paper, but the gate record itself would
still stand (pre-registration section 4: run once).
"""

import json
import os
import sys

from scipy.optimize import brentq

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from h2star import engineering as eng  # noqa: E402
from h2star import isotherm  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "analysis", "bop_anchor_sensitivity.json")

E1_TARGETS = {"m_sys": 140.99, "V_sys_L": 287.70, "t_wall_mm": 14.00}
E2 = {
    "H1_GC": (0.0339, 0.20), "H2_VC": (0.0210, 0.20),
    "H3_m": (99.8, 0.25), "H3_V_L": (206.6, 0.25),
}


def make_bop(variant):
    """Return a bop_mass_volume(P_design, params) replacement."""
    if variant == "frozen":
        return eng.bop_mass_volume
    if variant == "corrected":
        def f(P_design, params):
            # linear in FULL pressure; P_design = 1.25 * P_full
            P_full_bar = P_design / 1.25 / 1.0e5
            frac = (P_full_bar - 152.0) / (350.0 - 152.0)
            m = params.c_bop_mass * (16.0 + (30.0 - 16.0) * frac)
            v = params.c_bop_vol * (10.0 + (25.0 - 10.0) * frac)
            return m, v * 1.0e-3
        return f
    if variant == "fixed":
        def f(P_design, params):
            return params.c_bop_mass * 16.0, params.c_bop_vol * 10.0e-3
        return f
    raise ValueError(variant)


def run_variant(variant):
    bop = make_bop(variant)
    orig = eng.bop_mass_volume
    eng.bop_mass_volume = bop
    try:
        p0 = eng.EngineeringParamsV1.from_yaml(
            os.path.join(ROOT, "data", "engineering_v1.yaml"))
        mof5 = isotherm.Material.from_yaml(
            os.path.join(ROOT, "data", "materials", "mof5_hsecoe.yaml"))
        ax21 = isotherm.Material.from_yaml(
            os.path.join(ROOT, "data", "materials", "ax21.yaml"))

        def hexcell(params):
            return eng.evaluate_sized(eng.SystemDesignV1(
                mof5, isotherm.ModifiedDA(mof5), params, "type1",
                100e5, 80.0, 5e5, 140.0))

        if variant == "frozen":
            params = p0
        else:
            # E1 re-solve, frozen procedure: c_bop_mass exact on m_sys.
            lo, hi = 0.5, 2.5

            def m_resid(c):
                return hexcell(p0.with_factors(
                    c_bop_mass=c, c_bop_vol=1.0))["m_sys"] - E1_TARGETS["m_sys"]
            if m_resid(lo) * m_resid(hi) > 0:
                c_m = lo if abs(m_resid(lo)) < abs(m_resid(hi)) else hi
                c_m_clamped = True
            else:
                c_m = brentq(m_resid, lo, hi, xtol=1e-9)
                c_m_clamped = False

            def v_resid(c):
                return (hexcell(p0.with_factors(
                    c_bop_mass=c_m, c_bop_vol=c))["V_sys"] * 1e3
                    - E1_TARGETS["V_sys_L"])
            if v_resid(lo) * v_resid(hi) > 0:
                c_v = lo if abs(v_resid(lo)) < abs(v_resid(hi)) else hi
                c_v_clamped = True
            else:
                c_v = brentq(v_resid, lo, hi, xtol=1e-9)
                c_v_clamped = False
            params = p0.with_factors(c_bop_mass=c_m, c_bop_vol=c_v)

        e1 = hexcell(params)
        h12 = eng.evaluate_sized(eng.SystemDesignV1(
            ax21, isotherm.ModifiedDA(ax21), params, "type3",
            200e5, 80.0, 5e5, 160.0))
        h3 = eng.evaluate_sized(eng.SystemDesignV1(
            ax21, isotherm.ModifiedDA(ax21), params, "type1",
            60e5, 40.0, 5e5, 110.0))

        def dev(pred, tgt):
            return 100.0 * (pred / tgt - 1.0)

        rec = {
            "factors": {"c_bop_mass": params.c_bop_mass,
                        "c_bop_vol": params.c_bop_vol, "c_hx": params.c_hx},
            "E1": {"m_sys": e1["m_sys"], "V_sys_L": e1["V_sys"] * 1e3,
                   "t_wall_mm": e1["t_wall"] * 1e3,
                   "m_dev_pct": dev(e1["m_sys"], E1_TARGETS["m_sys"]),
                   "V_dev_pct": dev(e1["V_sys"] * 1e3,
                                    E1_TARGETS["V_sys_L"])},
            "E2": {
                "H1_GC": h12["GC"],
                "H1_dev_pct": dev(h12["GC"], E2["H1_GC"][0]),
                "H2_VC": h12["VC"],
                "H2_dev_pct": dev(h12["VC"], E2["H2_VC"][0]),
                "H3_m": h3["m_sys"],
                "H3_m_dev_pct": dev(h3["m_sys"], E2["H3_m"][0]),
                "H3_V_L": h3["V_sys"] * 1e3,
                "H3_V_dev_pct": dev(h3["V_sys"] * 1e3, E2["H3_V_L"][0]),
            },
        }
        if variant != "frozen":
            rec["factors"]["c_bop_mass_clamped"] = c_m_clamped
            rec["factors"]["c_bop_vol_clamped"] = c_v_clamped
        verdicts = {
            k: ("PASS" if abs(rec["E2"][k.split("_")[0] + "_"
                              + ("GC" if "GC" in k else
                                 "VC" if "VC" in k else
                                 "m" if k == "H3_m" else "V_L")]
                          / E2[k][0] - 1.0) <= E2[k][1] else "FAIL")
            for k in E2
        }
        rec["E2"]["verdicts"] = verdicts
        rec["E2"]["gate"] = ("PASS" if all(v == "PASS"
                                           for v in verdicts.values())
                             else "FAIL")
        return rec
    finally:
        eng.bop_mass_volume = orig


def main():
    out = {"note": __doc__, "variants": {}}
    for variant in ("frozen", "corrected", "fixed"):
        rec = run_variant(variant)
        out["variants"][variant] = rec
        f = rec["factors"]
        print(f"-- {variant}: c_bop_mass {f['c_bop_mass']:.4f}, "
              f"c_bop_vol {f['c_bop_vol']:.4f}")
        print(f"   E1 m {rec['E1']['m_sys']:.2f} ({rec['E1']['m_dev_pct']:+.2f}%)"
              f"  V {rec['E1']['V_sys_L']:.2f} ({rec['E1']['V_dev_pct']:+.2f}%)")
        e2 = rec["E2"]
        print(f"   H1 GC {e2['H1_GC']:.5f} ({e2['H1_dev_pct']:+.2f}%)"
              f" | H2 VC {e2['H2_VC']:.5f} ({e2['H2_dev_pct']:+.2f}%)"
              f" | H3 m {e2['H3_m']:.1f} ({e2['H3_m_dev_pct']:+.2f}%)"
              f" | H3 V {e2['H3_V_L']:.1f} ({e2['H3_V_dev_pct']:+.2f}%)"
              f" => gate {e2['gate']}")
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
