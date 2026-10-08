"""Global sensitivity analysis of system performance to input parameters.

Variance-based Sobol decomposition (SALib, Saltelli sampling) of system
gravimetric and volumetric capacity with respect to the declared material and
engineering parameters. First-order indices measure each input acting alone;
total-order indices include its interactions. One-at-a-time scans are not
adequate for this model -- an adsorption tank is nonlinear and its parameters
interact through the sizing solve -- which is why the decomposition is
variance-based rather than a tornado plot.

The scientific question this answers is claim C3 (manual 2.12): which material
property most controls system performance, and whether the answer changes
between cryogenic and ambient operation. That is an experimentally actionable
result, since it tells a materials chemist which property to improve first.

Two limits carry into every index this module produces.

The uniform-support substitution. Saltelli sampling needs a box, so each
declared distribution is replaced by a uniform distribution over its support.
A triangular prior and a uniform prior over the same interval put different
weight on the interior, so a Sobol index computed this way answers "how much of
the output variance does this parameter explain, if it is equally likely
anywhere in its declared range?" -- a slightly different question from the one
the Monte Carlo propagation in :mod:`h2star.uq` answers with the declared
shapes. The substitution is standard practice and it is recorded rather than
left implicit; :func:`sobol_indices` reports which parameters it widened.

The Gate V3 bias. The indices rank contributions to the SPREAD of a model whose
absolute level is known to be optimistic by a factor of about 4.2 in the system
mass denominator (manual 4.2). A ranking is a statement about relative
influence and survives that gap better than any absolute capacity does, but the
engineering parameters that drive the biased term are in the sampled set
precisely so the ranking reports honestly how much of the answer rests on them.
"""

import math

import numpy as np

from .constants import DEFAULT_TARGET_USABLE_KG
from .uq import system_capacities

#: Ishigami coefficients, the standard values for the test case.
ISHIGAMI_A = 7.0
ISHIGAMI_B = 0.1


def ishigami(X, a=ISHIGAMI_A, b=ISHIGAMI_B):
    """Evaluate the Ishigami function, the field's standard Sobol test case.

    ``f(x) = sin(x1) + a*sin^2(x2) + b*x3^4*sin(x1)``, with inputs uniform on
    ``[-pi, pi]``. Its variance decomposition is known in closed form, which is
    what makes it a test rather than a demonstration: x3 has a first-order
    index of exactly zero yet a substantial total-order index, so an
    implementation that confused the two, or that missed interactions
    altogether, cannot pass.

    Parameters
    ----------
    X : array_like
        Inputs, shape ``(n, 3)``.
    a, b : float, optional
        Coefficients; defaults are the standard values.

    Returns
    -------
    numpy.ndarray
        Shape ``(n,)``.
    """
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if X.shape[1] != 3:
        raise ValueError(f"Ishigami takes 3 inputs; got shape {X.shape}.")
    x1, x2, x3 = X[:, 0], X[:, 1], X[:, 2]
    return np.sin(x1) + a * np.sin(x2) ** 2 + b * x3**4 * np.sin(x1)


def ishigami_analytic(a=ISHIGAMI_A, b=ISHIGAMI_B):
    """Closed-form Sobol indices for the Ishigami function.

    Derived from the function's Fourier decomposition rather than quoted from a
    secondary source, so the Gate V4 reference values stand on their own:

        V1  = (1/2)(1 + b*pi^4/5)^2
        V2  = a^2/8
        V3  = 0
        V13 = 8*b^2*pi^8/225
        V   = V1 + V2 + V13

    with ``S1 = [V1, V2, V3]/V`` and
    ``ST = [(V1+V13), V2, V13]/V``. x3 enters only through its interaction with
    x1, hence ``S1_3 = 0`` exactly while ``ST_3 > 0``.

    Parameters
    ----------
    a, b : float, optional
        Coefficients; defaults are the standard values.

    Returns
    -------
    dict
        ``variance``, ``S1`` and ``ST`` as arrays of length 3, and the
        component variances ``V1``, ``V2``, ``V3``, ``V13``.
    """
    v1 = 0.5 * (1.0 + b * math.pi**4 / 5.0) ** 2
    v2 = a**2 / 8.0
    v3 = 0.0
    v13 = 8.0 * b**2 * math.pi**8 / 225.0
    total = v1 + v2 + v13
    return {
        "variance": total,
        "V1": v1,
        "V2": v2,
        "V3": v3,
        "V13": v13,
        "S1": np.array([v1 / total, v2 / total, v3 / total]),
        "ST": np.array([(v1 + v13) / total, v2 / total, v13 / total]),
    }


