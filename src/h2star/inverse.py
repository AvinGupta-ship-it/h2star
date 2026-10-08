"""Inverse design: solving for materials/conditions meeting target metrics.

The forward model answers "what would this material deliver?". Inverting it
answers the question the forward direction cannot: *what would a material have
to be* for a complete onboard system to meet the DOE targets? The literature is
almost entirely forward -- it evaluates candidate sorbents -- so a map of the
acceptable region of material-property space is the novel synthesis this
project contributes (manual 2.12, claim C2).

The engine here is deliberately plain. For a fixed operating envelope and a
fixed engineering parameter set, it sweeps two material parameters over a grid,
holds the rest at the reference material's values, and evaluates the full
system budget at every node. The acceptability region is the set of nodes where
the system meets both the gravimetric and the volumetric target at once. No
surrogate, no interpolation: every point on the map is a real system
evaluation, so a reader can recompute any node by hand from
:mod:`h2star.system` and get the same number. :func:`spot_check` exists to make
that check routine rather than aspirational.

Three things to hold in mind when reading a map this module produces.

First, the absolute position of the boundary inherits the Gate V3 gap. The
system mass denominator is an idealized vessel plus a fixed balance-of-plant
mass, light by a factor of about 4.2 against the HSECoE AX-21 anchor (manual
4.2), so the feasible region drawn here is larger than a real system's would
be. What the Gate V3 gap does not move is the *shape* of the boundary, the
*ordering* of materials across it, or the *width* that parameter uncertainty
puts on it -- which is what manual 4.2.3 permits the map to claim.

Second, holding parameters fixed while two vary is a modeling choice with
physical content, not a neutral default. The adsorbed-phase volume ``v_a`` is
the clearest case: assumption A-ISO-4 ties it to ``n_max`` through the
liquid-hydrogen molar volume, so a real material with a larger limiting uptake
would plausibly carry a larger ``v_a`` too. Sweeping ``n_max`` at fixed ``v_a``
therefore traces a slice through parameter space that no single family of real
materials follows. The slice is still the right object -- it answers "what does
this one property buy, all else equal?" -- but it is not a trajectory through
real materials, and it should not be read as one.

Third, not every point in a rectangular grid is a physically coherent material.
Packing more sorbent into a volume than its skeleton and adsorbed phase leave
room for drives the void volume negative, and the tank layer refuses such a
point rather than returning a number. Those nodes come back as ``nan`` and are
reported separately from nodes that are merely infeasible against the targets:
"this material cannot exist" and "this material exists but misses the target"
are different statements and the map keeps them apart.
"""

import math
from dataclasses import dataclass, replace

import numpy as np
import yaml
from scipy.optimize import brentq

from .constants import M_H2
from .envelope import DEFAULT_TARGET_USABLE_KG, OperatingPoint, evaluate_envelope
from .isotherm import ModifiedDA

#: Material attributes the acceptability map is allowed to sweep. Restricted to
#: the modified D-A parameter vector plus the two densities, which is theta in
#: manual 3.4I; sweeping anything else (the citation, the name) is a bug.
SWEEPABLE_PARAMETERS = (
    "n_max",  # limiting absolute adsorption, mol/kg
    "alpha",  # enthalpic factor of the characteristic energy, J/mol
    "beta",  # entropic factor of the characteristic energy, J/(mol*K)
    "p0",  # pseudo-saturation pressure, Pa
    "v_a",  # specific adsorbed-phase volume, m^3/kg
    "rho_bulk",  # packed bulk density, kg/m^3
    "rho_skel",  # skeletal density, kg/m^3
)


@dataclass(frozen=True)
class Targets:
    """A gravimetric and volumetric system target pair.

    Attributes
    ----------
    gc : float
        System gravimetric capacity target, kg H2 per kg of system.
    vc : float
        System volumetric capacity target, kg H2 per litre of system.
    label : str
        Which published tier these came from, carried so a figure caption
        cannot drift from the numbers it labels.
    citation : str
        Source of the targets, required for the same reason material
        parameters carry one.
    """

    gc: float
    vc: float
    label: str
    citation: str

    def __post_init__(self):
        """Reject targets that are not usable system capacities.

        The two numbers are easy to supply in the wrong unit: published tables
        quote gravimetric capacity as a weight percent and volumetric capacity
        in grams per litre, and both are roughly a hundredfold larger than the
        SI fractions this package works in. A target of ``5.5`` instead of
        ``0.055`` would silently make every material infeasible and the map
        would come back empty rather than wrong-looking, so the sanity bound
        is enforced here rather than left to the reader.
        """
        for name, value, ceiling, hint in (
            ("gc", self.gc, 1.0, "kg H2 per kg of system, not weight percent"),
            ("vc", self.vc, 1.0, "kg H2 per litre of system, not g/L"),
        ):
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(
                    f"Target {name} must be a finite positive number; got "
                    f"{value!r}."
                )
            if value >= ceiling:
                raise ValueError(
                    f"Target {name} = {value} is at or above {ceiling}, which "
                    f"is not a physical system capacity. Expected {hint}."
                )
        if not str(self.citation).strip():
            raise ValueError(
                "Targets require a non-empty citation, for the same reason "
                "material parameters do: a number without a source cannot be "
                "checked."
            )


def load_doe_targets(path, tier="2025"):
    """Load a DOE system-target tier from ``data/targets/doe_targets.yaml``.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the DOE targets YAML.
    tier : str, optional
        Which tier to read: ``"2020"``, ``"2025"`` or ``"ultimate"``; default
        ``"2025"``.

    Returns
    -------
    Targets
        The gravimetric and volumetric targets for that tier, in kg/kg and
        kg/L, with the source citation attached.

    Raises
    ------
    ValueError
        If the file is empty or does not parse into a mapping, if it carries no
        source title or URL, if the ``targets`` block or either capacity table
        is missing, or if the requested tier is absent. Targets without
        provenance are not loaded, for the same reason material parameters
        without a citation are not.
    """
    with open(path) as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(
            f"Targets file {str(path)!r} did not parse into a mapping; got "
            f"{type(data).__name__}. An indentation error will do this."
        )

    source = data.get("source") or {}
    title = source.get("title")
    url = source.get("url")
    if not title or not url:
        raise ValueError(
            f"DOE targets file {str(path)!r} is missing a source title or URL; "
            f"targets must be attributable to a published table."
        )

    targets = data.get("targets")
    if not isinstance(targets, dict):
        raise ValueError(
            f"Targets file {str(path)!r} has no 'targets' mapping."
        )
    try:
        gc_table = targets["gravimetric_capacity_kgH2_per_kg_system"]
        vc_table = targets["volumetric_capacity_kgH2_per_L_system"]
    except KeyError as exc:
        raise ValueError(
            f"Targets file {str(path)!r} is missing the capacity table "
            f"{exc.args[0]!r}."
        ) from exc
    for name, table in (("gravimetric", gc_table), ("volumetric", vc_table)):
        if tier not in table:
            raise ValueError(
                f"Tier {tier!r} is not present in the {name} target table; "
                f"available tiers are {sorted(table)}."
            )

    accessed = data.get("source", {}).get("date_accessed", "")
    version = source.get("version", "")
    citation = "; ".join(
        part for part in (title, source.get("publisher", ""), version, url,
                          f"accessed {accessed}" if accessed else "")
        if part
    )

    return Targets(
        gc=float(gc_table[tier]),
        vc=float(vc_table[tier]),
        label=f"DOE {tier}",
        citation=citation,
    )


