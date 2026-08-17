"""Thin-wall composite pressure-vessel mass model for H2STAR.

The vessel is a capsule: a cylindrical section of radius ``r`` and length
``L_cyl = LR * r``, closed by two hemispherical caps (together one sphere).
The wall is sized by the hoop-stress relation ``t = SF * P_max * r /
sigma_allow`` and that uniform thickness is applied to both the cylinder and
the caps -- a conservative thin-wall approximation, since the caps could be
thinner. The shell mass is the composite overwrap plus an aluminum liner
counted as an areal mass over the same surface.

A second, independent estimate uses a published performance factor
``PF = P*V/m`` (Pa*m^3/kg) as a cross-check only; it is never a sizing input.

All quantities are SI: pressures in pascals (Pa), volumes in cubic metres
(m^3), lengths in metres (m), masses in kilograms (kg).
"""

from dataclasses import dataclass

import numpy as np
import yaml

#: Units each vessel parameter must declare in the YAML file (values are SI).
_EXPECTED_UNITS = {
    "safety_factor": "dimensionless",
    "sigma_allow": "Pa",
    "aspect_ratio_LR": "dimensionless",
    "composite_density": "kg/m3",
    "liner_areal_mass": "kg/m2",
    "performance_factor": "Pa*m3/kg",
}


@dataclass(frozen=True)
class VesselParams:
    """Immutable container for the vessel-model engineering parameters (SI).

    Attributes
    ----------
    safety_factor : float
        Burst-ratio safety factor SF, dimensionless. The only margin in this
        model; it is applied in :func:`wall_thickness`, never folded into
        ``sigma_allow``.
    sigma_allow : float
        Effective allowable composite stress, Pa (manufacturing knockdowns
        already folded in; SF applied separately).
    aspect_ratio_LR : float
        Cylindrical-section length divided by radius, ``L_cyl / r``,
        dimensionless.
    composite_density : float
        Effective density of the CFRP overwrap, kg/m^3.
    liner_areal_mass : float
        Aluminum liner mass per unit shell area, kg/m^2.
    performance_factor : float
        Published benchmark ``P*V/m``, Pa*m^3/kg (= J/kg). Cross-check only.
    citation : str
        Provenance of the parameter set (required).
    """

    safety_factor: float  # SF, dimensionless
    sigma_allow: float  # effective allowable composite stress, Pa
    aspect_ratio_LR: float  # L_cyl / r, dimensionless
    composite_density: float  # CFRP overwrap density, kg/m^3
    liner_areal_mass: float  # liner mass per shell area, kg/m^2
    performance_factor: float  # P*V/m benchmark, Pa*m^3/kg
    citation: str  # provenance (required)

    @classmethod
    def from_yaml(cls, path):
        """Build a :class:`VesselParams` from an engineering YAML file.

        Parameters
        ----------
        path : str or path-like
            Path to ``data/engineering.yaml``.

        Returns
        -------
        VesselParams
            Parameters in SI units.

        Notes
        -----
        The file must carry a non-empty top-level ``name`` and a ``vessel``
        mapping whose entries are ``{value, unit}`` mappings for
        ``safety_factor``, ``sigma_allow``, ``aspect_ratio_LR``,
        ``composite_density``, ``liner_areal_mass`` and
        ``performance_factor``. Unlike the material files, this file has no
        top-level ``citation``: provenance lives in ``name``/``description``
        plus the per-parameter ``*_source`` strings, which are recorded in
        ``citation`` here. Values are already SI and are taken as-is, but each
        declared ``unit`` is checked against the expected SI string.

        Raises
        ------
        ValueError
            If the top-level ``name`` is missing/empty, or if any parameter
            declares a unit other than the expected SI string.
        """
        with open(path) as fh:
            data = yaml.safe_load(fh)

        # Validate provenance BEFORE touching any numeric value.
        name = data.get("name")
        if not name:
            raise ValueError(
                f"Vessel parameter file {path!r} is missing a non-empty "
                f"top-level 'name'; parameters must be attributable to a "
                f"source."
            )
        description = data.get("description")

        block = data["vessel"]

        values = {}
        for key, expected_unit in _EXPECTED_UNITS.items():
            entry = block[key]
            unit = entry["unit"]
            if unit != expected_unit:
                raise ValueError(
                    f"Unrecognized unit {unit!r} for {key!r} in {path!r}; "
                    f"expected SI unit {expected_unit!r}."
                )
            values[key] = float(entry["value"])

        # Provenance string: file identity plus the per-parameter _source notes.
        sources = [
            f"{key}: {block[key + '_source']}"
            for key in _EXPECTED_UNITS
            if block.get(key + "_source")
        ]
        citation = "; ".join([name, description or "", *sources]).strip()

        return cls(citation=citation, **values)


def radius_from_volume(V_internal, LR):
    """Capsule radius (m) enclosing an internal volume ``V_internal`` (m^3).

    The capsule volume is ``V = pi * r**3 * (LR + 4/3)`` -- cylinder
    ``pi*r^2*(LR*r)`` plus sphere ``(4/3)*pi*r^3`` -- inverted for ``r``.

    Parameters
    ----------
    V_internal : float or array-like
        Internal volume, m^3. Must be strictly positive.
    LR : float
        Cylinder length / radius, dimensionless. Must be strictly positive.

    Returns
    -------
    float or numpy.ndarray
        Radius in m, matching the shape of ``V_internal``.

    Raises
    ------
    ValueError
        If any volume is not strictly positive, or if ``LR <= 0``.
    """
    V = np.asarray(V_internal, dtype=float)
    if np.any(V <= 0.0):
        raise ValueError(
            f"Internal volume V_internal must be strictly positive (m^3); "
            f"got minimum {float(np.min(V))} m^3."
        )
    if LR <= 0.0:
        raise ValueError(
            f"Aspect ratio aspect_ratio_LR must be strictly positive "
            f"(dimensionless); got {LR}."
        )
    r = (V / (np.pi * (LR + 4.0 / 3.0))) ** (1.0 / 3.0)
    if r.ndim == 0:
        return float(r)
    return r


