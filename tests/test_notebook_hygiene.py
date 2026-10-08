"""The notebooks are narrative. These tests hold them to that.

Three rules, each of which a committed notebook has broken at least once:

1. **No physics.** Every model function lives in the package, so a notebook and
   the figure script call the same code rather than two implementations that
   happen to agree. A helper defined in notebook 08 was moved into
   ``inverse.material_from_corpus_entry`` for this reason.

2. **No writing into ``figures/``.** ``scripts/make_all_figures.py`` is the sole
   writer of the published figures. Notebook 02 used to save its own figure to
   ``figures/F2_ax21_isotherm.png``, built from the *unconstrained* refit --
   whose parameters the uncertainty layer deliberately does not use, as the
   script's own docstring says -- so executing that notebook silently replaced
   the published F2 with a different scientific object. Notebooks show their
   figures inline instead; the inline output is the record.

3. **Runnable from a fresh clone, and actually run.** Notebook 02 asserted that
   the working directory ended in ``/research/h2star``, a path on one machine,
   so it could not execute anywhere else. Notebook 07 was committed with no
   outputs at all -- it had never been executed, and nothing noticed, because
   nothing checked.
"""

import ast
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "notebooks"

NOTEBOOKS = sorted(NOTEBOOK_DIR.glob("*.ipynb"))

#: The eight notebooks mirror the eight figures. A missing one is a defect, so
#: the count is asserted rather than discovered.
EXPECTED_NOTEBOOK_COUNT = 8


def _code_cells(path):
    """The source of every code cell in a notebook, in order."""
    nb = json.loads(path.read_text())
    return [
        "".join(cell["source"])
        for cell in nb["cells"]
        if cell["cell_type"] == "code"
    ]


def _parsed_cells(path):
    """Code cells parsed to AST, skipping any cell that uses IPython syntax."""
    trees = []
    for src in _code_cells(path):
        if any(
            line.lstrip().startswith(("!", "%"))
            for line in src.splitlines()
        ):
            continue
        try:
            trees.append(ast.parse(src))
        except SyntaxError:
            continue
    return trees


def test_the_expected_notebooks_are_present():
    assert len(NOTEBOOKS) == EXPECTED_NOTEBOOK_COUNT, (
        f"expected {EXPECTED_NOTEBOOK_COUNT} notebooks, found "
        f"{[p.name for p in NOTEBOOKS]}"
    )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_defines_no_functions_or_classes(path):
    """All physics lives in the package, not in a notebook cell."""
    offenders = []
    for tree in _parsed_cells(path):
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                offenders.append(node.name)
    assert not offenders, (
        f"{path.name} defines {offenders}; move it into the package so the "
        "notebook and scripts/make_all_figures.py call the same code"
    )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_does_not_write_into_figures(path):
    """`scripts/make_all_figures.py` is the only writer of `figures/`."""
    offenders = []
    for src in _code_cells(path):
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "savefig" in stripped or "savepath" in stripped:
                offenders.append(stripped)
    assert not offenders, (
        f"{path.name} writes a figure file:\n  "
        + "\n  ".join(offenders)
        + "\nShow the figure inline instead; make_all_figures.py publishes it."
    )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_has_no_machine_specific_path(path):
    """A path from one person's disk makes the notebook unrunnable elsewhere."""
    text = path.read_text()
    offenders = [
        marker
        for marker in ("/research/", "/Users/", "/home/", "C:\\\\", "/mnt/")
        if marker in text
    ]
    assert not offenders, (
        f"{path.name} contains an absolute machine path ({offenders}); resolve "
        "paths from REPO_ROOT instead"
    )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_resolves_paths_from_the_repository_root(path):
    """Every notebook must run from the repo root or from `notebooks/`.

    The committed pattern derives a root and falls back one level up, so the
    notebook works under both, rather than assuming a working directory.
    """
    code = "\n".join(_code_cells(path))
    if "data" not in code and "REPO_ROOT" not in code:
        pytest.skip("notebook reads no repository files")
    assert 'Path("..").resolve()' in code, (
        f"{path.name} does not carry the repository-root fallback, so it "
        "depends on the working directory it happens to be run from"
    )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_is_committed_with_outputs(path):
    """An unexecuted notebook must not pass for an executed one.

    Notebook 07 was committed with zero outputs. The notebooks are part of the
    record, and a notebook with no outputs is a claim that was never run.
    """
    nb = json.loads(path.read_text())
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    with_output = [c for c in code_cells if c.get("outputs")]
    assert with_output, (
        f"{path.name} has {len(code_cells)} code cells and no outputs at all; "
        "it was committed unexecuted"
    )
