"""Adsorption isotherm models for hydrogen uptake on porous materials.

This module implements the modified (supercritical) Dubinin--Astakhov (D-A)
isotherm used for cryo-adsorptive hydrogen storage. All quantities are in SI
units: pressures in pascals (Pa), temperatures in kelvin (K), and loadings in
moles per kilogram of adsorbent (mol/kg).
"""

from dataclasses import dataclass

import numpy as np
import yaml
from scipy.optimize import brentq

from .constants import R
from .eos import molar_density


def rmse(predicted, observed):
    """Root-mean-square error between two 1-D arrays.

    predicted, observed : array-like, SAME physical units (e.g. mol/kg),
    SAME shape. Returns a float in those units.
    """
    predicted = np.asarray(predicted, dtype=float)
    observed = np.asarray(observed, dtype=float)
    if predicted.shape != observed.shape:
        raise ValueError(f"rmse: shape mismatch {predicted.shape} vs {observed.shape}")
    return float(np.sqrt(np.mean((predicted - observed) ** 2)))


@dataclass(frozen=True)
class Material:
    """Immutable container for a material's modified D-A parameters (SI units).

    Attributes
    ----------
    name : str
        Human-readable material identifier.
    n_max : float
        Limiting absolute adsorption, mol/kg.
    alpha : float
        Enthalpic factor of the characteristic energy, J/mol.
    beta : float
        Entropic factor of the characteristic energy, J/(mol*K).
    p0 : float
        Pseudo-saturation (reference) pressure, Pa.
    v_a : float
        Specific adsorbed-phase volume, m^3/kg.
    citation : str
        Bibliographic source of the parameters (required).
    rho_bulk : float or None
        Packed bulk density of the adsorbent, kg/m^3.
    rho_skel : float or None
        Skeletal (crystalline) density, kg/m^3. Absent for AX-21; the tank
        layer requires it.
    """

    name: str
    n_max: float  # limiting absolute adsorption, mol/kg
    alpha: float  # enthalpic factor, J/mol
    beta: float  # entropic factor, J/(mol*K)
    p0: float  # pseudo-saturation pressure, Pa
    v_a: float  # specific adsorbed-phase volume, m^3/kg
    citation: str  # bibliographic source (required)
    rho_bulk: float | None = None  # packed bulk density, kg/m^3
    rho_skel: float | None = None  # skeletal density, kg/m^3

    @classmethod
    def from_yaml(cls, path):
        """Build a :class:`Material` from a YAML parameter file.

        The file must carry a top-level ``name`` and non-empty ``citation``,
        and a top-level ``parameters`` mapping whose entries are
        ``{value, unit}`` mappings for ``n_max``, ``alpha``, ``beta``, ``p0``,
        and ``v_a``. Units are converted to SI: ``p0`` from MPa (or accepted
        as Pa); the remaining four parameters are already SI and taken as-is.
        ``rho_bulk`` is read from ``material_anchors.bulk_density_kg_per_m3``
        when present. ``rho_skel`` is set to ``None``.

        Raises
        ------
        ValueError
            If ``citation`` is missing/empty, if ``p0``'s unit is neither
            ``MPa`` nor ``Pa``, or if ``alpha``'s unit is expressed in kJ.
        """
        with open(path) as fh:
            data = yaml.safe_load(fh)

        # Validate citation BEFORE touching any parameters.
        citation = data.get("citation")
        if not citation:
            raise ValueError(
                f"Material file {path!r} is missing a non-empty top-level "
                f"'citation'; parameters must be attributable to a source."
            )

        name = data.get("name")
        params = data["parameters"]

        # p0: convert from the declared unit to Pa.
        p0_unit = params["p0"]["unit"]
        if p0_unit == "MPa":
            p0 = params["p0"]["value"] * 1e6
        elif p0_unit == "Pa":
            p0 = params["p0"]["value"]
        else:
            raise ValueError(
                f"Unrecognized unit {p0_unit!r} for p0; expected 'MPa' or 'Pa'."
            )

        # alpha must be J/mol, not kJ/mol.
        alpha_unit = params["alpha"]["unit"]
        if "kJ" in alpha_unit:
            raise ValueError(
                f"alpha unit {alpha_unit!r} appears to be in kJ; expected J/mol."
            )

        # The remaining parameters are already SI -- take the value directly.
        n_max = params["n_max"]["value"]
        alpha = params["alpha"]["value"]
        beta = params["beta"]["value"]
        v_a = params["v_a"]["value"]

        anchors = data.get("material_anchors") or {}
        rho_bulk = anchors.get("bulk_density_kg_per_m3")

        return cls(
            name=name,
            n_max=n_max,
            alpha=alpha,
            beta=beta,
            p0=p0,
            v_a=v_a,
            citation=citation,
            rho_bulk=rho_bulk,
            rho_skel=None,
        )