#: Material attributes that must be finite and strictly positive for the
#: parameter vector to describe a material at all.
_STRICTLY_POSITIVE = ("n_max", "p0", "v_a", "rho_bulk", "rho_skel")


def material_domain_error(material, temperatures):
    """Return why a parameter vector is not a material, or ``None`` if it is.

    ``SWEEPABLE_PARAMETERS`` restricts which attributes a map may vary; this
    restricts what values they may take. Without it a rectangular grid can
    reach points that are not materials and that the downstream model
    nevertheless evaluates to a number: a negative packing density inverts the
    sign of the sorbent mass, shrinks the system mass denominator, and returns
    a gravimetric capacity near unity that the feasibility mask then marks as
    meeting every DOE target. A map is not allowed to report that.

    The checks are the minimum needed for the symbols to mean what the model
    assumes. Void-volume consistency is deliberately left to
    :mod:`h2star.tank`, which already enforces it and whose error message names
    the three terms involved.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Candidate parameter vector.
    temperatures : sequence of float
        Temperatures in kelvin (K) at which the characteristic energy
        ``alpha + beta * T`` must be positive -- in practice the full and
        empty states of the envelope the material will be evaluated at.

    Returns
    -------
    str or None
        A short reason the vector is not a material, or ``None`` when it is.
    """
    for name in _STRICTLY_POSITIVE:
        value = getattr(material, name, None)
        if value is None:
            return f"{name} is not set"
        if not math.isfinite(value) or value <= 0.0:
            return f"{name} must be finite and positive, got {value!r}"

    for name in ("alpha", "beta"):
        if not math.isfinite(getattr(material, name)):
            return f"{name} must be finite, got {getattr(material, name)!r}"

    if material.rho_skel <= material.rho_bulk:
        return (
            f"rho_skel ({material.rho_skel}) must exceed rho_bulk "
            f"({material.rho_bulk}): a packed bed cannot be denser than the "
            f"pore-free solid it is made of"
        )

    for T in temperatures:
        energy = material.alpha + material.beta * T
        if energy <= 0.0:
            return (
                f"characteristic energy alpha + beta*T is {energy:.6g} J/mol "
                f"at {T:g} K; the Dubinin-Astakhov form requires it positive"
            )

    return None


def _validate_sweep(param_x, param_y):
    """Reject sweep parameters that are not part of the material vector."""
    for name in (param_x, param_y):
        if name not in SWEEPABLE_PARAMETERS:
            raise ValueError(
                f"{name!r} is not a sweepable material parameter; choose from "
                f"{list(SWEEPABLE_PARAMETERS)}."
            )
    if param_x == param_y:
        raise ValueError(
            f"param_x and param_y must differ; both are {param_x!r}. A map of "
            f"a parameter against itself is a line, not a region."
        )


def evaluate_material_point(
    base_material,
    engineering,
    overrides,
    operating_point,
    target_usable_kg=DEFAULT_TARGET_USABLE_KG,
):
    """Evaluate the system budget for one point in material-parameter space.

    Builds a variant of ``base_material`` with ``overrides`` applied, rebuilds
    its isotherm, sizes a tank to the mission at ``operating_point``, and
    returns the budget.

    Parameters
    ----------
    base_material : h2star.isotherm.Material
        Reference material; every parameter not in ``overrides`` keeps its
        value, including the citation.
    engineering : h2star.system.EngineeringParams
        Vessel, insulation and balance-of-plant parameters.
    overrides : dict
        Mapping of material attribute name to value, in the attribute's SI
        unit. Keys must be in :data:`SWEEPABLE_PARAMETERS`.
    operating_point : h2star.envelope.OperatingPoint
        Full and empty states.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg); default 5.6 kg.

    Returns
    -------
    dict or None
        The system budget, or ``None`` if this parameter combination is not a
        physically coherent material at this envelope -- a parameter outside
        its physical domain, or a negative void volume from over-dense
        packing, which the tank layer refuses.

    Raises
    ------
    ValueError
        If an override names an attribute outside
        :data:`SWEEPABLE_PARAMETERS`.

    See Also
    --------
    evaluate_material_point_with_reason : same evaluation, keeping the reason
        a point was rejected instead of collapsing it to ``None``.
    """
    budget, _ = evaluate_material_point_with_reason(
        base_material,
        engineering,
        overrides,
        operating_point,
        target_usable_kg=target_usable_kg,
    )
    return budget


def evaluate_material_point_with_reason(
    base_material,
    engineering,
    overrides,
    operating_point,
    target_usable_kg=DEFAULT_TARGET_USABLE_KG,
):
    """Evaluate one material point, returning the budget and why it failed.

    Same evaluation as :func:`evaluate_material_point`, but the second element
    of the returned pair records *why* a point produced nothing. The grid
    engine keeps those reasons so that a sparse map can be explained rather
    than merely observed, and so that an invalid argument is distinguishable
    from a genuinely impossible material.

    Parameters
    ----------
    base_material, engineering, overrides, operating_point, target_usable_kg
        As for :func:`evaluate_material_point`.

    Returns
    -------
    tuple
        ``(budget, reason)``. On success the budget dict and ``None``; on
        failure ``None`` and a short string naming the cause.

    Raises
    ------
    ValueError
        If an override names an attribute outside
        :data:`SWEEPABLE_PARAMETERS`.
    """
    for name in overrides:
        if name not in SWEEPABLE_PARAMETERS:
            raise ValueError(
                f"{name!r} is not a sweepable material parameter; choose from "
                f"{list(SWEEPABLE_PARAMETERS)}."
            )

    material = replace(base_material, **overrides)
    P_full, T_full, P_empty, T_empty = operating_point.as_tuple()

    domain_error = material_domain_error(material, (T_full, T_empty))
    if domain_error is not None:
        return None, domain_error

    isotherm = ModifiedDA(material)
    try:
        budget = evaluate_envelope(
            material,
            isotherm,
            engineering,
            P_full,
            T_full,
            P_empty,
            T_empty,
            target_usable_kg=target_usable_kg,
        )
    except (ValueError, ArithmeticError) as exc:
        return None, f"{type(exc).__name__}: {exc}"

    if not (math.isfinite(budget["GC"]) and math.isfinite(budget["VC"])):
        # A non-finite capacity is never a result. It means a nan propagated
        # through the budget, which must not reach the feasibility mask.
        return None, "model returned a non-finite capacity"

    return budget, None