def surface_area(r, LR):
    """Total capsule surface area (m^2) for radius ``r`` (m).

    Cylinder lateral area ``2*pi*r*(LR*r)`` plus sphere ``4*pi*r^2``, i.e.
    ``A = 2*pi*r**2*(LR + 2)``.

    Parameters
    ----------
    r : float or array-like
        Radius, m.
    LR : float
        Cylinder length / radius, dimensionless. Must be strictly positive.

    Returns
    -------
    float or numpy.ndarray
        Surface area in m^2, matching the shape of ``r``.

    Raises
    ------
    ValueError
        If ``LR <= 0``.
    """
    if LR <= 0.0:
        raise ValueError(
            f"Aspect ratio aspect_ratio_LR must be strictly positive "
            f"(dimensionless); got {LR}."
        )
    r = np.asarray(r, dtype=float)
    A = 2.0 * np.pi * r**2 * (LR + 2.0)
    if A.ndim == 0:
        return float(A)
    return A


def wall_thickness(P_max, r, SF, sigma_allow):
    """Thin-wall hoop-stress thickness (m).

    ``t = SF * P_max * r / sigma_allow``. The safety factor is applied here
    and is NOT already contained in ``sigma_allow``.

    Parameters
    ----------
    P_max : float or array-like
        Maximum (design) internal pressure, Pa. Must be strictly positive.
    r : float or array-like
        Capsule radius, m.
    SF : float
        Safety factor, dimensionless.
    sigma_allow : float
        Effective allowable composite stress, Pa. Must be strictly positive.

    Returns
    -------
    float or numpy.ndarray
        Wall thickness in m.

    Raises
    ------
    ValueError
        If any pressure is not strictly positive, or if ``sigma_allow <= 0``.
    """
    P = np.asarray(P_max, dtype=float)
    if np.any(P <= 0.0):
        raise ValueError(
            f"Design pressure P_max must be strictly positive (Pa); got "
            f"minimum {float(np.min(P))} Pa."
        )
    if sigma_allow <= 0.0:
        raise ValueError(
            f"Allowable stress sigma_allow must be strictly positive (Pa); "
            f"got {sigma_allow} Pa."
        )
    t = SF * P * np.asarray(r, dtype=float) / sigma_allow
    if t.ndim == 0:
        return float(t)
    return t


def vessel_mass_hoop(P_max, V_internal, params):
    """Vessel mass (kg) from the hoop-stress geometry route.

    Sizes the capsule from its internal volume, applies the uniform thin-wall
    thickness to the whole shell, and adds the aluminum liner as an areal
    mass over the same surface::

        m = A*t*composite_density + A*liner_areal_mass

    Parameters
    ----------
    P_max : float or array-like
        Maximum (design) internal pressure, Pa. Must be strictly positive.
    V_internal : float or array-like
        Internal volume, m^3. Must be strictly positive.
    params : VesselParams
        Engineering parameters in SI units.

    Returns
    -------
    float or numpy.ndarray
        Vessel (composite shell + liner) mass in kg.

    Raises
    ------
    ValueError
        If ``P_max`` or ``V_internal`` is not strictly positive, or if
        ``params.aspect_ratio_LR`` or ``params.sigma_allow`` is not strictly
        positive.
    """
    LR = params.aspect_ratio_LR
    r = radius_from_volume(V_internal, LR)
    A = surface_area(r, LR)
    t = wall_thickness(P_max, r, params.safety_factor, params.sigma_allow)
    m = A * t * params.composite_density + A * params.liner_areal_mass
    m = np.asarray(m, dtype=float)
    if m.ndim == 0:
        return float(m)
    return m


def vessel_mass_performance_factor(P_max, V_internal, params):
    """Vessel mass (kg) from the performance-factor (PF) cross-check route.

    ``m = P_max * V_internal / PF`` with ``PF = params.performance_factor``
    (Pa*m^3/kg). This is an independent benchmark estimate used only to
    cross-check :func:`vessel_mass_hoop`; it is never a sizing input.

    Parameters
    ----------
    P_max : float or array-like
        Maximum (design) internal pressure, Pa. Must be strictly positive.
    V_internal : float or array-like
        Internal volume, m^3. Must be strictly positive.
    params : VesselParams
        Engineering parameters in SI units.

    Returns
    -------
    float or numpy.ndarray
        Vessel mass in kg.

    Raises
    ------
    ValueError
        If ``P_max`` or ``V_internal`` is not strictly positive, or if
        ``params.performance_factor <= 0``.
    """
    P = np.asarray(P_max, dtype=float)
    V = np.asarray(V_internal, dtype=float)
    if np.any(P <= 0.0):
        raise ValueError(
            f"Design pressure P_max must be strictly positive (Pa); got "
            f"minimum {float(np.min(P))} Pa."
        )
    if np.any(V <= 0.0):
        raise ValueError(
            f"Internal volume V_internal must be strictly positive (m^3); "
            f"got minimum {float(np.min(V))} m^3."
        )
    if params.performance_factor <= 0.0:
        raise ValueError(
            f"Performance factor must be strictly positive (Pa*m^3/kg); got "
            f"{params.performance_factor} Pa*m^3/kg."
        )
    m = P * V / params.performance_factor
    if m.ndim == 0:
        return float(m)
    return m
