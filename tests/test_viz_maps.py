"""Tests for the F5 and F6 figure functions in h2star.viz.

Figure code is not physics, and these tests do not pretend otherwise: they
check that the drawing functions consume the map dictionaries exactly as the
engines produce them, that a figure carrying an absolute system capacity also
carries the Gate V3 caveat, and that nothing silently drops a panel or a legend
entry. A figure that renders without error but omits the caveat would be a
quiet overclaim, which is why that one is asserted rather than assumed.
"""

from pathlib import Path

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from h2star import envelope, inverse, viz  # noqa: E402

#: Repository root, resolved from this file. Deliberately NOT imported from
#: ``tests.conftest``: that import only resolves when the repository root
#: happens to be on ``sys.path``, which ``python -m pytest`` arranges and a
#: bare ``pytest`` does not. CI runs the bare form, so the import passed
#: locally and failed there.
REPO_ROOT = Path(__file__).resolve().parents[1]
DOE_TARGETS_YAML = REPO_ROOT / "data" / "targets" / "doe_targets.yaml"


@pytest.fixture(autouse=True)
def _close_figures():
    """Close every figure after each test so the suite does not leak them."""
    yield
    plt.close("all")


@pytest.fixture(scope="module")
def targets():
    """DOE 2025 system targets."""
    return inverse.load_doe_targets(DOE_TARGETS_YAML, "2025")


@pytest.fixture(scope="module")
def small_forward_grid(ax21_material, ax21_isotherm, engineering_params):
    """A coarse forward map, large enough to contour."""
    return envelope.forward_map(
        ax21_material,
        ax21_isotherm,
        engineering_params,
        np.linspace(20.0e5, 200.0e5, 9),
        np.linspace(60.0, 120.0, 7),
    )


@pytest.fixture(scope="module")
def small_accept_maps(ax21_material, engineering_params, targets):
    """Two coarse acceptability maps, one per plane."""
    point = envelope.OperatingPoint(P_full=100.0e5, T_full=80.0)
    return [
        inverse.acceptability_map(
            ax21_material,
            engineering_params,
            "n_max",
            "alpha",
            np.linspace(20.0, 200.0, 11),
            np.linspace(1500.0, 7000.0, 9),
            operating_point=point,
            targets=targets,
        ),
        inverse.acceptability_map(
            ax21_material,
            engineering_params,
            "n_max",
            "rho_bulk",
            np.linspace(20.0, 200.0, 11),
            np.linspace(150.0, 800.0, 9),
            operating_point=point,
            targets=targets,
        ),
    ]


def test_forward_maps_render_two_panels(small_forward_grid, targets):
    """F5 draws a gravimetric and a volumetric panel with labelled axes."""
    fig, (ax_gc, ax_vc) = viz.plot_forward_maps(
        small_forward_grid, targets=targets
    )
    assert ax_gc.get_ylabel().startswith("Full-state temperature")
    assert ax_gc.get_xlabel() == "Full-state pressure (bar)"
    assert ax_vc.get_xlabel() == "Full-state pressure (bar)"
    assert len(fig.axes) >= 4  # two panels plus two colourbars


def test_forward_maps_carry_the_gate_v3_caveat(small_forward_grid, targets):
    """Any absolute-capacity figure states the Gate V3 bound (manual 4.2.3)."""
    fig, _ = viz.plot_forward_maps(small_forward_grid, targets=targets)
    notes = [t.get_text() for t in fig.texts]
    assert any("Gate V3" in note and "optimistic bound" in note
               for note in notes), notes


def test_forward_maps_work_without_targets(small_forward_grid):
    """Targets are optional; the map still draws without a target contour."""
    fig, axes = viz.plot_forward_maps(small_forward_grid, targets=None)
    assert len(axes) == 2


def test_acceptability_maps_render_one_panel_per_map(small_accept_maps,
                                                     targets):
    """F6 draws one labelled panel per supplied map."""
    fig, axes = viz.plot_acceptability_maps(small_accept_maps)
    assert len(axes) == 2
    assert "n_{\\mathrm{max}}" in axes[0].get_xlabel()
    assert "\\alpha" in axes[0].get_ylabel()
    assert "rho_{\\mathrm{bulk}}" in axes[1].get_ylabel()


def test_acceptability_maps_carry_the_gate_v3_caveat(small_accept_maps):
    """The signature figure states the Gate V3 bound too."""
    fig, _ = viz.plot_acceptability_maps(small_accept_maps)
    notes = [t.get_text() for t in fig.texts]
    assert any("Gate V3" in note for note in notes), notes


def test_acceptability_title_says_the_band_is_still_to_come(small_accept_maps):
    """The draft must not be mistaken for the published probability-band F6."""
    fig, _ = viz.plot_acceptability_maps(small_accept_maps)
    suptitle = fig._suptitle.get_text()
    assert "deterministic draft" in suptitle


def test_reference_points_appear_only_in_matching_planes(small_accept_maps,
                                                         ax21_material):
    """A point is plotted only where both of its coordinates are swept."""
    refs = {
        "AX-21": {
            "n_max": ax21_material.n_max,
            "alpha": ax21_material.alpha,
        },
    }
    fig, axes = viz.plot_acceptability_maps(small_accept_maps,
                                            reference_points=refs)
    labels_first = [t.get_text() for t in axes[0].get_legend().get_texts()]
    labels_second = [t.get_text() for t in axes[1].get_legend().get_texts()]
    assert "AX-21" in labels_first
    # The second panel sweeps rho_bulk, which this reference point omits.
    assert "AX-21" not in labels_second


def test_incoherent_region_is_flagged_in_the_legend(small_accept_maps):
    """The rho_bulk plane contains impossible packings, and says so."""
    fig, axes = viz.plot_acceptability_maps(small_accept_maps)
    labels = [t.get_text() for t in axes[1].get_legend().get_texts()]
    assert any("coherent material" in label for label in labels), labels


def test_figures_save_to_disk(small_forward_grid, small_accept_maps, targets,
                              tmp_path):
    """Both functions write a non-trivial PNG when given a savepath."""
    f5 = tmp_path / "f5.png"
    f6 = tmp_path / "f6.png"
    viz.plot_forward_maps(small_forward_grid, targets=targets, savepath=f5)
    viz.plot_acceptability_maps(small_accept_maps, savepath=f6)
    assert f5.stat().st_size > 10_000
    assert f6.stat().st_size > 10_000


def test_param_label_falls_back_to_the_raw_name():
    """An unlabelled parameter still gets an axis label, not a KeyError."""
    assert viz._param_label("n_max").startswith("Limiting uptake")
    assert viz._param_label("not_a_parameter") == "not_a_parameter"