def _saltelli_sample(problem, n, seed):
    """Draw a Saltelli sample, tolerating either SALib API generation."""
    try:  # SALib >= 1.5
        from SALib.sample import sobol as sobol_sample

        return sobol_sample.sample(problem, n, seed=seed,
                                   calc_second_order=False)
    except ImportError:  # pragma: no cover - older SALib
        from SALib.sample import saltelli

        return saltelli.sample(problem, n, calc_second_order=False, seed=seed)


def _sobol_analyze(problem, y, seed):
    """Run the Sobol analysis reproducibly, including its confidence intervals.

    SALib's ``seed`` argument makes the point estimates reproducible but does
    NOT, in the version pinned here, reach the bootstrap resampling that
    produces ``S1_conf`` and ``ST_conf``: two identical calls returned
    confidence intervals differing by up to 38% (0.108 against 0.078 for the
    largest index). Published error bars that change between runs are not
    publishable error bars, so the legacy global generator is seeded here as
    well, which is what the bootstrap draws from.

    Seeding a global RNG inside a library function is not good practice and is
    done deliberately and narrowly: it is the only lever available over
    SALib's internals, the alternative is irreproducible published intervals,
    and the state is restored afterwards so a caller's own stream is not
    disturbed.
    """
    from SALib.analyze import sobol as sobol_analyze

    state = np.random.get_state()
    try:
        np.random.seed(seed)
        return sobol_analyze.analyze(problem, y, calc_second_order=False,
                                     seed=seed, print_to_console=False)
    finally:
        np.random.set_state(state)


def sobol_test_ishigami(n=2**18, seed=0, a=ISHIGAMI_A, b=ISHIGAMI_B):
    """Run the Sobol machinery on the Ishigami function (Gate V4.2).

    Parameters
    ----------
    n : int, optional
        Saltelli base sample size. The pre-registered ladder is
        ``2**14, 2**16, 2**18``, run in that order; the gate is judged at
        ``2**18``.
    seed : int, optional
        Seed, so the gate result is reproducible.
    a, b : float, optional
        Ishigami coefficients.

    Returns
    -------
    dict
        ``S1``, ``ST`` and their SALib confidence estimates; the analytic
        values; the relative errors for the non-zero indices and the absolute
        error for the analytically zero one; ``n`` and ``n_evaluations``.
    """
    problem = {
        "num_vars": 3,
        "names": ["x1", "x2", "x3"],
        "bounds": [[-math.pi, math.pi]] * 3,
    }
    X = _saltelli_sample(problem, n, seed)
    y = ishigami(X, a=a, b=b)
    result = _sobol_analyze(problem, y, seed)

    analytic = ishigami_analytic(a=a, b=b)
    s1 = np.asarray(result["S1"], dtype=float)
    st = np.asarray(result["ST"], dtype=float)

    # x3's first-order index is analytically zero, so a RELATIVE error against
    # it is undefined. The pre-registration declares an absolute tolerance for
    # that one index and relative tolerances for the rest.
    s1_relative = np.array(
        [
            abs(s1[i] - analytic["S1"][i]) / analytic["S1"][i]
            for i in (0, 1)
        ]
    )
    st_relative = np.array(
        [
            abs(st[i] - analytic["ST"][i]) / analytic["ST"][i]
            for i in (0, 1, 2)
        ]
    )

    return {
        "n": int(n),
        "n_evaluations": int(X.shape[0]),
        "S1": s1,
        "ST": st,
        "S1_conf": np.asarray(result["S1_conf"], dtype=float),
        "ST_conf": np.asarray(result["ST_conf"], dtype=float),
        "analytic_S1": analytic["S1"],
        "analytic_ST": analytic["ST"],
        "S1_relative_error": s1_relative,
        "ST_relative_error": st_relative,
        "S1_x3_absolute_error": float(abs(s1[2] - analytic["S1"][2])),
        "worst_relative_error": float(
            max(s1_relative.max(), st_relative.max())
        ),
    }


