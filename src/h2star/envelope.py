"""Operating envelope and performance boundary computations.

A sorbent storage system's gravimetric and volumetric capacity depend as much
on *where it is operated* as on what the sorbent is. The full state fixes how
much hydrogen the tank holds; the empty state fixes how much of that inventory
can actually be delivered; and both feed back into the vessel and insulation
sizing, because the tank is sized to a mission (5.6 kg usable) rather than to a
fixed volume. Comparing two materials at one arbitrary envelope therefore
compares an accident of that choice as much as it compares the materials.

This module removes that accident. :func:`optimize_envelope` finds, for a given
material, the operating point that maximizes system gravimetric capacity
subject to meeting a volumetric target, so materials can be compared at their
best achievable operating point (manual 2.7). :func:`forward_map` sweeps GC and
VC over a grid of full-state pressures and temperatures at a fixed swing, which
is figure F5.

All pressures are in pascals (Pa) and all temperatures in kelvin (K), as
everywhere in the package. Capacities follow :mod:`h2star.system`: ``GC`` is the
usable swing per kilogram of system (kg/kg) and ``VC`` is the usable swing per
litre of system (kg/L).

A warning that belongs with every number this module produces. The system mass
denominator is an idealized thin-wall composite vessel plus a fixed
balance-of-plant mass, and Gate V3 established that this block under-predicts a
real HSECoE Type-3 tank's dead mass by a factor of about 4.2 (manual 4.2). The
absolute GC and VC values below are therefore an optimistic bound, and the
optimizer will happily report an envelope whose GC exceeds a DOE target that a
real system at the same operating point would not meet. What survives the Gate
V3 gap is the *ordering* and *shape* of the response -- which envelope is better
than which, and by roughly how much -- not the absolute level. Manual 4.2.3 sets
out exactly which claims this permits.
"""

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import NonlinearConstraint, differential_evolution, minimize

from .constants import DEFAULT_TARGET_USABLE_KG, bar_to_pa
from .system import SystemDesign, size_for_usable

#: Default fuel-cell delivery floor, Pa. Manual 2.5 fixes P_empty at 5 bar: the
#: fuel cell needs a minimum delivery pressure, so the tank is never emptied
#: below it. It is held fixed rather than optimized, because an optimizer given
#: freedom over it would simply drive it to zero.
DEFAULT_P_EMPTY = bar_to_pa(5.0)

#: Objective value (negated GC, so kg/kg) returned for an operating point the
#: system model cannot evaluate -- for example one where the sizing solve cannot
#: bracket a root. Large and finite rather than ``inf`` so that differential
#: evolution's population statistics stay well defined, and far above any
#: physical |GC| so it can never win.
_INFEASIBLE_OBJECTIVE = 1.0e6

#: Constraint value (volumetric capacity, kg/L) reported at an operating point
#: that cannot be evaluated. Kept separate from the objective sentinel because
#: the two stand in for different physical quantities: one magnitude doing duty
#: for both would be a unit error waiting to happen.
_INFEASIBLE_CONSTRAINT = -1.0e6

#: Fraction of a variable's search span within which the optimum counts as
#: sitting on that bound, for the ``at_bound`` flag on :class:`EnvelopeResult`.
#: Applied as a fraction of span for pressure and temperature, and directly as
#: an absolute tolerance for the dimensionless warming fraction ``s``, whose
#: span is 1 by construction so the two readings coincide.
_BOUND_FRACTION = 1.0e-3


