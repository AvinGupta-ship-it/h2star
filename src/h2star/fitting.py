"""Parameter fitting of thermodynamic models to experimental data.

This module refits the modified Dubinin--Astakhov isotherm to digitized excess
adsorption data by nonlinear least squares (scipy trust-region reflective),
returning fitted parameters with a linearized covariance estimate. See
docs/model_derivations.md Sec. 4 for the objective, covariance, and
identifiability discussion. No gate verdicts are decided here: pass/fail bands
are recorded by the author in docs/validation_plan.md.
"""

import math
import warnings
from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import least_squares

from h2star.isotherm import Material, ModifiedDA


@dataclass(frozen=True)
class FitResult:
    """Result of a modified D-A least-squares refit.

    Attributes
    ----------
    material : Material
        Fitted material (published metadata carried over, fitted parameters
        substituted).
    param_names : tuple
        Names of the fitted parameters, in the order of ``popt``.
    popt : np.ndarray
        Fitted parameter values in fit-vector space
        ``(n_max, alpha, log10_p0, v_a)``.
    perr : np.ndarray
        1-sigma standard errors (sqrt of the covariance diagonal).
    cov : np.ndarray
        Linearized parameter covariance ``s^2 * pinv(J^T J)``.
    correlation : np.ndarray
        Correlation matrix ``cov / outer(perr, perr)``.
    rmse : float
        Root-mean-square of the excess residuals, mol/kg.
    n_points : int
        Number of data points used in the fit.
    dof : int
        Degrees of freedom ``n_points - 4``.
    condition_number : float
        Condition number of ``J^T J`` (conditioning diagnostic).
    success : bool
        Solver success flag from :func:`scipy.optimize.least_squares`.
    message : str
        Solver termination message.
    """

    material: Material
    param_names: tuple
    popt: np.ndarray
    perr: np.ndarray
    cov: np.ndarray
    correlation: np.ndarray
    rmse: float
    n_points: int
    dof: int
    condition_number: float
    success: bool
    message: str


def fit_modified_da(P, T, n_excess_data, material_init):
    """Refit the modified D-A isotherm to excess data at a single temperature.

    Parameters
    ----------
    P : array-like of float
        Pressure at each data point, in pascals (Pa), 1-D.
    T : float
        Temperature, a scalar in kelvin (K).
    n_excess_data : array-like of float
        Measured excess uptake at each pressure, in mol/kg, 1-D and the same
        length as ``P``.
    material_init : Material
        Supplies the initial parameter values, the FIXED ``beta``, and the
        metadata (``name``, ``citation``, densities) carried into the result.

    Returns
    -------
    FitResult
        Fitted parameters, linearized covariance, and diagnostics.

    Notes
    -----
    At a single temperature, ``alpha`` and ``beta`` enter the model only
    through the lump ``E(T) = alpha + beta*T`` and are therefore NOT separately
    identifiable (see docs/model_derivations.md Sec. 4.3). Accordingly ``beta``
    is held fixed at ``material_init.beta`` and the fitted ``alpha`` is
    conditional on that fixed ``beta`` -- algebraically equivalent to fitting
    ``E(T)`` directly.
    """
    P = np.asarray(P, dtype=float)
    n_excess_data = np.asarray(n_excess_data, dtype=float)

    if P.ndim != 1:
        raise ValueError(f"P must be 1-D; got {P.ndim}-D array of shape {P.shape}.")
    if n_excess_data.ndim != 1:
        raise ValueError(
            f"n_excess_data must be 1-D; got {n_excess_data.ndim}-D array of "
            f"shape {n_excess_data.shape}."
        )
    if P.shape != n_excess_data.shape:
        raise ValueError(
            f"P and n_excess_data must have the same length; got {P.shape} "
            f"and {n_excess_data.shape}."
        )
    if P.size < 6:
        raise ValueError(
            f"Need at least 6 data points to fit 4 parameters; got {P.size}."
        )
    if np.any(P <= 0.0):
        raise ValueError(
            f"All pressures must be strictly positive (Pa); got minimum "
            f"{float(np.min(P))} Pa."
        )
    if T <= 0.0:
        raise ValueError(f"Temperature T must be strictly positive (K); got {T}.")

    param_names = ("n_max", "alpha", "log10_p0", "v_a")

    x0 = [
        material_init.n_max,
        material_init.alpha,
        np.log10(material_init.p0),
        material_init.v_a,
    ]
    # log10_p0 >= 7 keeps p0 >= 10 MPa, above the data ceiling.
    bounds = ([1.0, 100.0, 7.0, 1e-5], [300.0, 20000.0, 11.0, 1e-2])
    x_scale = [70.0, 3000.0, 1.0, 1.5e-3]

    def _material_at(theta):
        return replace(
            material_init,
            name=material_init.name + " (refit)",
            n_max=theta[0],
            alpha=theta[1],
            p0=10.0 ** theta[2],
            v_a=theta[3],
        )

    def residual(theta):
        m = _material_at(theta)
        return ModifiedDA(m).n_excess(P, T) - n_excess_data

    res = least_squares(residual, x0, bounds=bounds, x_scale=x_scale, method="trf")

    r = res.fun
    dof = len(P) - 4
    s2 = float(r @ r) / dof

    # Covariance s^2 * (J^T J)^-1, computed from the SVD of J rather than by
    # forming and inverting J^T J: squaring J doubles the condition number and
    # can push a well-scaled but ill-conditioned direction below the pinv
    # truncation threshold, which would silently zero its variance and
    # understate perr. The SVD of J is scale-robust (matches scipy.curve_fit).
    U, s, Vt = np.linalg.svd(res.jac, full_matrices=False)
    thresh = np.finfo(float).eps * max(res.jac.shape) * s[0]
    n_trunc = int(np.sum(s <= thresh))
    if n_trunc:
        warnings.warn(
            f"{n_trunc} singular value(s) at or below threshold; a fitted "
            f"direction is numerically unidentifiable."
        )
    s_inv = np.where(s > thresh, 1.0 / s, 0.0)
    cov = s2 * (Vt.T * s_inv ** 2) @ Vt
    perr = np.sqrt(np.diag(cov))
    correlation = cov / np.outer(perr, perr)
    # Equals cond_2(J^T J) = cond_2(J)^2, computed stably from J's spectrum.
    condition_number = float((s[0] / s[-1]) ** 2)

    rmse_value = float(np.sqrt(np.mean(r ** 2)))
    material_fit = _material_at(res.x)

    return FitResult(
        material=material_fit,
        param_names=param_names,
        popt=np.asarray(res.x, dtype=float),
        perr=perr,
        cov=cov,
        correlation=correlation,
        rmse=rmse_value,
        n_points=len(P),
        dof=dof,
        condition_number=condition_number,
        success=bool(res.success),
        message=str(res.message),
    )


