"""The committed figures must come back byte-for-byte under a hostile host.

This is the test that makes H2STAR's reproducibility claim falsifiable, and it
exists because two weaker attempts were not.

The first claim was that the figures were "byte-identical on repeat runs on
this platform". That was true and it was the wrong test: repeat runs inside one
environment cannot detect output that depends on the environment. A clean-room
run then regenerated all nine PNGs from a fresh clone and all nine differed,
because the development container names ``Inter`` in ``font.family``.

The second claim was that the figures were byte-identical "for a given
Matplotlib and FreeType version", on the evidence of a cross-environment
comparison. That was also the wrong test: the two environments compared
differed in only the two settings the fix had pinned, so the comparison could
not distinguish "the pin neutralised the host" from "both hosts agreed on
everything else". An adversarial review then demonstrated sixteen further
host-settable ``rcParams`` that moved the bytes with that pin in force, with
the whole suite green.

The lesson was that enumerating settings is the wrong shape of fix and
comparing agreeable environments is the wrong shape of evidence. So
``viz.figure_style`` now applies an entire recorded configuration, and this
test checks it the only way that can fail: it makes the host hostile on
purpose, one setting at a time and then all at once, regenerates the figures
through the same code path that published them, and demands the committed
bytes back.

:data:`HOSTILE_RCPARAMS` includes every one of the sixteen. If the recorded
configuration ever stops covering something that reaches the canvas, the way
to find out is to add it here and watch this test fail.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

from h2star import viz

REPO_ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = REPO_ROOT / "figures"
SCRIPT_PATH = REPO_ROOT / "scripts" / "make_all_figures.py"

#: Settings a host can supply that reach the Agg canvas. Every entry is a value
#: deliberately unlike the recorded one. The first sixteen are the ones an
#: adversarial review demonstrated moving the committed bytes through the
#: earlier seven-key pin; the rest broaden the sweep across the namespaces that
#: draw.
HOSTILE_RCPARAMS = {
    # Demonstrated to move the bytes through the earlier pin.
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.37,
    "savefig.transparent": True,
    "savefig.facecolor": "red",
    "figure.facecolor": "gainsboro",
    "figure.dpi": 217.0,
    "font.weight": "bold",
    "font.stretch": "condensed",
    "font.style": "italic",
    "axes.titlesize": 21.0,
    "xtick.labelsize": 14.0,
    "legend.fontsize": 14.0,
    "lines.antialiased": False,
    "path.simplify": False,
    "path.simplify_threshold": 0.9,
    "mathtext.default": "rm",
    # Broader sweep over the namespaces that draw.
    "font.family": ["serif"],
    "font.serif": ["DejaVu Serif"],
    "font.size": 13.0,
    "text.hinting": "no_hinting",
    "text.antialiased": False,
    "mathtext.fontset": "stix",
    "axes.labelsize": 15.0,
    "axes.labelweight": "bold",
    "axes.linewidth": 2.5,
    "axes.grid": True,
    "axes.edgecolor": "magenta",
    "axes.facecolor": "lightyellow",
    "axes.titleweight": "bold",
    "axes.unicode_minus": False,
    "axes.prop_cycle": mpl.cycler(color=["#ff0000", "#00ff00", "#0000ff"]),
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 9.0,
    "ytick.major.width": 3.0,
    "ytick.labelsize": 14.0,
    "legend.frameon": False,
    "legend.markerscale": 2.0,
    "legend.borderpad": 1.4,
    "lines.linewidth": 3.5,
    "lines.markersize": 12.0,
    "lines.dash_capstyle": "round",
    "patch.antialiased": False,
    "patch.linewidth": 2.0,
    "patch.edgecolor": "cyan",
    "grid.color": "orange",
    "grid.linewidth": 2.0,
    "grid.alpha": 0.9,
    "hatch.linewidth": 3.0,
    "image.interpolation": "nearest",
    "image.cmap": "hot",
    "figure.edgecolor": "purple",
    "figure.titlesize": 22.0,
    "figure.titleweight": "bold",
    "figure.autolayout": True,
    "figure.constrained_layout.use": True,
    "savefig.edgecolor": "blue",
    "savefig.orientation": "landscape",
    "contour.linewidth": 2.5,
    "scatter.marker": "x",
    "errorbar.capsize": 5.0,
    "boxplot.notch": True,
    "pcolor.shading": "nearest",
}

def _covered_hostile_settings():
    """The hostile settings the recorded configuration actually pins here.

    On a Matplotlib that rejects some recorded settings they are dropped and
    fall back to the host, so the pin does not claim to cover them and the
    sweep must not either. On the recorded stack nothing is dropped and this
    is the whole set, which
    :func:`test_the_hostile_sweep_is_complete_on_the_recorded_stack` asserts.
    """
    return {
        key: value for key, value in HOSTILE_RCPARAMS.items()
        if key not in viz.FIGURE_STYLE_UNSUPPORTED
    }


#: The cheap figures. F1 is drawn entirely inside a ``viz`` function; F3 is
#: assembled by the *caller* around :func:`viz.plot_isosteric_heat`, so the two
#: together exercise both paths by which a published figure is produced. The
#: expensive figures share the same path and the clean-room run compares all
#: nine, so repeating them here would buy nothing for ten minutes.
CHEAP_FIGURES = {
    "F1": "F1_eos_parity.png",
    "F3": "F3_isosteric_heat.png",
}


def _load_script():
    """Import ``scripts/make_all_figures.py`` as a module.

    The figures must be regenerated through the code that published them, not
    through a reimplementation in the test: a test that built its own figure
    would verify the test's pin, not the script's.
    """
    spec = importlib.util.spec_from_file_location(
        "h2star_make_all_figures", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script():
    return _load_script()


@pytest.fixture(scope="module")
def committed_digests():
    """SHA-256 of each committed figure this test regenerates."""
    digests = {}
    for name, filename in CHEAP_FIGURES.items():
        path = FIGURE_DIR / filename
        assert path.is_file(), (
            f"{path} is missing; the committed figure is the reference"
        )
        digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


@pytest.fixture(scope="module")
def baseline_digests(script, tmp_path_factory):
    """SHA-256 of each figure regenerated *here*, with no host interference.

    The hostile sweep compares against this rather than against the committed
    bytes, which is what lets it run anywhere. The property under test is that
    the recorded configuration makes a figure independent of the host, and
    that is true on every platform; only equality with the *committed* bytes
    is specific to the rendering stack those were produced under.

    Checking against the committed bytes on a stack that cannot produce them
    was a real defect: CI runs macOS, and this module asserted byte-identity
    unconditionally while `docs/known_limitations.md` said byte-identity holds
    only within one stack. The test contradicted the documentation.
    """
    out = tmp_path_factory.mktemp("baseline")
    return _regenerate(script, CHEAP_FIGURES, out)


def stack_matches():
    """Whether this environment can produce the committed figures' bytes."""
    return viz.FIGURE_STYLE_STACK == viz.rendering_stack()