def build_problem(spec, include_material=True, include_engineering=True):
    """Build the SALib problem definition from an uncertainty specification.

    Each declared distribution is replaced by a uniform distribution over its
    support, because Saltelli sampling requires a box. The substitution is
    reported in the returned mapping so a caller can state it.

    Parameters
    ----------
    spec : h2star.uq.UncertaintySpec
        Declared input uncertainty.
    include_material, include_engineering : bool, optional
        Which layers to include.

    Returns
    -------
    dict
        ``problem`` (the SALib dict), ``names``, ``fixed`` (material
        parameters held at a published value), and ``widened``: the parameters
        whose declared shape was replaced by a uniform over the same support,
        with the shape that was replaced.

    Raises
    ------
    ValueError
        If no parameters would be included, or if the material layer is
        requested and the specification has none.

    Notes
    -----
    The material layer's bounds are taken as the mean +/- 3 sigma of each
    marginal, which DISCARDS the parameter correlation that
    :mod:`h2star.uq` is careful to preserve. Sobol analysis assumes
    independent inputs; with correlations up to 0.97 in this covariance, the
    indices are indices of the independent-input surrogate, not of the fitted
    joint distribution. They answer "which parameter would matter most if these
    could be varied independently?", which is the actionable question for a
    materials chemist, and they are not a decomposition of the Monte Carlo
    variance. Stated here because the distinction decides what claim C3 may
    say.
    """
    names = []
    bounds = []
    widened = {}

    if include_material:
        if spec.material is None:
            raise ValueError(
                "include_material is true but the specification has no "
                "material block."
            )
        sigma = np.sqrt(np.diag(spec.material.covariance))
        for index, name in enumerate(spec.material.parameters):
            lo = spec.material.mean[index] - 3.0 * sigma[index]
            hi = spec.material.mean[index] + 3.0 * sigma[index]
            names.append(name)
            bounds.append([float(lo), float(hi)])
            widened[name] = (
                "multivariate_normal -> uniform over mean +/- 3 sigma; "
                "correlation discarded"
            )

    if include_engineering:
        for scalar in spec.engineering:
            lo, hi = scalar.bounds()
            names.append(scalar.name)
            bounds.append([lo, hi])
            if scalar.distribution != "uniform":
                widened[scalar.name] = (
                    f"{scalar.distribution} -> uniform over the same support"
                )

    if not names:
        raise ValueError("No parameters selected; nothing to analyse.")

    return {
        "problem": {
            "num_vars": len(names),
            "names": names,
            "bounds": bounds,
        },
        "names": tuple(names),
        "fixed": dict(spec.material.fixed) if include_material else {},
        "widened": widened,
    }