def fit_report(result, material_published):
    """Build a fixed-width text table comparing fitted and published parameters.

    Parameters
    ----------
    result : FitResult
        Output of :func:`fit_modified_da`.
    material_published : Material
        Published reference material for the side-by-side comparison.

    Returns
    -------
    str
        A fixed-width table (this function does not print). One row per
        parameter (``n_max``, ``alpha``, ``beta``, ``p0``, ``v_a``): fitted
        value with +/- 1 sigma, the published value, and the percent
        difference. ``beta`` is reported as fixed (not identifiable at a single
        temperature). ``p0`` is reported in Pa with its 1-sigma expressed in
        decades of ``log10`` and its difference as a ``delta-log10`` rather than
        a percent. No pass/fail language: verdicts live in
        docs/validation_plan.md.
    """
    # Map fit-vector index by name for the identifiable parameters.
    idx = {name: i for i, name in enumerate(result.param_names)}
    popt = result.popt
    perr = result.perr

    n_max_fit = popt[idx["n_max"]]
    n_max_err = perr[idx["n_max"]]
    alpha_fit = popt[idx["alpha"]]
    alpha_err = perr[idx["alpha"]]
    log10_p0_fit = popt[idx["log10_p0"]]
    log10_p0_err = perr[idx["log10_p0"]]
    v_a_fit = popt[idx["v_a"]]
    v_a_err = perr[idx["v_a"]]

    p0_fit = 10.0 ** log10_p0_fit

    def _pct(fit, pub):
        if pub == 0.0:
            return math.nan
        return 100.0 * (fit - pub) / pub

    header = (
        f"{'parameter':<10}{'fitted +/- 1sigma':>28}"
        f"{'published':>16}{'difference':>16}"
    )
    sep = "-" * len(header)
    lines = [header, sep]

    lines.append(
        f"{'n_max':<10}"
        f"{f'{n_max_fit:.4g} +/- {n_max_err:.2g}':>28}"
        f"{f'{material_published.n_max:.4g}':>16}"
        f"{f'{_pct(n_max_fit, material_published.n_max):+.2f}%':>16}"
    )
    lines.append(
        f"{'alpha':<10}"
        f"{f'{alpha_fit:.4g} +/- {alpha_err:.2g}':>28}"
        f"{f'{material_published.alpha:.4g}':>16}"
        f"{f'{_pct(alpha_fit, material_published.alpha):+.2f}%':>16}"
    )
    lines.append(
        f"{'beta':<10}"
        f"{'fixed (not identifiable at single T)':>28}"
        f"{f'{material_published.beta:.4g}':>16}"
        f"{'--':>16}"
    )
    # p0: fitted value in Pa, 1-sigma in decades of log10, diff as delta-log10.
    delta_log10 = log10_p0_fit - math.log10(material_published.p0)
    lines.append(
        f"{'p0':<10}"
        f"{f'{p0_fit:.4g} Pa (+/- {log10_p0_err:.2g} dex)':>28}"
        f"{f'{material_published.p0:.4g}':>16}"
        f"{f'{delta_log10:+.3f} dex':>16}"
    )
    lines.append(
        f"{'v_a':<10}"
        f"{f'{v_a_fit:.4g} +/- {v_a_err:.2g}':>28}"
        f"{f'{material_published.v_a:.4g}':>16}"
        f"{f'{_pct(v_a_fit, material_published.v_a):+.2f}%':>16}"
    )

    lines.append(sep)
    lines.append(f"rmse             = {result.rmse:.4g} mol/kg")
    lines.append(f"n_points         = {result.n_points}")
    lines.append(f"dof              = {result.dof}")
    lines.append(f"condition number = {result.condition_number:.4g}  (J^T J)")

    return "\n".join(lines)
