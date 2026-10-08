"""Uncertainty quantification for thermodynamic and system predictions.

Monte Carlo propagation of declared input uncertainty through the system model.
Two layers are sampled, and they have different epistemic standing. The
MATERIAL layer is a covariance recovered from the Gate V2 refit of published
AX-21 data, so it is measured. The ENGINEERING layer is a set of declared
ranges, most of them modeling assumptions rather than reported uncertainties.
Both are specified in ``data/uncertainty.yaml``, which states which is which
for every entry and which this module refuses to load without a justification.

The seeding of the material layer is not a free choice. Gate V2 established
that the modified Dubinin-Astakhov parameters are not recoverable from a single
published isotherm, and the unconstrained fit's covariance is invalid because
its optimizer stopped at an active bound. The pre-registration dated 2026-10-08
in ``docs/validation_plan.md`` therefore fixes the material layer to the
fixed-p0 conditional covariance, with the consequence stated there and repeated
here because it bounds every number this module produces: **the uncertainty is
conditional on p0 and understates the total parameter uncertainty a single
isotherm implies.** Every interval from this module is a lower bound on the
true spread.

One further limit, also from the pre-registration and more important than
anything in this file. This module quantifies the SPREAD of the model's
predictions. It does not quantify the model's BIAS. Gate V3 measured that bias
for the system mass denominator and found the engineering block light by a
factor of about 4.2 against the HSECoE AX-21 anchor, which is an order of
magnitude larger than the widest band declared in the specification. An
interval computed here is an interval about an optimistic central estimate. It
must never be presented as though it bracketed the truth, and no sample size
repairs a documented FAIL.
"""

import math
from dataclasses import dataclass, field, replace

import numpy as np
import yaml

from .constants import DEFAULT_TARGET_USABLE_KG
from .envelope import evaluate_envelope
from .inverse import material_domain_error
from .isotherm import ModifiedDA

#: Distribution families the specification may declare for a scalar parameter.
#: Deliberately short: each one has to be defensible from a source or named as
#: an assumption, and a richer family would invite a shape nobody can justify.
SCALAR_DISTRIBUTIONS = ("uniform", "triangular", "normal")

#: Engineering parameters the sampler knows how to apply, mapped to the object
#: they live on -- ``"engineering"`` for a field of
#: :class:`h2star.system.EngineeringParams`, ``"vessel"`` for one of its nested
#: vessel parameters, ``"material"`` for a field of the material itself.
ENGINEERING_TARGETS = {
    "sigma_allow": "vessel",
    "composite_density": "vessel",
    "liner_areal_mass": "vessel",
    "performance_factor": "vessel",
    "safety_factor": "vessel",
    "mli_k_eff": "engineering",
    "mli_density": "engineering",
    "heat_leak_budget": "engineering",
    "T_env": "engineering",
    "bop_fixed": "engineering",
    "bop_scaling": "engineering",
    "rho_bulk": "material",
    "rho_skel": "material",
}

#: Discard fraction above which a truncated-Gaussian material sample must be
#: reported with the truncation named as a limitation (pre-registration V4.0).
DISCARD_REPORTING_THRESHOLD = 0.01

#: Draws attempted per requested sample before the sampler gives up. Rejection
#: sampling needs headroom; a specification whose mass lies largely outside the
#: physical domain should fail loudly rather than spin.
_MAX_DRAW_FACTOR = 50


@dataclass(frozen=True)
class MaterialSpec:
    """Joint distribution for the material parameters, with its provenance.

    Attributes
    ----------
    parameters : tuple of str
        Material attribute names, in the order of ``mean`` and ``covariance``.
    mean : numpy.ndarray
        Mean vector, each entry in its parameter's SI unit.
    covariance : numpy.ndarray
        Covariance matrix, symmetric and positive definite.
    fixed : dict
        Parameters held at a published value rather than sampled, as
        ``{name: value}`` in SI units.
    status : str
        Whether the covariance is measured or declared.
    citation : str
        Where the covariance came from.
    justification : str
        Why this covariance and not another. Required: the choice between the
        unconstrained and the fixed-p0 covariance is the single most
        consequential decision in this layer.
    """

    parameters: tuple
    mean: np.ndarray = field(repr=False)
    covariance: np.ndarray = field(repr=False)
    fixed: dict
    status: str
    citation: str
    justification: str


