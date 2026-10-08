"""Visualization of isotherms, envelopes, and system-level results."""

import functools
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from .heats import isosteric_heat

#: Rendering parameters pinned for every figure this module draws.
#:
#: A figure's *bytes* depend on the font its text is drawn with, and Matplotlib
#: takes that from whichever ``matplotlibrc`` the host environment supplies. A
#: host that names a different ``font.family`` -- some container images do --
#: silently changes every label, every tight bounding box, and therefore every
#: pixel, while leaving all the numbers untouched. Figures built under such a
#: host cannot be regenerated anywhere else. That is a defect in the figure,
#: not in the host, and it is invisible unless something compares bytes across
#: environments: H2STAR's own clean-room check found exactly this, with all
#: nine PNGs differing and all nine headline numbers reproducing exactly.
#:
#: Pinning these removes the host from the question. ``DejaVu Sans`` is named
#: outright rather than reached through the ``sans-serif`` alias because DejaVu
#: ships inside the Matplotlib wheel: it is present wherever Matplotlib is, so
#: the pin relies on no system font being installed and no alias resolving a
#: particular way. Every value is Matplotlib's own documented default, except
#: that ``font.family`` names the concrete font the default alias resolves to
#: on a stock install.
#:
#: What this buys is byte-identity for a given Matplotlib and FreeType version,
#: verified across two Python versions and two independent installs. It does
#: not buy byte-identity *across* those versions: FreeType rasterises glyphs
#: differently between releases, so different FreeType draws the same text with
#: different pixels. ``docs/known_limitations.md`` states the limit.
FIGURE_RCPARAMS = {
    "font.family": ["DejaVu Sans"],
    "font.size": 10.0,
    "mathtext.fontset": "dejavusans",
    "text.antialiased": True,
    "text.hinting": "default",
    "text.hinting_factor": None,
    "axes.unicode_minus": True,
}


def figure_style():
    """Context manager that applies :data:`FIGURE_RCPARAMS`.

    Every plotting function in this module already applies it to its own
    drawing. Use this directly when a *caller* creates the figure or saves it
    -- ``scripts/make_all_figures.py`` does, because the isosteric-heat figure
    is assembled by the caller around :func:`plot_isosteric_heat`, so the
    figure-level text would otherwise be drawn under the host's font.

    Returns
    -------
    matplotlib.rc_context
        A context manager. Ambient ``rcParams`` are restored on exit, so
        importing or calling this module never mutates a caller's global
        Matplotlib configuration.

    Examples
    --------
    >>> from h2star import viz
    >>> with viz.figure_style():
    ...     fig, ax = plt.subplots()
    ...     _ = ax.set_title("drawn with the pinned font")
    """
    return mpl.rc_context(FIGURE_RCPARAMS)


