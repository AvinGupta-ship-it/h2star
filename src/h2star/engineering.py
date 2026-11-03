"""Component-resolved system mass and volume model (v1.0 engineering block).

Replaces the v0.2 lumped engineering model (``h2star.vessel`` +
``h2star.system``), which the 2026-10-27 adversarial review found incomplete
(M1: missing vacuum shell, internal heat exchanger, supports, component-
resolved balance of plant with volume; hoop-only composite sizing; unscaled
liner; M10: missing usable-capacity physics). The superseded modules remain in
the tree as the documented v0.2 record; nothing here edits them.

Everything this module implements is specified, with sources, in
``data/engineering_v1.yaml`` and frozen in ``docs/preregistration_v1.0.md``
(DOI 10.5281/zenodo.23931242, section 3 as amended A1). The three calibration
factors (``c_bop_mass``, ``c_bop_vol``, ``c_hx``) are the only fitted values;
they are fitted once at calibration E1 and then frozen for the held-out gate
E2.

Vessel classes
--------------
``type1``
    All-metal aluminium vessel (HSECoE HexCell/MATI family): hoop-sized wall
    at a back-derived design stress, LN2 wall-chilling channel, MLVI at the
    design-fixed thickness, 2 mm aluminium outer shell.
``type3``
    Aluminium-lined carbon-fibre overwrap (HSECoE Phase-1-baseline family):
    netting analysis — helical plies carry the axial load, hoop plies the
    remainder, total cylinder composite ``t = 1.5 P r / sigma`` (exact,
    angle-independent); domes carry the helical plies; fixed 2.4 mm Al 2024
    liner; MLVI sized to a heat-leak budget; 3 mm Al 2024 vacuum shell.

Both classes: internal heat-exchanger/heater structure as an aluminium volume
fraction of the bed, constant boss/plug/support mass, and a component-class
balance of plant with mass AND volume interpolated between two published
anchors in design pressure.

Design pressure: ``P_design = vent_ratio * P_full`` (dormancy-set, 1.25); the
sources state their safety factors against the full/operating pressure, so
``SF_eff = SF_source / vent_ratio`` is applied to ``P_design`` — numerically
identical to each source's practice.

Capacities are USABLE-basis: ``GC = m_usable / m_sys`` and
``VC = m_usable / V_sys`` (kg per litre), with the full inventory carried in
``m_sys`` (residual hydrogen is still carried mass).

All quantities SI unless noted; VC is reported in kg/L by convention.
"""

import math
from dataclasses import dataclass, replace

import yaml
from scipy.optimize import brentq

from . import tank
from .constants import DEFAULT_TARGET_USABLE_KG


def _val(block, key):
    """Return ``block[key]['value']`` as float (YAML {value, unit} entry)."""
    return float(block[key]["value"])


