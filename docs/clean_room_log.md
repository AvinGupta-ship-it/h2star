# Clean-room reproduction log

Manual Part VII requires a full clean-room reproduction before release: a fresh
clone into a new directory, the documented install and nothing else, the full
suite, every figure regenerated, every notebook re-executed, and the headline
numbers reproduced from the artifact rather than read from a record.

The point of running it from a fresh clone rather than the working tree is that
some defects are properties of the development machine and are invisible to any
check performed on that machine. This log records three runs, because the first
one found exactly such a defect and the project's reproducibility claim had
been written without it.

Each run is dated, names the commit it ran against, and states what passed and
what did not.

---

## Run 1 — commit `4c371dd`, 2026-10-08. **FAILED on figures.**

### Environment

| | Clean room | Development environment |
|---|---|---|
| Python | 3.11.17 | 3.13 |
| Matplotlib | 3.11.2 | 3.11.2 |
| FreeType | 2.14.3 | 2.14.3 |

Fresh clone into a new directory, fresh `venv`, `pip install -e ".[dev]"` and
nothing further.

### What passed

- Full suite under bare `pytest`, the invocation CI uses: **255 passed, 1
  xfailed**. `ruff check .` clean.
- Validation subset 22 passed + 1 xfailed; provenance subset 29 passed.
- All eight figures regenerated from `scripts/make_all_figures.py` in one
  command.
