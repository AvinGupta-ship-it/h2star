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


def _strip_ipython_syntax(source):
    """Blank out line magics and shell escapes, keeping the rest parseable.

    An earlier version skipped the whole cell whenever any line began with
    ``%`` or ``!``. Five of the eight notebooks carry ``%matplotlib inline`` in
    their first cell, so the function-definition check was blind to exactly the
    cell where a helper would most naturally be added -- an adversarial review
    demonstrated a model function hiding there with the suite green. Replacing
    the magic with a blank line keeps the cell's real code under test and
    preserves line numbers.
    """
    return "\n".join(
        "" if line.lstrip().startswith(("!", "%", "?")) else line
        for line in source.splitlines()
    )


def _parsed_cells(path):
    """Every code cell of a notebook, parsed to AST.

    A cell that will not parse is a failure, not something to skip: swallowing
    ``SyntaxError`` would hide a function definition just as effectively as
    skipping a magic cell did.
    """
    trees = []
    for index, src in enumerate(_code_cells(path)):
        cleaned = _strip_ipython_syntax(src)
        try:
            trees.append(ast.parse(cleaned))
        except SyntaxError as exc:
            raise AssertionError(
                f"{path.name} code cell {index} does not parse as Python "
                f"({exc}), so it cannot be checked"
            ) from exc
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


#: Ways a notebook could write an image file. ``savefig`` and ``savepath`` were
#: the only two checked at first; an adversarial review wrote a published
#: figure straight out with ``fig.canvas.print_png(...)`` and the whole hygiene
#: suite stayed green.
FIGURE_WRITE_CALLS = (
    "savefig", "savepath", "print_png", "print_figure", "print_raw",
    "print_rgba", "imsave", "write_png", "to_png", "buffer_rgba",
)


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_does_not_write_into_figures(path):
    """`scripts/make_all_figures.py` is the only writer of `figures/`.

    Two independent checks, because either alone has a hole. Naming any
    image-writing call is caught wherever it writes; and naming the published
    directory at all is caught however it is written to. A notebook has no
    business referring to ``figures/`` in executable code now that it publishes
    nothing there.
    """
    writes, references = [], []
    for src in _code_cells(path):
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if any(call in stripped for call in FIGURE_WRITE_CALLS):
                writes.append(stripped)
            if "figures" in stripped:
                references.append(stripped)

    assert not writes, (
        f"{path.name} writes an image file:\n  " + "\n  ".join(writes)
        + "\nShow the figure inline instead; make_all_figures.py publishes it."
    )
    assert not references, (
        f"{path.name} refers to the published figure directory in executable "
        f"code:\n  " + "\n  ".join(references)
        + "\nOnly scripts/make_all_figures.py may touch figures/."
    )


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_figures_are_displayed(path):
    """A figure a notebook builds must be shown, not computed and discarded.

    Since the notebooks stopped writing into ``figures/``, the inline output is
    the only record of what they drew, so a figure that is assigned and never
    displayed is work thrown away. Notebook 02 had exactly that: the
    published-versus-refit comparison, which is the visual evidence for the
    project's central non-identifiability finding, was built in a cell with no
    output at all. Its sibling cell displayed only because the inline backend
    happens to flush the first figure of a session, which is not something to
    rely on.

    The rule is syntactic and therefore checkable: a cell that binds ``fig``
    ends with a bare ``fig``.
    """
    offenders = []
    for index, src in enumerate(_code_cells(path)):
        builds = "fig = " in src or "fig, " in src
        if not builds:
            continue
        lines = [line for line in src.rstrip().splitlines() if line.strip()]
        if lines and lines[-1].strip() != "fig":
            offenders.append(index)
    assert not offenders, (
        f"{path.name} code cells {offenders} build a figure without "
        "displaying it; end the cell with a bare `fig` so the inline output "
        "records what was drawn"
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
def test_notebook_is_committed_fully_executed(path):
    """An unexecuted or half-executed notebook must not pass for a run one.

    Notebook 07 was committed with zero outputs. The first version of this test
    asserted only that *some* cell had outputs, and an adversarial review
    showed that a notebook which died after its second cell satisfied it, as
    did one whose outputs were present with every execution count cleared --
    outputs pasted in rather than produced.

    So the check is on the execution counts, which are the kernel's own record
    of what it ran: every code cell must carry one, they must increase
    monotonically through the notebook, and no cell may have an error output.
    """
    nb = json.loads(path.read_text())
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert code_cells, f"{path.name} has no code cells"

    missing = [
        index for index, cell in enumerate(code_cells)
        if cell.get("execution_count") is None
    ]
    assert not missing, (
        f"{path.name} code cells {missing} carry no execution count, so the "
        "notebook was committed unexecuted or only partly executed"
    )

    counts = [cell["execution_count"] for cell in code_cells]
    out_of_order = [
        (counts[i], counts[i + 1])
        for i in range(len(counts) - 1)
        if counts[i + 1] <= counts[i]
    ]
    assert not out_of_order, (
        f"{path.name} execution counts do not increase through the notebook "
        f"({out_of_order}); the committed outputs are not from one run in "
        "order"
    )

    errored = [
        index for index, cell in enumerate(code_cells)
        if any(
            output.get("output_type") == "error"
            for output in cell.get("outputs", [])
        )
    ]
    assert not errored, (
        f"{path.name} code cells {errored} have an error output, so the "
        "committed notebook records a failed run"
    )
