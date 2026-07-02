"""Unit tests for the modified D-A least-squares refit (h2star.fitting).

These are plain unit tests (no ``validation`` marker): they exercise the
fitting machinery (parameter recovery, covariance calibration, input
validation), not a science gate against external data.
"""

from dataclasses import replace

import numpy as np
import pytest

from h2star.fitting import fit_modified_da
from h2star.isotherm import Material, ModifiedDA

TRUTH = Material(
    name="synthetic",
    n_max=71.6,
    alpha=3080.0,
    beta=18.9,
    p0=1.47e9,
    v_a=1.43e-3,
    rho_bulk=300.0,
    citation="synthetic truth for unit test",
)
T = 77.0
P = np.linspace(0.05e6, 6.0e6, 30)


def _perturbed_init():
    return replace(
        TRUTH,
        n_max=TRUTH.n_max * 1.3,
        alpha=TRUTH.alpha * 0.8,
        p0=TRUTH.p0 * 3.0,
        v_a=TRUTH.v_a * 1.3,
    )


def test_noise_free_recovery():
    data = ModifiedDA(TRUTH).n_excess(P, T)
    result = fit_modified_da(P, T, data, _perturbed_init())
    idx = {name: i for i, name in enumerate(result.param_names)}

    assert abs(result.popt[idx["n_max"]] - TRUTH.n_max) / TRUTH.n_max < 1e-3
    assert abs(result.popt[idx["alpha"]] - TRUTH.alpha) / TRUTH.alpha < 1e-3
    assert abs(result.popt[idx["v_a"]] - TRUTH.v_a) / TRUTH.v_a < 1e-3
    assert abs(result.popt[idx["log10_p0"]] - np.log10(1.47e9)) < 1e-3


def test_noisy_recovery_within_2sigma():
    # Seed fixed for determinism; this checks covariance calibration.
    rng = np.random.default_rng(0)
    clean = ModifiedDA(TRUTH).n_excess(P, T)
    data = clean + rng.normal(0.0, 0.5, size=P.shape)
    result = fit_modified_da(P, T, data, _perturbed_init())

    truth_vec = {
        "n_max": TRUTH.n_max,
        "alpha": TRUTH.alpha,
        "log10_p0": np.log10(TRUTH.p0),
        "v_a": TRUTH.v_a,
    }
    for i, name in enumerate(result.param_names):
        assert abs(result.popt[i] - truth_vec[name]) <= 2 * result.perr[i]


def test_shape_mismatch_raises():
    data = ModifiedDA(TRUTH).n_excess(P, T)
    with pytest.raises(ValueError):
        fit_modified_da(P, T, data[:-1], _perturbed_init())


def test_too_few_points_raises():
    P_short = np.linspace(0.05e6, 6.0e6, 5)
    data = ModifiedDA(TRUTH).n_excess(P_short, T)
    with pytest.raises(ValueError):
        fit_modified_da(P_short, T, data, _perturbed_init())
