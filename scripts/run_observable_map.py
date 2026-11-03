"""S6 requirement map in identifiable observables (pre-reg sections 4/7, D4).

Axes (referee round-1 M1 fix — EXCESS basis): DELIVERABLE EXCESS UPTAKE
between the full and empty states (kg H2 per kg sorbent, Gibbs-excess swing —
the quantity a sorption laboratory reports directly) and PACKING DENSITY
(kg/m^3). On this basis the adsorbed-phase volume v_a drops out of the map
algebraically: per m^3 of bed,

    deliverable = rho * dn_abs * M + (1 - rho/rho_skel - rho*v_a) * drho_g
                = rho * dn_exc * M + (1 - rho/rho_skel) * drho_g,

so the bed-level inventory needs only the measured excess swing, the packing
density, the skeletal density and the EOS — no isotherm-model inversion. The
earlier draft of this map used the absolute-adsorption swing as the axis,
which is NOT laboratory-observable without the fitted v_a (at this envelope
v_a*drho_g = 0.034 kg/kg, 47% of AX-21's own coordinate); that version is
superseded by this one, and the system totals are identical by the identity
above.

Remaining non-axis inputs, each varied as a labelled, reported sensitivity
(NOT sampled on the map — the frozen conditionality rule: no probability band
is drawn):
* rho_skel: 2300 baseline (AX-21 class), varied over 1800-2300 (carbon
  skeletal-density class range);
* u_res: residual EXCESS uptake carried at the empty state (also an
  observable), baseline 0, varied over {0.006 (AX-21's own posterior-median
  residual), 0.02} kg/kg.

Because gate E2 FAILED, the DOE target contours on this map carry the fork-
rule caption: the absolute placement of the feasibility boundary inherits the
engineering model's demonstrated tens-of-percent class uncertainty; the map's
claims are the observable AXES and the relative geometry, with the boundary
shown under BOTH the v1.0 model and the v0.2 lumped model. The two models are
structurally different but share several source anchors (MLI properties, the
BOP anchor, the fiber class), so the two-model shift is a LOWER BOUND on
engineering-model dependence, as disclosed in docs/known_limitations.md.

Output: data/analysis/observable_map_v1.json (grids for F5).
"""

import functools
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dataclasses import replace  # noqa: E402

from h2star import engineering as eng  # noqa: E402
from h2star import eos, isotherm, system, vessel  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "analysis", "observable_map_v1.json")

eos.density = functools.lru_cache(maxsize=4096)(eos.density)

P_FULL, T_FULL, P_EMPTY, T_EMPTY = 100e5, 80.0, 5e5, 160.0
M_H2 = 2.016e-3
TARGETS = {"2020": (0.045, 0.030), "2025": (0.055, 0.040),
           "Ultimate": (0.065, 0.050)}

U_GRID = np.linspace(0.005, 0.20, 40)        # deliverable EXCESS uptake kg/kg
RHO_GRID = np.linspace(100.0, 900.0, 41)     # packing density, kg/m^3
RHO_SKEL = 2300.0                            # AX-21 class skeletal density
U_RES = 0.0                                  # residual excess uptake baseline


def gas_swing_per_bed_volume(rho_pack, rho_skel=RHO_SKEL):
    """Gas swing (kg H2 per m^3 of bed) between the full and empty states in
    the TOTAL void (1 - rho/rho_skel): on the excess basis the adsorbed-phase
    volume belongs to the excess bookkeeping, not the void term."""
    void = 1.0 - rho_pack / rho_skel
    if void <= 0:
        return np.nan
    return void * (eos.density(P_FULL, T_FULL)
                   - eos.density(P_EMPTY, T_EMPTY))


