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

## Run 3 — commit `4d68c34`, 2026-10-08. Suite, figures and notebooks passed.

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

**Not properly done in this run.** This section originally said the
validation-marked tests pass and deferred the high-precision values to Run 1 —
a different commit in a different environment. That is reading from a record,
which is the one thing Part VII's wording rules out. An adversarial review also
established that no published number was asserted anywhere in the repository,
so nothing could have caught a drift. `scripts/report_headline_numbers.py` and
`tests/test_headline_numbers.py` were written in response, and Run 4 does this
step properly.

---

---

## Run 4 — commit `756a94c`, 2026-10-08. **PASSED, complete.**

The run after the adversarial review. Fresh clone into a new directory, fresh
`venv`, `pip install -e ".[dev,nb]"`, nothing further.

| | Clean room | Development environment |
|---|---|---|
| Python | 3.11.17 | 3.13 |
| NumPy | 2.4.6 | 2.5.3 |
| SciPy | 1.17.1 | 1.18.1 |
| Matplotlib | 3.11.2 | 3.11.2 |
| FreeType | 2.14.3 | 2.14.3 |
| Pillow | 12.3.0 | 12.3.0 |
| `rcParamsDefault['font.family']` | `['sans-serif']` (stock) | `['Inter', 'sans-serif', 'DejaVu Sans']` (injected) |

### Tests

| Command | Result |
|---|---|
| `pytest -q` (bare, the CI invocation) | 394 passed, 1 xfailed, 51.9 s |
| `ruff check .` | clean |
| `pytest -m validation` | 22 passed, 1 xfailed, 372 deselected |
| `pytest -m provenance` | 29 passed, 366 deselected |
| `scripts/record_figure_style.py --check` | "This environment's stock configuration matches the record" |

That last line is worth stating plainly: the rendering configuration the
figures are drawn under was recorded from a pristine Matplotlib, and this
environment's stock configuration agrees with it key for key, 324 of 324.

### Headline numbers

`scripts/report_headline_numbers.py --full`, which recomputes each value by
calling the package rather than reading it from anywhere. Every one matches
what `docs/validation_plan.md` and `README.md` publish.

| Quantity | Recomputed |
|---|---|
| Gate V1 max relative density error | 4.991664e-05 |
| Gate V3 `GC_full` | 0.077671 kg/kg (anchor 0.0312 — documented FAIL) |
| Gate V3 `VC_full` | 0.036308 kg/L (anchor 0.0194 — documented FAIL) |
| Gate V4.2 worst relative error at 2^14 | 0.1885 % |
| AX-21 baseline system GC | 0.065215 kg/kg |
| Coherence limit (fit correlation) | 104.9235 mol/kg |
| Coherence limit (A-ISO-4) | 124.1021 mol/kg |
| CNT primary inferred `n_max` | 53.5273 mol/kg |
| CNT primary system GC | 0.057103 kg/kg |
| Claim C4 ratio to AX-21 | 0.8756x |
| Claim C5 P = 0.05 crossing | 109.4167 mol/kg |
| Claim C5 P = 0.50 crossing | 125.5941 mol/kg |
| Claim C5 P = 0.95 crossing | 141.5196 mol/kg |
| Claim C5 separation | 32.1029 mol/kg (25.56% of the median) |

### Figures

`python scripts/make_all_figures.py` — F6 accounting for 452.4 s of the run.
**Nine of nine PNGs byte-identical** to the committed figures, by SHA-256, and
identical to the digests Run 3 recorded: the recorded configuration replaced
the seven-key pin without moving a single byte, because the settings it added
already matched stock on both hosts.

### Notebooks

`python scripts/run_notebooks.py --check` — all eight executed with no errors:
01 (4.7 s, 3 outputs), 02 (5.5 s, 8), 03 (4.8 s, 2), 04 (5.0 s, 5),
05 (16.7 s, 6), 06 (16.9 s, 7), 07 (331.4 s, 19), 08 (6.4 s, 9). Notebook 02
now carries 8 outputs rather than 6: it was building its published-versus-refit
comparison and discarding it.

### Working tree afterwards

`git status` clean.

### Afterwards

The only commits after this run change documentation and one help string, and
cannot affect a number or a byte.

---

## Run 5 — commit `9e414d0`, 2026-10-08. **PASSED, complete.**

The run after the cross-version fix. Same procedure: fresh clone into a new
directory, fresh `venv`, `pip install -e ".[dev,nb]"`, nothing further. Same
environment as Run 4 (Python 3.11.17, NumPy 2.4.6, SciPy 1.17.1, Matplotlib
3.11.2, FreeType 2.14.3, Pillow 12.3.0).

