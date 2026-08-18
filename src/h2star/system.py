"""System-level mass and volume budget for a cryo-adsorptive hydrogen tank.

This module assembles the layers below it -- the isotherm
(:mod:`h2star.isotherm`), the tank inventory (:mod:`h2star.tank`), and the
composite pressure vessel (:mod:`h2star.vessel`) -- into a single system
budget: the total mass and total volume of a complete storage system, and the
two figures of merit derived from them, gravimetric capacity (GC) and
volumetric capacity (VC).

Two engineering terms are added at this level:

* INSULATION, sized by steady-state one-dimensional conduction through a
  multilayer-insulation (MLI) blanket (manual 3.4G). The blanket thickness is
  whatever makes the conducted heat equal the allowable heat-leak budget,
  ``Q = k_eff * A * dT / t_ins`` inverted for ``t_ins``; and
* BALANCE OF PLANT (BOP), a lumped fixed mass plus a term proportional to the
  usable hydrogen mass.

A note on the capacity definitions, because the two hydrogen masses are not
interchangeable. The NUMERATOR of GC and VC is ``m_usable``, the swing between
the full and empty states -- the hydrogen the system actually delivers. The
system mass in the DENOMINATOR carries ``m_h2_full``, the full inventory,
because the residual hydrogen left at the empty state is still mass the
vehicle carries around. Substituting one for the other in either place is a
modelling error, not a simplification.

All quantities are SI: pressures in pascals (Pa), temperatures in kelvin (K),
lengths in metres (m), areas in square metres (m^2), volumes in cubic metres
(m^3), densities in kg/m^3, masses in kilograms (kg), thermal conductivity in
W/(m*K), and heat flow in watts (W). The single exception is VC, which is
reported in kg per litre by convention; the conversion from m^3 is explicit at
the point of use.
"""

from dataclasses import dataclass

import yaml
from scipy.optimize import brentq

from . import tank, vessel

#: Units each insulation parameter must declare in the YAML file (SI values).
_EXPECTED_INSULATION_UNITS = {
    "mli_k_eff": "W/(m*K)",
    "mli_density": "kg/m3",
    "heat_leak_budget": "W",
    "T_env": "K",
}

#: Units each balance-of-plant parameter must declare in the YAML file.
_EXPECTED_BOP_UNITS = {
    "bop_fixed": "kg",
    "bop_scaling": "kg per kg usable H2",
}


def _read_block(data, path, block_name, expected_units):
    """Read one ``{value, unit}`` block from a parsed engineering YAML file.

    Parameters
    ----------
    data : dict
        The already-parsed YAML document.
    path : str or path-like
        Path the document came from, used only in error messages.
    block_name : str
        Top-level key of the block to read, e.g. ``'insulation'``.
    expected_units : dict of {str: str}
        Mapping of parameter name to the SI unit string it must declare.

    Returns
    -------
    dict of {str: float}
        Parameter values in SI units, taken as-is from the file.

    Raises
    ------
    KeyError
        If the block or one of its expected parameters is absent.
    ValueError
        If any parameter declares a unit other than the expected SI string.
    """
    if block_name not in data:
        raise KeyError(
            f"Engineering parameter file {path!r} has no top-level "
            f"{block_name!r} block."
        )
    block = data[block_name]

    values = {}
    for key, expected_unit in expected_units.items():
        entry = block[key]
        unit = entry["unit"]
        if unit != expected_unit:
            raise ValueError(
                f"Unrecognized unit {unit!r} for {key!r} in {path!r}; "
                f"expected SI unit {expected_unit!r}."
            )
        values[key] = float(entry["value"])
    return values