class V1System:
    """System capacities from (u_exc, rho_pack) under the frozen v1.0 model."""

    def __init__(self, rho_skel=RHO_SKEL, u_res=U_RES):
        self.p = eng.EngineeringParamsV1.from_yaml(
            os.path.join(ROOT, "data", "engineering_v1.yaml"))
        self.rho_skel = rho_skel
        self.u_res = u_res

    def __call__(self, u_d, rho_pack):
        g = gas_swing_per_bed_volume(rho_pack, self.rho_skel)
        if not np.isfinite(g):
            return np.nan, np.nan
        usable_per_bed = u_d * rho_pack + g  # kg usable per m^3 bed
        if usable_per_bed <= 0:
            return np.nan, np.nan
        V_bed = 5.6 / usable_per_bed
        p = self.p
        V_int = V_bed / (1.0 - p.hx_vol_fraction)
        # Full-state inventory = usable + empty-state residual. On the excess
        # basis the residual is rho*u_res (residual excess uptake, an
        # observable, varied as a labelled sensitivity) plus the empty void
        # gas on the total void.
        m_h2_full = (5.6 + rho_pack * self.u_res * V_bed
                     + eos.density(P_EMPTY, T_EMPTY) * V_bed
                     * (1.0 - rho_pack / self.rho_skel))
        m_sorb = rho_pack * V_bed
        m_hx = p.c_hx * (V_int - V_bed) * p.hx_density
        r = eng.capsule_radius(V_int, p.t3_LR)
        L_cyl = p.t3_LR * r
        A_cyl = eng.capsule_area_cyl(r, p.t3_LR)
        A_caps = eng.capsule_area_caps(r)
        P_design = p.vent_ratio * P_FULL
        t_h, t_th = eng.type3_netting(P_design, P_FULL, r, p)
        m_comp = (A_cyl * (t_h + t_th) + A_caps * t_h) * p.t3_composite_density
        m_lin = (A_cyl + A_caps) * p.t3_liner_thickness * p.t3_liner_density
        r1 = r + t_h + t_th + p.t3_liner_thickness
        A1 = 2 * np.pi * r1 * L_cyl + 4 * np.pi * r1**2
        dT = p.T_env - T_FULL
        t_mli = p.mli_k_eff * A1 * dT / p.mli_Q_type3
        m_mli = A1 * t_mli * p.mli_density
        r2 = r1 + t_mli
        A2 = 2 * np.pi * r2 * L_cyl + 4 * np.pi * r2**2
        m_shell = A2 * p.shell_t_type3 * p.shell_density
        r_out = r2 + p.shell_t_type3
        m_bop, V_bop = eng.bop_mass_volume(P_design, p)
        m_sys = (m_h2_full + m_sorb + m_hx + m_comp + m_lin + m_mli
                 + m_shell + p.supports_mass + m_bop)
        V_sys = eng.capsule_outer_volume(r_out, L_cyl) + V_bop
        return 5.6 / m_sys, 5.6 / (V_sys * 1e3)


class V02System:
    """Same axes under the superseded v0.2 lumped model (two-model check)."""

    def __init__(self, rho_skel=RHO_SKEL, u_res=U_RES):
        self.p = system.EngineeringParams.from_yaml(
            os.path.join(ROOT, "data", "engineering.yaml"))
        self.rho_skel = rho_skel
        self.u_res = u_res

    def __call__(self, u_d, rho_pack):
        g = gas_swing_per_bed_volume(rho_pack, self.rho_skel)
        if not np.isfinite(g):
            return np.nan, np.nan
        usable_per_bed = u_d * rho_pack + g
        if usable_per_bed <= 0:
            return np.nan, np.nan
        V_int = 5.6 / usable_per_bed
        p = self.p
        m_h2_full = (5.6 + rho_pack * self.u_res * V_int
                     + eos.density(P_EMPTY, T_EMPTY) * V_int
                     * (1.0 - rho_pack / self.rho_skel))
        m_sorb = rho_pack * V_int
        m_vessel = vessel.vessel_mass_hoop(P_FULL, V_int, p.vessel)
        LR = p.vessel.aspect_ratio_LR
        r = vessel.radius_from_volume(V_int, LR)
        A = vessel.surface_area(r, LR)
        t_wall = vessel.wall_thickness(
            P_FULL, r, p.vessel.safety_factor, p.vessel.sigma_allow)
        t_ins = p.mli_k_eff * A * (p.T_env - T_FULL) / p.heat_leak_budget
        m_ins = A * t_ins * p.mli_density
        m_bop = p.bop_fixed
        m_sys = m_h2_full + m_sorb + m_vessel + m_ins + m_bop
        V_sys = V_int + A * t_wall + A * t_ins
        return 5.6 / m_sys, 5.6 / (V_sys * 1e3)


