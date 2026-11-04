"""Identifiability analysis for the modified Dubinin-Astakhov model (v1.0).

Implements the frozen analysis plan of ``docs/preregistration_v1.0.md``
section 6 (DOI 10.5281/zenodo.23931242):

* an explicit measurement-error model with error in pressure as well as
  uptake: per point, ``sigma_eff^2 = sigma_n^2 + (dn/dP)^2 sigma_P^2``, with
  the per-point sigmas from the reconciled dual digitization (never below the
  axis resolution);
* weighted least squares on that model as the objective for all fits;
* profile likelihood for every parameter (Raue et al. 2009), 95% threshold
  ``delta(objective) = 3.84``;
* the Fisher-information eigenvalue spectrum in log-parameter coordinates
  (Gutenkunst et al. 2007);
* single-isotherm (77 K) profiles alongside the multi-temperature ones;
* frozen bounds: n_max (0, 300] mol/kg, alpha (0, 20000] J/mol,
  beta [0, 50] J/(mol K), log10(P0/Pa) in [6.78, 12] (the data maximum;
  sensitivity to removing it reported), v_a [1e-5, 5e-3] m^3/kg.

The primary fit set is the isotherms 60-298 K, clear of the near-critical
region (hydrogen's Tc is 33.145 K: of the excluded low-T isotherms only 30 K
is subcritical; 35-45 K are near-critical supercritical). The 35-45 K
isotherms enter only a labelled sensitivity. Raw cond(J^T J) in native units
is never used as evidence.
"""

import csv
from dataclasses import replace

import numpy as np
from scipy.optimize import least_squares

from .isotherm import ModifiedDA

#: Frozen parameter bounds (pre-registration section 6).
BOUNDS = {
    "n_max": (1e-6, 300.0),
    "alpha": (1e-6, 20000.0),
    "beta": (0.0, 50.0),
    "log10_p0": (6.78, 12.0),
    "v_a": (1.0e-5, 5.0e-3),
}
PARAM_ORDER = ("n_max", "alpha", "beta", "log10_p0", "v_a")

#: 95% profile-likelihood threshold for one parameter (chi-square, 1 dof).
CHI2_95_1DOF = 3.84

#: Primary (supercritical) fit temperatures, K.
PRIMARY_TEMPS = (60.0, 77.0, 93.0, 113.0, 153.0, 213.0, 298.0)


def load_dataset(path, temps=PRIMARY_TEMPS):
    """Load the reconciled multi-temperature dataset.

    Returns ``(T, P, n, sigma_P, sigma_n)`` arrays in SI (P and sigma_P in
    Pa), restricted to ``temps``.
    """
    T, P, n, sP, sn = [], [], [], [], []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            t = float(r["temperature_K"])
            if t not in temps:
                continue
            T.append(t)
            P.append(float(r["pressure_MPa"]) * 1e6)
            n.append(float(r["n_excess_molkg"]))
            sP.append(float(r["sigma_P_MPa"]) * 1e6)
            sn.append(float(r["sigma_n_molkg"]))
    return tuple(np.asarray(x, dtype=float) for x in (T, P, n, sP, sn))


def _material(base, theta):
    """Material with the five fit parameters replaced from ``theta`` dict."""
    return replace(
        base,
        n_max=theta["n_max"],
        alpha=theta["alpha"],
        beta=theta["beta"],
        p0=10.0 ** theta["log10_p0"],
        v_a=theta["v_a"],
    )


def weighted_residuals(theta, base, T, P, n, sP, sn):
    """Error-model residuals ``(model - data) / sigma_eff`` (dimensionless).

    ``sigma_eff^2 = sigma_n^2 + (dn/dP)^2 sigma_P^2`` with the derivative
    evaluated on the model by central differences at each point.
    """
    iso = ModifiedDA(_material(base, theta))
    mod = iso.n_excess(P, T)
    dP = np.maximum(1e-4 * P, 10.0)
    dndP = (iso.n_excess(P + dP, T) - iso.n_excess(np.maximum(P - dP, 1.0), T)
            ) / (dP + np.minimum(dP, P - 1.0))
    sig = np.sqrt(sn**2 + (dndP * sP) ** 2)
    return (mod - n) / sig


def fit(base, T, P, n, sP, sn, free=PARAM_ORDER, fixed=None, x0=None):
    """Weighted fit of the ``free`` parameters; others fixed.

    Returns a dict with the optimum ``theta``, the weighted objective (sum of
    squared error-model residuals), and the scipy result object.
    """
    fixed = dict(fixed or {})
    lo = [BOUNDS[k][0] for k in free]
    hi = [BOUNDS[k][1] for k in free]
    if x0 is None:
        start = {
            "n_max": 71.6, "alpha": 3080.0, "beta": 18.9,
            "log10_p0": 9.167, "v_a": 1.43e-3,
        }
        x0 = [min(max(start[k], lo[i]), hi[i]) for i, k in enumerate(free)]
    scale = {"n_max": 70.0, "alpha": 3000.0, "beta": 19.0,
             "log10_p0": 1.0, "v_a": 1.5e-3}

    def resid(x):
        theta = dict(fixed)
        theta.update({k: v for k, v in zip(free, x)})
        return weighted_residuals(theta, base, T, P, n, sP, sn)

    res = least_squares(
        resid, x0, bounds=(lo, hi),
        x_scale=[scale[k] for k in free], max_nfev=4000,
    )
    theta = dict(fixed)
    theta.update({k: v for k, v in zip(free, res.x)})
    return {"theta": theta, "objective": float(2.0 * res.cost), "res": res}