@dataclass(frozen=True)
class ScalarSpec:
    """Declared distribution for one scalar engineering parameter.

    Attributes
    ----------
    name : str
        Parameter name; must be a key of :data:`ENGINEERING_TARGETS`.
    distribution : str
        One of :data:`SCALAR_DISTRIBUTIONS`.
    params : dict
        Distribution parameters: ``low``/``high`` for uniform,
        ``low``/``mode``/``high`` for triangular, ``mean``/``sigma`` for
        normal, all in the parameter's SI unit.
    unit : str
        SI unit of the parameter.
    status : str
        ``SOURCED`` or ``MODELING ASSUMPTION``, carried so a reader of the
        results can tell a measured range from a declared one.
    citation : str
        Where the nominal value came from.
    justification : str
        Why this range. Required.
    """

    name: str
    distribution: str
    params: dict
    unit: str
    status: str
    citation: str
    justification: str

    def sample(self, rng, size):
        """Draw ``size`` samples in the parameter's SI unit."""
        p = self.params
        if self.distribution == "uniform":
            return rng.uniform(p["low"], p["high"], size=size)
        if self.distribution == "triangular":
            return rng.triangular(p["low"], p["mode"], p["high"], size=size)
        if self.distribution == "normal":
            return rng.normal(p["mean"], p["sigma"], size=size)
        raise ValueError(  # pragma: no cover - guarded at load time
            f"Unknown distribution {self.distribution!r} for {self.name!r}."
        )

    def bounds(self):
        """Return ``(low, high)`` support bounds for Saltelli sampling.

        A normal distribution has unbounded support, so its bounds are taken as
        the central 99.73% interval (mean +/- 3 sigma). Sobol analysis needs a
        box, and truncating at 3 sigma is stated here rather than left implicit
        in the sensitivity module.
        """
        p = self.params
        if self.distribution in ("uniform", "triangular"):
            return (float(p["low"]), float(p["high"]))
        return (
            float(p["mean"] - 3.0 * p["sigma"]),
            float(p["mean"] + 3.0 * p["sigma"]),
        )