@dataclass(frozen=True)
class EngineeringParamsV1:
    """Immutable component-resolved engineering parameters (SI).

    Loaded from ``data/engineering_v1.yaml``; every attribute's provenance is
    the corresponding ``*_source`` field in that file.
    """

    # Design-pressure rule
    vent_ratio: float  # P_design / P_full (dormancy-set), dimensionless

    # Type-1 (all-metal Al) vessel
    t1_sigma_design: float  # Pa
    t1_safety_factor: float  # dimensionless (stated against P_full)
    t1_wall_density: float  # kg/m^3
    t1_LR: float  # L_cyl / r
    t1_ln2_thickness: float  # m
    t1_ln2_areal_mass: float  # kg/m^2

    # Type-3 (Al-lined CF overwrap) vessel
    t3_fiber_strength: float  # Pa
    t3_quality: float  # dimensionless
    t3_trans_350: float  # translation efficiency at 350 bar
    t3_trans_700: float  # translation efficiency at 700 bar
    t3_trans_cap: float  # extrapolation cap
    t3_safety_factor: float  # dimensionless (stated against P_full)
    t3_composite_density: float  # kg/m^3
    t3_helical_angle: float  # radians
    t3_liner_thickness: float  # m
    t3_liner_density: float  # kg/m^3
    t3_LR: float  # L_cyl / r
    t3_performance_factor: float  # Pa*m^3/kg, cross-check only

    # Outer (vacuum/impact) shell
    shell_t_type1: float  # m
    shell_t_type3: float  # m
    shell_density: float  # kg/m^3

    # MLVI
    mli_k_eff: float  # W/(m*K)
    mli_density: float  # kg/m^3
    mli_t_type1: float  # m (design-fixed for the type-1 family)
    mli_Q_type3: float  # W (sizing budget for the type-3 family)
    T_env: float  # K (worst-case ambient)

    # Internal HX / heater structure
    hx_vol_fraction: float  # aluminium volume fraction of the bed
    hx_density: float  # kg/m^3

    # Supports / bosses
    supports_mass: float  # kg

    # Balance of plant (anchors; pressure in bar for the interpolation)
    bop_m100: float  # kg at 100 bar design-class
    bop_m350: float  # kg at 350 bar design-class
    bop_v100: float  # L at 100 bar
    bop_v350: float  # L at 350 bar

    # Calibration factors (the ONLY fitted values; frozen after E1)
    c_bop_mass: float
    c_bop_vol: float
    c_hx: float

    citation: str

    @classmethod
    def from_yaml(cls, path):
        """Load the parameter set from ``data/engineering_v1.yaml``."""
        with open(path) as fh:
            data = yaml.safe_load(fh)
        name = data.get("name")
        if not name:
            raise ValueError(
                f"Engineering parameter file {path!r} is missing a non-empty "
                f"top-level 'name'; parameters must be attributable."
            )
        t1 = data["type1"]
        t3 = data["type3"]
        return cls(
            vent_ratio=_val(data["design_pressure"], "vent_ratio"),
            t1_sigma_design=_val(t1, "sigma_design"),
            t1_safety_factor=_val(t1, "safety_factor"),
            t1_wall_density=_val(t1, "wall_density"),
            t1_LR=_val(t1, "aspect_LR_cyl_over_r"),
            t1_ln2_thickness=_val(t1, "ln2_channel_thickness"),
            t1_ln2_areal_mass=_val(t1, "ln2_channel_areal_mass"),
            t3_fiber_strength=_val(t3, "fiber_strength"),
            t3_quality=_val(t3, "quality_knockdown"),
            t3_trans_350=_val(t3, "translation_at_350bar"),
            t3_trans_700=_val(t3, "translation_at_700bar"),
            t3_trans_cap=_val(t3, "translation_cap"),
            t3_safety_factor=_val(t3, "safety_factor"),
            t3_composite_density=_val(t3, "composite_density"),
            t3_helical_angle=math.radians(_val(t3, "helical_angle_deg")),
            t3_liner_thickness=_val(t3, "liner_thickness"),
            t3_liner_density=_val(t3, "liner_density"),
            t3_LR=_val(t3, "aspect_LR_cyl_over_r"),
            t3_performance_factor=_val(t3, "performance_factor"),
            shell_t_type1=_val(data["shell"], "thickness_type1"),
            shell_t_type3=_val(data["shell"], "thickness_type3"),
            shell_density=_val(data["shell"], "density"),
            mli_k_eff=_val(data["mli"], "k_eff"),
            mli_density=_val(data["mli"], "density"),
            mli_t_type1=_val(data["mli"], "thickness_type1"),
            mli_Q_type3=_val(data["mli"], "heat_leak_budget_type3"),
            T_env=_val(data["mli"], "T_env"),
            hx_vol_fraction=_val(data["internal_hx"], "al_volume_fraction"),
            hx_density=_val(data["internal_hx"], "al_density"),
            supports_mass=_val(data["supports"], "mass"),
            bop_m100=_val(data["bop"], "mass_at_100bar"),
            bop_m350=_val(data["bop"], "mass_at_350bar"),
            bop_v100=_val(data["bop"], "volume_at_100bar"),
            bop_v350=_val(data["bop"], "volume_at_350bar"),
            c_bop_mass=_val(data["calibration_factors"], "c_bop_mass"),
            c_bop_vol=_val(data["calibration_factors"], "c_bop_vol"),
            c_hx=_val(data["calibration_factors"], "c_hx"),
            citation=f"{name}; {data.get('description', '')}".strip(),
        )

    def with_factors(self, c_bop_mass=None, c_bop_vol=None, c_hx=None):
        """Return a copy with calibration factors replaced (E1 fitting)."""
        return replace(
            self,
            c_bop_mass=self.c_bop_mass if c_bop_mass is None else c_bop_mass,
            c_bop_vol=self.c_bop_vol if c_bop_vol is None else c_bop_vol,
            c_hx=self.c_hx if c_hx is None else c_hx,
        )


