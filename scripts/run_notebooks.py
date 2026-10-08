#!/usr/bin/env python3
"""Execute every notebook in place, from the repository root.

    python3 scripts/run_notebooks.py [--check] [--only 07] [...]

Stage 6 of the execution manual requires every notebook re-executed from a
fresh clone. This makes that one command rather than eight manual runs, and it
fails loudly: a notebook that raises is reported and the script exits non-zero,
because a notebook that half-executed but still looks committed is the exact
defect this exists to catch. Notebook 07 was once committed having never been
run at all.

``--check`` executes each notebook without writing it back, which is what to
use in a clean room: it answers "does this still run?" without producing a
diff. Without ``--check`` the notebooks are rewritten with their new outputs,
which is how they are committed.

The notebooks write nothing into ``figures/`` -- ``make_all_figures.py`` is the
sole writer -- so running this leaves the published figures untouched. That is
asserted by ``tests/test_notebook_hygiene.py`` and worth re-checking with
``git status`` afterwards.

Requires the ``nb`` extra: ``python3 -m pip install -e ".[dev,nb]"``.
"""

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "notebooks"

#: Notebook 07's probability maps dominate its runtime, so the per-notebook
#: ceiling is generous rather than tuned.
CELL_TIMEOUT_S = 3600


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="execute without writing the notebooks back",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="NN",
        help="run only notebooks whose name starts with this (repeatable)",
    )
    args = parser.parse_args(argv)

    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError as exc:
        print(
            f"{exc}\n\nThis script needs the notebook extra:\n"
            '    python3 -m pip install -e ".[dev,nb]"',
            file=sys.stderr,
        )
        return 2

    paths = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
    if args.only:
        prefixes = tuple(args.only)
        paths = [p for p in paths if p.name.startswith(prefixes)]
    if not paths:
        print(f"no notebooks matched in {NOTEBOOK_DIR}", file=sys.stderr)
        return 2

    failures = []
    started = time.perf_counter()
    for path in paths:
        print(f"{path.name:36s} ...", end=" ", flush=True)
        step = time.perf_counter()
        notebook = nbformat.read(path, as_version=4)
        # The kernel's working directory is the repository root, which is where
        # the notebooks resolve their data paths from.
        client = NotebookClient(
            notebook,
            timeout=CELL_TIMEOUT_S,
            kernel_name="python3",
            resources={"metadata": {"path": str(REPO_ROOT)}},
        )
        try:
            client.execute()
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            failures.append((path.name, exc))
            print(f"FAILED ({type(exc).__name__}: {exc})")
            continue
        if not args.check:
            nbformat.write(notebook, path)
        outputs = sum(
            len(cell.get("outputs", []))
            for cell in notebook.cells
            if cell.cell_type == "code"
        )
        print(f"ok ({time.perf_counter() - step:6.1f}s, {outputs} outputs)")

    elapsed = time.perf_counter() - started
    verb = "checked" if args.check else "written"
    print(f"\n{elapsed:.1f}s total, {len(paths) - len(failures)} {verb}")

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for name, exc in failures:
            print(f"  {name}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