@dataclass(frozen=True)
class UncertaintySpec:
    """The full declared input uncertainty, loaded from YAML.

    Attributes
    ----------
    material : MaterialSpec or None
        Joint material-parameter distribution.
    engineering : tuple of ScalarSpec
        Declared scalar ranges, in file order.
    excluded : dict
        Parameters deliberately not propagated, mapped to the reason. Carried
        with the data so that a zero sensitivity and a deliberate exclusion are
        never confused.
    notes : str
        The specification's own scope statement.
    """

    material: MaterialSpec | None
    engineering: tuple
    excluded: dict
    notes: str

    @property
    def scalar_names(self):
        """Names of the scalar engineering parameters, in file order."""
        return tuple(spec.name for spec in self.engineering)

    @classmethod
    def from_yaml(cls, path):
        """Load and validate an uncertainty specification.

        Parameters
        ----------
        path : str or pathlib.Path
            Path to ``data/uncertainty.yaml`` or an equivalent file.

        Returns
        -------
        UncertaintySpec

        Raises
        ------
        ValueError
            If the file does not parse into a mapping; if any entry lacks a
            ``_justification`` or ``_source``; if a distribution is unknown or
            its parameters are inconsistent; if the material covariance is not
            symmetric positive definite or disagrees with its declared
            one-sigma values; or if a scalar names a parameter the sampler
            cannot apply.

        Notes
        -----
        An entry without a justification is refused rather than defaulted. A
        declared range is a scientific claim about how much a quantity could
        differ, and an undefended one is indistinguishable from a guess once it
        has been propagated into an interval.
        """
        with open(path) as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ValueError(
                f"Uncertainty file {str(path)!r} did not parse into a mapping; "
                f"got {type(data).__name__}."
            )

        material = None
        if "material" in data:
            material = cls._material_from(data["material"], path)

        engineering = tuple(
            cls._scalar_from(name, block, path)
            for name, block in (data.get("engineering") or {}).items()
        )

        excluded = {
            name: (block or {}).get("reason", "")
            for name, block in (data.get("excluded") or {}).items()
        }
        for name, reason in excluded.items():
            if not str(reason).strip():
                raise ValueError(
                    f"Excluded parameter {name!r} in {str(path)!r} has no "
                    f"reason. An exclusion without a reason is indistinguishable "
                    f"from an omission."
                )

        return cls(
            material=material,
            engineering=engineering,
            excluded=excluded,
            notes=str(data.get("notes", "")),
        )

    @staticmethod
    def _material_from(block, path):
        """Build and validate the :class:`MaterialSpec` from its YAML block."""
        for key in ("_justification", "_source"):
            if not str(block.get(key, "")).strip():
                raise ValueError(
                    f"Material block in {str(path)!r} is missing {key!r}."
                )
        if block.get("distribution") != "multivariate_normal":
            raise ValueError(
                f"Material distribution must be 'multivariate_normal'; got "
                f"{block.get('distribution')!r}. The Gate V2 parameters are "
                f"strongly correlated, so sampling marginals independently "
                f"would overstate the information in the fit."
            )

        parameters = tuple(block["parameters"])
        mean = np.asarray(block["mean"], dtype=float)
        cov = np.asarray(block["covariance"], dtype=float)

        if mean.shape != (len(parameters),):
            raise ValueError(
                f"Material mean has shape {mean.shape}, expected "
                f"{(len(parameters),)} for parameters {parameters}."
            )
        if cov.shape != (len(parameters), len(parameters)):
            raise ValueError(
                f"Material covariance has shape {cov.shape}, expected "
                f"{(len(parameters), len(parameters))}."
            )
        if not np.allclose(cov, cov.T, rtol=1e-10, atol=0.0):
            raise ValueError("Material covariance is not symmetric.")
        eigenvalues = np.linalg.eigvalsh(cov)
        if eigenvalues.min() <= 0.0:
            raise ValueError(
                f"Material covariance is not positive definite; smallest "
                f"eigenvalue {eigenvalues.min():.6g}."
            )

        declared_sigma = block.get("one_sigma")
        if declared_sigma is not None:
            if not np.allclose(
                np.sqrt(np.diag(cov)), np.asarray(declared_sigma, dtype=float),
                rtol=1e-6,
            ):
                raise ValueError(
                    "Declared one_sigma disagrees with the covariance "
                    "diagonal. One of the two was edited without the other."
                )

        fixed = {}
        for name, entry in (block.get("fixed") or {}).items():
            if not str((entry or {}).get("_source", "")).strip():
                raise ValueError(
                    f"Fixed material parameter {name!r} in {str(path)!r} has "
                    f"no _source."
                )
            fixed[name] = float(entry["value"])

        return MaterialSpec(
            parameters=parameters,
            mean=mean,
            covariance=cov,
            fixed=fixed,
            status=str(block.get("status", "")),
            citation=str(block["_source"]),
            justification=str(block["_justification"]),
        )

    @staticmethod
    def _scalar_from(name, block, path):
        """Build and validate one :class:`ScalarSpec` from its YAML block."""
        block = block or {}
        for key in ("_justification", "_source"):
            if not str(block.get(key, "")).strip():
                raise ValueError(
                    f"Uncertainty entry {name!r} in {str(path)!r} is missing "
                    f"{key!r}. A declared range without a justification cannot "
                    f"be defended once it has been propagated."
                )
        if name not in ENGINEERING_TARGETS:
            raise ValueError(
                f"Uncertainty entry {name!r} is not a parameter the sampler "
                f"can apply; known parameters are "
                f"{sorted(ENGINEERING_TARGETS)}."
            )

        distribution = block.get("distribution")
        if distribution not in SCALAR_DISTRIBUTIONS:
            raise ValueError(
                f"Entry {name!r} declares distribution {distribution!r}; "
                f"expected one of {list(SCALAR_DISTRIBUTIONS)}."
            )

        if distribution == "uniform":
            required = ("low", "high")
        elif distribution == "triangular":
            required = ("low", "mode", "high")
        else:
            required = ("mean", "sigma")
        missing = [key for key in required if key not in block]
        if missing:
            raise ValueError(
                f"Entry {name!r} ({distribution}) is missing {missing}."
            )
        params = {key: float(block[key]) for key in required}

        if distribution == "uniform" and not params["low"] < params["high"]:
            raise ValueError(
                f"Entry {name!r}: uniform needs low < high; got {params}."
            )
        if distribution == "triangular" and not (
            params["low"] <= params["mode"] <= params["high"]
            and params["low"] < params["high"]
        ):
            raise ValueError(
                f"Entry {name!r}: triangular needs low <= mode <= high with "
                f"low < high; got {params}."
            )
        if distribution == "normal" and params["sigma"] <= 0.0:
            raise ValueError(
                f"Entry {name!r}: normal needs sigma > 0; got {params}."
            )

        return ScalarSpec(
            name=name,
            distribution=distribution,
            params=params,
            unit=str(block.get("unit", "")),
            status=str(block.get("status", "")),
            citation=str(block["_source"]),
            justification=str(block["_justification"]),
        )


