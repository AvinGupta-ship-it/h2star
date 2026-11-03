"""Tests for the v1.0 identifiability and UQ machinery."""

import os

import numpy as np
import pytest

from h2star import identifiability as ident
from h2star import isotherm, uq_v1

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data", "validation", "ax21_fig1a_multiT.csv")
AX21 = os.path.join(ROOT, "data", "materials", "ax21.yaml")

THETA_OPT = {
    "n_max": 61.91283, "alpha": 3560.11345, "beta": 16.60159,
    "log10_p0": 9.14954, "v_a": 1.1570e-3,
}


@pytest.fixture(scope="module")
def data():
    return ident.load_dataset(DATA)


@pytest.fixture(scope="module")
def base():
    return isotherm.Material.from_yaml(AX21)


def test_dataset_shape(data):
    T = data[0]
    assert len(T) == 119  # primary supercritical set
    assert set(np.unique(T)) == set(ident.PRIMARY_TEMPS)


def test_sigma_floors(data):
    _, _, _, sP, sn = data
    assert sP.min() >= 0.00492e6 - 1e-6
    assert sn.min() >= 0.0616 - 1e-9


def test_fast_slow_objective_agree(base, data):
    fd = uq_v1.FastData(*data)
    theta = np.array([THETA_OPT[k] for k in uq_v1.PARAM_ORDER])
    fast = uq_v1.mda_objective(theta, fd)
    r = ident.weighted_residuals(THETA_OPT, base, *data)
    assert abs(fast - float(np.sum(r**2))) < 1e-6 * fast


def test_multiT_optimum_regression(base, data):
    r = ident.fit(base, *data)
    assert abs(r["objective"] - 379.679) < 0.05
    assert abs(r["theta"]["n_max"] - 61.913) < 0.05
    assert 9.10 < r["theta"]["log10_p0"] < 9.20


def test_synthetic_recovery(base, data):
    """The weighted fit recovers known parameters from synthetic data."""
    rng = np.random.default_rng(7)
    T, P, _, sP, sn = data
    truth = dict(THETA_OPT)
    iso = isotherm.ModifiedDA(
        __import__("dataclasses").replace(
            base, n_max=truth["n_max"], alpha=truth["alpha"],
            beta=truth["beta"], p0=10 ** truth["log10_p0"],
            v_a=truth["v_a"]))
    n_syn = iso.n_excess(P, T) + rng.normal(0, 0.5 * sn)
    r = ident.fit(base, T, P, n_syn, sP, sn)
    assert abs(r["theta"]["n_max"] - truth["n_max"]) < 1.5
    assert abs(r["theta"]["log10_p0"] - truth["log10_p0"]) < 0.1


def test_profile_crossing_brackets_optimum(base, data):
    lo, hi = ident.profile_crossing(
        base, *data, param="n_max", theta_opt=THETA_OPT, obj0=379.679)
    assert lo < THETA_OPT["n_max"] < hi
    assert hi - lo < 3.0  # multi-T interval is tight (S5 record: 61.2-62.6)


def test_fisher_spectrum_sloppy(base, data):
    w, _ = ident.fisher_spectrum(base, THETA_OPT, *data)
    assert w[0] > 0 and w[-1] > 0
    assert w[0] / w[-1] > 1e3  # eigenvalue spread spans decades (sloppiness)


def test_ess_rhat_on_iid():
    rng = np.random.default_rng(3)
    chains = rng.standard_normal((4, 4000))
    ess, rhat = uq_v1.ess_and_rhat(chains)
    assert ess > 8000
    assert abs(rhat - 1.0) < 0.02
