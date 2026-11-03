"""v1.0 uncertainty quantification (pre-registration section 7).

Fast, fully vectorized likelihood for the multi-temperature modified-D-A fit
(the bulk-gas density and its pressure derivative at each DATA point do not
depend on the parameters, so they are precomputed once through the EOS and the
sampler runs in pure numpy), an emcee posterior over the frozen section-6
bounds as uniform priors, and alternative isotherm model forms (free-m
modified D-A, and Toth) for the model-form axis of the sensitivity study.

Every reported distribution must carry effective sample size >= 10,000 with
split-half agreement and R-hat < 1.01 (pre-registration section 7); the
runner script checks and records these.
"""

import numpy as np

from . import eos
from .constants import R as R_GAS

#: Frozen bounds (identifiability module is the source of truth; duplicated
#: here in array form for the samplers).
from .identifiability import BOUNDS, PARAM_ORDER  # noqa: F401

LO = np.array([BOUNDS[k][0] for k in PARAM_ORDER])
HI = np.array([BOUNDS[k][1] for k in PARAM_ORDER])


class FastData:
    """Precomputed data arrays for the vectorized likelihood."""

    def __init__(self, T, P, n, sP, sn):
        self.T = np.asarray(T, float)
        self.P = np.asarray(P, float)
        self.n = np.asarray(n, float)
        self.sP = np.asarray(sP, float)
        self.sn = np.asarray(sn, float)
        # Bulk-gas molar density and its dP derivative, parameter-independent.
        self.rho = np.array([eos.molar_density(p, t)
                             for p, t in zip(self.P, self.T)])
        dP = np.maximum(1e-4 * self.P, 10.0)
        hi = np.array([eos.molar_density(p + d, t)
                       for p, d, t in zip(self.P, dP, self.T)])
        lo = np.array([eos.molar_density(max(p - d, 1.0), t)
                       for p, d, t in zip(self.P, dP, self.T)])
        self.drho = (hi - lo) / (dP + np.minimum(dP, self.P - 1.0))


def mda_n_abs(theta, T, P, m=2.0):
    """Modified D-A absolute adsorption (mol/kg), vectorized, pure numpy.

    ``theta = (n_max, alpha, beta, log10_p0, v_a)``; ``m`` is the exponent
    (2 for the baseline form; free in the model-form sensitivity).
    """
    n_max, alpha, beta, lp0, _ = theta
    eps = alpha + beta * T
    x = (R_GAS * T / eps) ** m * np.abs(np.log((10.0 ** lp0) / P)) ** m
    return n_max * np.exp(-x)


def mda_n_excess(theta, data, m=2.0):
    """Excess adsorption at the data points (mol/kg)."""
    return mda_n_abs(theta, data.T, data.P, m=m) - data.rho * theta[4]


def mda_objective(theta, data, m=2.0):
    """Weighted error-model objective (sum of squared sigma-residuals).

    sigma_eff^2 = sigma_n^2 + (d n_ex / dP)^2 sigma_P^2 with the analytic
    model derivative: d n_abs/dP = n_abs * m * (RT/eps)^m
    * |ln(p0/P)|^(m-1) / P  (sign: increasing for P < p0), minus
    d rho/dP * v_a for the excess conversion.
    """
    n_max, alpha, beta, lp0, v_a = theta
    T, P = data.T, data.P
    eps = alpha + beta * T
    L = np.log((10.0 ** lp0) / P)
    base = (R_GAS * T / eps) ** m
    n_abs = n_max * np.exp(-base * np.abs(L) ** m)
    dnabs = n_abs * base * m * np.abs(L) ** (m - 1.0) * np.sign(L) / P
    mod = n_abs - data.rho * v_a
    dmod = dnabs - data.drho * v_a
    sig2 = data.sn**2 + (dmod * data.sP) ** 2
    return float(np.sum((mod - data.n) ** 2 / sig2))