#: Reason shown when the committed-bytes comparison is not applicable.
STACK_SKIP_REASON = (
    f"rendering stack differs from the one the committed figures were "
    f"produced under: recorded {viz.FIGURE_STYLE_STACK}, running "
    f"{viz.rendering_stack()}. Byte-identity is claimed only within one "
    f"stack (docs/known_limitations.md); the numbers are unaffected and the "
    f"host-independence tests in this module still run."
)


def _regenerate(script, names, out_dir):
    """Rebuild the named figures into ``out_dir`` and return their digests."""
    out_dir.mkdir(parents=True, exist_ok=True)
    builders = {name: builder for name, builder, _ in script.FIGURES}
    digests = {}
    for name in names:
        # Exactly what main() does: every builder runs under the pin.
        with viz.figure_style():
            builders[name](script.load_inputs(), out_dir)
        plt.close("all")
        digests[name] = hashlib.sha256(
            (out_dir / CHEAP_FIGURES[name]).read_bytes()
        ).hexdigest()
    return digests


@pytest.mark.skipif(not stack_matches(), reason=STACK_SKIP_REASON)
def test_the_recorded_configuration_covers_the_recorded_stack():
    """On the stack it was recorded from, nothing may be dropped.

    A recorded configuration cannot pin a setting another Matplotlib lacks or
    rejects, and such a setting falls back to the host. On the recorded stack
    that must never happen: a non-empty drop list there means the record and
    the library disagree, which is the record being broken.

    Off the recorded stack, dropping is expected -- 3.9.4 rejects 26 of these
    324 -- and is reported by :data:`viz.FIGURE_STYLE_UNSUPPORTED` rather than
    failed on, which is why byte-identity is not claimed there either.
    """
    assert not viz.FIGURE_STYLE_UNSUPPORTED, (
        f"on the recorded stack, {len(viz.FIGURE_STYLE_UNSUPPORTED)} recorded "
        f"settings were rejected by Matplotlib {mpl.__version__}: "
        f"{list(viz.FIGURE_STYLE_UNSUPPORTED)}. Re-record with "
        "scripts/record_figure_style.py on a pristine install, regenerate "
        "every figure, and re-run the clean room."
    )


def test_an_unsupported_setting_is_dropped_rather_than_raised():
    """Applying the configuration must never raise, on any Matplotlib.

    Matplotlib raises on an unknown key and on a value its validator rejects.
    A configuration recorded against one version and applied unfiltered to
    another therefore made *every* plotting call raise -- recorded against
    3.11.2 and run against 3.9.4, ``figure_style()`` died on
    ``hatch.color: 'edge'`` and the package was unusable. The filter is what
    keeps a version difference a caveat instead of an outage.
    """
    with viz.figure_style():
        pass
    assert isinstance(viz.FIGURE_STYLE_UNSUPPORTED, tuple)
    for key in viz.FIGURE_STYLE_UNSUPPORTED:
        assert key not in viz.FIGURE_RCPARAMS