def u_required(mod, u_grid=U_GRID):
    """Minimum deliverable excess uptake meeting both 2025 targets, per rho."""
    req = []
    for rho in RHO_GRID:
        ok = [u for u in u_grid
              if np.isfinite(mod(u, rho)[0]) and mod(u, rho)[0] >= 0.055
              and mod(u, rho)[1] >= 0.040]
        req.append(min(ok) if ok else None)
    return req


def main():
    models = {"v1_component": V1System(), "v02_lumped": V02System()}
    out = {"u_grid": U_GRID.tolist(), "rho_grid": RHO_GRID.tolist(),
           "basis": "deliverable Gibbs-EXCESS uptake between the stated "
                    "full and empty states (M1 fix; v_a-free by identity)",
           "envelope": [P_FULL, T_FULL, P_EMPTY, T_EMPTY],
           "targets": TARGETS, "models": {}}
    i500 = RHO_GRID.tolist().index(500.0)
    for name, mod in models.items():
        GC = np.full((U_GRID.size, RHO_GRID.size), np.nan)
        VC = np.full_like(GC, np.nan)
        for i, u in enumerate(U_GRID):
            for j, rho in enumerate(RHO_GRID):
                GC[i, j], VC[i, j] = mod(u, rho)
        out["models"][name] = {"GC": GC.tolist(), "VC": VC.tolist()}
        req = u_required(mod)
        out["models"][name]["u_required_2025"] = req
        print(name, "min required deliverable excess uptake at rho=500:",
              req[i500])

    # Labelled sensitivities promised with the map (M1): rho_skel class range
    # and the residual-uptake carried-mass term, reported at rho = 500.
    sens = {}
    fine = np.linspace(0.005, 0.20, 391)  # 0.0005 step resolves the shifts
    for rho_skel in (1800.0, 2300.0):
        for u_res in (0.0, 0.006, 0.02):
            key = f"rho_skel={rho_skel:.0f},u_res={u_res:.3f}"
            r = u_required(V1System(rho_skel=rho_skel, u_res=u_res),
                           u_grid=fine)[i500]
            sens[key] = r
            print("sens", key, "-> u_required(rho=500) =", r)
    out["u_required_2025_sensitivity_rho500"] = {
        "note": "v1 model, 0.0005 u-grid; rho_skel over the carbon class "
                "range and residual excess uptake u_res at the empty state "
                "(0.006 = AX-21's own posterior-median residual). u_res has "
                "no effect at rho=500 because the 2025 boundary there is "
                "VOLUMETRIC-limited in the v1 model (VC binds at 0.040 while "
                "GC has slack), and the residual term adds carried mass "
                "only.",
        "values": sens,
    }

    # AX-21 reference point on these axes (posterior-median parameters used
    # only to EVALUATE the observable at the stated states; a laboratory
    # would measure both excess values directly).
    mat = isotherm.Material.from_yaml(
        os.path.join(ROOT, "data", "materials", "ax21.yaml"))
    # Medians of the committed (seeded, bit-reproducible) posterior chain.
    mat = replace(mat, n_max=61.9031, alpha=3561.59, beta=16.6088,
                  p0=10 ** 9.15063, v_a=1.1563e-3)
    iso = isotherm.ModifiedDA(mat)
    du_exc = (iso.n_excess(P_FULL, T_FULL)
              - iso.n_excess(P_EMPTY, T_EMPTY)) * M_H2
    du_abs = (iso.n_absolute(P_FULL, T_FULL)
              - iso.n_absolute(P_EMPTY, T_EMPTY)) * M_H2
    u_res_ax21 = iso.n_excess(P_EMPTY, T_EMPTY) * M_H2
    out["ax21_point"] = {
        "deliverable_uptake_excess_swing": float(du_exc),
        "residual_excess_at_empty": float(u_res_ax21),
        "deliverable_uptake_abs_swing_reference_only": float(du_abs),
        "rho_pack": 300.0,
    }
    print("AX-21 point: u_exc = %.4f kg/kg (abs-basis reference %.4f) "
          "at rho 300" % (du_exc, du_abs))
    with open(OUT, "w") as fh:
        json.dump(out, fh)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