@dataclass(frozen=True)
class EnvelopeBounds:
    """Box bounds on the operating variables the optimizer may vary.

    Attributes
    ----------
    P_full : tuple of float
        ``(lo, hi)`` full-state pressure in pascals (Pa). The default
        20-200 bar spans the practical cryo-adsorption range: below ~20 bar the
        void-gas inventory is negligible, and above 200 bar the vessel class
        changes and the thin-wall correlation stops being defensible.
    T_full : tuple of float
        ``(lo, hi)`` full-state temperature in kelvin (K). The default floor of
        60 K is the envelope floor from manual 2.5 -- below it the
        ortho/para-conversion regime and multilayer-insulation practicality both
        start to matter, and neither is modeled.
    T_empty_max : float
        Upper bound on the empty-state temperature in kelvin (K). The empty
        state is reached by warming the bed, so ``T_empty`` is constrained to
        lie between ``T_full`` and this value.
    """

    P_full: tuple = (bar_to_pa(20.0), bar_to_pa(200.0))  # Pa
    T_full: tuple = (60.0, 120.0)  # K
    T_empty_max: float = 200.0  # K

    def __post_init__(self):
        """Reject bounds that are not strictly increasing positive intervals."""
        for name, (lo, hi) in (("P_full", self.P_full), ("T_full", self.T_full)):
            if not (0.0 < lo < hi):
                raise ValueError(
                    f"{name} bounds must satisfy 0 < lo < hi; got ({lo}, {hi})."
                )
        if self.T_empty_max < self.T_full[1]:
            raise ValueError(
                f"T_empty_max ({self.T_empty_max} K) must be at least the "
                f"upper T_full bound ({self.T_full[1]} K); the empty state is "
                f"reached by warming the bed, so it cannot be forced below the "
                f"full state."
            )


@dataclass(frozen=True)
class OperatingPoint:
    """A full/empty state pair, in SI units.

    Attributes
    ----------
    P_full, T_full : float
        Full state, in pascals (Pa) and kelvin (K).
    P_empty : float
        Empty-state pressure in pascals (Pa); defaults to the 5 bar fuel-cell
        delivery floor.
    T_empty : float
        Empty-state temperature in kelvin (K); defaults to the 160 K baseline
        discharge state of manual 2.4F.
    """

    P_full: float
    T_full: float
    P_empty: float = DEFAULT_P_EMPTY
    T_empty: float = 160.0

    def as_tuple(self):
        """Return ``(P_full, T_full, P_empty, T_empty)`` in (Pa, K, Pa, K)."""
        return (self.P_full, self.T_full, self.P_empty, self.T_empty)


@dataclass(frozen=True)
class EnvelopeResult:
    """Outcome of an envelope optimization.

    Attributes
    ----------
    P_full, T_full, P_empty, T_empty : float
        The operating point, in pascals (Pa) and kelvin (K).
    V_internal : float
        Internal tank volume sized to the usable-mass mission, m^3.
    GC : float
        System gravimetric capacity at this point, kg H2 per kg system.
    VC : float
        System volumetric capacity at this point, kg H2 per litre of system.
    budget : dict
        The full :meth:`h2star.system.SystemDesign.evaluate` budget.
    vc_target : float or None
        The volumetric constraint the optimization was run under, kg/L, or
        ``None`` if it was unconstrained.
    vc_feasible : bool
        Whether ``VC >= vc_target`` holds at the returned point, within
        ``vc_tol``. Always ``True`` when ``vc_target`` is ``None``.
    at_bound : tuple of str
        Names of the operating variables sitting on a bound of their search
        interval at the optimum. A corner solution is a legitimate answer, but
        it means the reported optimum is set by the bound rather than by the
        physics, so it is flagged rather than left for the reader to notice.
    n_evaluations : int
        Distinct operating points the optimizer attempted, counting those the
        model could not evaluate. Repeat queries at identical coordinates are
        served from a cache and are not counted.
    message : str
        Human-readable note on how the optimization terminated.
    """

    P_full: float
    T_full: float
    P_empty: float
    T_empty: float
    V_internal: float
    GC: float
    VC: float
    budget: dict = field(repr=False)
    vc_target: float | None
    vc_feasible: bool
    at_bound: tuple
    n_evaluations: int
    message: str

    @property
    def operating_point(self):
        """This optimum as an :class:`OperatingPoint`, for downstream maps."""
        return OperatingPoint(
            P_full=self.P_full,
            T_full=self.T_full,
            P_empty=self.P_empty,
            T_empty=self.T_empty,
        )