@dataclass(frozen=True)
class MaterialSample:
    """A set of material-parameter draws, with its truncation record.

    Attributes
    ----------
    parameters : tuple of str
        Parameter names, matching the columns of ``values``.
    values : numpy.ndarray
        Accepted draws, shape ``(n, len(parameters))``.
    n_requested, n_drawn, n_rejected : int
        Requested sample size, total draws attempted, and draws discarded for
        falling outside the physical domain.
    discard_fraction : float
        ``n_rejected / n_drawn``.
    rejection_reasons : dict
        Counts per rejection reason.
    truncation_material : bool
        ``True`` when the discard fraction exceeds
        :data:`DISCARD_REPORTING_THRESHOLD`, in which case the
        pre-registration requires the truncation to be reported as a
        limitation rather than the result presented as a clean Gaussian
        propagation.
    """

    parameters: tuple
    values: np.ndarray = field(repr=False)
    n_requested: int
    n_drawn: int
    n_rejected: int
    discard_fraction: float
    rejection_reasons: dict
    truncation_material: bool


def sample_material(spec, base_material, n, operating_point, rng):
    """Draw material parameters from the declared joint distribution.

    Samples are drawn from the multivariate normal and screened against the
    physical domain; those outside it are discarded and redrawn. Rejection
    rather than clipping, because clipping would pile probability mass onto the
    domain boundary and report a spurious spike there.

    Parameters
    ----------
    spec : MaterialSpec
        Declared joint distribution.
    base_material : h2star.isotherm.Material
        Material supplying every parameter not sampled or fixed.
    n : int
        Number of accepted samples required.
    operating_point : h2star.envelope.OperatingPoint
        Envelope whose temperatures the characteristic energy must stay
        positive at.
    rng : numpy.random.Generator
        Source of randomness.

    Returns
    -------
    MaterialSample

    Raises
    ------
    ValueError
        If ``n`` is not positive, or if the acceptance rate is so low that the
        sampler cannot reach ``n`` within its draw budget -- which means the
        declared distribution puts most of its mass outside the physical
        domain and should be reconsidered rather than sampled harder.
    """
    if n <= 0:
        raise ValueError(f"n must be positive; got {n}.")

    temperatures = (operating_point.T_full, operating_point.T_empty)
    accepted = []
    reasons = {}
    n_drawn = 0
    budget = _MAX_DRAW_FACTOR * n

    while len(accepted) < n:
        if n_drawn >= budget:
            raise ValueError(
                f"sample_material drew {n_drawn} samples and accepted only "
                f"{len(accepted)} of the {n} required. The declared "
                f"distribution puts most of its mass outside the physical "
                f"domain; rejection reasons so far: {reasons}."
            )
        block = min(max(n, 1024), budget - n_drawn)
        draws = rng.multivariate_normal(spec.mean, spec.covariance, size=block)
        n_drawn += block
        for row in draws:
            overrides = dict(zip(spec.parameters, (float(v) for v in row)))
            overrides.update(spec.fixed)
            candidate = replace(base_material, **overrides)
            reason = material_domain_error(candidate, temperatures)
            if reason is None:
                reason = _void_volume_error(candidate)
            if reason is not None:
                key = reason.split(",")[0][:60]
                reasons[key] = reasons.get(key, 0) + 1
                continue
            accepted.append(row)
            if len(accepted) == n:
                break

    values = np.asarray(accepted[:n], dtype=float)
    n_rejected = sum(reasons.values())
    discard = n_rejected / n_drawn if n_drawn else 0.0

    return MaterialSample(
        parameters=spec.parameters,
        values=values,
        n_requested=n,
        n_drawn=n_drawn,
        n_rejected=n_rejected,
        discard_fraction=discard,
        rejection_reasons=reasons,
        truncation_material=discard > DISCARD_REPORTING_THRESHOLD,
    )