def acceptability_map(
    base_material,
    engineering,
    param_x,
    param_y,
    x_values,
    y_values,
    *,
    operating_point=None,
    targets,
    target_usable_kg=DEFAULT_TARGET_USABLE_KG,
):
    """Map the region of material-property space that meets system targets.

    Sweeps two material parameters over the outer product of ``x_values`` and
    ``y_values``, holding every other parameter at the reference material's
    value, and evaluates a complete system at each node.

    Parameters
    ----------
    base_material : h2star.isotherm.Material
        Reference material supplying the parameters that are held fixed.
    engineering : h2star.system.EngineeringParams
        Vessel, insulation and balance-of-plant parameters.
    param_x, param_y : str
        Names of the two swept parameters; must be in
        :data:`SWEEPABLE_PARAMETERS` and must differ.
    x_values, y_values : array_like
        Values to sweep, in each parameter's SI unit. ``x`` varies across the
        columns, ``y`` down the rows.
    operating_point : h2star.envelope.OperatingPoint or None, optional
        Operating envelope held fixed across the map. Defaults to the manual's
        baseline, 100 bar / 80 K full and 5 bar / 160 K empty.
    targets : Targets
        The gravimetric and volumetric targets defining acceptability.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg); default 5.6 kg.

    Returns
    -------
    dict
        With keys:

        ``param_x``, ``param_y`` : str
            The swept parameter names.
        ``x_values``, ``y_values`` : ndarray
            The input axes.
        ``GC``, ``VC``, ``V_internal``, ``m_sys`` : ndarray
            Shape ``(n_y, n_x)``; ``nan`` at nodes that are not coherent
            materials.
        ``feasible`` : ndarray of bool
            ``GC >= targets.gc`` and ``VC >= targets.vc``, both. ``nan`` nodes
            are ``False``.
        ``evaluable`` : ndarray of bool
            Whether the node produced a budget at all. Distinguishes "no such
            material" from "material misses the target".
        ``targets`` : Targets
            The targets used, carried with the data.
        ``operating_point`` : h2star.envelope.OperatingPoint
            The envelope used, carried with the data.
        ``target_usable_kg`` : float
            The mission the tanks were sized to, carried so that
            :func:`spot_check` audits the map against the same mission it was
            built with rather than against its own default.
        ``reason_counts`` : dict
            How many nodes each rejection reason accounts for, so a sparse map
            can be explained rather than merely observed.
        ``n_evaluated`` : int
            Nodes that produced a budget. Not the number attempted: the
            attempted count is the array size.
        ``n_feasible`` : int
            Nodes meeting both targets.

    Raises
    ------
    ValueError
        If the swept parameters are invalid or identical.

    Notes
    -----
    An 80x80 grid is 6400 full system evaluations, each a Brent sizing solve
    plus a budget, and runs in well under a minute. There is no surrogate and
    no interpolation anywhere in this function, which is what makes
    :func:`spot_check` a meaningful audit rather than a tautology.
    """
    _validate_sweep(param_x, param_y)
    if operating_point is None:
        operating_point = OperatingPoint(P_full=100.0e5, T_full=80.0)

    # Copy rather than view: np.asarray hands back the caller's own array when
    # it is already float64, and a result that aliases its inputs can be
    # mutated from either side without the other noticing.
    x_values = np.atleast_1d(np.array(x_values, dtype=float, copy=True))
    y_values = np.atleast_1d(np.array(y_values, dtype=float, copy=True))
    for name, axis in (("x_values", x_values), ("y_values", y_values)):
        if axis.ndim != 1:
            raise ValueError(
                f"{name} must be one-dimensional; got shape {axis.shape}. "
                f"acceptability_map builds the outer product itself."
            )

    shape = (y_values.size, x_values.size)

    gc = np.full(shape, np.nan)
    vc = np.full(shape, np.nan)
    vol = np.full(shape, np.nan)
    m_sys = np.full(shape, np.nan)
    evaluable = np.zeros(shape, dtype=bool)
    reason_counts = {}

    for i, y in enumerate(y_values):
        for j, x in enumerate(x_values):
            budget, reason = evaluate_material_point_with_reason(
                base_material,
                engineering,
                {param_x: float(x), param_y: float(y)},
                operating_point,
                target_usable_kg=target_usable_kg,
            )
            if budget is None:
                key = reason.split(";")[0][:80]
                reason_counts[key] = reason_counts.get(key, 0) + 1
                continue
            evaluable[i, j] = True
            gc[i, j] = budget["GC"]
            vc[i, j] = budget["VC"]
            vol[i, j] = budget["V_internal"]
            m_sys[i, j] = budget["m_sys"]

    with np.errstate(invalid="ignore"):
        feasible = (gc >= targets.gc) & (vc >= targets.vc)
    feasible &= evaluable

    return {
        "param_x": param_x,
        "param_y": param_y,
        "x_values": x_values,
        "y_values": y_values,
        "GC": gc,
        "VC": vc,
        "V_internal": vol,
        "m_sys": m_sys,
        "feasible": feasible,
        "evaluable": evaluable,
        "targets": targets,
        "operating_point": operating_point,
        "target_usable_kg": float(target_usable_kg),
        "reason_counts": reason_counts,
        "n_evaluated": int(evaluable.sum()),
        "n_feasible": int(feasible.sum()),
    }