class ModifiedDA:
    """Modified (supercritical) Dubinin--Astakhov isotherm for one material.

    The absolute loading follows

        n_abs = n_max * exp[ -(R*T / (alpha + beta*T))^2 * ln^2(p0 / P) ]

    with a fixed distribution exponent m = 2. Excess loading subtracts the
    bulk gas that would occupy the adsorbed-phase volume ``v_a``.
    """

    def __init__(self, material):
        """Store the :class:`Material` whose parameters define the isotherm."""
        self.material = material

    def n_absolute(self, P, T):
        """Absolute adsorption in mol/kg at pressure ``P`` (Pa) and ``T`` (K).

        ``P`` may be a scalar or a numpy array; ``T`` is a scalar. For
        ``P >= p0`` the loading is CLAMPED to ``n_max`` rather than following
        the (unphysical) descending branch of the D-A form, which would
        otherwise dip back below ``n_max`` for ``P > p0``.

        Raises
        ------
        ValueError
            If any pressure is not strictly positive.
        """
        m = self.material
        P = np.asarray(P, dtype=float)
        if np.any(P <= 0.0):
            raise ValueError(
                f"Pressure P must be strictly positive (Pa); got minimum "
                f"{np.min(P)} Pa."
            )
        coeff = (R * T / (m.alpha + m.beta * T)) ** 2
        n = m.n_max * np.exp(-coeff * np.log(m.p0 / P) ** 2)
        # Clamp the saturation/descending branch to the limiting loading.
        n = np.where(P >= m.p0, m.n_max, n)
        if n.ndim == 0:
            return float(n)
        return n

    def n_excess(self, P, T):
        """Excess adsorption in mol/kg: absolute minus bulk gas in ``v_a``.

        Returns an array matching the shape of ``P`` (scalar for scalar
        ``P``). The bulk gas correction uses the EOS molar density evaluated
        at each pressure.
        """
        n_abs = self.n_absolute(P, T)
        rho_gas = molar_density(P, T)  # mol/m^3, vectorized over P
        return n_abs - rho_gas * self.material.v_a

    def pressure_at_loading(self, n, T):
        """Invert :meth:`n_absolute` for pressure (Pa) at fixed ``T`` (K).

        Solves ``n_absolute(P, T) == n`` for ``P`` with Brent's method,
        bracketing ``P`` in ``(1.0, p0*(1 - 1e-9))`` Pa. ``n`` may be a scalar
        or a numpy array.

        Raises
        ------
        ValueError
            If any target loading is not in the open interval ``(0, n_max)``.
        """
        m = self.material
        n_arr = np.asarray(n, dtype=float)

        def _solve_one(target):
            if target <= 0.0 or target >= m.n_max:
                raise ValueError(
                    f"Loading n must lie in (0, n_max={m.n_max}) mol/kg; "
                    f"got {target}."
                )
            return brentq(
                lambda P: self.n_absolute(P, T) - target,
                1.0,
                m.p0 * (1.0 - 1e-9),
                xtol=1e-9,
                rtol=1e-14,
                maxiter=200,
            )

        if n_arr.ndim == 0:
            return _solve_one(float(n_arr))
        return np.array([_solve_one(float(t)) for t in n_arr.ravel()]).reshape(
            n_arr.shape
        )