def evaluate_envelope(
    material,
    isotherm,
    engineering,
    P_full,
    T_full,
    P_empty,
    T_empty,
    target_usable_kg=DEFAULT_TARGET_USABLE_KG,
):
    """Size a tank at one operating point and return its system budget.

    This is the single system evaluation that every routine in this module is
    built from: construct the design, solve for the internal volume that
    delivers ``target_usable_kg`` of usable hydrogen, and evaluate the mass and
    volume budget at that volume.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Adsorbent, supplying ``rho_bulk``, ``rho_skel`` and ``v_a``.
    isotherm : h2star.isotherm.ModifiedDA
        Isotherm built on ``material``.
    engineering : h2star.system.EngineeringParams
        Vessel, insulation and balance-of-plant parameters in SI units.
    P_full, T_full : float
        Full state, in pascals (Pa) and kelvin (K).
    P_empty, T_empty : float
        Empty state, in pascals (Pa) and kelvin (K).
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg); default 5.6 kg.

    Returns
    -------
    dict
        The budget from :meth:`h2star.system.SystemDesign.evaluate`, with the
        ``GC`` (kg/kg) and ``VC`` (kg/L) keys among them.

    Raises
    ------
    ValueError
        Propagated from the system and sizing layers: a non-positive volume, a
        non-positive warm-cold temperature difference, or a sizing bracket that
        does not contain the target.
    ArithmeticError
        Propagated from the numerics (for example a root solve that fails to
        converge). Callers that sweep this function catch both.
    """
    design = SystemDesign(
        material, isotherm, engineering, P_full, T_full, P_empty, T_empty
    )
    V_internal = size_for_usable(design, target_usable_kg=target_usable_kg)
    return design.evaluate(V_internal)


def _unpack(x, bounds):
    """Map optimizer coordinates to a physical operating point.

    The empty-state temperature is parameterized as a fraction of the distance
    from ``T_full`` to ``T_empty_max`` rather than as a temperature. That keeps
    the search region a box -- which differential evolution requires -- while
    enforcing ``T_full <= T_empty <= T_empty_max`` exactly, with no clipping and
    no flat penalty shelf for the optimizer to get lost on.

    Parameters
    ----------
    x : sequence of float
        ``(P_full in Pa, T_full in K, s)`` with the warming fraction
        ``s`` in ``[0, 1]``.
    bounds : EnvelopeBounds
        Search bounds, supplying ``T_empty_max``.

    Returns
    -------
    tuple of float
        ``(P_full, T_full, T_empty)`` in (Pa, K, K).
    """
    P_full, T_full, s = float(x[0]), float(x[1]), float(x[2])
    T_empty = T_full + s * (bounds.T_empty_max - T_full)
    return P_full, T_full, T_empty


def _make_evaluator(
    material, isotherm, engineering, P_empty, target_usable_kg, bounds
):
    """Build a cached budget evaluator over optimizer coordinates.

    Differential evolution asks for the objective and the constraint at the
    same coordinates, and each system evaluation costs a Brent sizing solve.
    The cache keys on the exact coordinate tuple, which is enough because the
    objective and constraint calls receive bitwise-identical arrays: rounding
    the key would invent a tolerance in three different units and would, at the
    pressure scale used here, round to about a micropascal and do nothing.

    Returns
    -------
    tuple
        ``(evaluate, counter, last_error)`` where ``evaluate(x)`` returns the
        budget dict or ``None`` if the point could not be evaluated;
        ``counter`` is a one-element list counting distinct coordinates
        *attempted*, including those that failed; and ``last_error`` is a
        one-element list holding the most recent exception, so a caller that
        finds nothing evaluable can say why rather than guessing.
    """
    cache = {}
    counter = [0]
    last_error = [None]

    def evaluate(x):
        key = (float(x[0]), float(x[1]), float(x[2]))
        if key in cache:
            return cache[key]
        P_full, T_full, T_empty = _unpack(x, bounds)
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
            # An operating point the model cannot evaluate -- most often a
            # sizing bracket that does not contain the mission, but it can
            # equally be a bad parameter. Keep the exception so the cause is
            # recoverable instead of being collapsed into a bare None.
            budget = None
            last_error[0] = exc
        counter[0] += 1
        cache[key] = budget
        return budget

    return evaluate, counter, last_error