def test_the_recorded_configuration_is_not_a_short_list():
    """Guard against the fix regressing to an enumeration of settings.

    The seven-key pin was the defect. A configuration that has shrunk back to
    a handful of keys is that defect returning, and the byte tests below would
    still pass for whichever settings happened to be covered.
    """
    assert len(viz.FIGURE_RCPARAMS) > 250, (
        f"only {len(viz.FIGURE_RCPARAMS)} rcParams are pinned; the recorded "
        "configuration is meant to cover everything Matplotlib's style "
        "machinery considers settable"
    )


def test_recorded_file_is_json_with_a_version():
    """The record must say which Matplotlib it came from."""
    document = json.loads(viz.FIGURE_STYLE_PATH.read_text())
    assert document["matplotlib_version"]
    assert isinstance(document["rcparams"], dict)
    assert document["rcparams"]["font.family"] == ["DejaVu Sans"]


@pytest.mark.skipif(not stack_matches(), reason=STACK_SKIP_REASON)
def test_regenerated_figures_match_the_committed_bytes(baseline_digests,
                                                       committed_digests):
    """On the recorded stack, regenerating reproduces the committed figures.

    This is the claim README and docs/known_limitations.md make, and it is the
    only test here that is specific to a rendering stack. On any other stack
    it skips rather than failing, because the documentation does not claim it
    there -- FreeType rasterises glyphs differently between builds, Matplotlib
    stamps its version into the PNG, and Pillow encodes the file.
    """
    for name, digest in baseline_digests.items():
        assert digest == committed_digests[name], (
            f"{name} does not reproduce on the stack it was recorded under, "
            "so the committed figure and the current code disagree"
        )


@pytest.mark.parametrize("key", sorted(_covered_hostile_settings(), key=str))
def test_figures_reproduce_under_one_hostile_setting(key, script,
                                                     baseline_digests,
                                                     tmp_path):
    """One hostile setting at a time, so a failure names the culprit."""
    with mpl.rc_context({key: HOSTILE_RCPARAMS[key]}):
        digests = _regenerate(script, ["F1"], tmp_path)
    assert digests["F1"] == baseline_digests["F1"], (
        f"a host setting {key} = {HOSTILE_RCPARAMS[key]!r} changed F1's bytes "
        "despite the recorded configuration, so that setting reaches the "
        "canvas and is not covered"
    )


def test_figures_reproduce_under_every_hostile_setting_at_once(
    script, baseline_digests, tmp_path
):
    """The whole hostile environment, against both figure code paths.

    F3 is here rather than in the per-setting sweep because it is the figure
    the *caller* assembles, and the caller's own ``subplots`` and ``savefig``
    were the part the first fix nearly missed.
    """
    with mpl.rc_context(_covered_hostile_settings()):
        digests = _regenerate(script, CHEAP_FIGURES, tmp_path)
    for name, digest in digests.items():
        assert digest == baseline_digests[name], (
            f"{name} does not reproduce under a hostile host even though "
            "every setting individually was covered; something in the "
            "combination reaches the canvas"
        )


def test_the_test_can_fail(script, baseline_digests, tmp_path):
    """Without the pin, a hostile host does move the bytes.

    If this passed trivially the sweep above would prove nothing: it would be
    asserting that figures are stable for some reason other than the pin. So
    the pin is genuinely bypassed here and the bytes are required to *differ*.

    Bypassing it means calling the *undecorated* plotting function through
    ``__wrapped__``. Wrapping the builder in nothing is not a bypass, because
    the ``viz`` function it calls carries ``@_styled`` itself -- which is
    defence in depth worth having, and which made the first version of this
    control pass vacuously.
    """
    isotherms = script._nist_isotherms(script.load_inputs())
    target = tmp_path / CHEAP_FIGURES["F1"]
    with mpl.rc_context(_covered_hostile_settings()):
        viz.eos_parity_plot.__wrapped__(isotherms, savepath=target)
        plt.close("all")
    unpinned = hashlib.sha256(target.read_bytes()).hexdigest()
    assert unpinned != baseline_digests["F1"], (
        "a hostile host left F1's bytes unchanged with the pin genuinely "
        "bypassed, so this module's hostile settings do not reach the canvas "
        "and the sweep above is vacuous"
    )


@pytest.mark.skipif(not stack_matches(), reason=STACK_SKIP_REASON)
def test_the_hostile_sweep_is_complete_on_the_recorded_stack():
    """On the recorded stack the sweep must cover every hostile setting.

    The sweep is scoped to the settings the configuration actually pins, so
    that a Matplotlib which rejects some of them does not fail a test for not
    covering what it never claimed to. That scoping must not quietly shrink
    the sweep where it is supposed to be whole.
    """
    assert _covered_hostile_settings() == HOSTILE_RCPARAMS