def _void_volume_error(material):
    """Return a reason the packing leaves no void volume, or ``None``.

    Mirrors the tank layer's constraint at the reference packing so that a
    sample can be screened before a system evaluation is attempted. The tank
    layer remains the authority; this is a cheap pre-screen, not a second
    implementation of the physics.
    """
    if material.rho_bulk is None or material.rho_skel is None:
        return None
    void = 1.0 / material.rho_bulk - 1.0 / material.rho_skel - material.v_a
    if void < 0.0:
        return (
            f"void volume {void:.6g} m^3/kg is negative at the reference "
            f"packing: skeleton plus adsorbed phase leave no room for gas"
        )
    return None


def sample_scalars(specs, n, rng):
    """Draw the declared scalar engineering parameters independently.

    Independence is a modeling choice and is stated: no source reports a
    covariance between, say, the composite allowable stress and the MLI
    conductivity, and inventing one would be less defensible than assuming
    none. Where two parameters would be physically coupled, the specification
    excludes one rather than guessing their correlation.

    Parameters
    ----------
    specs : sequence of ScalarSpec
        Declared scalar distributions.
    n : int
        Number of samples.
    rng : numpy.random.Generator
        Source of randomness.

    Returns
    -------
    dict
        ``{name: ndarray of shape (n,)}`` in each parameter's SI unit.
    """
    return {spec.name: spec.sample(rng, n) for spec in specs}


