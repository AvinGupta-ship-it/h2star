"""The figure rendering configuration is the repository's, not the host's.

A figure's bytes depend on the font its text is drawn with. Matplotlib takes
that font from whichever ``matplotlibrc`` the host environment supplies, so a
host that names a different ``font.family`` changes every label, every tight
bounding box and therefore every pixel of every figure, while leaving every
number it plots untouched. Figures drawn that way reproduce nowhere else.

H2STAR shipped figures with exactly that defect. The clean-room check at the
end of Stage 6 regenerated all nine PNGs from a fresh clone in a fresh
environment: all nine headline numbers reproduced to the last digit and all
nine images differed. The cause was two ``rcParams`` -- ``font.family`` and
``text.hinting`` -- injected by the development container and declared by no
dependency the repository names. Forcing those two values in the clean room
reproduced the committed bytes exactly, which is what established that the
differences were the font configuration and nothing numerical.

These tests exist so that cannot happen quietly again. The important one is
:func:`test_every_public_plot_function_is_styled`: the defect returns the
moment someone adds a plotting function and forgets the pin, and a byte
comparison across environments is the only other thing that would notice.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest
from matplotlib.font_manager import FontProperties, findfont

from h2star import viz

# A host configuration deliberately unlike the pin, standing in for the kind
# of ambient override a container image applies. Palatino is a serif face, so
# a figure drawn under it is visibly and measurably not the pinned figure.
AMBIENT_OVERRIDE = {
    "font.family": ["Palatino", "serif"],
    "font.size": 13.0,
    "text.hinting": "no_hinting",
}


@pytest.fixture
def ambient_override():
    """Run the test body under a host-like ``rcParams`` override."""
    with mpl.rc_context(AMBIENT_OVERRIDE):
        yield


def _plot_functions():
    """Every public plotting entry point in :mod:`h2star.viz`."""
    return sorted(
        name
        for name in dir(viz)
        if not name.startswith("_")
        and callable(getattr(viz, name))
        and (name.startswith("plot_") or name.endswith("_plot"))
    )


def test_every_public_plot_function_is_styled():
    """No plotting function may draw under the host's font configuration.

    ``functools.wraps`` leaves ``__wrapped__`` on the decorated function, so
    the pin is detectable from outside. A new plotting function that forgets
    ``@_styled`` fails here rather than silently shipping figures that only
    reproduce on the machine that drew them.
    """
    names = _plot_functions()
    # Guard the guard: if the discovery predicate ever stops matching, this
    # test would pass by finding nothing to check.
    assert len(names) >= 9, f"expected the full plotting surface, found {names}"

    unstyled = [
        name for name in names if not hasattr(getattr(viz, name), "__wrapped__")
    ]
    assert not unstyled, (
        "these plotting functions draw under the host's rcParams rather than "
        f"the pinned ones; add @_styled: {unstyled}"
    )


def test_pin_names_only_real_rcparams():
    """A typo in a pinned key would silently pin nothing."""
    unknown = [key for key in viz.FIGURE_RCPARAMS if key not in mpl.rcParams]
    assert not unknown, f"not Matplotlib rcParams keys: {unknown}"


#: Matplotlib's own stock defaults for the pinned keys, read from an
#: unmodified Matplotlib 3.11.2 install.
#:
#: These are written out as literals rather than read from
#: ``mpl.rcParamsDefault`` on purpose. ``rcParamsDefault`` is not a record of
#: what Matplotlib ships: a host can modify it, and the container this project
#: was developed in does exactly that -- it reports ``font.family`` as
#: ``['Inter', 'sans-serif', 'DejaVu Sans']`` and ``text.hinting`` as
#: ``'no_hinting'``. Comparing the pin against it would therefore compare the
#: pin against the host, which is the comparison the pin exists to escape.
STOCK_DEFAULTS = {
    "font.size": 10.0,
    "mathtext.fontset": "dejavusans",
    "text.antialiased": True,
    "text.hinting": "default",
    "text.hinting_factor": None,
    "axes.unicode_minus": True,
}


def test_pin_matches_matplotlib_defaults_except_font_family():
    """The pin is Matplotlib's own default behaviour, made explicit.

    Pinning anything else would mean the figures depend on a styling choice
    this repository invented, which is harder to defend and no more
    reproducible. ``font.family`` is the single exception: it names the
    concrete font that the default ``sans-serif`` alias resolves to, so that
    resolution cannot be redirected by the host's ``font.sans-serif`` list or
    by which fonts the host happens to have installed.
    """
    assert set(viz.FIGURE_RCPARAMS) == set(STOCK_DEFAULTS) | {"font.family"}, (
        "the pinned key set changed; confirm the new key's stock default "
        "against an unmodified Matplotlib install and record it here"
    )
    assert viz.FIGURE_RCPARAMS["font.family"] == ["DejaVu Sans"]
    for key, stock in STOCK_DEFAULTS.items():
        assert viz.FIGURE_RCPARAMS[key] == stock, (
            f"{key} is pinned to {viz.FIGURE_RCPARAMS[key]!r} but Matplotlib "
            f"ships {stock!r}"
        )


def test_pinned_font_ships_with_matplotlib():
    """The pinned font must need no system font to be installed.

    DejaVu Sans lives inside the Matplotlib wheel. Resolving to a path under
    ``mpl-data`` is what makes the pin portable: a machine with no fonts of
    its own still draws these figures identically.
    """
    with viz.figure_style():
        resolved = findfont(FontProperties(family=viz.FIGURE_RCPARAMS["font.family"]))
    assert "mpl-data" in resolved, (
        f"pinned font resolved to {resolved}, which is outside Matplotlib's "
        "bundled fonts, so figures would depend on the host's installed fonts"
    )
    assert "DejaVuSans" in resolved


def test_figure_style_applies_the_pin(ambient_override):
    """Inside the context manager, the pin wins over the host."""
    assert mpl.rcParams["font.family"] == ["Palatino", "serif"]
    with viz.figure_style():
        for key, pinned in viz.FIGURE_RCPARAMS.items():
            assert mpl.rcParams[key] == pinned


def test_figure_style_restores_ambient_rcparams(ambient_override):
    """Importing or calling this module must not mutate a caller's config.

    A library that leaves global state changed behind it is its own bug, and
    it would make the pin unfalsifiable: every later figure in the process
    would look pinned whether or not it was drawn under the pin.
    """
    before = {key: mpl.rcParams[key] for key in viz.FIGURE_RCPARAMS}
    with viz.figure_style():
        pass
    after = {key: mpl.rcParams[key] for key in viz.FIGURE_RCPARAMS}
    assert after == before
    assert after["font.family"] == ["Palatino", "serif"]


def test_plot_call_draws_with_the_pinned_font(ambient_override):
    """A decorated plotting call ignores the host font, end to end.

    Text artists capture their font properties when they are created, so the
    title of a figure drawn under the override reports the pinned family only
    if the pin was actually in force while the artist was built.
    """
    isotherms = [{"T": 77.0, "nist": [1.0, 2.0, 3.0], "model": [1.0, 2.0, 3.0]}]
    fig, ax = viz.eos_parity_plot(isotherms)
    try:
        assert ax.title.get_fontfamily() == ["DejaVu Sans"]
        assert ax.xaxis.label.get_fontfamily() == ["DejaVu Sans"]
        # The host set font.size to 13; the pin puts it back to 10, and the
        # tick labels take their size from it.
        assert ax.get_xticklabels()[0].get_fontsize() == pytest.approx(10.0)
    finally:
        plt.close(fig)
    # And the host's configuration is intact for whatever runs next.
    assert mpl.rcParams["font.family"] == ["Palatino", "serif"]