# --------------------------------------------------------------------------
# Geometry (capsule: cylinder of length LR*r closed by two hemispherical caps)
# --------------------------------------------------------------------------

def capsule_radius(V_internal, LR):
    """Radius (m) of a capsule of internal volume ``V_internal`` (m^3)."""
    if V_internal <= 0.0 or LR <= 0.0:
        raise ValueError(
            f"V_internal and LR must be strictly positive; got "
            f"{V_internal} m^3, {LR}."
        )
    return (V_internal / (math.pi * (LR + 4.0 / 3.0))) ** (1.0 / 3.0)


def capsule_area_cyl(r, LR):
    """Cylindrical-section lateral area (m^2)."""
    return 2.0 * math.pi * r * r * LR


def capsule_area_caps(r):
    """Combined area of the two hemispherical caps = one sphere (m^2)."""
    return 4.0 * math.pi * r * r


def capsule_outer_volume(r_outer, L_cyl):
    """Outer envelope volume (m^3) of a capsule with outer radius and the
    SAME cylindrical length as the inner vessel (layers add radially)."""
    return math.pi * r_outer**2 * L_cyl + (4.0 / 3.0) * math.pi * r_outer**3


# --------------------------------------------------------------------------
# Walls
# --------------------------------------------------------------------------

def type1_wall_thickness(P_design, r, params):
    """Aluminium type-1 wall thickness (m): hoop-governed thin wall.

    ``t = SF_eff * P_design * r / sigma_design`` with
    ``SF_eff = SF_source / vent_ratio`` (see module docstring). The von Mises
    stress of a closed thin-wall cylinder is ``sqrt(3)/2 ~ 0.866`` of the
    hoop stress, so hoop governs.
    """
    sf_eff = params.t1_safety_factor / params.vent_ratio
    return sf_eff * P_design * r / params.t1_sigma_design


def type3_sigma_eff(P_full, params):
    """Effective composite stress (Pa) for netting sizing at ``P_full``.

    ``sigma = fiber_strength * quality * translation(P_full)`` with the
    source's linear translation efficiency in pressure, capped at
    ``translation_cap`` (guarded extrapolation below ~215 bar).
    """
    P_bar = P_full / 1.0e5
    slope = (params.t3_trans_700 - params.t3_trans_350) / (700.0 - 350.0)
    eff = params.t3_trans_350 + slope * (P_bar - 350.0)
    eff = min(eff, params.t3_trans_cap)
    if eff <= 0.0:
        raise ValueError(
            f"Translation efficiency collapsed to {eff} at {P_bar} bar."
        )
    return params.t3_fiber_strength * params.t3_quality * eff


def type3_netting(P_design, P_full, r, params):
    """Netting-analysis composite thicknesses (m) on the cylinder.

    Returns ``(t_helical, t_hoop)``. Axial equilibrium sizes the helical
    plies, ``t_h = P r / (2 sigma cos^2 a)``; hoop equilibrium sizes the hoop
    plies, ``t_th = P r / sigma - t_h sin^2 a``. The total
    ``t_h + t_th = 1.5 P r / sigma`` exactly, independent of the angle.
    ``P`` here is ``SF_eff * P_design``.
    """
    sigma = type3_sigma_eff(P_full, params)
    sf_eff = params.t3_safety_factor / params.vent_ratio
    P = sf_eff * P_design
    a = params.t3_helical_angle
    t_h = P * r / (2.0 * sigma * math.cos(a) ** 2)
    t_th = P * r / sigma - t_h * math.sin(a) ** 2
    return t_h, t_th


# --------------------------------------------------------------------------
# Balance of plant
# --------------------------------------------------------------------------

def bop_mass_volume(P_design, params):
    """Component-class BOP mass (kg) and volume (m^3) at ``P_design``.

    Linear interpolation between the two published anchors in design
    pressure (bar), scaled by the calibration factors.
    """
    P_bar = P_design / 1.0e5
    frac = (P_bar - 100.0) / 250.0
    m = params.c_bop_mass * (
        params.bop_m100 + (params.bop_m350 - params.bop_m100) * frac
    )
    v = params.c_bop_vol * (
        params.bop_v100 + (params.bop_v350 - params.bop_v100) * frac
    )
    return m, v * 1.0e-3  # L -> m^3