def spot_check(result, base_material, engineering, indices,
               target_usable_kg=None):
    """Recompute named grid nodes from scratch and compare against the map.

    The map engine is a loop, and a loop with a transposed index or a stale
    override would still produce a plausible-looking contour plot. This
    rebuilds the material at the given nodes independently of the stored arrays
    and reports the discrepancy, which is the sanity ritual manual Part VI
    Stage 2 makes mandatory before a map is trusted.

    Parameters
    ----------
    result : dict
        Output of :func:`acceptability_map`.
    base_material : h2star.isotherm.Material
        The same reference material the map was built from.
    engineering : h2star.system.EngineeringParams
        The same engineering parameters.
    indices : sequence of tuple of int
        ``(i, j)`` row/column index pairs to recheck.
    target_usable_kg : float, optional
        Usable-hydrogen mission. Defaults to the one recorded in ``result``,
        which is what makes this an audit: passing a different mission than
        the map was built with produces a mismatch that looks like a map
        defect but is an argument error, so the default is taken from the data
        rather than from a second copy of the constant.

    Returns
    -------
    list of dict
        One record per index with the swept parameter values, the stored and
        recomputed ``GC`` and ``VC``, the absolute differences, and a
        ``matches`` flag. For an evaluable node ``matches`` is ``True`` only on
        exact bitwise equality -- the recomputation runs the identical code
        path on identical inputs, so anything other than an exact match is a
        real defect, not a tolerance question. For a node that is not a
        material, there is no number to compare: ``matches`` is then ``True``
        when the recomputation also rejects the node, the differences are
        reported as ``nan``, and ``nan_node`` is ``True`` so the two kinds of
        agreement are never conflated.

    Raises
    ------
    IndexError
        If an index lies outside the map's grid.
    """
    if target_usable_kg is None:
        target_usable_kg = result.get(
            "target_usable_kg", DEFAULT_TARGET_USABLE_KG
        )

    records = []
    n_y, n_x = result["GC"].shape
    for i, j in indices:
        if not (0 <= i < n_y and 0 <= j < n_x):
            raise IndexError(
                f"index ({i}, {j}) is outside the map grid of shape "
                f"({n_y}, {n_x})."
            )
        x = float(result["x_values"][j])
        y = float(result["y_values"][i])
        budget, reason = evaluate_material_point_with_reason(
            base_material,
            engineering,
            {result["param_x"]: x, result["param_y"]: y},
            result["operating_point"],
            target_usable_kg=target_usable_kg,
        )
        stored_gc = float(result["GC"][i, j])
        stored_vc = float(result["VC"][i, j])
        stored_evaluable = bool(result["evaluable"][i, j])

        if budget is None:
            records.append(
                {
                    "index": (i, j),
                    result["param_x"]: x,
                    result["param_y"]: y,
                    "stored_GC": stored_gc,
                    "recomputed_GC": float("nan"),
                    "stored_VC": stored_vc,
                    "recomputed_VC": float("nan"),
                    "dGC": float("nan"),
                    "dVC": float("nan"),
                    "nan_node": True,
                    "reason": reason,
                    "matches": not stored_evaluable,
                }
            )
            continue
        records.append(
            {
                "index": (i, j),
                result["param_x"]: x,
                result["param_y"]: y,
                "stored_GC": stored_gc,
                "recomputed_GC": budget["GC"],
                "stored_VC": stored_vc,
                "recomputed_VC": budget["VC"],
                "dGC": abs(stored_gc - budget["GC"]),
                "dVC": abs(stored_vc - budget["VC"]),
                "nan_node": False,
                "reason": None,
                "matches": (
                    stored_evaluable
                    and stored_gc == budget["GC"]
                    and stored_vc == budget["VC"]
                ),
            }
        )
    return records


def conditional_material_distribution(spec_material, fixed_values):
    """Conditional distribution of the unswept material parameters.

    When the acceptability map fixes two parameters as its axes, the
    uncertainty that remains at a grid node is the uncertainty in the OTHER
    parameters *given* those two -- not their marginal uncertainty. With
    pairwise correlations up to 0.97 in the Gate V2 covariance the difference is
    large, and using the marginals would both overstate the spread and ignore
    what the fit says about how the parameters move together.

    This is also, incidentally, the honest answer to the objection in this
    module's docstring that sweeping ``n_max`` at fixed ``v_a`` traces a slice
    no real material follows. Conditioning lets ``v_a`` follow ``n_max`` along
    the direction the fit actually found, rather than pinning it.

    Parameters
    ----------
    spec_material : h2star.uq.MaterialSpec
        Joint distribution over the material parameters.
    fixed_values : dict
        ``{parameter_name: value}`` for the parameters being conditioned on;
        must be a subset of ``spec_material.parameters``.

    Returns
    -------
    dict
        ``parameters`` (the remaining names, in the spec's order), ``mean``
        and ``covariance`` of the conditional distribution, and
        ``variance_reduction``: one minus the ratio of conditional to marginal
        variance, per remaining parameter, which is how much the fit's
        correlation structure constrains each one once the axes are pinned.

    Raises
    ------
    ValueError
        If ``fixed_values`` names a parameter the distribution does not cover,
        or if it would leave nothing to condition.
    """
    names = list(spec_material.parameters)
    unknown = [name for name in fixed_values if name not in names]
    if unknown:
        raise ValueError(
            f"Cannot condition on {unknown}: not in the material distribution "
            f"{tuple(names)}."
        )
    fixed_index = [names.index(name) for name in fixed_values]
    free_index = [i for i in range(len(names)) if i not in fixed_index]
    if not free_index:
        raise ValueError(
            "Conditioning on every parameter leaves no distribution; the "
            "material would be fully determined by the grid axes."
        )

    mean = np.asarray(spec_material.mean, dtype=float)
    cov = np.asarray(spec_material.covariance, dtype=float)

    s_aa = cov[np.ix_(free_index, free_index)]
    s_ab = cov[np.ix_(free_index, fixed_index)]
    s_bb = cov[np.ix_(fixed_index, fixed_index)]

    gain = s_ab @ np.linalg.inv(s_bb)
    observed = np.array(
        [float(fixed_values[names[i]]) for i in fixed_index], dtype=float
    )
    cond_mean = mean[free_index] + gain @ (observed - mean[fixed_index])
    cond_cov = s_aa - gain @ cov[np.ix_(fixed_index, free_index)]

    # Symmetrize against accumulated floating-point asymmetry; the Schur
    # complement is symmetric in exact arithmetic.
    cond_cov = 0.5 * (cond_cov + cond_cov.T)

    marginal = np.diag(s_aa)
    with np.errstate(divide="ignore", invalid="ignore"):
        reduction = np.where(marginal > 0.0, 1.0 - np.diag(cond_cov) / marginal, 0.0)

    return {
        "parameters": tuple(names[i] for i in free_index),
        "mean": cond_mean,
        "covariance": cond_cov,
        "variance_reduction": reduction,
    }