@dataclass(frozen=True)
class EngineeringParams:
    """Immutable container for the system-level engineering parameters (SI).

    Composes the vessel parameters so that one file yields one consistent
    parameter set: the geometry the insulation is wrapped around is the same
    geometry the vessel mass is computed from.

    Attributes
    ----------
    mli_k_eff : float
        MLI effective (apparent) thermal conductivity, W/(m*K). Lumps
        radiation, spacer conduction, and residual-gas conduction into one
        number.
    mli_density : float
        MLI blanket bulk density, kg/m^3. Converts the solved blanket
        thickness into insulation mass.
    heat_leak_budget : float
        Allowable total steady-state heat in-leakage, W. This is the
        insulation sizing driver.
    T_env : float
        Warm-boundary (ambient) design temperature, K. The cold boundary is
        the operating full-state temperature, applied in code.
    bop_fixed : float
        Lumped fixed balance-of-plant mass, kg.
    bop_scaling : float
        Balance-of-plant mass proportional to usable hydrogen, in kg per kg
        of usable H2.
    vessel : h2star.vessel.VesselParams
        Pressure-vessel parameters loaded from the same file.
    citation : str
        Provenance of the parameter set (required).
    """

    mli_k_eff: float  # MLI effective conductivity, W/(m*K)
    mli_density: float  # MLI blanket bulk density, kg/m^3
    heat_leak_budget: float  # allowable heat in-leakage, W
    T_env: float  # warm-boundary temperature, K
    bop_fixed: float  # fixed balance-of-plant mass, kg
    bop_scaling: float  # BOP mass per usable H2 mass, kg/kg
    vessel: vessel.VesselParams  # pressure-vessel parameters (SI)
    citation: str  # provenance (required)

    @classmethod
    def from_yaml(cls, path):
        """Build an :class:`EngineeringParams` from an engineering YAML file.

        Parameters
        ----------
        path : str or path-like
            Path to ``data/engineering.yaml``.

        Returns
        -------
        EngineeringParams
            Parameters in SI units, including the :class:`~h2star.vessel.
            VesselParams` loaded from the same file.

        Notes
        -----
        The file must carry a non-empty top-level ``name``, an ``insulation``
        mapping with ``{value, unit}`` entries for ``mli_k_eff``,
        ``mli_density``, ``heat_leak_budget`` and ``T_env``, and a ``bop``
        mapping with ``{value, unit}`` entries for ``bop_fixed`` and
        ``bop_scaling``. Values are already SI and are taken as-is, but each
        declared ``unit`` is checked against the expected SI string, mirroring
        :meth:`h2star.vessel.VesselParams.from_yaml`.

        Raises
        ------
        ValueError
            If the top-level ``name`` is missing/empty, or if any parameter
            declares a unit other than the expected SI string.
        KeyError
            If the ``insulation`` or ``bop`` block, or one of their expected
            parameters, is absent.
        """
        with open(path) as fh:
            data = yaml.safe_load(fh)

        # Validate provenance BEFORE touching any numeric value.
        name = data.get("name")
        if not name:
            raise ValueError(
                f"Engineering parameter file {path!r} is missing a non-empty "
                f"top-level 'name'; parameters must be attributable to a "
                f"source."
            )
        description = data.get("description")

        values = _read_block(
            data, path, "insulation", _EXPECTED_INSULATION_UNITS
        )
        values.update(_read_block(data, path, "bop", _EXPECTED_BOP_UNITS))

        # Provenance string: file identity plus the per-parameter _source notes.
        sources = []
        for block_name, expected in (
            ("insulation", _EXPECTED_INSULATION_UNITS),
            ("bop", _EXPECTED_BOP_UNITS),
        ):
            block = data[block_name]
            sources.extend(
                f"{key}: {block[key + '_source']}"
                for key in expected
                if block.get(key + "_source")
            )
        citation = "; ".join([name, description or "", *sources]).strip()

        return cls(
            vessel=vessel.VesselParams.from_yaml(path),
            citation=citation,
            **values,
        )


