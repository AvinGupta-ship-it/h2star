"""Provenance and machine-readability tests for everything under ``data/``.

Two failure modes motivate this module, and both have actually happened in this
repository.

The first is a data file that is readable to a person and not to a program.
``data/targets/doe_targets.yaml`` shipped on Day 1 with ``source:`` at column 0
and ``targets:`` indented three spaces, which PyYAML rejects. Nobody noticed for
four months because the DOE targets were read off the screen and retyped into
prose; the first attempt to load the file in code, for the acceptability map,
failed on the first line. A file nothing parses is a file nothing checks.

The second is scientific notation without an explicit exponent sign. PyYAML
parses ``1.836e9`` as the *string* ``"1.836e9"``, not as a float, and the
failure is silent until something downstream multiplies by it. The engineering
parameters are written ``1.836e+9`` for exactly this reason, and these tests pin
that every numeric value really is numeric after a round trip through the
loader.

The provenance checks enforce the repository's standing rule that it contains no
number without a source (manual 2.6). The shape of that attribution differs by
file -- a top-level ``citation``, a ``source`` block with a URL, or per-value
``_source`` fields -- so the test accepts any of them and requires at least one.
"""

import csv
from pathlib import Path

import pytest
import yaml

#: Repository root, resolved from this file. Deliberately NOT imported from
#: ``tests.conftest``: that import only resolves when the repository root
#: happens to be on ``sys.path``, which ``python -m pytest`` arranges and a
#: bare ``pytest`` does not. CI runs the bare form, so the import passed
#: locally and failed there.
REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = REPO_ROOT / "data"

#: Every YAML the repository ships under data/.
YAML_FILES = sorted(DATA_DIR.rglob("*.yaml"))

#: The NIST validation tables backing Gate V1.
NIST_CSVS = sorted((DATA_DIR / "validation").glob("nist_h2_*.csv"))


def _load(path):
    """Parse a YAML data file, failing the test with its path on error."""
    with open(path) as fh:
        return yaml.safe_load(fh)


def test_data_directory_is_not_empty():
    """Guard against the globs silently matching nothing."""
    assert YAML_FILES, f"no YAML files found under {DATA_DIR}"
    assert len(NIST_CSVS) == 4, f"expected four NIST isotherms, got {NIST_CSVS}"


@pytest.mark.provenance
@pytest.mark.parametrize("path", YAML_FILES, ids=lambda p: p.name)
def test_every_data_yaml_parses(path):
    """Every shipped YAML loads into a mapping."""
    data = _load(path)
    assert isinstance(data, dict), (
        f"{path.relative_to(REPO_ROOT)} did not parse into a mapping; "
        f"got {type(data).__name__}."
    )


@pytest.mark.provenance
@pytest.mark.parametrize("path", YAML_FILES, ids=lambda p: p.name)
def test_every_data_yaml_carries_provenance(path):
    """Each data file attributes its numbers, in one of the accepted shapes."""
    data = _load(path)

    has_citation = bool(data.get("citation"))
    source = data.get("source")
    has_source_url = isinstance(source, dict) and bool(source.get("url"))
    has_per_value_sources = any(
        isinstance(block, dict)
        and any(k.endswith("_source") and block[k] for k in block)
        for block in data.values()
        if isinstance(block, dict)
    )

    assert has_citation or has_source_url or has_per_value_sources, (
        f"{path.relative_to(REPO_ROOT)} carries no attribution: it needs a "
        f"top-level 'citation', a 'source' block with a 'url', or per-value "
        f"'*_source' fields."
    )
    assert data.get("date_accessed") or (
        isinstance(source, dict) and source.get("date_accessed")
    ), f"{path.relative_to(REPO_ROOT)} is missing a date_accessed."


@pytest.mark.provenance
@pytest.mark.parametrize("path", YAML_FILES, ids=lambda p: p.name)
def test_no_source_field_is_blank(path):
    """A ``*_source`` key present but empty is worse than one absent."""
    data = _load(path)
    blanks = []
    for block_name, block in data.items():
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            if key.endswith("_source") and not str(value).strip():
                blanks.append(f"{block_name}.{key}")
    assert not blanks, (
        f"{path.relative_to(REPO_ROOT)} has empty source fields: {blanks}"
    )