def apply_overrides(base_material, base_engineering, overrides):
    """Return a material and engineering pair with ``overrides`` applied.

    Routes each override to the object it belongs on, per
    :data:`ENGINEERING_TARGETS`, so a caller never has to know whether a
    parameter lives on the material, the engineering block, or its nested
    vessel parameters.

    Parameters
    ----------
    base_material : h2star.isotherm.Material
        Reference material.
    base_engineering : h2star.system.EngineeringParams
        Reference engineering parameters.
    overrides : dict
        ``{name: value}`` in SI units. Material parameters outside
        :data:`ENGINEERING_TARGETS` are also accepted and applied to the
        material, which is how the sampled D-A parameters arrive.

    Returns
    -------
    tuple
        ``(material, engineering)``.

    Raises
    ------
    ValueError
        If a name is neither a known engineering target nor a material field.
    """
    material_overrides = {}
    engineering_overrides = {}
    vessel_overrides = {}

    material_fields = set(vars(base_material))
    for name, value in overrides.items():
        target = ENGINEERING_TARGETS.get(name)
        if target == "vessel":
            vessel_overrides[name] = value
        elif target == "engineering":
            engineering_overrides[name] = value
        elif target == "material" or name in material_fields:
            material_overrides[name] = value
        else:
            raise ValueError(
                f"Override {name!r} is neither a known engineering parameter "
                f"nor a material field."
            )

    material = (
        replace(base_material, **material_overrides)
        if material_overrides
        else base_material
    )
    engineering = base_engineering
    if vessel_overrides:
        engineering = replace(
            engineering, vessel=replace(engineering.vessel, **vessel_overrides)
        )
    if engineering_overrides:
        engineering = replace(engineering, **engineering_overrides)

    return material, engineering


def system_capacities(base_material, base_engineering, overrides,
                      operating_point,
                      target_usable_kg=DEFAULT_TARGET_USABLE_KG):
    """Evaluate ``(GC, VC)`` for one parameter draw, or ``(nan, nan)``.

    The model function the propagation and the sensitivity analysis share.
    Returns ``nan`` rather than raising for a draw the model cannot evaluate,
    because a single impossible draw must not discard a whole sample; the
    caller reports how many failed.

    Parameters
    ----------
    base_material : h2star.isotherm.Material
        Reference material.
    base_engineering : h2star.system.EngineeringParams
        Reference engineering parameters.
    overrides : dict
        Sampled parameter values in SI units.
    operating_point : h2star.envelope.OperatingPoint
        Fixed operating envelope.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg).

    Returns
    -------
    tuple of float
        ``(GC in kg/kg, VC in kg/L)``, or ``(nan, nan)``.
    """
    material, engineering = apply_overrides(
        base_material, base_engineering, overrides
    )
    P_full, T_full, P_empty, T_empty = operating_point.as_tuple()

    if material_domain_error(material, (T_full, T_empty)) is not None:
        return (math.nan, math.nan)

    try:
        budget = evaluate_envelope(
            material,
            ModifiedDA(material),
            engineering,
            P_full,
            T_full,
            P_empty,
            T_empty,
            target_usable_kg=target_usable_kg,
        )
    except (ValueError, ArithmeticError):
        return (math.nan, math.nan)

    gc, vc = budget["GC"], budget["VC"]
    if not (math.isfinite(gc) and math.isfinite(vc)):
        return (math.nan, math.nan)
    return (gc, vc)


def propagate(model_fn, samples):
    """Evaluate a model over a table of samples.

    Parameters
    ----------
    model_fn : callable
        Takes a dict of ``{name: value}`` and returns a float or a sequence of
        floats.
    samples : dict
        ``{name: ndarray of shape (n,)}``; every array the same length.

    Returns
    -------
    numpy.ndarray
        Shape ``(n,)`` for a scalar model, ``(n, k)`` for a model returning
        ``k`` outputs. Failed evaluations are ``nan``.

    Raises
    ------
    ValueError
        If ``samples`` is empty or its arrays differ in length.
    """
    if not samples:
        raise ValueError("samples is empty; nothing to propagate.")
    lengths = {len(v) for v in samples.values()}
    if len(lengths) != 1:
        raise ValueError(
            f"All sample arrays must have the same length; got lengths "
            f"{sorted(lengths)}."
        )
    n = lengths.pop()
    names = list(samples)

    first = model_fn({name: float(samples[name][0]) for name in names})
    scalar = np.isscalar(first) or np.asarray(first).ndim == 0
    width = 1 if scalar else int(np.asarray(first).size)

    out = np.full((n, width), np.nan)
    out[0] = first
    for i in range(1, n):
        out[i] = model_fn({name: float(samples[name][i]) for name in names})

    return out[:, 0] if scalar else out