def _probability_node(args):
    """Evaluate one grid node of :func:`probability_map`.

    Kept at module level and taking a single tuple so a node is a
    self-contained unit of work. The node's randomness comes from a seed
    sequence derived from its own ``(i, j)`` grid index, so its result does not
    depend on the order the grid is traversed in -- which is what makes the map
    reproducible and would let it be parallelized.

    It is NOT parallelized here, deliberately. A process pool inside a library
    function needs the caller's module to be import-safe, and a caller that
    runs this from a script without an ``if __name__ == "__main__"`` guard gets
    recursive process spawning rather than a speedup. On the two-core
    environment this project runs in, that risk buys under a factor of two, and
    the clean-room reproduction has to be robust more than it has to be fast.
    """
    (
        i,
        j,
        node,
        sample_names,
        mean,
        cov,
        base_material,
        engineering,
        fixed,
        operating_point,
        targets,
        n_samples,
        entropy,
        target_usable_kg,
    ) = args

    temperatures = (operating_point.T_full, operating_point.T_empty)
    child = np.random.default_rng(
        np.random.SeedSequence(entropy=entropy, spawn_key=(i, j))
    )
    draws = (
        child.multivariate_normal(mean, cov, size=n_samples)
        if len(sample_names)
        else np.zeros((n_samples, 0))
    )

    gcs, vcs = [], []
    for row in draws:
        overrides = dict(node)
        overrides.update(zip(sample_names, (float(v) for v in row)))
        overrides.update(fixed)
        candidate = replace(base_material, **overrides)
        if material_domain_error(candidate, temperatures) is not None:
            continue
        try:
            budget = evaluate_envelope(
                candidate,
                ModifiedDA(candidate),
                engineering,
                *operating_point.as_tuple(),
                target_usable_kg=target_usable_kg,
            )
        except (ValueError, ArithmeticError):
            continue
        if not (math.isfinite(budget["GC"]) and math.isfinite(budget["VC"])):
            continue
        gcs.append(budget["GC"])
        vcs.append(budget["VC"])

    if not gcs:
        return (i, j, 0, math.nan, math.nan, math.nan, math.nan, math.nan)

    gc_array = np.asarray(gcs)
    vc_array = np.asarray(vcs)
    # Probabilities are over the DRAWN samples, not the survivors: a node whose
    # samples are mostly incoherent has a low probability of yielding a
    # material that meets the targets, and dividing by the survivors would
    # report the opposite.
    return (
        i,
        j,
        len(gcs),
        float(np.count_nonzero((gc_array >= targets.gc) & (vc_array >= targets.vc)) / n_samples),
        float(np.count_nonzero(gc_array >= targets.gc) / n_samples),
        float(np.count_nonzero(vc_array >= targets.vc) / n_samples),
        float(np.median(gc_array)),
        float(np.median(vc_array)),
    )


def probability_map(spec, base_material, engineering, param_x, param_y,
                    x_values, y_values, *, operating_point=None, targets,
                    n_samples=1000, seed=0,
                    target_usable_kg=DEFAULT_TARGET_USABLE_KG,
                    conditional=True, progress=None):
    """Monte Carlo probability that a material at each grid node meets targets.

    The signature result (manual 2.10 F6, 4.3). At each node the two swept
    parameters are held at the node's coordinates and the remaining uncertain
    material parameters are sampled, giving the probability that a material
    measured to sit at that point would meet both DOE targets. The boundary
    becomes a probability band rather than a line, which is the only defensible
    form given that Gate V2 found the parameters non-identifiable from a single
    published isotherm.

    Only the MATERIAL layer is sampled here, because claim C5 is specifically
    that material-parameter uncertainty *alone* blurs the boundary. Mixing in
    the engineering layer would make the band wider and the claim weaker.

    Parameters
    ----------
    spec : h2star.uq.UncertaintySpec
        Declared input uncertainty; its material block is used.
    base_material : h2star.isotherm.Material
        Reference material supplying parameters neither swept nor sampled.
    engineering : h2star.system.EngineeringParams
        Engineering parameters, held at their nominal values.
    param_x, param_y : str
        Swept parameters, forming the axes.
    x_values, y_values : array_like
        Grid coordinates in each parameter's SI unit.
    operating_point : h2star.envelope.OperatingPoint, optional
        Fixed envelope; defaults to the 100 bar / 80 K baseline.
    targets : h2star.inverse.Targets
        Targets defining feasibility.
    n_samples : int, optional
        Material samples per node; default 1000, the pre-registered minimum.
    seed : int, optional
        Base seed. Each node draws from its own child generator, so the map is
        reproducible and a node's result does not depend on grid traversal
        order.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg).
    conditional : bool, optional
        When ``True`` (default), the unswept material parameters are sampled
        from their distribution *conditional* on the node's coordinates, so
        they follow the correlation the fit found. When ``False``, they are
        sampled from their marginal distribution about the fit mean, which
        ignores that correlation; retained for the comparison that shows how
        much the correlation matters.
    progress : callable, optional
        Called as ``progress(done, total)`` as nodes complete. The map is the
        most expensive routine in the package -- a node is ``n_samples``
        system evaluations, each a Brent sizing solve -- so a caller running a
        publication-sized grid will want it.

    Returns
    -------
    dict
        The axes; ``probability`` (shape ``(n_y, n_x)``), the fraction of
        samples meeting both targets at each node; ``p_gc`` and ``p_vc``, the
        same for each target separately; ``n_valid``, how many samples at each
        node were coherent materials; ``median_GC`` and ``median_VC``;
        ``variance_reduction`` from the conditioning; and the metadata and
        caveat needed to report the figure.

    Raises
    ------
    ValueError
        If the specification has no material block, if the swept parameters are
        invalid, or if ``n_samples`` is not positive.

    Notes
    -----
    Nodes where no sample is a coherent material report ``nan`` probability
    and ``n_valid`` of zero, which is distinct from a probability of zero. The
    distinction matters here more than usual: conditioning makes ``v_a`` grow
    with ``n_max`` along the fitted direction, and far enough out that implies
    an adsorbed phase larger than the pore volume -- so the high-uptake corner
    is *incoherent* under this fit's correlation structure rather than merely
    infeasible. That is a finding about extrapolating the fit, and collapsing
    it into "probability zero" would hide it.
    """
    if spec.material is None:
        raise ValueError("The specification has no material block to sample.")
    _validate_sweep(param_x, param_y)
    if n_samples <= 0:
        raise ValueError(f"n_samples must be positive; got {n_samples}.")
    if operating_point is None:
        operating_point = OperatingPoint(P_full=100.0e5, T_full=80.0)

    x_values = np.atleast_1d(np.array(x_values, dtype=float, copy=True))
    y_values = np.atleast_1d(np.array(y_values, dtype=float, copy=True))
    shape = (y_values.size, x_values.size)

    probability = np.full(shape, np.nan)
    p_gc = np.full(shape, np.nan)
    p_vc = np.full(shape, np.nan)
    n_valid = np.zeros(shape, dtype=int)
    median_gc = np.full(shape, np.nan)
    median_vc = np.full(shape, np.nan)

    swept = {param_x, param_y}
    material_names = set(spec.material.parameters)
    conditioned = swept & material_names
    reduction = None

    entropy = np.random.SeedSequence(seed).entropy

    tasks = []
    for i, y in enumerate(y_values):
        for j, x in enumerate(x_values):
            node = {param_x: float(x), param_y: float(y)}

            if conditional and conditioned:
                conditional_spec = conditional_material_distribution(
                    spec.material, {k: node[k] for k in conditioned}
                )
                sample_names = conditional_spec["parameters"]
                mean = conditional_spec["mean"]
                cov = conditional_spec["covariance"]
                reduction = conditional_spec["variance_reduction"]
            else:
                free = [
                    k for k in spec.material.parameters if k not in conditioned
                ]
                keep = [spec.material.parameters.index(k) for k in free]
                sample_names = tuple(free)
                mean = np.asarray(spec.material.mean)[keep]
                cov = np.asarray(spec.material.covariance)[np.ix_(keep, keep)]

            tasks.append(
                (
                    i,
                    j,
                    node,
                    sample_names,
                    mean,
                    cov,
                    base_material,
                    engineering,
                    dict(spec.material.fixed),
                    operating_point,
                    targets,
                    int(n_samples),
                    entropy,
                    float(target_usable_kg),
                )
            )

    outcomes = []
    for count, task in enumerate(tasks, 1):
        outcomes.append(_probability_node(task))
        if progress is not None:
            progress(count, len(tasks))

    for i, j, valid, p_both, pg, pv, mgc, mvc in outcomes:
        n_valid[i, j] = valid
        if valid:
            probability[i, j] = p_both
            p_gc[i, j] = pg
            p_vc[i, j] = pv
            median_gc[i, j] = mgc
            median_vc[i, j] = mvc

    return {
        "param_x": param_x,
        "param_y": param_y,
        "x_values": x_values,
        "y_values": y_values,
        "probability": probability,
        "p_gc": p_gc,
        "p_vc": p_vc,
        "n_valid": n_valid,
        "n_samples": int(n_samples),
        "median_GC": median_gc,
        "median_VC": median_vc,
        "targets": targets,
        "operating_point": operating_point,
        "target_usable_kg": float(target_usable_kg),
        "conditional": bool(conditional),
        "conditioned_on": tuple(sorted(conditioned)),
        "variance_reduction": (
            None if reduction is None else np.asarray(reduction)
        ),
        "seed": int(seed),
        "caveat": (
            "Material-parameter uncertainty only, conditional on a fixed p0 "
            "and therefore a LOWER BOUND on the blur a single published "
            "isotherm implies. The underlying system mass model is separately "
            "known from Gate V3 to be optimistic by a factor of about 4.2, so "
            "the band's position is optimistic even where its width is honest."
        ),
    }


