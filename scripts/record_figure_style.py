#!/usr/bin/env python3
"""Record the rendering configuration that H2STAR's figures are drawn with.

    python3 scripts/record_figure_style.py --check
    python3 scripts/record_figure_style.py --write

``src/h2star/figure_style.json`` holds every ``rcParams`` key Matplotlib's
style machinery considers settable, with its stock value, plus the one
deliberate deviation (``font.family``: ``DejaVu Sans``, named outright rather
than reached through the ``sans-serif`` alias, because DejaVu ships inside the
Matplotlib wheel). ``viz.figure_style`` applies it, which leaves nothing for
the host environment to contribute to a figure's bytes.

**This must be run under a pristine Matplotlib.** It reads
``matplotlib.rcParamsDefault``, and a host can modify that: the container this
project was developed in injects ``font.family: Inter, sans-serif, DejaVu
Sans`` and ``text.hinting: no_hinting`` into it, which is the defect the
recorded configuration exists to neutralise. Recording from such a host would
bake the defect into the file instead. ``--check`` is therefore the normal
mode: it compares the current environment against the recorded file and
reports every difference, so running it anywhere says whether that environment
agrees with the record and names the host's fingerprints if it does not.

``--write`` regenerates the file and refuses unless ``--force`` is given,
because the committed figures were drawn under the current record and
rewriting it invalidates them.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = REPO_ROOT / "src" / "h2star" / "figure_style.json"

#: Not recorded: Matplotlib's own style blacklist plus ``backend``. These
#: select a backend, a timezone, a window-focus policy and similar, none of
#: which reaches the Agg canvas, and several of which are not serialisable.
EXTRA_EXCLUDED = {"backend"}


def _blacklist():
    """Matplotlib's style blacklist, across the versions that moved it.

    3.11 renamed the public ``STYLE_BLACKLIST`` to ``_STYLE_BLACKLIST`` and
    deprecated the ``matplotlib.style.core`` module it used to live in, so
    reaching for the old path emits a warning. Both spellings are tried, newest
    first, and a Matplotlib exposing neither falls back to a literal copy --
    which is safe because every name in it selects a backend, a timezone or a
    window policy, none of which reaches the Agg canvas.
    """
    import matplotlib.style as style

    for attribute in ("_STYLE_BLACKLIST", "STYLE_BLACKLIST"):
        blacklist = getattr(style, attribute, None)
        if blacklist is not None:
            return set(blacklist)
    return {
        "backend", "backend_fallback", "date.epoch", "docstring.hardcopy",
        "figure.max_open_warning", "figure.raise_window", "interactive",
        "savefig.directory", "timezone", "tk.window_focus", "toolbar",
        "webagg.address", "webagg.open_in_browser", "webagg.port",
        "webagg.port_retries",
    }


def rendering_stack():
    """The three libraries a figure's bytes depend on, in this environment.

    Matplotlib lays the figure out, FreeType rasterises the glyphs, and Pillow
    encodes the PNG. The recorded configuration removes the *host* from the
    question; it cannot remove these, so the committed figures' bytes are
    conditional on them and the versions are recorded alongside.
    """
    import matplotlib as mpl
    import matplotlib.ft2font as ft
    import PIL

    return {
        "matplotlib": mpl.__version__,
        "freetype": ft.__freetype_version__,
        "pillow": PIL.__version__,
    }


def current_configuration():
    """The stock configuration of the Matplotlib in this environment."""
    import matplotlib as mpl

    excluded = _blacklist() | EXTRA_EXCLUDED
    recorded = {}
    for key in sorted(mpl.rcParams):
        if key in excluded:
            continue
        value = mpl.rcParamsDefault[key]
        if key == "axes.prop_cycle":
            recorded[key] = {"__cycler_color__": list(value.by_key()["color"])}
            continue
        try:
            json.loads(json.dumps(value))
        except (TypeError, ValueError):
            continue
        recorded[key] = value
    recorded["font.family"] = ["DejaVu Sans"]
    return mpl.__version__, recorded


def _normalise(value):
    """JSON round-trip a value so tuples and lists compare equal."""
    return json.loads(json.dumps(value))


def check():
    """Compare this environment's stock configuration with the record."""
    import matplotlib as mpl

    version, current = current_configuration()
    document = json.loads(RECORD_PATH.read_text())
    recorded = document["rcparams"]

    print(f"recorded from Matplotlib {document.get('matplotlib_version')}, "
          f"running Matplotlib {version}")
    recorded_stack = document.get("rendering_stack", {})
    running_stack = rendering_stack()
    print(f"recorded rendering stack {recorded_stack}")
    print(f"running  rendering stack {running_stack}")
    if recorded_stack and recorded_stack != running_stack:
        print("The rendering stack differs, so the committed figures are not "
              "expected to reproduce byte for byte here. The numbers are "
              "unaffected.")
    print(f"recorded keys {len(recorded)}, this environment {len(current)}")

    missing = sorted(set(recorded) - set(current))
    added = sorted(set(current) - set(recorded))
    differing = sorted(
        key for key in set(recorded) & set(current)
        if _normalise(recorded[key]) != _normalise(current[key])
    )

    # font.family is the deliberate deviation and must differ from nothing:
    # both sides carry the override, so it should not appear below.
    for label, keys in (
        ("only in the record", missing),
        ("only in this environment", added),
        ("different value", differing),
    ):
        if keys:
            print(f"\n{label} ({len(keys)}):")
            for key in keys:
                if label == "different value":
                    print(f"  {key}")
                    print(f"      recorded: {recorded[key]!r}")
                    print(f"      here:     {current[key]!r}")
                else:
                    print(f"  {key}")

    if not (missing or added or differing):
        print("\nThis environment's stock configuration matches the record.")
        return 0

    print(
        "\nThis environment differs from the record. If the differences are "
        "keys a newer Matplotlib added or removed, the recorded configuration "
        "no longer covers this environment and figure bytes may move. If they "
        "are values, this host modifies Matplotlib's defaults -- which is "
        "exactly what viz.figure_style neutralises, so the figures are still "
        "reproducible; the record is simply not re-recordable here."
    )
    print(
        f"\nNote: rcParams['font.family'] here is "
        f"{mpl.rcParamsDefault['font.family']!r}."
    )
    return 1


def write(force):
    """Regenerate the recorded configuration."""
    if RECORD_PATH.exists() and not force:
        print(
            f"{RECORD_PATH} exists. The committed figures were drawn under it, "
            "so rewriting it invalidates them: regenerate every figure and "
            "re-run the clean room afterwards. Pass --force if that is "
            "intended.",
            file=sys.stderr,
        )
        return 2
    version, current = current_configuration()
    RECORD_PATH.write_text(
        json.dumps(
            {
                "matplotlib_version": version,
                "rendering_stack": rendering_stack(),
                "rcparams": current,
            },
            indent=1, sort_keys=False,
        )
        + "\n"
    )
    print(f"wrote {RECORD_PATH} from Matplotlib {version} "
          f"({len(current)} keys)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="compare this environment with the record")
    group.add_argument("--write", action="store_true",
                       help="regenerate the record (needs --force to replace)")
    parser.add_argument("--force", action="store_true",
                        help="allow --write to replace an existing record")
    args = parser.parse_args(argv)
    return check() if args.check else write(args.force)


if __name__ == "__main__":
    sys.exit(main())
