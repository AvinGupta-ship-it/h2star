"""Supplementary reported metrics (referee round-1, M3): every metric the
documentation asserts is 'computed and reported' now IS, in one committed
record.

Sections of data/analysis/supplementary_metrics_v1.json:

* use_metrics — per reference system (E1 HexCell; E2 H1/H2 200-bar type-3;
  E2 H3 60-bar type-1):
  - heater energy per full discharge (A-USE-1, pre-registration section 3):
    first-order sum of (i) desorption heat, m_sorb * dn_abs * q_st with q_st
    from the committed isotherm via heats.isosteric_heat at mid-loading and
    mid-temperature; (ii) sensible heating of the average resident H2
    inventory at mid-state cv; (iii) sensible heating of the sorbent over the
    swing, with cp carried as a DECLARED RANGE 0.2-1.0 J/g/K: the only
    verified cp anchor held is Ming et al., Micropor. Mesopor. Mater. 185
    (2014) 235-244 (DOI 10.1016/j.micromeso.2013.11.015), MOF-5 powder cp =
    0.72 J/g/K at 300 K, measured 220-370 K only, so no verified cryogenic
    value exists for either sorbent and the range is reported, not a point.
  - dormancy LOWER BOUND (A-USE-3): void-gas-only isochoric time from the
    full state to the vent pressure 1.25 P_full at the system's heat-leak
    budget; adsorption and sorbent heat capacity are neglected, both of which
    lengthen real dormancy, so the bound is conservative in the safe
    direction and is labelled as such.
  - delivery-warming duty (A-USE-2): mdot * (h(233.15 K) - h(T_empty)) at the
    empty pressure, with mdot = 0.02 (g/s)/kW x 80 kW = 1.6 g/s (DOE targets
    table full-flow rate; usdrive2017). This duty is met by fuel-cell waste
    heat per the reference designs; the BOP block carries its hardware.
* dome_angle_sensitivity — composite dome mass and system GC for the 200-bar
  type-3 system at helical angles 8/12/25 deg (promised with the E1 record in
  data/engineering_v1.yaml; the cylinder total is angle-independent exactly).
* para_hydrogen_contrast — para- vs normal-H2 density at the four envelope
  states (A-ISO-3/A-EOS-1).
* mof5_2012_crosscheck — pre-registration section 4 secondary, non-binding
  check: frozen model, FEDSM Table 2 powder MOF-5, 60 bar/40 K -> 5 bar/110 K
  (slide midpoint), 5.6 kg usable, against DOE AMR 2012 ST044 slide 12:
  'Powder MOF-5 (Aluminum Tank) 87.3 kg 182.7 L' (type-1) and 'Powder MOF-5
  (Composite Tank) 74.6 kg 180.6 L' (type-3), read 2026-11-03.
"""

import functools
import json
import math
import os
import sys
from dataclasses import replace

from CoolProp.CoolProp import PropsSI

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from h2star import engineering as eng  # noqa: E402
from h2star import eos, heats, isotherm  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "analysis", "supplementary_metrics_v1.json")

eos.density = functools.lru_cache(maxsize=4096)(eos.density)

CP_SORBENT_RANGE = (200.0, 1000.0)  # J/(kg K); declared range, see docstring
WARM_T_OUT = 233.15                 # K (-40 C delivery floor)
MDOT_FULL_FLOW = 1.6e-3             # kg/s = 0.02 (g/s)/kW x 80 kW