def summarize(values, target=None):
    """Summarize a propagated output distribution.

    Parameters
    ----------
    values : array_like
        Propagated samples, shape ``(n,)``. ``nan`` entries are excluded from
        the statistics and reported separately.
    target : float, optional
        Threshold for a exceedance probability, in the output's own unit.

    Returns
    -------
    dict
        ``n``, ``n_finite``, ``n_failed``, ``mean``, ``std`` (sample standard
        deviation, ddof=1), ``median``, ``p16``, ``p84``, ``p2_5``, ``p97_5``,
        the 68% and 95% intervals as tuples, and, when ``target`` is given,
        ``p_meets_target``: the fraction of FINITE samples at or above it.

    Raises
    ------
    ValueError
        If no sample is finite. A distribution of nothing has no summary, and
        returning a dict of ``nan`` would let an empty result pass for a real
        one.
    """
    values = np.asarray(values, dtype=float).ravel()
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError(
            f"No finite samples to summarize ({values.size} given, all "
            f"non-finite). Check the model and the declared ranges."
        )

    percentiles = np.percentile(finite, [2.5, 16.0, 50.0, 84.0, 97.5])
    summary = {
        "n": int(values.size),
        "n_finite": int(finite.size),
        "n_failed": int(values.size - finite.size),
        "mean": float(np.mean(finite)),
        "std": float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0,
        "p2_5": float(percentiles[0]),
        "p16": float(percentiles[1]),
        "median": float(percentiles[2]),
        "p84": float(percentiles[3]),
        "p97_5": float(percentiles[4]),
        "interval_68": (float(percentiles[1]), float(percentiles[3])),
        "interval_95": (float(percentiles[0]), float(percentiles[4])),
    }
    if target is not None:
        summary["target"] = float(target)
        summary["p_meets_target"] = float(np.mean(finite >= target))
    return summary


def half_sample_convergence(values, tolerance=0.02):
    """Check Monte Carlo convergence by the half-sample criterion.

    Splits the sample in two halves in draw order and compares the median and
    the 5th and 95th percentiles. Pre-registered (V4.3) as the convergence
    criterion for any reported system-level Monte Carlo result.

    Parameters
    ----------
    values : array_like
        Propagated samples in draw order. ``nan`` entries are dropped first,
        so the halves are equal in finite count rather than in draw count.
    tolerance : float, optional
        Maximum allowed relative disagreement between halves; default 0.02,
        the pre-registered 2%.

    Returns
    -------
    dict
        ``converged`` (bool), ``tolerance``, the three statistics for each
        half, their relative differences, and ``worst_statistic``.

    Raises
    ------
    ValueError
        If fewer than four finite samples are given, which cannot be split
        into two halves with a meaningful percentile each.
    """
    values = np.asarray(values, dtype=float).ravel()
    finite = values[np.isfinite(values)]
    if finite.size < 4:
        raise ValueError(
            f"half_sample_convergence needs at least 4 finite samples; got "
            f"{finite.size}."
        )

    half = finite.size // 2
    first, second = finite[:half], finite[half : 2 * half]
    quantiles = [5.0, 50.0, 95.0]
    labels = ("p5", "median", "p95")

    a = np.percentile(first, quantiles)
    b = np.percentile(second, quantiles)
    with np.errstate(divide="ignore", invalid="ignore"):
        relative = np.where(
            np.abs(a) > 0.0, np.abs(a - b) / np.abs(a), np.abs(a - b)
        )

    worst = int(np.argmax(relative))
    return {
        "converged": bool(np.all(relative <= tolerance)),
        "tolerance": float(tolerance),
        "n_finite": int(finite.size),
        "n_per_half": int(half),
        "first_half": dict(zip(labels, (float(v) for v in a))),
        "second_half": dict(zip(labels, (float(v) for v in b))),
        "relative_difference": dict(zip(labels, (float(v) for v in relative))),
        "worst_statistic": labels[worst],
        "worst_relative_difference": float(relative[worst]),
    }


