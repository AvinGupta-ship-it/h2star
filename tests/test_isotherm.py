"""Tests for the modified Dubinin--Astakhov isotherm (h2star.isotherm).

These are plain unit tests (no ``validation`` marker): they check internal
consistency of the isotherm model rather than agreement with external data.
"""

from pathlib import Path

import numpy as np
import pytest

from h2star.isotherm import Material, ModifiedDA

AX21_YAML = Path(__file__).resolve().parents[1] / "data" / "materials" / "ax21.yaml"


@pytest.fixture(scope="module")
def da():
    return ModifiedDA(Material.from_yaml(AX21_YAML))


def test_excess_approaches_absolute_at_low_P(da):
    # At low pressure the bulk-gas correction is negligible, so excess ~ absolute.
    P = 1e5
    T = 77.0
    n_abs = da.n_absolute(P, T)
    n_exc = da.n_excess(P, T)
    assert n_exc == pytest.approx(n_abs, rel=0.05)


def test_excess_has_interior_maximum_77K(da):
    P = np.linspace(1e5, 2e7, 400)
    n_exc = da.n_excess(P, 77.0)
    idx = int(np.argmax(n_exc))
    assert idx != 0
    assert idx != len(P) - 1


def test_roundtrip_P_n_P(da):
    T = 77.0
    for P in [1e5, 1e6, 5e6, 1e7]:
        n = da.n_absolute(P, T)
        P_rec = da.pressure_at_loading(n, T)
        assert P_rec == pytest.approx(P, rel=1e-6)


def test_from_yaml_requires_citation(tmp_path):
    bad = tmp_path / "no_citation.yaml"
    bad.write_text(
        "name: NoCite\n"
        "parameters:\n"
        "  n_max: {value: 50.0, unit: 'mol/kg'}\n"
        "  alpha: {value: 3000, unit: 'J/mol'}\n"
        "  beta:  {value: 18.0, unit: 'J/(mol*K)'}\n"
        "  p0:    {value: 1000, unit: 'MPa'}\n"
        "  v_a:   {value: 0.001, unit: 'm3/kg'}\n"
    )
    with pytest.raises(ValueError):
        Material.from_yaml(bad)