def sobol_indices(spec, base_material, base_engineering, operating_point,
                  n=1024, *, seed=0,
                  target_usable_kg=DEFAULT_TARGET_USABLE_KG,
                  include_material=True, include_engineering=True):
    """Sobol indices of system capacity with respect to the declared inputs.

    Parameters
    ----------
    spec : h2star.uq.UncertaintySpec
        Declared input uncertainty.
    base_material : h2star.isotherm.Material
        Reference material.
    base_engineering : h2star.system.EngineeringParams
        Reference engineering parameters.
    operating_point : h2star.envelope.OperatingPoint
        Fixed operating envelope. Running the analysis at two envelopes is how
        the regime question behind claim C3 is answered.
    n : int, optional
        Saltelli base sample size; the model is evaluated
        ``n * (num_vars + 2)`` times.
    seed : int, optional
        Seed, so a reported ranking is reproducible.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg).
    include_material, include_engineering : bool, optional
        Which layers to include.

    Returns
    -------
    dict
        ``names``; ``S1``, ``ST`` and their confidence estimates for ``GC``
        and ``VC``; ``ranking_GC`` and ``ranking_VC``, the parameter names
        ordered by descending total-order index; ``n_evaluations``;
        ``n_failed``; ``widened``; and ``caveat``.

    Raises
    ------
    ValueError
        If more than 5% of model evaluations fail, which would make the
        variance decomposition a decomposition of the surviving subset rather
        than of the declared input space.

    Notes
    -----
    Failed evaluations are replaced by the mean of the finite results so that
    SALib receives a complete array. That is a compromise, and it is why the 5%
    ceiling exists: substituting the mean for a handful of impossible
    parameter combinations perturbs the indices slightly, while substituting it
    for a large fraction would manufacture a result. The failure count is
    returned so it can be reported.
    """
    built = build_problem(
        spec,
        include_material=include_material,
        include_engineering=include_engineering,
    )
    problem = built["problem"]
    names = built["names"]
    fixed = built["fixed"]

    X = _saltelli_sample(problem, n, seed)

    gc = np.empty(X.shape[0])
    vc = np.empty(X.shape[0])
    for row_index, row in enumerate(X):
        overrides = {name: float(value) for name, value in zip(names, row)}
        overrides.update(fixed)
        gc[row_index], vc[row_index] = system_capacities(
            base_material,
            base_engineering,
            overrides,
            operating_point,
            target_usable_kg=target_usable_kg,
        )

    n_failed = int(np.count_nonzero(~np.isfinite(gc)))
    failure_fraction = n_failed / gc.size
    if failure_fraction > 0.05:
        raise ValueError(
            f"{n_failed} of {gc.size} model evaluations failed "
            f"({100 * failure_fraction:.2f}%), above the 5% ceiling. The "
            f"declared bounds reach too far outside the physical domain for a "
            f"variance decomposition over them to be meaningful."
        )

    results = {}
    for label, values in (("GC", gc), ("VC", vc)):
        filled = values.copy()
        if n_failed:
            filled[~np.isfinite(filled)] = np.mean(filled[np.isfinite(filled)])
        analysis = _sobol_analyze(problem, filled, seed)
        s1 = np.asarray(analysis["S1"], dtype=float)
        st = np.asarray(analysis["ST"], dtype=float)
        order = np.argsort(st)[::-1]
        results[f"S1_{label}"] = s1
        results[f"ST_{label}"] = st
        results[f"S1_conf_{label}"] = np.asarray(
            analysis["S1_conf"], dtype=float
        )
        results[f"ST_conf_{label}"] = np.asarray(
            analysis["ST_conf"], dtype=float
        )
        results[f"ranking_{label}"] = tuple(names[i] for i in order)

    results.update(
        {
            "names": names,
            "n": int(n),
            "n_evaluations": int(X.shape[0]),
            "n_failed": n_failed,
            "failure_fraction": float(failure_fraction),
            "operating_point": operating_point,
            "seed": int(seed),
            "widened": built["widened"],
            "layers": tuple(
                label
                for label, included in (
                    ("material", include_material),
                    ("engineering", include_engineering),
                )
                if included
            ),
            "caveat": (
                "Indices are of an independent-input surrogate: Saltelli "
                "sampling requires a box, so declared shapes are widened to "
                "uniforms over their support and the material correlation "
                "(up to 0.97) is discarded. They rank relative influence on "
                "the spread of a model whose absolute level is optimistic by "
                "the Gate V3 factor; they are not a decomposition of the "
                "Monte Carlo variance."
            ),
        }
    )
    return results