def log_posterior(theta, data):
    """Log-posterior: uniform priors on the frozen bounds, Gaussian error
    model with the theta-dependent sigma_eff (its normalization term kept)."""
    if np.any(theta < LO) or np.any(theta > HI):
        return -np.inf
    n_max, alpha, beta, lp0, v_a = theta
    T, P = data.T, data.P
    eps = alpha + beta * T
    L = np.log((10.0 ** lp0) / P)
    base = (R_GAS * T / eps) ** 2
    n_abs = n_max * np.exp(-base * L**2)
    dnabs = n_abs * base * 2.0 * np.abs(L) * np.sign(L) / P
    mod = n_abs - data.rho * v_a
    dmod = dnabs - data.drho * v_a
    sig2 = data.sn**2 + (dmod * data.sP) ** 2
    return float(-0.5 * np.sum((mod - data.n) ** 2 / sig2
                               + np.log(2.0 * np.pi * sig2)))


def toth_n_excess(theta_t, data):
    """Toth-form excess adsorption (mol/kg), vectorized.

    ``theta_t = (n_max, b0, Q, t_exp, v_a)`` with
    ``b(T) = b0 * exp(Q / (R T))`` (b0 in 1/Pa, Q in J/mol):
    ``n_abs = n_max * b P / (1 + (b P)^t)^(1/t)``.
    """
    n_max, b0, Q, t_exp, v_a = theta_t
    b = b0 * np.exp(Q / (R_GAS * data.T))
    bp = b * data.P
    n_abs = n_max * bp / (1.0 + bp**t_exp) ** (1.0 / t_exp)
    return n_abs - data.rho * v_a


def toth_objective(theta_t, data):
    """Weighted objective for the Toth form (numeric dP derivative)."""
    mod = toth_n_excess(theta_t, data)
    dP = np.maximum(1e-4 * data.P, 10.0)
    d2 = FastShift(data, dP)
    hi = toth_n_excess(theta_t, d2.plus)
    lo = toth_n_excess(theta_t, d2.minus)
    dmod = (hi - lo) / d2.span
    sig2 = data.sn**2 + (dmod * data.sP) ** 2
    return float(np.sum((mod - data.n) ** 2 / sig2))


class FastShift:
    """P-shifted views of a FastData for numeric dP derivatives."""

    def __init__(self, data, dP):
        self.span = dP + np.minimum(dP, data.P - 1.0)

        class _V:
            pass

        self.plus = _V()
        self.plus.T, self.plus.P = data.T, data.P + dP
        self.plus.rho = data.rho + data.drho * dP
        self.minus = _V()
        self.minus.T = data.T
        self.minus.P = np.maximum(data.P - dP, 1.0)
        self.minus.rho = data.rho - data.drho * np.minimum(dP, data.P - 1.0)


def ess_and_rhat(chains):
    """Effective sample size (autocorrelation estimate, summed over chains)
    and split-chain R-hat for a (n_chains, n_steps) array."""
    c = np.asarray(chains, float)
    n_ch, n_st = c.shape
    # split-chain R-hat (Gelman)
    half = n_st // 2
    splits = np.concatenate([c[:, :half], c[:, half:2 * half]], axis=0)
    m, n = splits.shape
    means = splits.mean(axis=1)
    W = splits.var(axis=1, ddof=1).mean()
    B = n * means.var(ddof=1)
    var_plus = (n - 1) / n * W + B / n
    rhat = float(np.sqrt(var_plus / W))
    # ESS via initial positive sequence of the mean autocorrelation
    ess = 0.0
    for row in c:
        x = row - row.mean()
        acf = np.correlate(x, x, "full")[x.size - 1:]
        acf /= acf[0]
        s, t = 1.0, 1
        while t < x.size - 1:
            pair = acf[t] + acf[t + 1] if t + 1 < x.size else acf[t]
            if pair < 0:
                break
            s += 2.0 * acf[t] + (2.0 * acf[t + 1] if t + 1 < x.size else 0.0)
            t += 2
        ess += x.size / s
    return float(ess), rhat