def optimize_envelope(
    material,
    isotherm,
    engineering,
    vc_target=None,
    *,
    P_empty=DEFAULT_P_EMPTY,
    bounds=None,
    target_usable_kg=DEFAULT_TARGET_USABLE_KG,
    vc_tol=1.0e-12,
    seed=0,
    maxiter=60,
    popsize=15,
    polish=True,
):
    """Maximize system gravimetric capacity over the operating envelope.

    Searches ``(P_full, T_full, T_empty)`` with ``P_empty`` held at the
    fuel-cell delivery floor, maximizing GC subject to ``VC >= vc_target``. The
    tank is re-sized to the usable-hydrogen mission at every candidate point, so
    the comparison is between tanks that all deliver the same hydrogen, not
    between tanks of the same volume.

    Global search is differential evolution (the GC surface is cheap to evaluate
    but not guaranteed unimodal once the volumetric constraint bites), followed
    by an SLSQP polish from the global best.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Adsorbent.
    isotherm : h2star.isotherm.ModifiedDA
        Isotherm built on ``material``.
    engineering : h2star.system.EngineeringParams
        Vessel, insulation and balance-of-plant parameters.
    vc_target : float or None, optional
        Volumetric capacity the optimum must meet, in kg H2 per litre of
        system. ``None`` (the default) runs the optimization unconstrained.
    P_empty : float, optional
        Empty-state pressure in pascals (Pa); default 5 bar. Held fixed, not
        optimized.
    bounds : EnvelopeBounds or None, optional
        Search bounds; the dataclass defaults are used when ``None``.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg); default 5.6 kg.
    vc_tol : float, optional
        Absolute tolerance in kg/L when reporting whether the volumetric
        constraint holds at the returned point; default 1e-12.
    seed : int, optional
        Seed for differential evolution, so repeated runs are reproducible;
        default 0.
    maxiter, popsize : int, optional
        Differential-evolution budget.
    polish : bool, optional
        Whether to run the SLSQP polish; default ``True``.

    Returns
    -------
    EnvelopeResult
        The optimum, its budget, whether the volumetric constraint is met, and
        which variables sit on a search bound there.

    Raises
    ------
    ValueError
        If no evaluable operating point was found anywhere in the search
        region, or if ``vc_target`` is not strictly positive when given.

    Notes
    -----
    For AX-21 under the default bounds the optimum is a corner: GC rises
    monotonically with full-state pressure and falls with full-state
    temperature over the whole region, so the answer is the coldest, highest
    pressure, warmest-discharge corner available. ``at_bound`` reports that
    rather than hiding it. A corner optimum means the bounds, not the physics,
    set the reported point -- which is worth knowing before quoting the number.
    """
    if vc_target is not None and vc_target <= 0.0:
        raise ValueError(
            f"vc_target must be strictly positive (kg/L) when given; got "
            f"{vc_target}."
        )
    if bounds is None:
        bounds = EnvelopeBounds()

    evaluate, counter, last_error = _make_evaluator(
        material, isotherm, engineering, P_empty, target_usable_kg, bounds
    )

    def objective(x):
        """Negated GC, so minimizing the objective maximizes capacity."""
        budget = evaluate(x)
        if budget is None:
            return _INFEASIBLE_OBJECTIVE
        return -budget["GC"]

    def vc_of(x):
        """Volumetric capacity (kg/L), or a strongly negative sentinel."""
        budget = evaluate(x)
        if budget is None:
            return _INFEASIBLE_CONSTRAINT
        return budget["VC"]

    search_box = [bounds.P_full, bounds.T_full, (0.0, 1.0)]

    constraints = ()
    if vc_target is not None:
        constraints = NonlinearConstraint(
            lambda x: vc_of(x), vc_target, np.inf
        )

    de = differential_evolution(
        objective,
        bounds=search_box,
        constraints=constraints,
        seed=seed,
        maxiter=maxiter,
        popsize=popsize,
        tol=1.0e-8,
        polish=False,
        init="sobol",
    )

    best_x = np.asarray(de.x, dtype=float)
    message = f"differential evolution: {de.message}"

    if polish:
        polish_constraints = []
        if vc_target is not None:
            polish_constraints.append(
                {"type": "ineq", "fun": lambda x: vc_of(x) - vc_target}
            )
        local = minimize(
            objective,
            best_x,
            method="SLSQP",
            bounds=search_box,
            constraints=polish_constraints,
            options={"maxiter": 200, "ftol": 1.0e-12},
        )
        # Accept the polish only if it is evaluable, no worse, and still
        # feasible. SLSQP on a constrained problem can step outside the
        # feasible set; silently returning such a point would report an
        # optimum the constraint forbids.
        if local.success and evaluate(local.x) is not None:
            improved = objective(local.x) <= objective(best_x)
            feasible = vc_target is None or vc_of(local.x) >= vc_target - vc_tol
            if improved and feasible:
                best_x = np.asarray(local.x, dtype=float)
                message += "; SLSQP polish accepted"
            else:
                message += "; SLSQP polish rejected (worse or infeasible)"
        else:
            message += "; SLSQP polish did not converge"

    budget = evaluate(best_x)
    if budget is None:
        cause = last_error[0]
        detail = (
            f" The last failure was {type(cause).__name__}: {cause}"
            if cause is not None
            else ""
        )
        raise ValueError(
            "optimize_envelope found no evaluable operating point anywhere in "
            "the search region. Common causes are a usable-mass mission that "
            "cannot be met inside the given bounds, an environment temperature "
            "at or below the full-state temperature, or an unphysical "
            "parameter." + detail
        )

    P_full, T_full, T_empty = _unpack(best_x, bounds)

    # "On a bound" is judged at 0.1% of the search span, not at machine
    # precision. A gradient optimizer pushed against a boundary stops a short
    # way short of it, and reporting 199.997 bar as an interior optimum when
    # the bound is 200 bar would hide exactly the fact the flag exists to
    # surface. Over-flagging is the safe direction here.
    at_bound = []
    for name, value, (lo, hi) in (
        ("P_full", P_full, bounds.P_full),
        ("T_full", T_full, bounds.T_full),
    ):
        span = hi - lo
        if abs(value - lo) <= _BOUND_FRACTION * span:
            at_bound.append(f"{name}@lower")
        elif abs(value - hi) <= _BOUND_FRACTION * span:
            at_bound.append(f"{name}@upper")
    if abs(best_x[2] - 1.0) <= _BOUND_FRACTION:
        at_bound.append("T_empty@upper")
    elif abs(best_x[2]) <= _BOUND_FRACTION:
        at_bound.append("T_empty@lower")

    return EnvelopeResult(
        P_full=float(P_full),
        T_full=float(T_full),
        P_empty=float(P_empty),
        T_empty=float(T_empty),
        V_internal=float(budget["V_internal"]),
        GC=float(budget["GC"]),
        VC=float(budget["VC"]),
        budget=budget,
        vc_target=vc_target,
        vc_feasible=(
            True if vc_target is None else budget["VC"] >= vc_target - vc_tol
        ),
        at_bound=tuple(at_bound),
        n_evaluations=counter[0],
        message=message,
    )