def profile(base, T, P, n, sP, sn, param, grid, others=PARAM_ORDER,
            theta_opt=None):
    """Profile likelihood over ``param`` at the ``grid`` values.

    Re-optimizes all other parameters at each grid point. To avoid the
    walked-into-a-local-minimum artifact, each point is fit from two starts —
    the previous grid point's conditional optimum (warm start) and the global
    optimum ``theta_opt`` — and the better objective is kept. The grid is
    traversed outward from the value nearest the global optimum.
    Returns a list of ``(value, objective, theta)`` sorted by value.
    """
    free = [k for k in others if k != param]
    if theta_opt is None:
        theta_opt = fit(base, T, P, n, sP, sn)["theta"]
    x_opt = [theta_opt[k] for k in free]
    grid = sorted(float(v) for v in grid)
    i0 = min(range(len(grid)), key=lambda i: abs(grid[i] - theta_opt[param]))
    results = {}

    def run(v, warm):
        best = None
        for x0 in ([warm] if warm is not None else []) + [x_opt]:
            r = fit(base, T, P, n, sP, sn, free=free,
                    fixed={param: v}, x0=list(x0))
            if best is None or r["objective"] < best["objective"]:
                best = r
        return best

    for idx_seq in (range(i0, len(grid)), range(i0 - 1, -1, -1)):
        warm = None
        for i in idx_seq:
            r = run(grid[i], warm)
            warm = [r["theta"][k] for k in free]
            results[grid[i]] = r
    return [(v, results[v]["objective"], results[v]["theta"])
            for v in grid]


def profile_interval(prof, obj_min, threshold=CHI2_95_1DOF):
    """Grid values inside the 95% profile region."""
    inside = [v for v, obj, _ in prof if obj <= obj_min + threshold]
    return (min(inside), max(inside)) if inside else (None, None)


def profile_crossing(base, T, P, n, sP, sn, param, theta_opt, obj0,
                     threshold=CHI2_95_1DOF, rel_tol=1e-3, span=None):
    """Precise 95% interval endpoints by bisection on the profile.

    Walks outward from the optimum in each direction until the profile
    objective exceeds ``obj0 + threshold`` (or a bound is hit), then bisects
    the crossing. Returns ``(lo, hi)``; an endpoint equal to the parameter
    bound means the interval is open at that bound.
    """
    free = [k for k in PARAM_ORDER if k != param]
    x_opt = [theta_opt[k] for k in free]
    lo_b, hi_b = BOUNDS[param]
    v0 = theta_opt[param]
    cache = {}

    def g(v):
        if v not in cache:
            r = fit(base, T, P, n, sP, sn, free=free,
                    fixed={param: v}, x0=list(x_opt))
            cache[v] = r["objective"] - (obj0 + threshold)
        return cache[v]

    def endpoint(direction):
        step = (span or max(abs(v0) * 0.02, (hi_b - lo_b) * 1e-3))
        v = v0
        for _ in range(60):
            nxt = v + direction * step
            nxt = min(max(nxt, lo_b), hi_b)
            if g(nxt) > 0.0:
                a, b = (v, nxt) if direction > 0 else (nxt, v)
                for _ in range(40):
                    mid = 0.5 * (a + b)
                    if (g(mid) > 0.0) == (direction > 0):
                        b = mid
                    else:
                        a = mid
                    if abs(b - a) <= rel_tol * max(abs(mid), 1e-12):
                        break
                return 0.5 * (a + b)
            v = nxt
            if v in (lo_b, hi_b):
                return v  # open at the bound
            step *= 1.8
        return v

    return endpoint(-1.0), endpoint(+1.0)


def fisher_spectrum(base, theta, T, P, n, sP, sn, params=PARAM_ORDER):
    """Fisher-information eigenvalues in log-parameter coordinates.

    J_ij = d r_i / d ln(theta_j) (log10_p0 taken per decade); returns the
    eigenvalues of J^T J, descending, with their eigenvectors.
    """
    r0 = weighted_residuals(theta, base, T, P, n, sP, sn)
    J = np.zeros((r0.size, len(params)))
    for j, k in enumerate(params):
        h = 1e-4 * max(abs(theta[k]), 1e-12)
        tp = dict(theta)
        tp[k] += h
        tm = dict(theta)
        tm[k] -= h
        d = (weighted_residuals(tp, base, T, P, n, sP, sn)
             - weighted_residuals(tm, base, T, P, n, sP, sn)) / (2 * h)
        # d r / d ln theta = theta * d r / d theta  (per-decade for log10_p0)
        J[:, j] = d if k == "log10_p0" else d * theta[k]
    M = J.T @ J
    w, V = np.linalg.eigh(M)
    order = np.argsort(w)[::-1]
    return w[order], V[:, order]
