"""S6 requirement map in identifiable observables (pre-reg sections 4/7, D4).

Axes: DELIVERABLE MATERIAL-LEVEL UPTAKE between the full and empty states
(kg H2 per kg sorbent, absolute-adsorption swing plus intra-bed gas swing per
kg of sorbent at the stated packing density) and PACKING DENSITY (kg/m^3).
These are measurable without inverting the isotherm model: a lab measures the
uptake swing between 100 bar/80 K and 5 bar/160 K directly.

For each (deliverable uptake u_d, packing density rho_pack) node, the system
capacities follow from the frozen v1.0 engineering model without any isotherm
evaluation: sizing V_bed = 5.6 / (u_d * rho_pack + g_swing(rho_pack)), where
g_swing is the inter/intra-particle gas swing per unit bed volume, computed
from the envelope densities and the void fraction 1 - rho_pack/rho_skel minus
the adsorbed-phase volume (v_a and rho_skel enter only the small gas-swing
correction and are varied across their posterior range as a reported
sensitivity, not sampled on the map — the frozen conditionality rule: no
probability band is drawn on this map).

Because gate E2 FAILED, the DOE target contours on this map carry the fork-
rule caption: the absolute placement of the feasibility boundary inherits the
engineering model's demonstrated tens-of-percent class uncertainty; the map's
claims are the observable AXES and the relative geometry, with the boundary
shown under BOTH the v1.0 model and the v0.2 lumped model as the two-model
robustness demonstration (M2).

Output: data/analysis/observable_map_v1.json (grids for F6-v1).
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

U_GRID = np.linspace(0.005, 0.20, 40)        # deliverable uptake, kg/kg
RHO_GRID = np.linspace(100.0, 900.0, 41)     # packing density, kg/m^3
RHO_SKEL = 2300.0                            # AX-21 class skeletal density
V_A = 1.1563e-3                              # posterior median, for gas swing


def gas_swing_per_bed_volume(rho_pack, v_a=V_A, rho_skel=RHO_SKEL):
    """Gas swing (kg H2 per m^3 of bed) between full and empty states in the
    void volume: (1 - rho/rho_skel - rho*v_a) * (rho_g_full - rho_g_empty)."""
    void = 1.0 - rho_pack / rho_skel - rho_pack * v_a
    if void <= 0:
        return np.nan
    return void * (eos.density(P_FULL, T_FULL)
                   - eos.density(P_EMPTY, T_EMPTY))


class V1System:
    """System capacities from (u_d, rho_pack) under the frozen v1.0 model."""

    def __init__(self):
        self.p = eng.EngineeringParamsV1.from_yaml(
            os.path.join(ROOT, "data", "engineering_v1.yaml"))

    def __call__(self, u_d, rho_pack):
        g = gas_swing_per_bed_volume(rho_pack)
        if not np.isfinite(g):
            return np.nan, np.nan
        usable_per_bed = u_d * rho_pack + g  # kg usable per m^3 bed
        if usable_per_bed <= 0:
            return np.nan, np.nan
        V_bed = 5.6 / usable_per_bed
        p = self.p
        V_int = V_bed / (1.0 - p.hx_vol_fraction)
        # full-state inventory: usable + empty-state residual; the residual
        # gas+adsorbed at empty is approximated by the empty void gas plus
        # a residual-uptake term u_res; on these axes u_res is not observable
        # separately, so the carried-mass term uses the void gas only and the
        # residual adsorbed mass enters the +/- band reported with the map.
        m_h2_full = 5.6 + eos.density(P_EMPTY, T_EMPTY) * (
            V_bed * (1.0 - rho_pack / RHO_SKEL - rho_pack * V_A))
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

    def __init__(self):
        self.p = system.EngineeringParams.from_yaml(
            os.path.join(ROOT, "data", "engineering.yaml"))

    def __call__(self, u_d, rho_pack):
        g = gas_swing_per_bed_volume(rho_pack)
        if not np.isfinite(g):
            return np.nan, np.nan
        usable_per_bed = u_d * rho_pack + g
        if usable_per_bed <= 0:
            return np.nan, np.nan
        V_int = 5.6 / usable_per_bed
        p = self.p
        m_h2_full = 5.6 + eos.density(P_EMPTY, T_EMPTY) * (
            V_int * (1.0 - rho_pack / RHO_SKEL - rho_pack * V_A))
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


def main():
    models = {"v1_component": V1System(), "v02_lumped": V02System()}
    out = {"u_grid": U_GRID.tolist(), "rho_grid": RHO_GRID.tolist(),
           "envelope": [P_FULL, T_FULL, P_EMPTY, T_EMPTY],
           "targets": TARGETS, "models": {}}
    for name, mod in models.items():
        GC = np.full((U_GRID.size, RHO_GRID.size), np.nan)
        VC = np.full_like(GC, np.nan)
        for i, u in enumerate(U_GRID):
            for j, rho in enumerate(RHO_GRID):
                GC[i, j], VC[i, j] = mod(u, rho)
        out["models"][name] = {"GC": GC.tolist(), "VC": VC.tolist()}
        # feasibility threshold summary: minimum deliverable uptake meeting
        # both 2025 targets at each packing density
        req = []
        for j, rho in enumerate(RHO_GRID):
            ok = [u for i, u in enumerate(U_GRID)
                  if np.isfinite(GC[i, j]) and GC[i, j] >= 0.055
                  and VC[i, j] >= 0.040]
            req.append(min(ok) if ok else None)
        out["models"][name]["u_required_2025"] = req
        print(name, "min required deliverable uptake at rho=500:",
              req[RHO_GRID.tolist().index(500.0)])
    # AX-21 reference point on these axes (posterior median parameters)
    mat = isotherm.Material.from_yaml(
        os.path.join(ROOT, "data", "materials", "ax21.yaml"))
    # Medians of the committed (seeded, bit-reproducible) posterior chain.
    mat = replace(mat, n_max=61.9031, alpha=3561.59, beta=16.6088,
                  p0=10 ** 9.15063, v_a=1.1563e-3)
    iso = isotherm.ModifiedDA(mat)
    du = (iso.n_absolute(P_FULL, T_FULL)
          - iso.n_absolute(P_EMPTY, T_EMPTY)) * M_H2
    out["ax21_point"] = {"deliverable_uptake_abs_swing": float(du),
                         "rho_pack": 300.0}
    print("AX-21 point: u_d = %.4f kg/kg at rho 300" % du)
    with open(OUT, "w") as fh:
        json.dump(out, fh)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
