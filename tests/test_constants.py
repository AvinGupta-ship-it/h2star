"""Tests for h2star.constants: physical constants and pressure conversions.

The conversion helpers are the package's single source of truth for pressure
units (see the module docstring in ``h2star.constants``). These tests pin the
exact factors, the round-trip identity, and the requirement that the helpers
work elementwise on NumPy arrays as well as on scalars -- the vectorized
isotherm and tank routines pass arrays through them.

Note that the Gate V1 and Gate V3 validation tests deliberately keep their own
local bar-to-pascal factor rather than importing these helpers, so that a gate
comparing the model against published reference data does not depend on the
package code it is certifying. That independence is intentional and is not an
oversight to be "fixed".
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from h2star import constants
from h2star.isotherm import Material

#: The AX-21 material file is the project's canonical material-YAML boundary.
_AX21_YAML = Path(__file__).resolve().parents[1] / "data" / "materials" / "ax21.yaml"


def test_gas_constant_value():
    """R matches the CODATA exact value used throughout the package."""
    assert constants.R == pytest.approx(8.314462618, rel=1e-12)


def test_molar_mass_value():
    """M_H2 is the molar mass of molecular hydrogen in kg/mol, not g/mol."""
    assert constants.M_H2 == pytest.approx(2.016e-3, rel=1e-12)


def test_bar_to_pa_known_value():
    """One bar is exactly 1e5 Pa; 100 bar is 1e7 Pa."""
    assert constants.bar_to_pa(1.0) == pytest.approx(1.0e5, rel=1e-15)
    assert constants.bar_to_pa(100.0) == pytest.approx(1.0e7, rel=1e-15)


def test_pa_to_bar_known_value():
    """1e7 Pa is 100 bar."""
    assert constants.pa_to_bar(1.0e7) == pytest.approx(100.0, rel=1e-15)


def test_mpa_to_pa_known_value():
    """The AX-21 p0 of 1470 MPa is 1.47e9 Pa -- the value the gates depend on."""
    assert constants.mpa_to_pa(1470.0) == pytest.approx(1.47e9, rel=1e-15)


def test_pa_to_mpa_known_value():
    """6e6 Pa is 6 MPa, the upper edge of the AX-21 digitized data range."""
    assert constants.pa_to_mpa(6.0e6) == pytest.approx(6.0, rel=1e-15)


@pytest.mark.parametrize("p_bar", [1.0, 5.0, 100.0, 200.0])
def test_bar_pascal_round_trip(p_bar):
    """bar -> Pa -> bar returns the original pressure."""
    assert constants.pa_to_bar(constants.bar_to_pa(p_bar)) == pytest.approx(
        p_bar, rel=1e-15
    )


@pytest.mark.parametrize("p_mpa", [0.1, 6.0, 20.0, 1470.0])
def test_mpa_pascal_round_trip(p_mpa):
    """MPa -> Pa -> MPa returns the original pressure."""
    assert constants.pa_to_mpa(constants.mpa_to_pa(p_mpa)) == pytest.approx(
        p_mpa, rel=1e-15
    )


def test_bar_and_mpa_scales_are_consistent():
    """100 bar and 10 MPa are the same pressure: the two factors differ by 10."""
    assert constants.bar_to_pa(100.0) == pytest.approx(
        constants.mpa_to_pa(10.0), rel=1e-15
    )


def test_conversions_are_elementwise_on_arrays():
    """The helpers pass NumPy arrays through elementwise, returning arrays."""
    p_bar = np.array([1.0, 50.0, 200.0])
    p_pa = constants.bar_to_pa(p_bar)
    assert isinstance(p_pa, np.ndarray)
    np.testing.assert_allclose(p_pa, [1.0e5, 5.0e6, 2.0e7], rtol=1e-15)
    np.testing.assert_allclose(constants.pa_to_bar(p_pa), p_bar, rtol=1e-15)


def test_material_from_yaml_uses_the_mpa_helper():
    """The AX-21 loader routes its MPa->Pa conversion through constants.

    ``Material.from_yaml`` is the project's material-file I/O boundary. This
    test pins that the loaded p0 equals the helper applied to the YAML's native
    value, so a future inline literal creeping back in would fail here rather
    than silently diverging from the single source of truth.
    """
    with open(_AX21_YAML) as fh:
        raw = yaml.safe_load(fh)

    assert raw["parameters"]["p0"]["unit"] == "MPa"
    expected = constants.mpa_to_pa(raw["parameters"]["p0"]["value"])

    material = Material.from_yaml(_AX21_YAML)
    assert material.p0 == pytest.approx(expected, rel=1e-15)