def system_case(name, mat_file, vtype, Pf, Tf, Pe, Te):
    p = eng.EngineeringParamsV1.from_yaml(
        os.path.join(ROOT, "data", "engineering_v1.yaml"))
    mat = isotherm.Material.from_yaml(
        os.path.join(ROOT, "data", "materials", mat_file))
    iso = isotherm.ModifiedDA(mat)
    d = eng.SystemDesignV1(mat, iso, p, vtype, Pf, Tf, Pe, Te)
    b = eng.evaluate_sized(d)
    m_sorb = b["m_sorbent"]
    V_bed = b["V_bed"]

    # --- heater energy per discharge (A-USE-1) --------------------------
    dn_abs = float(iso.n_absolute(Pf, Tf) - iso.n_absolute(Pe, Te))  # mol/kg
    n_mid = float(0.5 * (iso.n_absolute(Pf, Tf) + iso.n_absolute(Pe, Te)))
    T_mid = 0.5 * (Tf + Te)
    q_st = float(heats.isosteric_heat(iso, n_mid, T_mid))  # J/mol
    E_des = m_sorb * dn_abs * q_st
    m_h2_avg = b["m_h2_full"] - 0.5 * b["m_usable"]
    cv_mid = PropsSI("CVMASS", "P", 0.5 * (Pf + Pe), "T", T_mid, "Hydrogen")
    E_h2 = m_h2_avg * cv_mid * (Te - Tf)
    E_sorb = [m_sorb * cp * (Te - Tf) for cp in CP_SORBENT_RANGE]
    E_tot = [E_des + E_h2 + e for e in E_sorb]

    # --- dormancy lower bound (A-USE-3) ---------------------------------
    rho_pack = mat.rho_bulk
    void = 1.0 - rho_pack / mat.rho_skel - rho_pack * mat.v_a
    V_void = V_bed * void
    rho_g = eos.density(Pf, Tf)
    m_void = rho_g * V_void
    P_vent = p.vent_ratio * Pf
    T_vent = PropsSI("T", "D", rho_g, "P", P_vent, "Hydrogen")
    du = (PropsSI("U", "D", rho_g, "T", T_vent, "Hydrogen")
          - PropsSI("U", "D", rho_g, "T", Tf, "Hydrogen"))
    Q = b["Q_implied_W"] if vtype == "type1" else p.mli_Q_type3
    t_dorm_s = m_void * du / Q

    # --- delivery-warming duty (A-USE-2) --------------------------------
    duty = MDOT_FULL_FLOW * (
        PropsSI("H", "P", Pe, "T", WARM_T_OUT, "Hydrogen")
        - PropsSI("H", "P", Pe, "T", Te, "Hydrogen"))

    return {
        "system": name, "vessel": vtype,
        "envelope_Pa_K": [Pf, Tf, Pe, Te],
        "heater_energy_per_discharge_MJ": {
            "desorption_term": E_des / 1e6,
            "h2_sensible_term": E_h2 / 1e6,
            "sorbent_sensible_term_range": [e / 1e6 for e in E_sorb],
            "total_range": [e / 1e6 for e in E_tot],
            "total_range_kWh": [e / 3.6e6 for e in E_tot],
            "q_st_J_per_mol_at_mid": q_st,
            "dn_abs_mol_per_kg": dn_abs,
        },
        "dormancy_lower_bound_days": t_dorm_s / 86400.0,
        "dormancy_note": "void-gas-only isochore to 1.25*P_full at "
                         f"Q = {Q:.2f} W; adsorption buffering and sorbent "
                         "heat capacity neglected (both lengthen it)",
        "delivery_warming_duty_W_at_full_flow": duty,
    }