| Check | Result |
|---|---|
| `pytest -q` (bare, the CI invocation) | 397 passed, 1 xfailed |
| `ruff check .` | clean |
| `record_figure_style.py --check` | stock configuration matches the record, 324 of 324 |
| Figures | **nine of nine byte-identical**, unchanged from Runs 3 and 4 |
| Headline numbers (`--full`) | all reproduce, C5 crossings 109.4167 / 125.5941 / 141.5196, separation 32.1029 |
| Notebooks | all eight executed, no errors |
| Working tree afterwards | clean |

The point of this run was that the figure configuration is now *filtered* on
load to what the running Matplotlib accepts. On the recorded stack nothing is
filtered, so the bytes had to be unchanged — and they are, matching Run 3's and
Run 4's digests exactly.

What this run still does not cover is the case the fix was written for, since
it has the same Matplotlib as the record. That case is covered instead by two
pinned virtualenvs (Matplotlib 3.9.4 and 3.11.0, the latter being the version
the macOS CI job had) and by the new `oldest-supported-matplotlib` CI job.
Across those three stacks the suite gives 393 passed / 3 skipped, 394 / 3, and
397 / 0, the skips being exactly the byte comparisons on a stack that cannot
produce those bytes.

---

## Run 6 — commit `be9fbd1`, 2026-10-08. **PASSED, complete. Release candidate.**

Fresh clone into a new directory, fresh `venv`, `pip install -e ".[dev,nb]"`.
Same environment as Runs 4 and 5.

| Check | Result |
|---|---|
| `pytest -q` (bare, the CI invocation) | 397 passed, 1 xfailed |
| `ruff check .` | clean |
| `record_figure_style.py --check` | stock configuration matches the record, 324 of 324 |
| Figures | **nine of nine byte-identical**, unchanged from Runs 3, 4 and 5 |
| Headline numbers (`--full`) | all reproduce, C5 crossings 109.4167 / 125.5941 / 141.5196, separation 32.1029 |
| Notebooks | all eight executed, no errors |
| Working tree afterwards | clean |

And, for the first time, **all five CI jobs green**: Ubuntu 3.11 and 3.12,
macOS 3.11 and 3.12, and `oldest-supported-matplotlib` on Matplotlib 3.9.4.
That matters more than another clean-room pass, because the macOS jobs are the
only check in this project that runs on a different operating system, and they
are what established that byte-identity is platform-specific — something five
clean-room runs on one machine could not have shown.

## What a clean room cannot catch

Run 4 passed completely, and the very next CI run went red on both macOS jobs
with 65 failures. None of the four runs could have caught it, and the reason is
worth stating plainly rather than filed as bad luck.

Every clean-room run here is a fresh clone into a new directory with a fresh
virtual environment — but all four resolved their dependencies from the same
index on the same machine at the same time, so all four had Matplotlib 3.11.2.
macOS CI had 3.11.0 and Pillow 12.2.0, a different rendering stack, so the
regenerated figures legitimately differed from the committed ones and every
byte comparison failed. The test was asserting on every platform exactly what
`docs/known_limitations.md` says holds only within one stack.

**"Fresh environment" and "different environment" are not the same property.**
Four runs of the first gave no evidence for claims that needed the second.

Chasing the fix against a deliberately old Matplotlib then found something
worse than the failure that prompted it: of the 324 recorded settings, 3.9.4
rejects 26, and applying them unfiltered made *every plotting call in the
package* raise. The package was not merely unreproducible on another
Matplotlib, it was unusable there — and no clean-room run would ever have shown
that, because each one had the version the configuration was recorded from.

CI now carries an `oldest-supported-matplotlib` job pinned to 3.9.4, which is
the coverage the clean room structurally lacks.

---

## What the six runs together establish

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
- Every headline number, including claim C5's contour crossings, is recomputed
  from the artifact by one command and pinned by the test suite, so "the
  numbers reproduce" is a thing that fails rather than a thing a session
  checked once.
- Defects that reached this stage invisible to every check running on the
  development machine: figures that only reproduced in one container, a
  notebook that could only execute in one directory, a notebook that had never
  been executed, a figure computed and discarded, a smoke test that overwrote
  published figures, and a notebook runner that reported success for a failed
  run. Each is now covered by a test. A clean room run once before release
  catches what it catches; a test catches it every time.
- And the honest one: the first two fixes for the figure defect were each
  verified by evidence that could not have contradicted them. What found that
  was not another clean-room run but an adversarial reviewer with no access to
  the reasoning behind the fix. Runs are necessary; they are not sufficient
  against a blind spot shared by the diagnosis and its test.