def boundary_separation(result, along_value, level_low=0.05, level_high=0.95,
                        median_level=0.50):
    """Horizontal separation of two probability contours, as C5 defines it.

    Pre-registered in ``docs/validation_plan.md`` (V4.4): claim C5's
    "quantified amount" is the horizontal distance between the
    ``P(feasible) = 0.05`` and ``0.95`` contours along a fixed value of the
    y-axis parameter, expressed absolutely and as a percentage of the x value
    at which the median contour crosses the same line.

    Defining the metric before the map was computed is the point. A separation
    read off a finished figure could be chosen to look impressive; this one was
    specified in advance, including the instruction to report a bound rather
    than extend the mapped range when a contour does not cross.

    Parameters
    ----------
    result : dict
        Output of :func:`probability_map`.
    along_value : float
        Value of the y-axis parameter to take the horizontal cut at, in that
        parameter's SI unit.
    level_low, level_high, median_level : float, optional
        Probability levels; defaults are the pre-registered 0.05, 0.95 and
        0.50.

    Returns
    -------
    dict
        ``row_value`` actually used and its index; the x value at which each
        level is crossed (``nan`` when it is not crossed inside the mapped
        range); ``separation`` and ``separation_percent``; ``bounded``, true
        when a level was not crossed so the result is a bound; and ``note``,
        the sentence to put in the figure caption or the claim.

    Raises
    ------
    ValueError
        If the map has fewer than two columns, so no horizontal interpolation
        is possible.
    """
    y_values = np.asarray(result["y_values"], dtype=float)
    x_values = np.asarray(result["x_values"], dtype=float)
    if x_values.size < 2:
        raise ValueError(
            "boundary_separation needs at least two columns to interpolate."
        )

    row = int(np.argmin(np.abs(y_values - along_value)))
    probabilities = np.asarray(result["probability"], dtype=float)[row]

    def crossing(level):
        """First x where the probability row crosses ``level``, by linear interp."""
        finite = np.isfinite(probabilities)
        if finite.sum() < 2:
            return math.nan
        xs = x_values[finite]
        ps = probabilities[finite]
        for k in range(ps.size - 1):
            lo, hi = ps[k], ps[k + 1]
            if (lo - level) * (hi - level) <= 0.0 and lo != hi:
                t = (level - lo) / (hi - lo)
                return float(xs[k] + t * (xs[k + 1] - xs[k]))
        return math.nan

    x_low = crossing(level_low)
    x_high = crossing(level_high)
    x_median = crossing(median_level)

    separation = (
        abs(x_high - x_low)
        if math.isfinite(x_low) and math.isfinite(x_high)
        else math.nan
    )
    percent = (
        100.0 * separation / x_median
        if math.isfinite(separation) and math.isfinite(x_median) and x_median
        else math.nan
    )
    bounded = not math.isfinite(separation)

    if bounded:
        note = (
            f"The P={level_low:g} and P={level_high:g} contours do not both "
            f"cross {result['param_y']} = {float(y_values[row]):g} inside the "
            f"mapped range {result['param_x']} in "
            f"[{x_values.min():g}, {x_values.max():g}]; the separation is "
            f"reported as a bound rather than the range extended."
        )
    else:
        note = (
            f"Material-parameter uncertainty alone blurs the feasibility "
            f"boundary over {separation:.3g} in {result['param_x']} "
            f"({percent:.1f}% of the median-contour crossing at "
            f"{x_median:.3g}) along {result['param_y']} = "
            f"{float(y_values[row]):g}. Conditional on a fixed p0, so a lower "
            f"bound."
        )

    return {
        "row_index": row,
        "row_value": float(y_values[row]),
        "requested_value": float(along_value),
        "x_at_low": x_low,
        "x_at_median": x_median,
        "x_at_high": x_high,
        "levels": (float(level_low), float(median_level), float(level_high)),
        "separation": separation,
        "separation_percent": percent,
        "bounded": bounded,
        "note": note,
    }


#: Liquid-hydrogen molar volume, m^3/mol, as used by assumption A-ISO-4 to
#: estimate the adsorbed-phase volume from the limiting uptake.
V_LIQUID_H2_MOLAR = 2.8e-5


