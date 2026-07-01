"""Isosteric heats of adsorption and associated thermal effects.

The isosteric heat is obtained from the Clausius--Clapeyron relation applied at
constant loading: ``q_st = -R * d(ln P) / d(1/T)``. Pressures are in pascals
(Pa), temperatures in kelvin (K), loadings in mol/kg, and the returned heat is
in J/mol.
"""

from math import log

from .constants import R


def isosteric_heat(da, n, T, dT=1.0):
    """Isosteric heat of adsorption at loading ``n`` and temperature ``T``.

    Uses a centered finite difference of ``ln(P)`` with respect to ``1/T`` at
    fixed loading, with the two flanking pressures obtained by inverting the
    isotherm at ``(n, T - dT)`` and ``(n, T + dT)``.

    Sign convention: ``q_st`` is returned POSITIVE for exothermic adsorption
    (the physically expected sign for hydrogen physisorption).

    Parameters
    ----------
    da : ModifiedDA
        Isotherm model exposing ``pressure_at_loading(n, T)``.
    n : float
        Fixed loading, mol/kg.
    T : float
        Central temperature, K.
    dT : float, optional
        Half-width of the temperature step, K (default 1.0).

    Returns
    -------
    float
        Isosteric heat in J/mol.
    """
    p_plus = da.pressure_at_loading(n, T + dT)
    p_minus = da.pressure_at_loading(n, T - dT)
    slope = (log(p_plus) - log(p_minus)) / (1.0 / (T + dT) - 1.0 / (T - dT))
    q_st = -R * slope  # positive for exothermic adsorption
    return q_st


def isosteric_heat_convergence(da, n, T, dTs):
    """Isosteric heat evaluated for each temperature step in ``dTs``.

    Parameters
    ----------
    da : ModifiedDA
        Isotherm model.
    n : float
        Fixed loading, mol/kg.
    T : float
        Central temperature, K.
    dTs : iterable of float
        Temperature half-steps to sweep, K.

    Returns
    -------
    list of float
        ``q_st`` (J/mol) for each ``dT`` in ``dTs``, in order.
    """
    return [isosteric_heat(da, n, T, dT) for dT in dTs]
