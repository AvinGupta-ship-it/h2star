"""Visualization of isotherms, envelopes, and system-level results."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .heats import isosteric_heat


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
