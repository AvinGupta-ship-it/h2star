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