# --------------------------------------------------------------------------
# System evaluation
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class SystemDesignV1:
    """A storage system minus its size (v1.0 component-resolved model).

    Attributes mirror the v0.2 ``SystemDesign`` plus ``vessel_type``
    ('type1' | 'type3'). ``evaluate(V_internal)`` returns the component
    budget; ``size_for_usable`` solves the internal volume for a usable
    target.
    """

    material: object  # h2star.isotherm.Material
    isotherm: object  # h2star.isotherm.ModifiedDA
    engineering: EngineeringParamsV1
    vessel_type: str  # 'type1' | 'type3'
    P_full: float  # Pa
    T_full: float  # K
    P_empty: float  # Pa
    T_empty: float  # K

    def __post_init__(self):
        if self.vessel_type not in ("type1", "type3"):
            raise ValueError(
                f"vessel_type must be 'type1' or 'type3'; got "
                f"{self.vessel_type!r}."
            )

    @property
    def P_design(self):
        """Dormancy-set design pressure, Pa."""
        return self.engineering.vent_ratio * self.P_full

    def usable(self, V_internal):
        """Usable hydrogen (kg) with the HX structure displacing bed volume."""
        V_bed = V_internal * (1.0 - self.engineering.hx_vol_fraction)
        return tank.usable_h2(
            self.material,
            self.isotherm,
            (self.P_full, self.T_full),
            (self.P_empty, self.T_empty),
            V_bed,
        )

    def evaluate(self, V_internal):
        """Component-resolved budget at a given internal volume (m^3).

        Returns a dict of masses (kg), volumes (m^3), thicknesses (m),
        usable-basis ``GC`` (kg/kg) and ``VC`` (kg/L), plus the reported
        dormancy/energy metrics' inputs (implied heat leak).
        """
        if V_internal <= 0.0:
            raise ValueError(
                f"V_internal must be strictly positive; got {V_internal}."
            )
        p = self.engineering
        t1 = self.vessel_type == "type1"
        LR = p.t1_LR if t1 else p.t3_LR

        # --- Hydrogen and sorbent (HX displaces bed volume) ---------------
        V_hx = V_internal * p.hx_vol_fraction  # m^3 of Al structure
        V_bed = V_internal - V_hx
        m_h2_full = tank.total_h2_mass(
            self.material, self.isotherm, self.P_full, self.T_full, V_bed
        )
        m_usable = self.usable(V_internal)
        m_sorbent = self.material.rho_bulk * V_bed
        m_hx = p.c_hx * V_hx * p.hx_density

        # --- Vessel wall ----------------------------------------------------
        r = capsule_radius(V_internal, LR)
        L_cyl = LR * r
        A_cyl = capsule_area_cyl(r, LR)
        A_caps = capsule_area_caps(r)
        A_total = A_cyl + A_caps

        if t1:
            t_wall = type1_wall_thickness(self.P_design, r, p)
            m_wall = A_total * t_wall * p.t1_wall_density
            m_liner = 0.0
            t_liner = 0.0
            wall_detail = {"t_wall": t_wall}
        else:
            t_h, t_th = type3_netting(self.P_design, self.P_full, r, p)
            t_wall = t_h + t_th  # cylinder total
            # Cylinder carries helical + hoop; domes carry helical only.
            m_composite = (
                A_cyl * t_wall + A_caps * t_h
            ) * p.t3_composite_density
            t_liner = p.t3_liner_thickness
            m_liner = A_total * t_liner * p.t3_liner_density
            m_wall = m_composite + m_liner
            wall_detail = {
                "t_helical": t_h,
                "t_hoop": t_th,
                "t_wall": t_wall,
                "m_composite": m_composite,
                "m_liner": m_liner,
            }

        # --- Radial build-up (volumes of the layers) -----------------------
        r1 = r + t_wall + (t_liner if not t1 else 0.0)
        # LN2 wall-chilling channel (type-1 family only)
        if t1:
            t_ln2 = p.t1_ln2_thickness
            A_ln2 = 2.0 * math.pi * r1 * L_cyl + 4.0 * math.pi * r1**2
            m_ln2 = A_ln2 * p.t1_ln2_areal_mass
            r2 = r1 + t_ln2
        else:
            t_ln2, m_ln2 = 0.0, 0.0
            r2 = r1

        # MLVI: fixed thickness (type-1 family) or sized to the heat budget
        A_mli = 2.0 * math.pi * r2 * L_cyl + 4.0 * math.pi * r2**2
        dT = p.T_env - self.T_full
        if dT <= 0.0:
            raise ValueError(
                f"T_env ({p.T_env} K) must exceed T_full ({self.T_full} K)."
            )
        if t1:
            t_mli = p.mli_t_type1
            Q_implied = p.mli_k_eff * A_mli * dT / t_mli
        else:
            t_mli = p.mli_k_eff * A_mli * dT / p.mli_Q_type3
            Q_implied = p.mli_Q_type3
        m_mli = A_mli * t_mli * p.mli_density
        r3 = r2 + t_mli

        # Outer shell
        t_shell = p.shell_t_type1 if t1 else p.shell_t_type3
        A_shell = 2.0 * math.pi * r3 * L_cyl + 4.0 * math.pi * r3**2
        m_shell = A_shell * t_shell * p.shell_density
        r_out = r3 + t_shell

        # --- Supports and BOP ----------------------------------------------
        m_supports = p.supports_mass
        m_bop, V_bop = bop_mass_volume(self.P_design, p)

        # --- Totals ---------------------------------------------------------
        m_sys = (
            m_h2_full
            + m_sorbent
            + m_hx
            + m_wall
            + m_ln2
            + m_mli
            + m_shell
            + m_supports
            + m_bop
        )
        V_tank_outer = capsule_outer_volume(r_out, L_cyl)
        V_sys = V_tank_outer + V_bop

        out = {
            "m_h2_full": float(m_h2_full),
            "m_usable": float(m_usable),
            "m_sorbent": float(m_sorbent),
            "m_hx": float(m_hx),
            "m_wall": float(m_wall),
            "m_ln2_channel": float(m_ln2),
            "m_mli": float(m_mli),
            "m_shell": float(m_shell),
            "m_supports": float(m_supports),
            "m_bop": float(m_bop),
            "m_sys": float(m_sys),
            "V_internal": float(V_internal),
            "V_bed": float(V_bed),
            "V_tank_outer": float(V_tank_outer),
            "V_bop": float(V_bop),
            "V_sys": float(V_sys),
            "r_inner": float(r),
            "r_outer": float(r_out),
            "L_cyl": float(L_cyl),
            "t_mli": float(t_mli),
            "t_shell": float(t_shell),
            "t_ln2": float(t_ln2),
            "Q_implied_W": float(Q_implied),
            "P_design": float(self.P_design),
            "GC": float(m_usable / m_sys),
            "VC": float(m_usable / (V_sys * 1000.0)),
        }
        out.update({k: float(v) for k, v in wall_detail.items()})
        return out


def size_for_usable(
    design, target_usable_kg=DEFAULT_TARGET_USABLE_KG,
    bracket=(1.0e-3, 5.0), xtol=1.0e-12
):
    """Internal volume (m^3) delivering ``target_usable_kg`` of usable H2."""
    if target_usable_kg <= 0.0:
        raise ValueError(
            f"target_usable_kg must be strictly positive; got "
            f"{target_usable_kg}."
        )
    V_lo, V_hi = bracket
    f = lambda V: design.usable(V) - target_usable_kg  # noqa: E731
    f_lo, f_hi = f(V_lo), f(V_hi)
    if f_lo * f_hi > 0.0:
        raise ValueError(
            f"Cannot bracket target {target_usable_kg} kg on "
            f"[{V_lo}, {V_hi}] m^3 (usable {f_lo + target_usable_kg} .. "
            f"{f_hi + target_usable_kg} kg)."
        )
    return float(brentq(f, V_lo, V_hi, xtol=xtol, rtol=1.0e-14, maxiter=200))


def evaluate_sized(design, target_usable_kg=DEFAULT_TARGET_USABLE_KG):
    """Size to the usable target and return the budget (convenience)."""
    V = size_for_usable(design, target_usable_kg)
    return design.evaluate(V)