def forward_map(
    material,
    isotherm,
    engineering,
    P_full_grid,
    T_full_grid,
    *,
    P_empty=DEFAULT_P_EMPTY,
    T_empty=160.0,
    target_usable_kg=DEFAULT_TARGET_USABLE_KG,
):
    """Sweep GC and VC over a grid of full-state pressures and temperatures.

    The swing endpoint is held fixed, so the map isolates the effect of the
    full state. This is the data behind figure F5.

    Parameters
    ----------
    material : h2star.isotherm.Material
        Adsorbent.
    isotherm : h2star.isotherm.ModifiedDA
        Isotherm built on ``material``.
    engineering : h2star.system.EngineeringParams
        Vessel, insulation and balance-of-plant parameters.
    P_full_grid : array_like
        Full-state pressures in pascals (Pa), shape ``(n_p,)``.
    T_full_grid : array_like
        Full-state temperatures in kelvin (K), shape ``(n_t,)``.
    P_empty : float, optional
        Empty-state pressure in pascals (Pa); default 5 bar.
    T_empty : float, optional
        Empty-state temperature in kelvin (K); default 160 K, the baseline
        discharge state from manual 2.4F.
    target_usable_kg : float, optional
        Usable-hydrogen mission in kilograms (kg); default 5.6 kg.

    Returns
    -------
    dict
        ``P_full`` and ``T_full`` (copies of the input axes), and ``GC``
        (kg/kg), ``VC`` (kg/L) and ``V_internal`` (m^3) as arrays of shape
        ``(n_t, n_p)`` -- temperature down the rows, pressure across the
        columns, so the arrays plot directly with ``T_full`` on the vertical
        axis. Also ``evaluable``, a boolean array of the same shape, and
        ``n_evaluated``, its count.

        A node is ``nan`` and not evaluable when the model refused it or when
        its empty state is strictly colder than its full state, which this
        model cannot represent. An isothermal swing, ``T_empty == T_full``, is
        a legitimate pure-pressure-swing case (manual 2.4F) and is evaluated.

    Raises
    ------
    ValueError
        If either axis is not one-dimensional. A two-dimensional grid would
        otherwise fail deep inside the loop with an opaque truth-value error.

    Notes
    -----
    Failures are recorded as ``nan`` rather than raised, so that one impossible
    corner does not discard an otherwise good map. That also means a wholly
    invalid call -- a negative pressure, say -- comes back as an all-``nan``
    map rather than an exception, so check ``n_evaluated`` before plotting.
    """
    P_full_grid = np.atleast_1d(np.array(P_full_grid, dtype=float, copy=True))
    T_full_grid = np.atleast_1d(np.array(T_full_grid, dtype=float, copy=True))
    for name, axis in (("P_full_grid", P_full_grid), ("T_full_grid", T_full_grid)):
        if axis.ndim != 1:
            raise ValueError(
                f"{name} must be one-dimensional; got shape {axis.shape}. "
                f"forward_map builds the outer product itself."
            )

    shape = (T_full_grid.size, P_full_grid.size)
    gc = np.full(shape, np.nan)
    vc = np.full(shape, np.nan)
    vol = np.full(shape, np.nan)
    evaluable = np.zeros(shape, dtype=bool)

    for i, T_full in enumerate(T_full_grid):
        if T_empty < T_full:
            # Discharging cannot cool the bed in this model; leave the row nan
            # rather than silently evaluating a reversed swing.
            continue
        for j, P_full in enumerate(P_full_grid):
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
            except (ValueError, ArithmeticError):
                continue
            evaluable[i, j] = True
            gc[i, j] = budget["GC"]
            vc[i, j] = budget["VC"]
            vol[i, j] = budget["V_internal"]

    return {
        "P_full": P_full_grid,
        "T_full": T_full_grid,
        "GC": gc,
        "VC": vc,
        "V_internal": vol,
        "evaluable": evaluable,
        "n_evaluated": int(evaluable.sum()),
    }