- **Every headline number reproduced exactly**: Gate V1's maximum relative
  density error `4.99166e-05`; Gate V3's `GC_full 0.077671` and `VC_full
  0.036308`; Gate V4.2's worst relative error `0.1885%` at 2^14; the AX-21
  baseline system gravimetric capacity `0.065215`; the pore-volume coherence
  limits `104.9` and `124.1` mol/kg; `liu2010`'s inferred `n_max 53.527`; and
  its ratio to AX-21, `0.8756`.

### What failed

Byte comparison of the regenerated figures against the committed ones:
**nine of nine PNGs differed.** Four also differed in pixel dimensions, which
is the signature of `bbox_inches="tight"` resolving different text extents.

### Diagnosis

Not numerical. Matplotlib reads `font.family` and `text.hinting` from whatever
configuration the host environment supplies, and the development container
injects

```
font.family: Inter, sans-serif, DejaVu Sans
text.hinting: no_hinting
```

into `rcParamsDefault` itself, so even a fresh install inside that container
inherits them. Neither value is declared by any dependency this repository
names. Every label was therefore drawn in a font no other machine has, which
moved every tight bounding box and so every pixel, while leaving every plotted
number untouched.

The decisive test: forcing those two values in the clean-room environment and
regenerating reproduced the committed bytes **exactly** — F1 at 150 dpi and F3
at 300 dpi, SHA-256 identical. That is what established that the differences
were the host's font configuration and nothing else.

### What it cost the project's claims

`README.md` and `docs/known_limitations.md` claimed the figures were
byte-identical *on repeat runs on this platform*. That statement was true and
it was the wrong test: repeat runs inside one environment cannot detect output
that depends on the environment. The claim was corrected to what a
cross-environment comparison actually shows, and the defect is recorded in
`docs/known_limitations.md` rather than quietly fixed.

### Fix

`viz.FIGURE_RCPARAMS` pins the rendering configuration and every plotting
function applies it. The values are Matplotlib's own stock defaults, except
that `font.family` names `DejaVu Sans` outright instead of reaching it through
the `sans-serif` alias: DejaVu ships inside the Matplotlib wheel, so the pin
depends on no system font being installed. `tests/test_viz_style.py` asserts
that every public plotting function carries the pin.

---

## Run 2 — commit `dcd1760`, 2026-10-08. Figures passed; notebooks not yet run.

Same procedure, new directory, new `venv`.

| | Clean room | Development environment |
|---|---|---|
| Python | 3.11.17 | 3.13 |
| NumPy | 2.4.6 | 2.5.3 |
| SciPy | 1.17.1 | 1.18.1 |
| Matplotlib | 3.11.2 | 3.11.2 |
| FreeType | 2.14.3 | 2.14.3 |

- **262 passed, 1 xfailed** under bare `pytest`; `ruff` clean; validation 22 +
  1 xfail; provenance 29.
- **Nine of nine PNGs byte-identical**, by SHA-256, across two Python minor
  versions, two NumPy versions, two SciPy versions and two independent
  installs.

Attempting the notebook step then found that notebook 02 could not execute at
all — it asserted that the working directory ended in `/research/h2star`, a
path on one machine — and that notebook 07 had been committed with zero
outputs, having never been executed. Those and two further notebook defects
are recorded in `CHANGELOG.md`; `tests/test_notebook_hygiene.py` now holds the
notebooks to being narrative, and fails fourteen times against the notebooks
as they stood at this commit.

---

## Run 3 — commit `4d68c34`, 2026-10-08. **PASSED, complete.**

Fresh clone into a new directory, fresh `venv`,
`pip install -e ".[dev,nb]"`, nothing further.

| | Clean room | Development environment |
|---|---|---|
| Python | 3.11.17 | 3.13 |
| NumPy | 2.4.6 | 2.5.3 |
| SciPy | 1.17.1 | 1.18.1 |
| Matplotlib | 3.11.2 | 3.11.2 |
| FreeType | 2.14.3 | 2.14.3 |
| `rcParamsDefault['font.family']` | `['sans-serif']` (stock) | `['Inter', 'sans-serif', 'DejaVu Sans']` (injected) |

### Tests

| Command | Result |
|---|---|
| `pytest -q` (bare, the CI invocation) | 303 passed, 1 xfailed, 41.2 s |
| `ruff check .` | clean |
| `pytest -m validation` | 22 passed, 1 xfailed, 281 deselected |
| `pytest -m provenance` | 29 passed, 275 deselected |

The one xfail is Gate V3, which is a documented FAIL and is strict: if a change
closes the gap, it XPASSes and fails the suite, forcing the gate to be
re-adjudicated rather than letting a changed model turn a recorded failure into
an unexamined pass.

### Figures

`python scripts/make_all_figures.py` — 649.5 s total, F6 accounting for
610.6 s and F7 for 32.7 s.

**Nine of nine PNGs byte-identical to the committed figures**, by SHA-256:

| Figure | SHA-256 (first 16) |
|---|---|
| F1_eos_parity | `58205006b1fd4058` |
| F2_ax21_isotherm | `7123ba8a7e9e87ed` |
| F3_isosteric_heat | `aab2016fdc7a449d` |
| F4_system_validation | `340f133bfe906d98` |
| F5_forward_maps | `7cea73e5a475a0c0` |
| F6_acceptability_probability | `5eceef32c430a8b3` |
| F7_sobol_gc | `110962ccf7d8c8b8` |
| F7_sobol_vc | `7b47635383195dfa` |
| F8_cnt_gap | `efc123f1a47daba0` |

### Notebooks

`python scripts/run_notebooks.py --check` — all eight executed with no errors.

| Notebook | Time | Outputs |
|---|---|---|
| 01_eos_validation | 6.9 s | 3 |
| 02_isotherm_fit_ax21 | 7.0 s | 6 |
| 03_isosteric_heat | 7.2 s | 2 |
| 04_system_validation_hsecoe | 7.6 s | 5 |
| 05_forward_maps | 23.4 s | 6 |
| 06_acceptability_maps | 25.2 s | 7 |
| 07_sensitivity_uq | 364.5 s | 19 |
| 08_cnt_case_study | 7.0 s | 9 |

### Working tree afterwards

`git status` clean. The figure script *does* write all nine PNGs on every
run -- the tree was clean because the bytes it wrote were identical, which is
the result, not because nothing was written. The notebooks write nothing, and
`run_notebooks.py --check` does not write them back either. `--quick` writes
into `figures/quick/` so a smoke test cannot leave a coarsened image under a
published name.

### Headline numbers

Reproduced by the validation-marked tests, which read their tolerances and
anchors from the YAML at runtime rather than carrying them as literals, and
which pass in this environment. The gate values themselves are recorded at gate
precision in `docs/validation_plan.md`; the higher-precision readouts listed
under Run 1 reproduced exactly there and the numbers have not changed since.

---

## What the three runs together establish

- The numbers are deterministic under a fixed seed and reproduce across two
  Python minor versions, two NumPy versions, two SciPy versions and three
  independent installs.
- The figures are byte-identical given the same Matplotlib, FreeType and
  Pillow. They are **not** claimed to be byte-identical across those versions:
  FreeType rasterises glyphs differently between releases, Matplotlib stamps
  its own version into the PNG's `Software` chunk, and Pillow encodes the file.
  Text is not the whole of the difference either -- `path.simplify`,
  `lines.antialiased` and the background colours move non-text pixels. A
  version change moves the bytes and not the numbers.
- Every notebook runs from a fresh clone in a directory of any name, and is
  committed with its outputs.
- Three defects reached this stage invisible to every check that ran on the
  development machine: figures that only reproduced in one container, a
  notebook that could only execute in one directory, and a notebook that had
  never been executed. Each is now covered by a test, because a clean room run
  once before release catches what it catches, and a test catches it every time.
