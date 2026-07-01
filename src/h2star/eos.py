"""Equations of state for hydrogen gas-phase density and compressibility.

Thin wrapper around CoolProp's Helmholtz-energy reference equation of state for
normal hydrogen (``'Hydrogen'``). All quantities are in SI units: pressure in
pascals (Pa), temperature in kelvin (K), and specific quantities per kilogram.

Density and molar density are related by the molar mass :data:`h2star.constants.M_H2`.
"""

import numpy as np
from CoolProp.CoolProp import PropsSI

from . import constants

#: CoolProp fluid name for normal hydrogen.
_FLUID = "Hydrogen"

#: Lower temperature bound (K). Below this the reference EOS enters the
#: two-phase / critical region and single-phase gas properties are not valid.
_T_MIN = 33.2


def _validate(P, T):
    """Validate pressure and temperature arrays.

    Parameters
    ----------
    P : float or numpy.ndarray
        Pressure in pascals (Pa). Must be strictly positive.
    T : float or numpy.ndarray
        Temperature in kelvin (K). Must be >= 33.2 K.

    Returns
    -------
    tuple of numpy.ndarray
        ``(P, T)`` as float arrays (0-d for scalar inputs).

    Raises
    ------
    ValueError
        If any pressure is not strictly positive, or any temperature is
        below 33.2 K.
    """
    P = np.asarray(P, dtype=float)
    T = np.asarray(T, dtype=float)
    if np.any(P <= 0.0):
        raise ValueError(
            f"Pressure P must be strictly positive (Pa); got minimum {np.min(P)} Pa."
        )
    if np.any(T < _T_MIN):
        raise ValueError(
            f"Temperature T must be >= {_T_MIN} K (below this the gas-phase EOS is "
            f"invalid); got minimum {np.min(T)} K."
        )
    return P, T


def _props(output, P, T):
    """Evaluate a CoolProp output over (possibly array) P and T.

    Parameters
    ----------
    output : str
        CoolProp output key (e.g. ``'D'``, ``'H'``, ``'S'``).
    P : float or numpy.ndarray
        Pressure in pascals (Pa).
    T : float or numpy.ndarray
        Temperature in kelvin (K).

    Returns
    -------
    float or numpy.ndarray
        The requested property in CoolProp's SI units. Returns a scalar
        ``float`` when both inputs are scalars, otherwise an array broadcast
        to the common shape.
    """
    P_arr, T_arr = np.broadcast_arrays(P, T)
    scalar = P_arr.ndim == 0
    it = np.nditer(
        [P_arr, T_arr, None],
        op_flags=[["readonly"], ["readonly"], ["writeonly", "allocate"]],
        op_dtypes=[float, float, float],
    )
    with it:
        for p, t, out in it:
            out[...] = PropsSI(output, "P", float(p), "T", float(t), _FLUID)
        result = it.operands[2]
    if scalar:
        return float(result)
    return result


def density(P, T):
    """Mass density of normal hydrogen.

    Parameters
    ----------
    P : float or numpy.ndarray
        Pressure in pascals (Pa). Must be strictly positive.
    T : float or numpy.ndarray
        Temperature in kelvin (K). Must be >= 33.2 K.

    Returns
    -------
    float or numpy.ndarray
        Mass density in kilograms per cubic metre (kg/m^3).
    """
    P, T = _validate(P, T)
    return _props("D", P, T)


def molar_density(P, T):
    """Molar density of normal hydrogen.

    Parameters
    ----------
    P : float or numpy.ndarray
        Pressure in pascals (Pa). Must be strictly positive.
    T : float or numpy.ndarray
        Temperature in kelvin (K). Must be >= 33.2 K.

    Returns
    -------
    float or numpy.ndarray
        Molar density in moles per cubic metre (mol/m^3), computed as the mass
        density divided by the molar mass :data:`h2star.constants.M_H2`.
    """
    return density(P, T) / constants.M_H2


def enthalpy(P, T):
    """Specific enthalpy of normal hydrogen.

    Parameters
    ----------
    P : float or numpy.ndarray
        Pressure in pascals (Pa). Must be strictly positive.
    T : float or numpy.ndarray
        Temperature in kelvin (K). Must be >= 33.2 K.

    Returns
    -------
    float or numpy.ndarray
        Specific enthalpy in joules per kilogram (J/kg), on CoolProp's
        reference-state datum for hydrogen.
    """
    P, T = _validate(P, T)
    return _props("H", P, T)


def entropy(P, T):
    """Specific entropy of normal hydrogen.

    Parameters
    ----------
    P : float or numpy.ndarray
        Pressure in pascals (Pa). Must be strictly positive.
    T : float or numpy.ndarray
        Temperature in kelvin (K). Must be >= 33.2 K.

    Returns
    -------
    float or numpy.ndarray
        Specific entropy in joules per kilogram per kelvin (J/(kg*K)), on
        CoolProp's reference-state datum for hydrogen.
    """
    P, T = _validate(P, T)
    return _props("S", P, T)


def isothermal_compression_work(P1, P2, T):
    """Reversible isothermal compression work for normal hydrogen.

    Computes the specific work of a reversible isothermal compression from
    ``P1`` to ``P2`` at constant temperature ``T`` using real-gas properties
    from CoolProp (NOT the ideal-gas expression ``R*T/M * ln(P2/P1)``).

    For a reversible isothermal process the minimum specific shaft work equals
    the change in specific Gibbs free energy at constant ``T``:

        w = (h2 - h1) - T * (s2 - s1)

    where ``h`` and ``s`` are the real-gas specific enthalpy and entropy.

    Parameters
    ----------
    P1 : float or numpy.ndarray
        Initial pressure in pascals (Pa). Must be strictly positive.
    P2 : float or numpy.ndarray
        Final pressure in pascals (Pa). Must be strictly positive.
    T : float or numpy.ndarray
        Temperature in kelvin (K), held constant. Must be >= 33.2 K.

    Returns
    -------
    float or numpy.ndarray
        Specific compression work in joules per kilogram (J/kg). Positive when
        ``P2 > P1`` (work done on the gas).
    """
    P1, T1 = _validate(P1, T)
    P2, _ = _validate(P2, T)
    h1 = _props("H", P1, T1)
    s1 = _props("S", P1, T1)
    h2 = _props("H", P2, T1)
    s2 = _props("S", P2, T1)
    return (h2 - h1) - T * (s2 - s1)
