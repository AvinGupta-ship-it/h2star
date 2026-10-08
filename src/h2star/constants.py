"""Physical constants and unit conversions for hydrogen thermodynamics.

This module is the single source of truth for the project's physical constants
and for every pressure-unit conversion. The package works in SI internally at
all times (pascals, kelvin, mol/kg, m^3/kg, kg); the helpers below exist so that
conversions happen only at input/output boundaries -- reading a YAML parameter
file, labelling a figure axis -- and never as an inline numeric literal buried
in a physics routine.

The conversion helpers are deliberately pure arithmetic with no validation and
no NumPy dependency: they accept a Python float or a NumPy array and return the
same kind, so they compose with the vectorized routines elsewhere in the
package. Guarding physically meaningless pressures is the job of the module that
consumes the value (see :func:`h2star.eos._validate`), not of a unit conversion.
"""

R = 8.314462618  # universal gas constant, J per mol per K
M_H2 = 2.016e-3  # molar mass of molecular hydrogen, kg per mol

#: Pascals per bar (exact by definition: 1 bar = 10^5 Pa).
PA_PER_BAR = 1.0e5

#: Pascals per megapascal (exact).
PA_PER_MPA = 1.0e6


def bar_to_pa(p):
    """Convert pressure from bar to pascals (Pa).

    Parameters
    ----------
    p : float or numpy.ndarray
        Pressure in bar.

    Returns
    -------
    float or numpy.ndarray
        The same pressure in pascals (Pa).
    """
    return p * PA_PER_BAR


def pa_to_bar(p):
    """Convert pressure from pascals (Pa) to bar.

    Parameters
    ----------
    p : float or numpy.ndarray
        Pressure in pascals (Pa).

    Returns
    -------
    float or numpy.ndarray
        The same pressure in bar.
    """
    return p / PA_PER_BAR


def mpa_to_pa(p):
    """Convert pressure from megapascals (MPa) to pascals (Pa).

    Used at the material-YAML boundary: the Richard-Benard-Chahine AX-21
    parameter table reports the pseudo-saturation pressure p0 in MPa, and
    ``data/materials/ax21.yaml`` preserves the source's native units.

    Parameters
    ----------
    p : float or numpy.ndarray
        Pressure in megapascals (MPa).

    Returns
    -------
    float or numpy.ndarray
        The same pressure in pascals (Pa).
    """
    return p * PA_PER_MPA


def pa_to_mpa(p):
    """Convert pressure from pascals (Pa) to megapascals (MPa).

    Used at the figure boundary: the digitized AX-21 isotherm data and the F2
    plot axis are both in MPa, matching the source figure.

    Parameters
    ----------
    p : float or numpy.ndarray
        Pressure in pascals (Pa).

    Returns
    -------
    float or numpy.ndarray
        The same pressure in megapascals (MPa).
    """
    return p / PA_PER_MPA