@pytest.mark.provenance
def test_engineering_values_are_numbers_not_strings():
    """Scientific notation in engineering.yaml survives the YAML round trip.

    ``1.836e9`` without the sign parses as a string and fails silently much
    later. Every ``{value, unit}`` entry must come back as a real number.
    """
    data = _load(DATA_DIR / "engineering.yaml")
    offenders = []
    for block_name in ("vessel", "insulation", "bop"):
        for key, entry in data[block_name].items():
            if not isinstance(entry, dict) or "value" not in entry:
                continue
            if not isinstance(entry["value"], (int, float)):
                offenders.append(
                    f"{block_name}.{key} = {entry['value']!r} "
                    f"({type(entry['value']).__name__})"
                )
    assert not offenders, (
        f"engineering.yaml values did not parse as numbers: {offenders}. "
        f"Scientific notation needs an explicit exponent sign, e.g. 1.836e+9."
    )


@pytest.mark.provenance
def test_engineering_entries_declare_units():
    """Every engineering parameter states the unit its value is in."""
    data = _load(DATA_DIR / "engineering.yaml")
    missing = []
    for block_name in ("vessel", "insulation", "bop"):
        for key, entry in data[block_name].items():
            if not isinstance(entry, dict) or "value" not in entry:
                continue
            if not str(entry.get("unit", "")).strip():
                missing.append(f"{block_name}.{key}")
    assert not missing, f"engineering.yaml entries without a unit: {missing}"


@pytest.mark.provenance
@pytest.mark.parametrize("path", NIST_CSVS, ids=lambda p: p.name)
def test_nist_tables_carry_a_provenance_header(path):
    """Each NIST isotherm begins with '#' comment lines naming its source."""
    header = []
    with open(path) as fh:
        for line in fh:
            if not line.startswith("#"):
                break
            header.append(line.lower())
    assert header, f"{path.name} has no '#' provenance header."
    joined = " ".join(header)
    assert "nist" in joined, (
        f"{path.name} header does not name NIST as the source: {header[:2]}"
    )


@pytest.mark.provenance
@pytest.mark.parametrize("path", NIST_CSVS, ids=lambda p: p.name)
def test_nist_tables_are_numeric_and_positive(path):
    """Pressures and densities parse as positive floats on every row."""
    rows = 0
    with open(path) as fh:
        reader = csv.reader(line for line in fh if not line.startswith("#"))
        header = next(reader)
        assert header[0].strip().startswith("pressure"), header
        for row in reader:
            if not row:
                continue
            pressure, density = float(row[0]), float(row[1])
            assert pressure > 0.0 and density > 0.0, (path.name, row)
            rows += 1
    assert rows > 10, f"{path.name} holds only {rows} rows."


@pytest.mark.provenance
def test_digitized_ax21_points_are_bounded_by_the_published_range():
    """The digitized 77 K points lie inside the paper's stated data range.

    ``ax21.yaml`` records the source's validity as 0-6 MPa. A digitized point
    outside that window would mean the wrong figure, or the wrong axis, was
    read -- which is the kind of error that produces a confident, wrong Gate V2
    number.
    """
    path = DATA_DIR / "validation" / "ax21_digitized.csv"
    material = _load(DATA_DIR / "materials" / "ax21.yaml")
    p_lo, p_hi = material["valid_range"]["pressure_MPa"]

    pressures = []
    with open(path) as fh:
        reader = csv.reader(line for line in fh if not line.startswith("#"))
        header = next(reader)
        for row in reader:
            if row:
                pressures.append(float(row[0]))

    assert pressures, f"no digitized points parsed from {path.name}"
    assert min(pressures) >= p_lo, (header, min(pressures), p_lo)
    assert max(pressures) <= p_hi, (header, max(pressures), p_hi)
