"""Validation tests for h2star.eos against NIST reference density data.

Each ``data/validation/nist_h2_*.csv`` table holds an isothermal set of
(pressure_bar, density_kg_m3) points for normal hydrogen from the NIST Chemistry
WebBook. For every row we compare ``eos.density`` (CoolProp) against the NIST
density and require a relative error below 0.1 %.
"""

import csv
import re
from pathlib import Path

import pytest

from h2star import eos

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "validation"

# One bar in pascals; equivalent to constants.bar_to_pa (which is a thin wrapper
# around this factor).
BAR_TO_PA = 1e5

# Maximum allowed relative density error (0.1 %).
REL_TOL = 1e-3


def _temperature_from_filename(path):
    """Extract the fixed temperature in kelvin from a nist_h2_<T>K.csv filename."""
    match = re.search(r"nist_h2_(\d+)K\.csv$", path.name)
    if match is None:
        raise ValueError(f"Cannot parse temperature from filename: {path.name}")
    return float(match.group(1))


def _load_isotherm(path):
    """Parse a NIST validation CSV into a list of (pressure_bar, density) rows.

    Skips leading '#' comment lines and the 'pressure_bar,density_kg_m3' header.
    """
    rows = []
    with open(path, newline="") as fh:
        reader = csv.reader(
            line for line in fh if not line.lstrip().startswith("#")
        )
        header = next(reader)
        assert header == ["pressure_bar", "density_kg_m3"], (
            f"Unexpected header {header} in {path.name}"
        )
        for record in reader:
            if not record:
                continue
            pressure_bar, density_kg_m3 = record
            rows.append((float(pressure_bar), float(density_kg_m3)))
    return rows


def _isotherm_cases():
    """Yield (filename, temperature_K) pytest params for each validation table."""
    cases = []
    for temp in (77, 100, 160, 298):
        path = DATA_DIR / f"nist_h2_{temp}K.csv"
        cases.append(pytest.param(path, id=f"{temp}K"))
    return cases


@pytest.mark.validation
@pytest.mark.parametrize("path", _isotherm_cases())
def test_density_matches_nist(path):
    """Model density matches NIST to < 0.1 % relative error at every row."""
    T = _temperature_from_filename(path)
    rows = _load_isotherm(path)
    assert rows, f"No data rows parsed from {path.name}"

    for pressure_bar, nist_density in rows:
        P_pa = pressure_bar * BAR_TO_PA
        model_density = eos.density(P_pa, T)
        rel_err = abs(model_density - nist_density) / nist_density
        assert rel_err < REL_TOL, (
            f"{path.name} @ {pressure_bar} bar, {T} K: "
            f"model={model_density:.6g} kg/m^3, nist={nist_density:.6g} kg/m^3, "
            f"rel_err={rel_err:.2e} >= {REL_TOL:.0e}"
        )
