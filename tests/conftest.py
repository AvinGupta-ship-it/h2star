"""Shared fixtures for the h2star test suite.

The reference AX-21 material and the engineering parameter set are loaded from
the committed data files rather than constructed in code, so a test can never
pass against parameters the repository does not actually ship. Building them
once per session keeps the system-level tests cheap without letting any test
mutate shared state: ``Material`` and ``EngineeringParams`` are frozen
dataclasses, and the acceptability map builds its variants with
``dataclasses.replace`` rather than by assignment.
"""

from pathlib import Path

import pytest

from h2star import isotherm, system

#: Repository root, resolved from this file so the suite runs from any cwd.
REPO_ROOT = Path(__file__).resolve().parents[1]

AX21_YAML = REPO_ROOT / "data" / "materials" / "ax21.yaml"
ENGINEERING_YAML = REPO_ROOT / "data" / "engineering.yaml"
DOE_TARGETS_YAML = REPO_ROOT / "data" / "targets" / "doe_targets.yaml"


@pytest.fixture(scope="session")
def ax21_material():
    """The reference AX-21 material, loaded from the committed YAML."""
    return isotherm.Material.from_yaml(AX21_YAML)


@pytest.fixture(scope="session")
def ax21_isotherm(ax21_material):
    """A modified Dubinin-Astakhov isotherm on the reference AX-21 material."""
    return isotherm.ModifiedDA(ax21_material)


@pytest.fixture(scope="session")
def engineering_params():
    """Vessel, insulation and balance-of-plant parameters, from the YAML."""
    return system.EngineeringParams.from_yaml(ENGINEERING_YAML)


@pytest.fixture(scope="session")
def ax21_envelope_optimum(ax21_material, ax21_isotherm, engineering_params):
    """The optimized operating envelope for AX-21, computed once per session.

    A full optimization is a few thousand system evaluations. Several tests
    interrogate the same optimum from different angles, and recomputing it per
    test would multiply the suite's runtime for no extra coverage: the
    optimizer is deterministic under a fixed seed, which
    ``test_optimum_is_reproducible`` checks separately and cheaply.
    """
    from h2star import envelope

    return envelope.optimize_envelope(
        ax21_material, ax21_isotherm, engineering_params, seed=0
    )
