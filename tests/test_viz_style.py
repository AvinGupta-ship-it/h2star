"""The figure rendering configuration is the repository's, not the host's.

A figure's bytes are a function of the whole of ``rcParams``, and Matplotlib
builds ``rcParams`` from whatever configuration the host supplies. A host that
changes any of a few hundred settings changes every pixel of every figure while
leaving every number it plots untouched, and figures drawn that way reproduce
nowhere else.

H2STAR shipped that defect and then fixed it twice. The first fix pinned the
seven font and text settings the original defect involved; an adversarial
review demonstrated sixteen more that still moved the bytes with that pin in
force, with the whole suite green. So ``viz.figure_style`` now applies an
entire recorded configuration rather than a list of settings believed to
matter.

These tests cover the *mechanism*: that the configuration is whole, that it is
applied to every drawing function, and that it leaves no global state behind.
Whether it actually holds the bytes still is ``tests/test_figure_bytes.py``,
which regenerates figures under a hostile host and demands the committed bytes
back. Both are needed: this file would pass for a pin that covered the wrong
settings, and that file would pass for a function nobody had decorated if the
host happened to be benign.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest
from matplotlib.font_manager import FontProperties, findfont

from h2star import viz

# A host configuration deliberately unlike the recorded one, standing in for
# the kind of ambient override a container image applies. Palatino is a serif
# face, so a figure drawn under it is visibly and measurably not the pinned one.
AMBIENT_OVERRIDE = {
    "font.family": ["Palatino", "serif"],
    "font.size": 13.0,
    "text.hinting": "no_hinting",
    "savefig.bbox": "tight",
    "figure.dpi": 171.0,
}

#: Public callables in :mod:`h2star.viz` that are not drawing functions and so
#: are not expected to carry the pin. Kept as a short allowlist rather than a
#: name pattern: the previous version of this test discovered functions by the
#: ``plot_*`` / ``*_plot`` naming convention, and an adversarial review showed
#: an unstyled ``draw_parity_grid`` sailing past it.
NON_DRAWING_PUBLIC_NAMES = {"figure_style"}


@pytest.fixture
def ambient_override():
    """Run the test body under a host-like ``rcParams`` override."""
    with mpl.rc_context(AMBIENT_OVERRIDE):
        yield


def _drawing_functions():
    """Every public callable this module defines that should carry the pin.

    Discovery is by defining module, not by name, so a drawing function named
    anything at all is still found. Imported names (``Path``, ``Line2D``,
    ``cycler``, ``isosteric_heat``) are excluded because their ``__module__``
    is not this one.
    """
    found = {}
    for name in dir(viz):
        if name.startswith("_") or name in NON_DRAWING_PUBLIC_NAMES:
            continue
        obj = getattr(viz, name)
        if callable(obj) and getattr(obj, "__module__", None) == viz.__name__:
            found[name] = obj
    return found


def test_every_drawing_function_carries_the_pin():
    """No drawing function may run under the host's configuration.

    ``_styled`` stamps its wrapper with ``_h2star_styled``. The stamp is what
    is checked, rather than ``functools.wraps``'s ``__wrapped__``: an
    adversarial review showed that any unrelated ``wraps``-based decorator
    satisfies ``__wrapped__``, so a function could carry a logging wrapper, no
    pin, and a passing test.
    """
    functions = _drawing_functions()
    # Guard the guard: if discovery ever stops matching, this test would pass
    # by finding nothing to check.
    assert len(functions) >= 9, (
        f"expected the full drawing surface, found {sorted(functions)}"
    )

    unstyled = sorted(
        name for name, obj in functions.items()
        if not getattr(obj, "_h2star_styled", False)
    )
    assert not unstyled, (
        "these drawing functions run under the host's rcParams rather than "
        f"the recorded configuration; add @_styled: {unstyled}"
    )


def test_the_recorded_configuration_is_not_empty():
    """A vacuous configuration would make several tests below pass trivially."""
    assert len(viz.FIGURE_RCPARAMS) > 250, (
        f"only {len(viz.FIGURE_RCPARAMS)} rcParams are recorded; the point of "
        "recording a whole configuration is that it is whole"
    )
    assert viz.FIGURE_STYLE_VERSION


def test_recorded_keys_are_all_real_rcparams():
    """A typo, or a key a newer Matplotlib dropped, would pin nothing."""
    unknown = sorted(k for k in viz.FIGURE_RCPARAMS if k not in mpl.rcParams)
    assert not unknown, f"not rcParams keys in this Matplotlib: {unknown}"


def test_the_one_deliberate_deviation_is_the_font():
    """The configuration is stock except for naming the font outright.

    Recording stock values means the figures depend on Matplotlib's documented
    behaviour rather than on a house style this project invented. The single
    exception is ``font.family``, which names the concrete font the default
    ``sans-serif`` alias resolves to, so that resolution cannot be redirected
    by the host's ``font.sans-serif`` list or by which fonts it has installed.
    """
    assert viz.FIGURE_RCPARAMS["font.family"] == ["DejaVu Sans"]


def test_pinned_font_ships_with_matplotlib():
    """The pinned font must need no system font to be installed.

    DejaVu Sans lives inside the Matplotlib wheel. Resolving to a path under
    ``mpl-data`` is what makes the configuration portable: a machine with no
    fonts of its own still draws these figures identically.
    """
    with viz.figure_style():
        resolved = findfont(FontProperties(family=viz.FIGURE_RCPARAMS["font.family"]))
    assert "mpl-data" in resolved, (
        f"pinned font resolved to {resolved}, outside Matplotlib's bundled "
        "fonts, so figures would depend on the host's installed fonts"
    )
    assert "DejaVuSans" in resolved


def test_figure_style_overrides_the_host(ambient_override):
    """Inside the context manager, the recorded configuration wins."""
    assert mpl.rcParams["font.family"] == ["Palatino", "serif"]
    assert mpl.rcParams["savefig.bbox"] == "tight"
    with viz.figure_style():
        for key in AMBIENT_OVERRIDE:
            assert mpl.rcParams[key] == viz.FIGURE_RCPARAMS[key], (
                f"{key} was left at the host's value inside figure_style"
            )
        assert mpl.rcParams["font.family"] == ["DejaVu Sans"]
        assert mpl.rcParams["savefig.bbox"] is None


def test_figure_style_restores_ambient_rcparams(ambient_override):
    """Importing or calling this module must not mutate a caller's config.

    A library that leaves global state changed behind it is its own bug, and it
    would make the pin unfalsifiable: every later figure in the process would
    look pinned whether or not it was drawn under the pin.
    """
    before = {key: mpl.rcParams[key] for key in AMBIENT_OVERRIDE}
    with viz.figure_style():
        pass
    after = {key: mpl.rcParams[key] for key in AMBIENT_OVERRIDE}
    assert after == before
    assert after["font.family"] == ["Palatino", "serif"]


def test_plot_call_draws_with_the_pinned_font(ambient_override):
    """A decorated plotting call ignores the host, end to end.

    Text artists capture their font properties when they are created, so the
    title of a figure drawn under the override reports the pinned family only
    if the configuration was in force while the artist was built.
    """
    isotherms = [{"T": 77.0, "nist": [1.0, 2.0, 3.0], "model": [1.0, 2.0, 3.0]}]
    fig, ax = viz.eos_parity_plot(isotherms)
    try:
        assert ax.title.get_fontfamily() == ["DejaVu Sans"]
        assert ax.xaxis.label.get_fontfamily() == ["DejaVu Sans"]
        # The host set font.size to 13; the configuration puts it back to 10,
        # and the tick labels take their size from it.
        assert ax.get_xticklabels()[0].get_fontsize() == pytest.approx(10.0)
    finally:
        plt.close(fig)
    # And the host's configuration is intact for whatever runs next.
    assert mpl.rcParams["font.family"] == ["Palatino", "serif"]