@dataclass(frozen=True)
class SystemDesign:
    """Immutable description of a storage system, minus its size.

    Everything needed to evaluate a system budget EXCEPT the internal volume,
    which is the free variable: :meth:`evaluate` takes it as an argument and
    :func:`size_for_usable` solves for it.

    Attributes
    ----------
    material : h2star.isotherm.Material
        Adsorbent, supplying ``rho_bulk`` (kg/m^3), ``rho_skel`` (kg/m^3) and
        ``v_a`` (m^3/kg).
    isotherm : h2star.isotherm.ModifiedDA
        Isotherm built on ``material``, supplying loadings in mol/kg.
    engineering : EngineeringParams
        Insulation, BOP and (composed) vessel parameters in SI units.
    P_full : float
        Full-state pressure, Pa. Also the vessel design pressure ``P_max``.
    T_full : float
        Full-state temperature, K. Also the insulation cold boundary.
    P_empty : float
        Empty (depleted) state pressure, Pa.
    T_empty : float
        Empty (depleted) state temperature, K.
    """

    material: object  # h2star.isotherm.Material
    isotherm: object  # h2star.isotherm.ModifiedDA
    engineering: EngineeringParams  # insulation + BOP + vessel params (SI)
    P_full: float  # full-state pressure, Pa
    T_full: float  # full-state temperature, K
    P_empty: float  # empty-state pressure, Pa
    T_empty: float  # empty-state temperature, K

    @property
    def vessel_params(self):
        """The :class:`~h2star.vessel.VesselParams` for this design.

        Returns
        -------
        h2star.vessel.VesselParams
            The vessel parameters composed into :attr:`engineering`, so that
            vessel and insulation geometry cannot drift apart.
        """
        return self.engineering.vessel

    @property
    def full(self):
        """Full state as ``(P, T)`` in (Pa, K), for the tank-layer calls."""
        return (self.P_full, self.T_full)

    @property
    def empty(self):
        """Empty state as ``(P, T)`` in (Pa, K), for the tank-layer calls."""
        return (self.P_empty, self.T_empty)

    def usable(self, V_internal):
        """Usable (deliverable) hydrogen mass for a given internal volume.

        Parameters
        ----------
        V_internal : float
            Internal (geometric) tank volume, m^3. Must be strictly positive.

        Returns
        -------
        float
            Usable hydrogen mass in kilograms (kg): the full-state inventory
            minus the empty-state inventory.

        Raises
        ------
        ValueError
            If ``V_internal`` is not strictly positive.
        """
        _check_positive(V_internal, "V_internal", "m^3")
        return tank.usable_h2(
            self.material, self.isotherm, self.full, self.empty, V_internal
        )

    def evaluate(self, V_internal):
        """Full system mass and volume budget at a GIVEN internal volume.

        Does not size anything: ``V_internal`` is an input. Use
        :func:`size_for_usable` first if the volume must be solved for.

        Parameters
        ----------
        V_internal : float
            Internal (geometric) tank volume, m^3. Must be strictly positive.

        Returns
        -------
        dict
            Budget with the following keys, all SI except ``VC``:

            ``m_h2_full`` : float
                Total hydrogen inventory at the full state, kg.
            ``m_usable`` : float
                Usable swing from full to empty, kg.
            ``m_sorbent`` : float
                Packed adsorbent mass, kg.
            ``m_vessel`` : float
                Composite shell plus liner mass, kg.
            ``m_insulation`` : float
                MLI blanket mass, kg.
            ``m_bop`` : float
                Balance-of-plant mass, kg.
            ``m_sys`` : float
                Total system mass, kg. Carries ``m_h2_full``, not
                ``m_usable``: the residual hydrogen is still carried mass.
            ``V_internal`` : float
                The input internal volume, m^3.
            ``V_shell`` : float
                Composite-plus-liner shell volume, ``A * t_wall``, m^3.
            ``V_insulation`` : float
                MLI blanket volume, ``A * t_ins``, m^3.
            ``V_sys`` : float
                Total system volume, m^3.
            ``GC`` : float
                Gravimetric capacity, ``m_usable / m_sys``, kg/kg.
            ``VC`` : float
                Volumetric capacity, ``m_usable / V_sys`` expressed in kg per
                litre.

        Raises
        ------
        ValueError
            If ``V_internal`` is not strictly positive, if the insulation
            parameters (``mli_k_eff``, ``heat_leak_budget``) are not strictly
            positive, or if the warm-cold temperature difference
            ``T_env - T_full`` is not strictly positive.
        """
        _check_positive(V_internal, "V_internal", "m^3")

        eng = self.engineering
        vp = self.vessel_params

        # --- Hydrogen inventory (tank layer) ------------------------------
        m_h2_full = tank.total_h2_mass(
            self.material,
            self.isotherm,
            self.P_full,
            self.T_full,
            V_internal,
        )  # kg
        m_usable = tank.usable_h2(
            self.material, self.isotherm, self.full, self.empty, V_internal
        )  # kg

        # --- Sorbent ------------------------------------------------------
        m_sorbent = self.material.rho_bulk * V_internal  # kg

        # --- Vessel -------------------------------------------------------
        # The design pressure is the full-state pressure.
        m_vessel = vessel.vessel_mass_hoop(self.P_full, V_internal, vp)  # kg

        # --- Geometry, reproduced exactly as vessel_mass_hoop computes it --
        LR = vp.aspect_ratio_LR
        r = vessel.radius_from_volume(V_internal, LR)  # m
        A = vessel.surface_area(r, LR)  # m^2
        t_wall = vessel.wall_thickness(
            self.P_full, r, vp.safety_factor, vp.sigma_allow
        )  # m

        # --- Insulation: invert Q = k*A*dT/t_ins for t_ins (manual 3.4G) ---
        t_ins = self._insulation_thickness(A)  # m
        m_insulation = A * t_ins * eng.mli_density  # kg

        # --- Balance of plant ---------------------------------------------
        m_bop = eng.bop_fixed + eng.bop_scaling * m_usable  # kg

        # --- Totals -------------------------------------------------------
        # NOTE: the mass sum carries the FULL inventory, m_h2_full, because
        # the residual hydrogen at the empty state is still carried mass.
        # The GC/VC numerator is the SWING, m_usable. Do not swap them.
        m_sys = (
            m_h2_full + m_sorbent + m_vessel + m_insulation + m_bop
        )  # kg

        V_shell = A * t_wall  # m^3
        V_insulation = A * t_ins  # m^3
        V_sys = V_internal + V_shell + V_insulation  # m^3

        return {
            "m_h2_full": float(m_h2_full),
            "m_usable": float(m_usable),
            "m_sorbent": float(m_sorbent),
            "m_vessel": float(m_vessel),
            "m_insulation": float(m_insulation),
            "m_bop": float(m_bop),
            "m_sys": float(m_sys),
            "V_internal": float(V_internal),
            "V_shell": float(V_shell),
            "V_insulation": float(V_insulation),
            "V_sys": float(V_sys),
            "GC": float(m_usable / m_sys),  # kg/kg
            "VC": float(m_usable / (V_sys * 1000.0)),  # kg per litre
        }

    def _insulation_thickness(self, A):
        """MLI blanket thickness (m) that meets the heat-leak budget.

        Steady-state one-dimensional conduction (manual 3.4G): the conducted
        heat ``Q = k_eff * A * dT / t_ins`` is set equal to the allowable
        budget and inverted for the thickness, so
        ``t_ins = k_eff * A * dT / Q_budget``.

        Parameters
        ----------
        A : float
            Shell surface area the blanket wraps, m^2.

        Returns
        -------
        float
            Blanket thickness in metres (m).

        Raises
        ------
        ValueError
            If ``mli_k_eff`` or ``heat_leak_budget`` is not strictly positive,
            or if ``dT = T_env - T_full`` is not strictly positive (the
            environment must be warmer than the cold tank for the conduction
            model to have a sign).
        """
        eng = self.engineering
        _check_positive(eng.mli_k_eff, "mli_k_eff", "W/(m*K)")
        _check_positive(eng.heat_leak_budget, "heat_leak_budget", "W")

        dT = eng.T_env - self.T_full  # K
        if dT <= 0.0:
            raise ValueError(
                f"Temperature difference dT = T_env - T_full must be "
                f"strictly positive (K); got T_env = {eng.T_env} K and "
                f"T_full = {self.T_full} K, i.e. dT = {dT} K. The insulation "
                f"model assumes heat leaks INTO a cold tank."
            )
        return eng.mli_k_eff * A * dT / eng.heat_leak_budget