def pore_volume_available(material):
    """Specific pore volume a packed bed leaves for the adsorbed phase, m^3/kg.

    ``1/rho_bulk - 1/rho_skel``: the volume per kilogram of sorbent that is not
    occupied by the pore-free solid. The adsorbed phase has to fit inside it,
    which is the constraint :func:`coherent_n_max_limit` expresses.
    """
    return 1.0 / material.rho_bulk - 1.0 / material.rho_skel


def coherent_n_max_limit(material, slope):
    """Largest limiting uptake whose adsorbed phase still fits in the pores.

    If the adsorbed-phase volume grows with the limiting uptake at rate
    ``slope``, the two meet the available pore volume at

        n_max_limit = n_max_ref + (V_pore - v_a_ref) / slope

    Beyond that the adsorbed phase would exceed the space the packing leaves
    for it, and the parameter vector does not describe a material at all.

    This matters because the deterministic acceptability map holds ``v_a``
    fixed while sweeping ``n_max``, which silently assumes the adsorbed phase
    does not grow with the uptake. It does, by two independent accounts: the
    Gate V2 fit's own parameter correlation implies
    ``dv_a/dn_max = 8.87e-5 m^3/mol``, and assumption A-ISO-4's liquid-hydrogen
    argument implies ``2.8e-5 m^3/mol``. Both place the limit *below* the
    uptake the deterministic map identifies as the requirement, so that
    requirement is not reachable at fixed packing density.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Reference material, supplying ``n_max``, ``v_a`` and the two densities.
    slope : float
        ``dv_a/dn_max`` in m^3/mol. Use
        :data:`V_LIQUID_H2_MOLAR` for the A-ISO-4 argument, or the conditional
        regression coefficient from the fit covariance.

    Returns
    -------
    float
        Limiting uptake in mol/kg at which the pore volume is exhausted.

    Raises
    ------
    ValueError
        If ``slope`` is not strictly positive; a non-positive slope would mean
        the adsorbed phase does not grow with uptake, and the limit would not
        exist.
    """
    if slope <= 0.0:
        raise ValueError(
            f"slope must be strictly positive (m^3/mol); got {slope}."
        )
    return material.n_max + (pore_volume_available(material) - material.v_a) / slope


def coherent_rho_bulk_limit(material, n_max_values, slope):
    """Largest packing density that still leaves room for the adsorbed phase.

    Inverts the pore-volume constraint for the packing density: at a given
    limiting uptake, the bed can be packed no more densely than

        rho_bulk_max = 1 / (v_a(n_max) + 1/rho_skel)

    which is the boundary curve to draw on an ``(n_max, rho_bulk)``
    acceptability map. It states the real trade the map has to confront: a
    higher-uptake sorbent needs more pore volume, which means packing it less
    densely, which costs volumetric capacity.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Reference material, supplying ``n_max``, ``v_a`` and ``rho_skel``.
    n_max_values : array_like
        Limiting uptakes in mol/kg.
    slope : float
        ``dv_a/dn_max`` in m^3/mol.

    Returns
    -------
    numpy.ndarray
        Maximum packing density in kg/m^3 at each uptake. Entries where the
        implied adsorbed-phase volume is non-positive are ``nan``.
    """
    if slope <= 0.0:
        raise ValueError(
            f"slope must be strictly positive (m^3/mol); got {slope}."
        )
    n_max_values = np.atleast_1d(np.asarray(n_max_values, dtype=float))
    v_a = material.v_a + slope * (n_max_values - material.n_max)
    with np.errstate(divide="ignore", invalid="ignore"):
        limit = np.where(v_a > 0.0, 1.0 / (v_a + 1.0 / material.rho_skel), np.nan)
    return limit


def fit_va_slope(spec_material, x_name="n_max", y_name="v_a"):
    """Regression slope ``dv_a/dn_max`` implied by the fit covariance.

    The conditional expectation of one fitted parameter given another is
    linear with slope ``Sigma_xy / Sigma_xx``. Taking it from the covariance
    rather than hard-coding a number keeps the figure and the constraint tied
    to the fit that produced them.

    Parameters
    ----------
    spec_material : h2star.uq.MaterialSpec
        Joint distribution over the material parameters.
    x_name, y_name : str, optional
        Parameter names; defaults give ``dv_a/dn_max``.

    Returns
    -------
    float
        Slope in the ratio of the two parameters' units (m^3/mol for the
        default pair).
    """
    names = list(spec_material.parameters)
    i, j = names.index(x_name), names.index(y_name)
    cov = np.asarray(spec_material.covariance, dtype=float)
    return float(cov[i, j] / cov[i, i])


#: Molar mass of carbon, kg/mol, for the weight-percent convention check.
M_CARBON = 12.011e-3

#: The two conventions a paper may mean by "x weight percent hydrogen".
WT_PERCENT_CONVENTIONS = ("of_total", "of_sorbent")


def wt_percent_to_mass_ratio(value, convention="of_total"):
    """Convert a reported hydrogen weight percent to kg H2 per kg of sorbent.

    The literature uses two conventions and rarely says which:

    - ``of_total``: ``wt% = 100 * m_H2 / (m_H2 + m_sorbent)``
    - ``of_sorbent``: ``wt% = 100 * m_H2 / m_sorbent``

    At 4 wt% they differ by about 4%, which is small next to the spread between
    papers but is not nothing, and at the 20 wt% end of the contested range
    they differ by 25%.

    For one entry in ``data/materials/cnt_literature.yaml`` the convention can
    be determined from the paper itself rather than assumed. Liu 1999 reports
    "4.2 weight percent, or a hydrogen to carbon atom ratio of 0.52": the
    ``of_total`` convention gives H/C = 0.522 and ``of_sorbent`` gives 0.500,
    so that paper is on the total-mass basis. ``of_total`` is therefore the
    default here, and :func:`hydrogen_to_carbon_ratio` lets the same check be
    applied to any other paper that happens to report both quantities.

    Parameters
    ----------
    value : float
        Reported weight percent.
    convention : str, optional
        One of :data:`WT_PERCENT_CONVENTIONS`.

    Returns
    -------
    float
        Hydrogen mass per unit sorbent mass, kg/kg.

    Raises
    ------
    ValueError
        If the convention is unknown, or if ``value`` is not in [0, 100) for
        the total-mass convention, where 100 wt% would be pure hydrogen.
    """
    if convention not in WT_PERCENT_CONVENTIONS:
        raise ValueError(
            f"Unknown weight-percent convention {convention!r}; expected one "
            f"of {list(WT_PERCENT_CONVENTIONS)}."
        )
    if value < 0.0:
        raise ValueError(f"Weight percent cannot be negative; got {value}.")
    if convention == "of_sorbent":
        return value / 100.0
    if value >= 100.0:
        raise ValueError(
            f"A total-mass weight percent of {value} is not physical: 100 wt% "
            f"would be hydrogen with no sorbent."
        )
    fraction = value / 100.0
    return fraction / (1.0 - fraction)