def main():
    out = {"note": __doc__}

    out["use_metrics"] = [
        system_case("E1 HexCell MOF-5", "mof5_hsecoe.yaml", "type1",
                    100e5, 80.0, 5e5, 140.0),
        system_case("E2 H1/H2 AX-21 200 bar", "ax21.yaml", "type3",
                    200e5, 80.0, 5e5, 160.0),
        system_case("E2 H3 AX-21 60 bar", "ax21.yaml", "type1",
                    60e5, 40.0, 5e5, 110.0),
    ]

    # --- dome-angle sensitivity (type-3, 200 bar system) -----------------
    p = eng.EngineeringParamsV1.from_yaml(
        os.path.join(ROOT, "data", "engineering_v1.yaml"))
    mat = isotherm.Material.from_yaml(
        os.path.join(ROOT, "data", "materials", "ax21.yaml"))
    rows = []
    for deg in (8.0, 12.0, 25.0):
        p_a = replace(p, t3_helical_angle=math.radians(deg))
        b = eng.evaluate_sized(eng.SystemDesignV1(
            mat, isotherm.ModifiedDA(mat), p_a, "type3",
            200e5, 80.0, 5e5, 160.0))
        rows.append({"helical_angle_deg": deg, "m_wall_kg": b["m_wall"],
                     "m_sys_kg": b["m_sys"], "GC": b["GC"]})
    out["dome_angle_sensitivity"] = {
        "note": "cylinder composite total is angle-independent exactly; the "
                "angle sets the dome (helical-ply) thickness. Promised with "
                "the E1 record in data/engineering_v1.yaml.",
        "rows": rows,
    }

    # --- para-hydrogen contrast ------------------------------------------
    states = [(100e5, 80.0), (5e5, 80.0), (100e5, 160.0), (5e5, 160.0),
              (200e5, 80.0), (60e5, 40.0), (5e5, 110.0), (5e5, 140.0)]
    rows = []
    for P, T in states:
        n = PropsSI("D", "P", P, "T", T, "Hydrogen")
        pa = PropsSI("D", "P", P, "T", T, "ParaHydrogen")
        rows.append({"P_Pa": P, "T_K": T, "rho_normal": n, "rho_para": pa,
                     "ratio_minus_1": pa / n - 1.0})
    out["para_hydrogen_contrast"] = {
        "note": "para- vs normal-H2 density at the reference states "
                "(A-ISO-3/A-EOS-1); max |ratio-1| printed below.",
        "rows": rows,
        "max_abs_ratio_minus_1": max(abs(r["ratio_minus_1"]) for r in rows),
    }

    # --- MOF-5 ST044-2012 slide-12 cross-check (pre-reg section 4) --------
    mof5 = isotherm.Material.from_yaml(
        os.path.join(ROOT, "data", "materials", "mof5_hsecoe.yaml"))
    xrows = []
    for vtype, m_t, v_t, label in (
            ("type1", 87.3, 182.7, "Powder MOF-5 (Aluminum Tank)"),
            ("type3", 74.6, 180.6, "Powder MOF-5 (Composite Tank)")):
        b = eng.evaluate_sized(eng.SystemDesignV1(
            mof5, isotherm.ModifiedDA(mof5), p, vtype,
            60e5, 40.0, 5e5, 110.0))
        xrows.append({
            "slide_row": label, "vessel": vtype,
            "target_m_kg": m_t, "target_V_L": v_t,
            "model_m_kg": b["m_sys"], "model_V_L": b["V_sys"] * 1e3,
            "m_dev_pct": 100.0 * (b["m_sys"] / m_t - 1.0),
            "V_dev_pct": 100.0 * (b["V_sys"] * 1e3 / v_t - 1.0),
        })
    out["mof5_2012_crosscheck"] = {
        "note": "Secondary, NON-BINDING family check (pre-registration "
                "section 4): frozen model, FEDSM Table 2 powder MOF-5, "
                "60 bar/40 K -> 5 bar/110 K (slide-12 empty midpoint), "
                "5.6 kg usable, vs DOE AMR 2012 ST044 slide 12 (read "
                "2026-11-03). The slide's flow-through design differs from "
                "the HexCell-family internals the model is calibrated to; "
                "deviations are reported, not adjudicated.",
        "rows": xrows,
    }

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)

    for c in out["use_metrics"]:
        h = c["heater_energy_per_discharge_MJ"]
        print(f"{c['system']}: heater {h['total_range_kWh'][0]:.2f}-"
              f"{h['total_range_kWh'][1]:.2f} kWh/discharge "
              f"(des {h['desorption_term']:.2f} MJ, H2 "
              f"{h['h2_sensible_term']:.2f} MJ); dormancy lower bound "
              f"{c['dormancy_lower_bound_days']:.2f} d; warming duty "
              f"{c['delivery_warming_duty_W_at_full_flow']:.0f} W")
    for r in out["dome_angle_sensitivity"]["rows"]:
        print(f"dome angle {r['helical_angle_deg']:.0f} deg: m_wall "
              f"{r['m_wall_kg']:.2f} kg, GC {r['GC']:.5f}")
    print("para-H2 max |ratio-1|:",
          f"{out['para_hydrogen_contrast']['max_abs_ratio_minus_1']:.2e}")
    for r in out["mof5_2012_crosscheck"]["rows"]:
        print(f"MOF-5 2012 {r['vessel']}: m {r['model_m_kg']:.1f} vs "
              f"{r['target_m_kg']} ({r['m_dev_pct']:+.1f}%), V "
              f"{r['model_V_L']:.1f} vs {r['target_V_L']} "
              f"({r['V_dev_pct']:+.1f}%)")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