def propagate_system(spec, base_material, base_engineering, operating_point,
                     n=10_000, *, targets=None, seed=0,
                     target_usable_kg=DEFAULT_TARGET_USABLE_KG,
                     include_material=True, include_engineering=True):
    """Propagate declared input uncertainty through the system model.

    Parameters
    ----------
    spec : UncertaintySpec
        Declared input uncertainty.
    base_material : h2star.isotherm.Material
        Reference material.
    base_engineering : h2star.system.EngineeringParams
        Reference engineering parameters.
    operating_point : h2star.envelope.OperatingPoint
        Fixed operating envelope.
    n : int, optional
        Number of samples; default 10,000, the pre-registered minimum for a
        reported distribution.
    targets : h2star.inverse.Targets, optional
        When given, the summaries carry the probability of meeting each target.
    seed : int, optional
        Seed for the generator, so a reported result is reproducible.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg).
    include_material, include_engineering : bool, optional
        Which layers to sample. Running one at a time is how the material-only
        blur behind claim C5 is separated from the engineering contribution.

    Returns
    -------
    dict
        ``GC`` and ``VC`` sample arrays; ``summary_GC`` and ``summary_VC``;
        ``convergence_GC`` and ``convergence_VC``; ``material_sample`` (or
        ``None``); ``scalar_samples``; ``n_failed``; ``layers``; and
        ``caveat``, the standing scope statement that any report of these
        numbers must carry.

    Raises
    ------
    ValueError
        If neither layer is included, or if the material layer is requested and
        the specification has none.
    """
    if not (include_material or include_engineering):
        raise ValueError(
            "At least one of include_material or include_engineering must be "
            "true; there is nothing to propagate otherwise."
        )
    if include_material and spec.material is None:
        raise ValueError(
            "include_material is true but the specification has no material "
            "block."
        )

    rng = np.random.default_rng(seed)

    material_sample = None
    columns = {}
    if include_material:
        material_sample = sample_material(
            spec.material, base_material, n, operating_point, rng
        )
        for index, name in enumerate(material_sample.parameters):
            columns[name] = material_sample.values[:, index]

    scalar_samples = {}
    if include_engineering:
        scalar_samples = sample_scalars(spec.engineering, n, rng)
        columns.update(scalar_samples)

    fixed = dict(spec.material.fixed) if include_material else {}

    def model(draw):
        overrides = dict(draw)
        overrides.update(fixed)
        return system_capacities(
            base_material,
            base_engineering,
            overrides,
            operating_point,
            target_usable_kg=target_usable_kg,
        )

    results = propagate(model, columns)
    gc, vc = results[:, 0], results[:, 1]

    layers = []
    if include_material:
        layers.append("material")
    if include_engineering:
        layers.append("engineering")

    return {
        "GC": gc,
        "VC": vc,
        "summary_GC": summarize(gc, None if targets is None else targets.gc),
        "summary_VC": summarize(vc, None if targets is None else targets.vc),
        "convergence_GC": half_sample_convergence(gc),
        "convergence_VC": half_sample_convergence(vc),
        "material_sample": material_sample,
        "scalar_samples": scalar_samples,
        "n": int(n),
        "n_failed": int(np.count_nonzero(~np.isfinite(gc))),
        "layers": tuple(layers),
        "operating_point": operating_point,
        "seed": int(seed),
        "caveat": (
            "Spread only, not bias. The material layer is conditional on a "
            "fixed p0 and understates single-isotherm parameter uncertainty; "
            "the system mass denominator is separately known from Gate V3 to "
            "be light by a factor of about 4.2. These intervals surround an "
            "optimistic central estimate and do not bracket the truth."
        ),
    }