def _check_positive(value, name, unit):
    """Raise :class:`ValueError` unless ``value`` is strictly positive.

    Parameters
    ----------
    value : float
        Quantity to check, in ``unit``.
    name : str
        Parameter name, used in the error message.
    unit : str
        SI unit string, used in the error message.

    Raises
    ------
    ValueError
        If ``value <= 0``.
    """
    if value <= 0.0:
        raise ValueError(
            f"{name} must be strictly positive ({unit}); got {value} {unit}."
        )


def evaluate(design, V_internal):
    """Module-level alias for :meth:`SystemDesign.evaluate`.

    Parameters
    ----------
    design : SystemDesign
        System description (material, isotherm, parameters, envelope).
    V_internal : float
        Internal (geometric) tank volume, m^3. Must be strictly positive.

    Returns
    -------
    dict
        The system budget; see :meth:`SystemDesign.evaluate` for the keys and
        their units.
    """
    return design.evaluate(V_internal)


def size_for_usable(
    design, target_usable_kg=5.6, bracket=(1.0e-3, 5.0), xtol=1.0e-12
):
    """Solve for the internal volume delivering a target usable H2 mass.

    Roots ``f(V) = usable_h2(..., V) - target_usable_kg`` with Brent's method.
    The usable mass rises monotonically with internal volume (more sorbent and
    more void gas both add inventory at the full state faster than at the
    empty state), so the root is unique inside any bracket that contains it.

    Parameters
    ----------
    design : SystemDesign
        System description supplying the material, isotherm and envelope.
    target_usable_kg : float, optional
        Target usable (deliverable) hydrogen mass in kilograms (kg); default
        5.6 kg. Must be strictly positive.
    bracket : tuple of float, optional
        Search bracket ``(V_lo, V_hi)`` for the internal volume in cubic
        metres (m^3); default ``(1e-3, 5.0)``. Both bounds must be strictly
        positive with ``V_lo < V_hi``.
    xtol : float, optional
        Absolute tolerance on the solved volume in cubic metres (m^3), passed
        to :func:`scipy.optimize.brentq`; default 1e-12 m^3.

    Returns
    -------
    float
        Internal (geometric) tank volume in cubic metres (m^3) whose usable
        hydrogen mass equals ``target_usable_kg``.

    Raises
    ------
    ValueError
        If ``target_usable_kg`` is not strictly positive, if the bracket is
        not a strictly positive increasing interval, or if the target does not
        lie between the usable masses at the two bracket ends (so no root can
        be bracketed).
    """
    _check_positive(target_usable_kg, "target_usable_kg", "kg")

    V_lo, V_hi = bracket
    _check_positive(V_lo, "bracket lower bound", "m^3")
    _check_positive(V_hi, "bracket upper bound", "m^3")
    if V_lo >= V_hi:
        raise ValueError(
            f"Sizing bracket must be increasing; got (V_lo, V_hi) = "
            f"({V_lo}, {V_hi}) m^3."
        )

    def f(V):
        """Usable-mass residual (kg) at internal volume ``V`` (m^3)."""
        return design.usable(V) - target_usable_kg

    f_lo = f(V_lo)
    f_hi = f(V_hi)
    if f_lo * f_hi > 0.0:
        raise ValueError(
            f"Cannot bracket a root for target_usable_kg = "
            f"{target_usable_kg} kg on V_internal in [{V_lo}, {V_hi}] m^3: "
            f"usable H2 is {f_lo + target_usable_kg} kg at the lower bound "
            f"and {f_hi + target_usable_kg} kg at the upper bound, so the "
            f"target lies outside that range. Widen the bracket."
        )

    return float(brentq(f, V_lo, V_hi, xtol=xtol, rtol=1.0e-14, maxiter=200))
