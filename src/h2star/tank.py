"""Tank-level hydrogen inventory for a packed adsorbent vessel.

This module converts a material's isotherm into the TOTAL hydrogen mass stored
in a tank of a given internal volume, by two equivalent bookkeeping routes:

* the ABSOLUTE route, which adds absolute adsorbed moles to the gas filling the
  void volume that EXCLUDES the adsorbed-phase volume ``v_a``; and
* the EXCESS route, which adds excess adsorbed moles to the gas filling the
  full gas-accessible volume that INCLUDES ``v_a``.

The two routes are identical by construction (the ``rho_gas * v_a`` term that
:meth:`h2star.isotherm.ModifiedDA.n_excess` subtracts is exactly the term the
absolute route omits from its void volume), so agreement between them is a
bookkeeping invariant rather than a physical result.

All quantities are in SI units: pressure in pascals (Pa), temperature in
kelvin (K), volumes in cubic metres (m^3), densities in kg/m^3, loadings in
mol/kg, and masses in kilograms (kg).
"""

from .constants import M_H2
from .eos import molar_density


def _sorbent_mass(material, V_internal, packing):
    """Sorbent mass (kg) packed into ``V_internal`` (m^3), with guards.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Material whose ``rho_bulk`` (kg/m^3) and ``rho_skel`` (kg/m^3) must
        both be set.
    V_internal : float
        Internal (geometric) volume of the tank in cubic metres (m^3).
    packing : str
        Packing mode; only ``'full'`` is supported.

    Returns
    -------
    float
        Mass of adsorbent in kilograms (kg).

    Raises
    ------
    NotImplementedError
        If ``packing`` is anything other than ``'full'``.
    ValueError
        If ``rho_bulk`` or ``rho_skel`` is ``None``.
    """
    if packing != "full":
        raise NotImplementedError(
            f"packing={packing!r} is not supported; only 'full' packing "
            f"(sorbent fills the entire internal volume) is implemented."
        )
    missing = [
        field
        for field in ("rho_bulk", "rho_skel")
        if getattr(material, field) is None
    ]
    if missing:
        raise ValueError(
            f"Material {material.name!r} is missing {' and '.join(missing)}; "
            f"the tank layer requires both the packed bulk density "
            f"(rho_bulk, kg/m^3) and the skeletal density (rho_skel, kg/m^3)."
        )
    return material.rho_bulk * V_internal


def _check_void(V_void):
    """Raise if the void volume (m^3) came out negative.

    Parameters
    ----------
    V_void : float
        Void (gas-filled) volume in cubic metres (m^3).

    Raises
    ------
    ValueError
        If ``V_void < 0``, which means the skeletal and adsorbed-phase volumes
        together exceed the internal volume -- an inconsistent packing.
    """
    if V_void < 0.0:
        raise ValueError(
            f"Void volume is negative (V_void = {V_void} m^3): the skeleton "
            f"and adsorbed phase together exceed the tank internal volume. "
            f"Check rho_bulk, rho_skel, and v_a for packing consistency."
        )


def total_h2_mass(material, isotherm, P, T, V_internal, packing="full"):
    """Total stored hydrogen mass in a packed tank, ABSOLUTE bookkeeping.

    Adds the absolute adsorbed inventory to the bulk gas occupying the void
    volume, where the void EXCLUDES both the sorbent skeleton and the
    adsorbed-phase volume ``v_a``.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Material supplying ``rho_bulk`` (kg/m^3), ``rho_skel`` (kg/m^3), and
        ``v_a`` (m^3/kg).
    isotherm : h2star.isotherm.ModifiedDA
        Isotherm supplying ``n_absolute(P, T)`` in mol/kg.
    P : float
        Pressure in pascals (Pa).
    T : float
        Temperature in kelvin (K).
    V_internal : float
        Internal (geometric) volume of the tank in cubic metres (m^3).
    packing : str, optional
        Packing mode; only ``'full'`` is supported (default).

    Returns
    -------
    float
        Total hydrogen mass in the tank, in kilograms (kg).

    Raises
    ------
    NotImplementedError
        If ``packing`` is anything other than ``'full'``.
    ValueError
        If ``rho_bulk`` or ``rho_skel`` is ``None``, or if the resulting void
        volume is negative.
    """
    m_s = _sorbent_mass(material, V_internal, packing)  # kg sorbent
    V_void = V_internal - m_s / material.rho_skel - m_s * material.v_a  # m^3
    _check_void(V_void)

    n_ads = m_s * isotherm.n_absolute(P, T)  # mol adsorbed (absolute)
    n_void = molar_density(P, T) * V_void  # mol of gas in the void
    return float(M_H2 * (n_ads + n_void))  # kg


def total_h2_mass_via_excess(
    material, isotherm, P, T, V_internal, packing="full"
):
    """Total stored hydrogen mass in a packed tank, EXCESS bookkeeping.

    Adds the excess adsorbed inventory to the bulk gas occupying the whole
    gas-accessible volume, which INCLUDES the adsorbed-phase volume ``v_a``.
    Equal to :func:`total_h2_mass` by construction.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Material supplying ``rho_bulk`` (kg/m^3) and ``rho_skel`` (kg/m^3).
    isotherm : h2star.isotherm.ModifiedDA
        Isotherm supplying ``n_excess(P, T)`` in mol/kg.
    P : float
        Pressure in pascals (Pa).
    T : float
        Temperature in kelvin (K).
    V_internal : float
        Internal (geometric) volume of the tank in cubic metres (m^3).
    packing : str, optional
        Packing mode; only ``'full'`` is supported (default).

    Returns
    -------
    float
        Total hydrogen mass in the tank, in kilograms (kg).

    Raises
    ------
    NotImplementedError
        If ``packing`` is anything other than ``'full'``.
    ValueError
        If ``rho_bulk`` or ``rho_skel`` is ``None``, or if the resulting void
        volume (skeleton and adsorbed phase excluded) is negative.
    """
    m_s = _sorbent_mass(material, V_internal, packing)  # kg sorbent
    V_gas = V_internal - m_s / material.rho_skel  # m^3, includes v_a
    # Guard on the SAME void volume as the absolute route, so both routes
    # reject the same inconsistent packings.
    _check_void(V_gas - m_s * material.v_a)

    n_ads = m_s * isotherm.n_excess(P, T)  # mol adsorbed (excess)
    n_gas = molar_density(P, T) * V_gas  # mol of gas filling V_gas
    return float(M_H2 * (n_ads + n_gas))  # kg


def usable_h2(material, isotherm, full, empty, V_internal):
    """Deliverable hydrogen mass between a full and an empty tank state.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Material supplying ``rho_bulk`` (kg/m^3), ``rho_skel`` (kg/m^3), and
        ``v_a`` (m^3/kg).
    isotherm : h2star.isotherm.ModifiedDA
        Isotherm supplying ``n_absolute(P, T)`` in mol/kg.
    full : tuple of float
        Full state as ``(P, T)`` in (Pa, K).
    empty : tuple of float
        Empty (depleted) state as ``(P, T)`` in (Pa, K).
    V_internal : float
        Internal (geometric) volume of the tank in cubic metres (m^3).

    Returns
    -------
    float
        Usable (deliverable) hydrogen mass in kilograms (kg): the total
        inventory at the full state minus that at the empty state. Positive
        when the full state holds more hydrogen than the empty state.
    """
    P_full, T_full = full
    P_empty, T_empty = empty
    m_full = total_h2_mass(material, isotherm, P_full, T_full, V_internal)
    m_empty = total_h2_mass(material, isotherm, P_empty, T_empty, V_internal)
    return float(m_full - m_empty)