def _styled(func):
    """Apply :data:`FIGURE_RCPARAMS` for the duration of a plotting call.

    A decorator rather than an indented ``with`` block inside each function
    body: it keeps the pin in one place, so a new plotting function opts in
    with one line and cannot half-apply it.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with figure_style():
            return func(*args, **kwargs)

    return wrapper


@_styled
def eos_parity_plot(isotherms, savepath=None):
    """Parity plot of model vs. reference density for one or more isotherms.

    Draws model density against reference (e.g. NIST) density for each isotherm,
    together with a ``y = x`` reference line, so that agreement appears as points
    lying on the diagonal.

    Parameters
    ----------
    isotherms : sequence of dict
        One entry per isotherm. Each dict must provide:

        - ``'T'`` : float
            Temperature in kelvin (K), used for the legend label.
        - ``'nist'`` : array-like of float
            Reference density in kilograms per cubic metre (kg/m^3), plotted on
            the x-axis.
        - ``'model'`` : array-like of float
            Model density in kilograms per cubic metre (kg/m^3), plotted on the
            y-axis.
    savepath : str or pathlib.Path, optional
        If given, the figure is saved to this path (PNG inferred from the
        extension) at 150 dpi. The parent directory must already exist.

    Returns
    -------
    tuple
        ``(fig, ax)`` — the Matplotlib :class:`~matplotlib.figure.Figure` and
        :class:`~matplotlib.axes.Axes` objects.
    """
    fig, ax = plt.subplots(figsize=(6, 6))

    lo = float("inf")
    hi = float("-inf")
    for iso in isotherms:
        nist = iso["nist"]
        model = iso["model"]
        ax.scatter(nist, model, s=18, label=f"{iso['T']:g} K", zorder=3)
        lo = min(lo, min(nist), min(model))
        hi = max(hi, max(nist), max(model))

    # y = x reference line spanning the full data range.
    ax.plot([lo, hi], [lo, hi], color="k", linestyle="--", linewidth=1,
            label="y = x", zorder=2)

    ax.set_xlabel("NIST density (kg/m$^3$)")
    ax.set_ylabel("Model density (kg/m$^3$)")
    ax.set_title("H2STAR EOS parity: model vs. NIST density")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(title="Isotherm")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=150)

    return fig, ax


@_styled
def plot_ax21_isotherm(P_data_mpa, n_excess_data, P_curve_mpa, n_excess_curve,
                       n_absolute_curve, residuals, rmse_value=None,
                       threshold=None, savepath=None, *,
                       n_excess_fit=None, residuals_fit=None, rmse_fit=None,
                       fit_label="Refit (this work)"):
    """Two-panel AX-21 isotherm figure (F2): overlay and residuals.

    All physics is done by the caller; this function only draws the arrays it
    is given. Pressures are in megapascals (MPa) and uptake in mol/kg.

    Parameters
    ----------
    P_data_mpa, n_excess_data : array-like
        Digitized excess data points (77 K, Fig. 1a): pressure (MPa) and
        excess uptake (mol/kg).
    P_curve_mpa : array-like
        Pressure grid (MPa) shared by the model curves.
    n_excess_curve, n_absolute_curve : array-like
        Model excess and absolute loading (mol/kg) on ``P_curve_mpa``.
    residuals : array-like
        Model-minus-data residuals (mol/kg) at ``P_data_mpa``.
    rmse_value : float, optional
        If given, the RMSE (mol/kg) annotated on the top panel.
    threshold : float, optional
        If given alongside ``rmse_value``, the RMSE threshold shown with it.
    savepath : str or pathlib.Path, optional
        If given, the figure is saved here at 300 dpi; the parent directory is
        created if needed.
    n_excess_fit : array-like, optional
        Refitted model excess (mol/kg) on ``P_curve_mpa``. If given, drawn in
        the top panel as a dash-dot line in a distinct color and added to the
        legend.
    residuals_fit : array-like, optional
        Refit model-minus-data residuals (mol/kg) at ``P_data_mpa``. If given,
        drawn in the bottom panel as triangles with its own legend entry.
    rmse_fit : float, optional
        If given, the refit RMSE (mol/kg) appended to the top-panel annotation.
    fit_label : str, optional
        Legend label for the refit curve and residuals.

    Returns
    -------
    matplotlib.figure.Figure
        The two-panel figure.
    """
    fig, (ax_top, ax_bot) = plt.subplots(
        2, 1, figsize=(7, 7), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    # Top panel: model curves and digitized data.
    ax_top.plot(P_curve_mpa, n_absolute_curve, color="grey", linestyle="--",
                label="Absolute (published params)")
    ax_top.plot(P_curve_mpa, n_excess_curve, color="tab:blue",
                label="Excess (published params)")
    ax_top.scatter(P_data_mpa, n_excess_data, color="k", marker="x",
                   label="Digitized excess (77 K, Fig. 1a)", zorder=3)
    if n_excess_fit is not None:
        ax_top.plot(P_curve_mpa, n_excess_fit, color="tab:green",
                    linestyle="-.", label=fit_label)
    ax_top.set_ylabel("Uptake (mol kg$^{-1}$)")
    ax_top.set_title("AX-21 H$_2$ excess isotherm at 77 K")
    ax_top.legend(frameon=False)
    ax_top.grid(True, alpha=0.3)

    if rmse_value is not None:
        text = f"RMSE = {rmse_value:.3g} mol kg$^{{-1}}$"
        if threshold is not None:
            text += f"\nthreshold = {threshold:.3g} mol kg$^{{-1}}$"
        if rmse_fit is not None:
            text += f"\n{fit_label} RMSE = {rmse_fit:.3g} mol kg$^{{-1}}$"
        ax_top.annotate(
            text, xy=(0.98, 0.02), xycoords="axes fraction",
            ha="right", va="bottom",
            bbox={"boxstyle": "round", "facecolor": "white", "edgecolor": "grey"},
        )

    # Bottom panel: residuals.
    ax_bot.axhline(0.0, color="k", linewidth=1)
    ax_bot.scatter(P_data_mpa, residuals, color="tab:red", marker="o", zorder=3,
                   label="Published params")
    if residuals_fit is not None:
        ax_bot.scatter(P_data_mpa, residuals_fit, color="tab:green",
                       marker="^", zorder=3, label=fit_label)
        ax_bot.legend(frameon=False)
    ax_bot.set_xlabel("Pressure (MPa)")
    ax_bot.set_ylabel("Residual (mol kg$^{-1}$)")
    ax_bot.grid(True, alpha=0.3)

    fig.tight_layout()

    if savepath is not None:
        Path(savepath).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(savepath, dpi=300, bbox_inches="tight")

    return fig


@_styled
def plot_isosteric_heat(da, n_over_nmax_min=0.02, n_over_nmax_max=0.60, T=77.0,
                        band=(4000.0, 7000.0), n_points=100, ax=None):
    """Isosteric heat vs. coverage (F3): numerical curve, D-A limit, anchor band.

    No physics is done here: the numerical curve comes from
    :func:`h2star.heats.isosteric_heat` and the overlay is the closed-form D-A
    limit ``alpha * sqrt(ln(n_max / n))`` evaluated from the material already
    attached to ``da``. Heats are computed in J/mol and divided by 1000 for
    display only.

    Parameters
    ----------
    da : ModifiedDA
        Isotherm model; its ``material`` supplies ``alpha`` (J/mol) and
        ``n_max`` (mol/kg).
    n_over_nmax_min, n_over_nmax_max : float, optional
        Coverage-fraction limits ``n / n_max`` of the plotted window.
    T : float, optional
        Temperature in kelvin (K) at which the numerical heat is evaluated.
    band : tuple of float, optional
        ``(low, high)`` bounds of the carbon literature range in J/mol, shaded
        horizontally (converted to kJ/mol for display).
    n_points : int, optional
        Number of coverage points in the ``linspace`` grid.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on. A new figure and axes are created if omitted.

    Returns
    -------
    matplotlib.axes.Axes
        The axes containing the plot.
    """
    material = da.material

    frac = np.linspace(n_over_nmax_min, n_over_nmax_max, n_points)
    n_grid = frac * material.n_max

    q_numerical = np.array([isosteric_heat(da, float(n), T) for n in n_grid])
    q_analytic = material.alpha * np.sqrt(np.log(material.n_max / n_grid))

    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4.5))

    ax.axhspan(band[0] / 1000.0, band[1] / 1000.0, color="tab:grey", alpha=0.3,
               label="carbon literature range (4–7 kJ/mol)")
    ax.plot(frac, q_numerical / 1000.0, color="tab:blue",
            label=f"Numerical $q_{{st}}$ ({T:g} K)")
    ax.plot(frac, q_analytic / 1000.0, color="k", linestyle="--",
            label=r"Analytic D-A limit $\alpha\sqrt{\ln(n_{max}/n)}$")

    ax.set_xlabel("Coverage $n / n_{max}$ (-)")
    ax.set_ylabel("Isosteric heat $q_{st}$ (kJ mol$^{-1}$)")
    ax.set_title(f"{material.name} isosteric heat vs. coverage")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)

    return ax


@_styled
def plot_system_validation(
    gc_model, vc_model,
    gc_anchor, vc_anchor,
    tolerance_pct,
    anchor_label="HSECoE AX-21 (ST044, 2013)",
    model_label="H2STAR model",
    savepath=None,
):
    """Gate V3 system-validation figure (F4): model GC/VC vs. published anchor.

    Two side-by-side panels compare the model's full-state system gravimetric
    capacity (left) and volumetric capacity (right) against a single published
    anchor value, with the pre-registered tolerance band drawn around the
    ANCHOR (not around the model). Model points that fall outside that band
    therefore depict a documented FAIL of the gate.

    All values are passed in by the caller as plain numbers; this function
    performs NO physics and evaluates no model. It only draws.

    Parameters
    ----------
    gc_model : float
        Model system gravimetric capacity in kilograms H2 per kilogram of
        system (kg/kg).
    vc_model : float
        Model system volumetric capacity in kilograms H2 per litre of system
        (kg/L).
    gc_anchor : float
        Published anchor system gravimetric capacity (kg/kg).
    vc_anchor : float
        Published anchor system volumetric capacity (kg/L).
    tolerance_pct : float
        Pre-registered tolerance as a percentage (e.g. ``15`` for +/-15%). The
        shaded band spans ``anchor * (1 - tolerance_pct / 100)`` to
        ``anchor * (1 + tolerance_pct / 100)`` in each panel.
    anchor_label : str, optional
        Legend label for the anchor reference line and band source.
    model_label : str, optional
        Legend label for the model point.
    savepath : str or pathlib.Path, optional
        If given, the figure is saved here at 300 dpi with tight bounding box.
        The parent directory must already exist; it is not created.

    Returns
    -------
    tuple
        ``(fig, (ax_gc, ax_vc))`` — the Matplotlib
        :class:`~matplotlib.figure.Figure` and the gravimetric and volumetric
        :class:`~matplotlib.axes.Axes` objects.
    """
    fig, (ax_gc, ax_vc) = plt.subplots(1, 2, figsize=(10, 5))

    tol = tolerance_pct / 100.0
    band_label = f"$\\pm${tolerance_pct:g}% tolerance"

    panels = (
        (ax_gc, gc_model, gc_anchor, "Gravimetric",
         "System gravimetric capacity (kg kg$^{-1}$)"),
        (ax_vc, vc_model, vc_anchor, "Volumetric",
         "System volumetric capacity (kg L$^{-1}$)"),
    )

    for ax, model_value, anchor_value, title, ylabel in panels:
        lo = anchor_value * (1.0 - tol)
        hi = anchor_value * (1.0 + tol)

        # Band is drawn around the ANCHOR, so the model point may sit outside it.
        ax.axhspan(lo, hi, color="tab:grey", alpha=0.25, label=band_label)
        ax.axhline(anchor_value, color="k", linewidth=1.5, label=anchor_label)
        ax.plot([0.0], [model_value], marker="o", markersize=12,
                color="tab:red", linestyle="none", label=model_label, zorder=3)

        # Pad so both the full band and the model point stay visible.
        y_lo = min(lo, model_value)
        y_hi = max(hi, model_value)
        pad = 0.1 * (y_hi - y_lo) if y_hi > y_lo else 0.1 * abs(y_hi)
        ax.set_ylim(y_lo - pad, y_hi + pad)

        ax.set_xlim(-0.5, 0.5)
        ax.set_xticks([0.0])
        ax.set_xticklabels(["Model result"])
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)

    ax_gc.legend(frameon=False, loc="best")

    fig.suptitle(
        "Gate V3: system validation vs HSECoE AX-21 (full-state basis)")
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")

    return fig, (ax_gc, ax_vc)


#: Standing caption note for any figure whose axis carries an ABSOLUTE system
#: gravimetric or volumetric capacity. Gate V3 established that the system mass
#: denominator -- an idealized thin-wall composite vessel plus a fixed
#: balance-of-plant mass -- is light by a factor of about 4.2 against the HSECoE
#: AX-21 anchor, so every absolute capacity this model reports is an optimistic
#: bound. Manual 4.2.3 requires the note on F4, F5, F6 and F8; keeping the
#: wording in one constant stops the figures from drifting apart.
GATE_V3_NOTE = (
    "System mass model is an optimistic bound: Gate V3 (documented FAIL) "
    "places the vessel + insulation + BOP block ~4.2x light vs the HSECoE "
    "AX-21 anchor. Relative structure is robust; absolute levels are not."
)

#: Axis labels, with units, for the material parameters the maps may sweep.
_PARAM_LABELS = {
    "n_max": "Limiting uptake $n_{\\mathrm{max}}$ (mol kg$^{-1}$)",
    "alpha": "Enthalpic factor $\\alpha$ (J mol$^{-1}$)",
    "beta": "Entropic factor $\\beta$ (J mol$^{-1}$ K$^{-1}$)",
    "p0": "Pseudo-saturation pressure $P_0$ (Pa)",
    "v_a": "Adsorbed-phase volume $v_a$ (m$^3$ kg$^{-1}$)",
    "rho_bulk": "Packed bulk density $\\rho_{\\mathrm{bulk}}$ (kg m$^{-3}$)",
    "rho_skel": "Skeletal density $\\rho_{\\mathrm{skel}}$ (kg m$^{-3}$)",
}


#: Compact tick labels, for the sensitivity bar chart where the full axis
#: labels would not fit.
_PARAM_SHORT = {
    "n_max": "$n_{\\mathrm{max}}$",
    "alpha": "$\\alpha$",
    "beta": "$\\beta$",
    "p0": "$P_0$",
    "v_a": "$v_a$",
    "rho_bulk": "$\\rho_{\\mathrm{bulk}}$",
    "rho_skel": "$\\rho_{\\mathrm{skel}}$",
    "sigma_allow": "$\\sigma_{\\mathrm{allow}}$",
    "composite_density": "composite $\\rho$",
    "liner_areal_mass": "liner areal mass",
    "mli_k_eff": "MLI $k_{\\mathrm{eff}}$",
    "mli_density": "MLI $\\rho$",
    "heat_leak_budget": "heat-leak budget",
    "T_env": "$T_{\\mathrm{env}}$",
    "bop_fixed": "BOP mass",
    "bop_scaling": "BOP scaling",
}


def _param_label(name):
    """Axis label with units for a swept material parameter."""
    return _PARAM_LABELS.get(name, name)


@_styled
def plot_forward_maps(grid, targets=None, title=None, savepath=None):
    """Forward GC and VC maps over the full state (F5).

    Two filled-contour panels over full-state pressure and temperature at a
    fixed swing endpoint, with the DOE target level drawn as a single bold
    contour on each so the reader can see directly where the model crosses it.

    Performs NO physics: ``grid`` is consumed exactly as
    :func:`h2star.envelope.forward_map` returns it.

    Parameters
    ----------
    grid : dict
        Output of :func:`h2star.envelope.forward_map`, carrying ``P_full``
        (Pa), ``T_full`` (K), ``GC`` (kg/kg) and ``VC`` (kg/L).
    targets : object, optional
        Anything exposing ``gc`` (kg/kg), ``vc`` (kg/L) and ``label``; the DOE
        tier from :func:`h2star.inverse.load_doe_targets`. When given, each
        panel gains a target contour.
    title : str, optional
        Figure suptitle. A default naming the swing endpoint is used if absent.
    savepath : str or pathlib.Path, optional
        If given, the figure is saved here at 300 dpi with a tight bounding
        box. The parent directory must already exist.

    Returns
    -------
    tuple
        ``(fig, (ax_gc, ax_vc))``.
    """
    P_bar = np.asarray(grid["P_full"], dtype=float) / 1.0e5
    T = np.asarray(grid["T_full"], dtype=float)

    fig, (ax_gc, ax_vc) = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

    panels = (
        (ax_gc, np.asarray(grid["GC"], dtype=float), "viridis",
         "System gravimetric capacity (kg kg$^{-1}$)",
         None if targets is None else targets.gc),
        (ax_vc, np.asarray(grid["VC"], dtype=float), "magma",
         "System volumetric capacity (kg L$^{-1}$)",
         None if targets is None else targets.vc),
    )

    for ax, field, cmap, cbar_label, target_level in panels:
        filled = ax.contourf(P_bar, T, field, levels=18, cmap=cmap)
        fig.colorbar(filled, ax=ax, label=cbar_label)

        lines = ax.contour(P_bar, T, field, levels=8, colors="white",
                           linewidths=0.6, alpha=0.6)
        ax.clabel(lines, inline=True, fontsize=7, fmt="%.3f")

        finite = field[np.isfinite(field)]
        if target_level is not None and finite.size:
            if finite.min() < target_level < finite.max():
                ax.contour(P_bar, T, field, levels=[target_level],
                           colors="red", linewidths=2.2)
                # Matplotlib will not accept a ContourSet as a legend handle,
                # so the legend entry is a proxy line drawn in the same style.
                ax.legend(
                    handles=[
                        Line2D([], [], color="red", linewidth=2.2,
                               label=f"{targets.label} target")
                    ],
                    loc="upper right", frameon=True, fontsize=8,
                )
            else:
                side = "above" if finite.min() >= target_level else "below"
                ax.text(
                    0.98, 0.02,
                    f"{targets.label} target ({target_level:g}) is {side}\n"
                    f"the whole mapped range",
                    transform=ax.transAxes, ha="right", va="bottom",
                    fontsize=7, color="red",
                )

        ax.set_xlabel("Full-state pressure (bar)")
        ax.grid(True, alpha=0.2, linestyle=":")

    ax_gc.set_ylabel("Full-state temperature (K)")

    fig.suptitle(title or "Forward system capacity maps (AX-21)")
    fig.text(0.5, -0.02, GATE_V3_NOTE, ha="center", va="top", fontsize=7,
             style="italic", wrap=True)
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")

    return fig, (ax_gc, ax_vc)


@_styled
def plot_acceptability_maps(maps, reference_points=None, title=None,
                            savepath=None):
    """Material acceptability maps in two parameter planes (F6).

    One panel per map. The acceptable region -- where the system meets both the
    gravimetric and the volumetric target -- is shaded, each target's own
    boundary is drawn as a labelled contour so the reader can see which of the
    two is binding where, and parameter combinations that are not coherent
    materials at all are hatched rather than left blank.

    This is the deterministic draft of the signature figure. The published
    version redraws the boundary as a Monte Carlo probability band once the
    uncertainty layer exists; a single line here asserts a sharpness the
    underlying parameter estimates do not support (manual 4.1, 4.3).

    Performs NO physics: each entry of ``maps`` is consumed exactly as
    :func:`h2star.inverse.acceptability_map` returns it.

    Parameters
    ----------
    maps : sequence of dict
        One acceptability-map result per panel.
    reference_points : dict, optional
        ``{label: {parameter_name: value}}``. A point is plotted on a panel
        only when both of that panel's swept parameters are present in its
        mapping, so one dictionary can serve panels in different planes.
    title : str, optional
        Figure suptitle.
    savepath : str or pathlib.Path, optional
        If given, the figure is saved here at 300 dpi with a tight bounding
        box.

    Returns
    -------
    tuple
        ``(fig, axes)`` with one axis per map.
    """
    maps = list(maps)
    fig, axes = plt.subplots(1, len(maps), figsize=(6.5 * len(maps), 5.5),
                             squeeze=False)
    axes = list(axes[0])

    for ax, result in zip(axes, maps):
        x = np.asarray(result["x_values"], dtype=float)
        y = np.asarray(result["y_values"], dtype=float)
        gc = np.asarray(result["GC"], dtype=float)
        vc = np.asarray(result["VC"], dtype=float)
        feasible = np.asarray(result["feasible"], dtype=bool)
        evaluable = np.asarray(result["evaluable"], dtype=bool)
        targets = result["targets"]

        # Legend handles are built as proxies: Matplotlib will not accept a
        # ContourSet or a hatch fill as a legend handle.
        handles = []

        # Acceptable region.
        ax.contourf(x, y, feasible.astype(float), levels=[0.5, 1.5],
                    colors=["tab:green"], alpha=0.30)
        handles.append(
            Patch(facecolor="tab:green", alpha=0.30,
                  label="Meets both targets")
        )

        # Nodes that are not coherent materials, kept visually distinct from
        # nodes that are merely below target.
        if not evaluable.all():
            mask = (~evaluable).astype(float)
            # A grey fill carries the region even where the hatch is too fine
            # to read; the hatch distinguishes it from a low-capacity region.
            ax.contourf(x, y, mask, levels=[0.5, 1.5],
                        colors=["lightgrey"], alpha=0.55)
            ax.contourf(x, y, mask, levels=[0.5, 1.5],
                        colors=["none"], hatches=["xx"])
            ax.contour(x, y, mask, levels=[0.5], colors="dimgrey",
                       linewidths=0.9, linestyles=":")
            handles.append(
                Patch(facecolor="lightgrey", alpha=0.55, edgecolor="dimgrey",
                      hatch="xx",
                      label="Not a coherent material (void volume $<$ 0)")
            )

        for field, level, colour, label in (
            (gc, targets.gc, "tab:blue", f"GC = {targets.gc:g} kg kg$^{{-1}}$"),
            (vc, targets.vc, "tab:orange", f"VC = {targets.vc:g} kg L$^{{-1}}$"),
        ):
            finite = field[np.isfinite(field)]
            if finite.size and finite.min() < level < finite.max():
                ax.contour(x, y, field, levels=[level], colors=colour,
                           linewidths=2.0)
                handles.append(
                    Line2D([], [], color=colour, linewidth=2.0, label=label)
                )

        if reference_points:
            for label, coords in reference_points.items():
                if result["param_x"] in coords and result["param_y"] in coords:
                    marker, = ax.plot(
                        coords[result["param_x"]],
                        coords[result["param_y"]],
                        marker="*", markersize=15, linestyle="none",
                        markeredgecolor="k", markerfacecolor="white",
                        zorder=5, label=label,
                    )
                    handles.append(marker)

        ax.set_xlabel(_param_label(result["param_x"]))
        ax.set_ylabel(_param_label(result["param_y"]))
        point = result["operating_point"]
        ax.set_title(
            f"Acceptable region vs {targets.label}\n"
            f"{point.P_full / 1e5:.0f} bar / {point.T_full:.0f} K full, "
            f"{point.P_empty / 1e5:.0f} bar / {point.T_empty:.0f} K empty",
            fontsize=10,
        )
        ax.legend(handles=handles, loc="best", fontsize=8, frameon=True)
        ax.grid(True, alpha=0.2, linestyle=":")

    fig.suptitle(
        title
        or "Material acceptability map (deterministic draft; "
           "uncertainty band added at Gate V4)"
    )
    fig.text(0.5, -0.03, GATE_V3_NOTE, ha="center", va="top", fontsize=7,
             style="italic", wrap=True)
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")

    return fig, axes


@_styled
def plot_probability_maps(maps, coherence_curves=None, reference_points=None,
                          title=None, savepath=None,
                          levels=(0.05, 0.50, 0.95)):
    """Material acceptability as a Monte Carlo probability band (F6).

    The signature figure. Each panel shades ``P(feasible)`` over a plane of two
    material parameters and draws the pre-registered probability contours, so
    the feasibility boundary appears as a band whose width is the blur that
    material-parameter uncertainty alone puts on it. A single line would assert
    a precision the Gate V2 parameter estimates do not support.

    Performs NO physics. Each entry of ``maps`` is consumed exactly as
    :func:`h2star.inverse.probability_map` returns it.

    Parameters
    ----------
    maps : sequence of dict
        One probability-map result per panel.
    coherence_curves : sequence of dict, optional
        One entry per panel, each ``{label: (x, y)}`` or
        ``{label: (x, None)}``. A curve with ``y`` given is drawn as a line; a
        curve with ``y`` of ``None`` is drawn as a vertical line at the single
        x value. Used for the pore-volume coherence limits, which say where the
        adsorbed phase would exceed the space the packing leaves for it.
    reference_points : dict, optional
        ``{label: {parameter: value}}``; a point is drawn on a panel only when
        both of that panel's swept parameters appear in its mapping.
    title : str, optional
        Figure suptitle.
    savepath : str or pathlib.Path, optional
        Saved at 300 dpi with a tight bounding box.
    levels : sequence of float, optional
        Probability contours to draw; the pre-registered 0.05, 0.50 and 0.95.

    Returns
    -------
    tuple
        ``(fig, axes)``.
    """
    maps = list(maps)
    fig, axes = plt.subplots(1, len(maps), figsize=(7.0 * len(maps), 5.8),
                             squeeze=False)
    axes = list(axes[0])
    curves = list(coherence_curves or [{} for _ in maps])

    for panel, (ax, result) in enumerate(zip(axes, maps)):
        x = np.asarray(result["x_values"], dtype=float)
        y = np.asarray(result["y_values"], dtype=float)
        probability = np.asarray(result["probability"], dtype=float)
        targets = result["targets"]

        handles = []

        shaded = ax.contourf(x, y, probability, levels=np.linspace(0, 1, 21),
                             cmap="RdYlGn", vmin=0.0, vmax=1.0)
        fig.colorbar(shaded, ax=ax, label="P(meets both DOE targets)")

        styles = {0.05: ":", 0.50: "-", 0.95: "--"}
        for level in levels:
            finite = probability[np.isfinite(probability)]
            if finite.size and finite.min() < level < finite.max():
                ax.contour(x, y, probability, levels=[level], colors="black",
                           linewidths=1.8,
                           linestyles=styles.get(level, "-"))
                handles.append(
                    Line2D([], [], color="black", linewidth=1.8,
                           linestyle=styles.get(level, "-"),
                           label=f"P = {level:g}")
                )

        for label, (cx, cy) in (curves[panel] if panel < len(curves) else {}).items():
            if cy is None:
                line = ax.axvline(float(cx), color="tab:purple",
                                  linewidth=2.0, linestyle="-.")
            else:
                line, = ax.plot(cx, cy, color="tab:purple", linewidth=2.0,
                                linestyle="-.")
            line.set_label(label)
            handles.append(line)

        # An overlaid curve must not stretch the axes past the mapped region:
        # the blank margin it would add reads as unmapped data.
        ax.set_xlim(x.min(), x.max())
        ax.set_ylim(y.min(), y.max())

        if reference_points:
            for label, coords in reference_points.items():
                if result["param_x"] in coords and result["param_y"] in coords:
                    marker, = ax.plot(
                        coords[result["param_x"]], coords[result["param_y"]],
                        marker="*", markersize=16, linestyle="none",
                        markeredgecolor="k", markerfacecolor="white",
                        zorder=6, label=label,
                    )
                    handles.append(marker)

        point = result["operating_point"]
        ax.set_xlabel(_param_label(result["param_x"]))
        ax.set_ylabel(_param_label(result["param_y"]))
        ax.set_title(
            f"P(meets {targets.label}) under material-parameter uncertainty\n"
            f"{point.P_full / 1e5:.0f} bar / {point.T_full:.0f} K full, "
            f"{point.P_empty / 1e5:.0f} bar / {point.T_empty:.0f} K empty, "
            f"N = {result['n_samples']} per node",
            fontsize=10,
        )
        # Upper left: the low-probability corner, which carries no detail a
        # legend can obscure. Lower right is where the band lives.
        ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=True,
                  framealpha=0.92)
        ax.grid(True, alpha=0.2, linestyle=":")

    fig.suptitle(
        title or "Material acceptability as a probability band (F6)"
    )
    caveat = maps[0].get("caveat", GATE_V3_NOTE)
    fig.text(0.5, -0.04, caveat, ha="center", va="top", fontsize=7,
             style="italic", wrap=True)
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")

    return fig, axes


@_styled
def plot_sobol_indices(studies, labels, output="GC", title=None, savepath=None):
    """Sobol first- and total-order indices at two envelopes, side by side (F7).

    Grouped horizontal bars per parameter, one panel per envelope, ordered by
    the first panel's total-order index so the two panels are directly
    comparable. The point of the figure is the CHANGE between panels: whether
    the property that controls system performance shifts with operating regime
    (claim C3).

    Performs NO physics; consumes :func:`h2star.sensitivity.sobol_indices`
    output.

    Parameters
    ----------
    studies : sequence of dict
        One Sobol result per envelope.
    labels : sequence of str
        Panel labels, same length as ``studies``.
    output : str, optional
        ``"GC"`` or ``"VC"``; which output's indices to draw.
    title : str, optional
        Figure suptitle.
    savepath : str or pathlib.Path, optional
        Saved at 300 dpi with a tight bounding box.

    Returns
    -------
    tuple
        ``(fig, axes)``.
    """
    studies = list(studies)
    labels = list(labels)
    if len(studies) != len(labels):
        raise ValueError(
            f"Got {len(studies)} studies and {len(labels)} labels; they must "
            f"correspond."
        )

    # Order by the first panel so the panels can be read against each other.
    names = list(studies[0]["names"])
    order = np.argsort(studies[0][f"ST_{output}"])
    names = [names[i] for i in order]

    fig, axes = plt.subplots(1, len(studies), figsize=(6.4 * len(studies), 5.2),
                             sharex=True, squeeze=False)
    axes = list(axes[0])
    positions = np.arange(len(names))

    for ax, study, label in zip(axes, studies, labels):
        study_names = list(study["names"])
        s1 = np.array([study[f"S1_{output}"][study_names.index(n)] for n in names])
        st = np.array([study[f"ST_{output}"][study_names.index(n)] for n in names])
        s1_conf = np.array(
            [study[f"S1_conf_{output}"][study_names.index(n)] for n in names]
        )
        st_conf = np.array(
            [study[f"ST_conf_{output}"][study_names.index(n)] for n in names]
        )

        ax.barh(positions + 0.2, st, height=0.38, xerr=st_conf,
                color="tab:blue", alpha=0.85, label="Total order $S_T$",
                error_kw={"elinewidth": 0.8})
        ax.barh(positions - 0.2, s1, height=0.38, xerr=s1_conf,
                color="tab:orange", alpha=0.85, label="First order $S_1$",
                error_kw={"elinewidth": 0.8})

        ax.set_yticks(positions)
        ax.set_yticklabels([_PARAM_SHORT.get(n, n) for n in names], fontsize=9)
        ax.set_xlabel(f"Sobol index for system {output}")
        ax.set_title(label, fontsize=10)
        ax.axvline(0.0, color="k", linewidth=0.8)
        ax.grid(True, axis="x", alpha=0.25, linestyle=":")

    axes[0].legend(loc="lower right", fontsize=8, frameon=True)

    fig.suptitle(
        title or f"Global sensitivity of system {output} by operating regime (F7)"
    )
    fig.text(0.5, -0.05, studies[0].get("caveat", ""), ha="center", va="top",
             fontsize=7, style="italic", wrap=True)
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")

    return fig, axes


@_styled
def plot_cnt_gap(waterfalls, screen, title=None, savepath=None):
    """CNT case study: the material-to-system gap and the consistency screen (F8).

    Two panels. The left is the gap waterfall for the best-provenanced reported
    uptake, each bar the same usable hydrogen divided by a larger denominator,
    with the excess/absolute ambiguity drawn as the whisker -- because no paper
    in the corpus states which basis its measurement is on, and that ambiguity
    is larger than any engineering uncertainty in the cascade.

    The right is the physical-consistency screen: the limiting uptake each
    reported value implies, against the uptake at which the adsorbed phase
    would exceed the pore volume the packing leaves. Entries beyond that line
    describe materials that cannot exist at the assumed packing density.

    Performs no physics; consumes prepared dictionaries.

    Parameters
    ----------
    waterfalls : dict
        ``{"label": str, "primary": waterfall, "alternate": waterfall}`` where
        each waterfall is :func:`h2star.system.gap_waterfall` output. The
        alternate supplies the whisker.
    screen : dict
        ``entries``, a list of ``(key, n_max_or_None, accepted_bool, note)``;
        ``limits``, ``{label: value}`` for the coherence lines; and
        ``reference``, ``(label, n_max)`` for the comparison sorbent.
    title : str, optional
        Figure suptitle.
    savepath : str or pathlib.Path, optional
        Saved at 300 dpi with a tight bounding box.

    Returns
    -------
    tuple
        ``(fig, (ax_waterfall, ax_screen))``.
    """
    fig, (ax_w, ax_s) = plt.subplots(1, 2, figsize=(14.0, 5.8))

    # ---- left: the gap waterfall ----------------------------------------
    primary = waterfalls["primary"]
    alternate = waterfalls.get("alternate")
    labels = [label for _, label, _, _ in primary["stages"]]
    values = [value for _, _, value, _ in primary["stages"]]
    positions = np.arange(len(values))

    colours = ["tab:blue"] + ["tab:orange"] * (len(values) - 2) + ["tab:green"]
    ax_w.bar(positions, values, color=colours, alpha=0.85, width=0.68)

    if alternate is not None:
        other = [value for _, _, value, _ in alternate["stages"]]
        lower = [min(a, b) for a, b in zip(values, other)]
        upper = [max(a, b) for a, b in zip(values, other)]
        ax_w.errorbar(
            positions, values,
            yerr=[
                [v - lo for v, lo in zip(values, lower)],
                [hi - v for v, hi in zip(values, upper)],
            ],
            fmt="none", ecolor="black", elinewidth=1.2, capsize=5,
            label="excess / absolute basis ambiguity",
        )

    for position, value in zip(positions, values):
        ax_w.annotate(f"{value:.3f}", (position, value), ha="center",
                      va="bottom", fontsize=8,
                      xytext=(0, 3), textcoords="offset points")

    ax_w.set_xticks(positions)
    ax_w.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax_w.set_ylabel("Usable H$_2$ per kg of accumulated mass (kg kg$^{-1}$)")
    ax_w.set_title(
        f"Material-to-system cascade: {waterfalls['label']}\n"
        f"total loss factor {primary['total_factor']:.2f}x",
        fontsize=10,
    )
    ax_w.legend(loc="upper right", fontsize=8, frameon=True)
    ax_w.grid(True, axis="y", alpha=0.25, linestyle=":")

    # ---- right: the consistency screen ----------------------------------
    keys = [key for key, _, _, _ in screen["entries"]]
    inferred = [
        value if value is not None else 0.0
        for _, value, _, _ in screen["entries"]
    ]
    accepted = [flag for _, _, flag, _ in screen["entries"]]
    rows = np.arange(len(keys))

    ax_s.barh(
        rows, inferred,
        color=["tab:green" if flag else "tab:red" for flag in accepted],
        alpha=0.8, height=0.6,
    )
    for row, (key, value, flag, note) in zip(rows, screen["entries"]):
        if value is None:
            ax_s.annotate(
                note, (0.0, row), xytext=(6, 0), textcoords="offset points",
                va="center", fontsize=8, color="tab:red", style="italic",
            )
        else:
            ax_s.annotate(
                f"{value:.0f}", (value, row), xytext=(4, 0),
                textcoords="offset points", va="center", fontsize=8,
            )

    handles = [
        Patch(facecolor="tab:green", alpha=0.8, label="within the pore-volume limit"),
        Patch(facecolor="tab:red", alpha=0.8, label="rejected by the screen"),
    ]
    for style, (label, value) in zip(("-.", ":"), screen["limits"].items()):
        ax_s.axvline(value, color="tab:purple", linewidth=2.0, linestyle=style)
        handles.append(
            Line2D([], [], color="tab:purple", linewidth=2.0, linestyle=style,
                   label=f"{label} ({value:.0f} mol kg$^{{-1}}$)")
        )
    ref_label, ref_value = screen["reference"]
    ax_s.axvline(ref_value, color="black", linewidth=1.5, linestyle="--")
    handles.append(
        Line2D([], [], color="black", linewidth=1.5, linestyle="--",
               label=f"{ref_label} ({ref_value:.0f} mol kg$^{{-1}}$)")
    )

    ax_s.set_yticks(rows)
    ax_s.set_yticklabels(keys, fontsize=9)
    ax_s.invert_yaxis()
    ax_s.set_xlabel("Limiting uptake $n_{\\mathrm{max}}$ implied by the "
                    "reported value (mol kg$^{-1}$)")
    ax_s.set_title(
        "Physical-consistency screen on reported CNT uptakes\n"
        "(absolute basis; the adsorbed phase must fit the pore volume)",
        fontsize=10,
    )
    ax_s.legend(handles=handles, loc="lower right", fontsize=8, frameon=True)
    ax_s.grid(True, axis="x", alpha=0.25, linestyle=":")

    fig.suptitle(title or "Carbon nanotubes: the system-level gap (F8)")
    fig.text(0.5, -0.08, GATE_V3_NOTE + " Every inferred limiting uptake "
             "additionally rests on transferring AX-21's characteristic energy "
             "and densities to a nanotube sample, which no paper in the corpus "
             "reports.", ha="center", va="top", fontsize=7, style="italic",
             wrap=True)
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=300, bbox_inches="tight")

    return fig, (ax_w, ax_s)