def hydrogen_to_carbon_ratio(wt_percent, convention="of_total"):
    """Hydrogen atoms per carbon atom implied by a reported weight percent.

    Lets a paper's own internal consistency decide which weight-percent
    convention it used, when it reports both a wt% and an H/C ratio. Used to
    establish that Liu 1999 is on the total-mass basis.

    Parameters
    ----------
    wt_percent : float
        Reported weight percent.
    convention : str, optional
        One of :data:`WT_PERCENT_CONVENTIONS`.

    Returns
    -------
    float
        H atoms per C atom, assuming the sorbent is pure carbon.
    """
    ratio = wt_percent_to_mass_ratio(wt_percent, convention)
    moles_h2_per_kg = ratio / M_H2
    moles_c_per_kg = 1.0 / M_CARBON
    return 2.0 * moles_h2_per_kg / moles_c_per_kg


def material_from_reported_uptake(base_material, reported_mol_per_kg,
                                  temperature, pressure, *, basis="absolute",
                                  n_max_bracket=(1.0, 2000.0)):
    """Back-solve a limiting uptake that reproduces one reported isotherm point.

    This is the inference chain the CNT case study rests on, and it should be
    read as an inference and not a measurement. The literature reports a single
    uptake at a single temperature and pressure; the system model needs a full
    modified Dubinin-Astakhov parameter vector. The gap is bridged by keeping
    the reference material's characteristic energy, pseudo-saturation pressure
    and adsorbed-phase volume, and solving only for the limiting uptake
    ``n_max`` that makes the isotherm pass through the reported point.

    Every link in that chain is an assumption, and they are the reason the
    case study's uncertainty is as large as it is:

    1. The D-A functional form describes the reported material. Not tested
       against it; no CNT paper in the corpus reports an isotherm shape.
    2. ``alpha``, ``beta`` and ``p0`` transfer from AX-21 activated carbon to a
       nanotube sample. These control the temperature and pressure dependence,
       so the inferred ``n_max`` depends on them.
    3. ``v_a``, ``rho_bulk`` and ``rho_skel`` also transfer. No CNT paper in
       the corpus reports a packed bulk density at all.
    4. The reported value is on the basis the caller states. For every entry in
       the corpus the paper does NOT state whether its uptake is excess or
       absolute, so both must be tried and the pair reported.

    Parameters
    ----------
    base_material : h2star.isotherm.Material
        Reference material supplying every parameter except ``n_max``.
    reported_mol_per_kg : float
        Reported uptake in mol H2 per kg of sorbent.
    temperature : float
        Temperature of the reported point, K.
    pressure : float
        Pressure of the reported point, Pa.
    basis : str, optional
        ``"absolute"`` or ``"excess"``: which quantity the reported value is
        taken to be.
    n_max_bracket : tuple of float, optional
        Search bracket for the limiting uptake, mol/kg.

    Returns
    -------
    h2star.isotherm.Material
        A material whose isotherm passes through the reported point.

    Raises
    ------
    ValueError
        If ``basis`` is unknown, if the reported uptake is not positive, or if
        no limiting uptake inside the bracket reproduces the point -- which
        happens when the reported value exceeds what the assumed isotherm shape
        can deliver at that temperature and pressure, and is itself worth
        reporting rather than working around.
    """
    if basis not in ("absolute", "excess"):
        raise ValueError(
            f"basis must be 'absolute' or 'excess'; got {basis!r}."
        )
    if reported_mol_per_kg <= 0.0:
        raise ValueError(
            f"Reported uptake must be positive (mol/kg); got "
            f"{reported_mol_per_kg}."
        )

    def residual(n_max):
        """Modelled minus reported uptake at the reported point, mol/kg."""
        candidate = replace(base_material, n_max=float(n_max))
        isotherm = ModifiedDA(candidate)
        modelled = (
            isotherm.n_absolute(pressure, temperature)
            if basis == "absolute"
            else isotherm.n_excess(pressure, temperature)
        )
        return float(modelled) - reported_mol_per_kg

    low, high = n_max_bracket
    f_low, f_high = residual(low), residual(high)
    if f_low * f_high > 0.0:
        raise ValueError(
            f"No limiting uptake in [{low}, {high}] mol/kg reproduces "
            f"{reported_mol_per_kg:.4g} mol/kg on a {basis} basis at "
            f"{temperature:g} K and {pressure / 1e6:g} MPa: the modelled "
            f"uptake is {f_low + reported_mol_per_kg:.4g} at the lower bound "
            f"and {f_high + reported_mol_per_kg:.4g} at the upper. The "
            f"reported value may be outside what this isotherm shape can "
            f"deliver at that state."
        )

    solved = brentq(residual, low, high, xtol=1e-10, rtol=1e-14, maxiter=200)
    return replace(base_material, n_max=float(solved))


def material_from_corpus_entry(base_material, entry, basis="absolute",
                               convention="of_total"):
    """Back-solve a material from one ``cnt_literature.yaml`` entry.

    Convenience wrapper tying the corpus file's schema to
    :func:`material_from_reported_uptake`, so that a notebook can present the
    case study without defining a conversion of its own. The architecture rule
    that notebooks carry narrative and figure calls only is not a stylistic
    preference here: a weight-percent conversion written in a notebook is
    physics that no test covers.

    Parameters
    ----------
    base_material : h2star.isotherm.Material
        Reference material supplying every parameter except ``n_max``.
    entry : dict
        One element of the corpus file's ``entries`` list.
    basis : str, optional
        ``"absolute"`` or ``"excess"``. No paper in the corpus states which its
        measurement is, so both are run and the pair reported.
    convention : str, optional
        Weight-percent convention; see
        :func:`wt_percent_to_mass_ratio`.

    Returns
    -------
    h2star.isotherm.Material
        A material whose isotherm passes through the entry's reported point.

    Raises
    ------
    ValueError
        Propagated from :func:`material_from_reported_uptake` when no limiting
        uptake reproduces the reported point -- which is itself a result about
        that entry, not a failure to be worked around.
    """
    uptake = entry["uptake"]
    moles_per_kg = (
        wt_percent_to_mass_ratio(uptake["value"], convention) / M_H2
    )
    return material_from_reported_uptake(
        base_material,
        moles_per_kg,
        uptake["temperature_K"],
        uptake["pressure_MPa"] * 1.0e6,
        basis=basis,
    )
