# Changelog

All notable changes to H2STAR are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Validation gates are recorded with their verdicts, including the ones that
failed. A pre-registered FAIL is a result, and a changelog that listed only
passes would misrepresent the project.

## [Unreleased]

## [0.2.0] — 2026-10-08

The release that completes the model: the inverse engine, the uncertainty and
sensitivity layers, and the carbon-nanotube case study. Gate V4 closed, two
claims revised against evidence, and three findings recorded that the plan did
not anticipate.

### Added

- **Operating-envelope layer** (`envelope.py`). Maximizes system gravimetric
  capacity over full-state pressure and temperature and the discharge
  temperature, with the delivery pressure fixed at the fuel-cell floor, so
  materials are compared at their best achievable operating point rather than
  at an arbitrary one. `forward_map` sweeps the full state for figure F5.
- **Inverse acceptability-map engine** (`inverse.py`). Sweeps two material
  parameters on a grid and marks where a system meets both DOE targets. Every
  node is a real system evaluation — no surrogate, no interpolation — which is
  what makes `spot_check` an audit rather than a tautology.
- **Monte Carlo uncertainty propagation** (`uq.py`), seeded from the fixed-p₀
  conditional covariance of the Gate V2 refit, with rejection sampling against
  the physical domain and the half-sample convergence criterion.
- **Sobol global sensitivity analysis** (`sensitivity.py`) at two operating
  envelopes, with the Ishigami closed form derived in the module rather than
  quoted.
- **Carbon-nanotube corpus** (`data/materials/cnt_literature.yaml`): seven
  papers read as primary sources, each number carrying the verbatim sentence
  and page it came from. Drawn from the HyCAN-DB corpus, which is the interlock
  this project was designed around.
- **Pore-volume coherence constraint** (`coherent_n_max_limit`,
  `coherent_rho_bulk_limit`): the adsorbed phase must fit the volume the
  packing leaves. Implemented as testable code rather than a remark, and later
  used as a consistency screen on reported CNT uptakes.
- **Declared input uncertainty** (`data/uncertainty.yaml`), every entry labelled
  `SOURCED` or `MODELING ASSUMPTION`, with three parameters excluded and the
  reasons recorded.
- **Figures F5–F8** and notebooks 05–08.
- **`scripts/make_all_figures.py`**: all eight figures from the committed data
  in one command, with `--quick` for a smoke test that announces itself in the
  figure title so it cannot be mistaken for the published one.
- **`docs/known_limitations.md`**: the Gate V3 bias, the non-identifiability,
  and the inference chain behind the CNT study, each with its magnitude.
- **Provenance test suite** (`tests/test_data_provenance.py`, `provenance`
  marker): every data file parses, attributes its numbers, declares its units,
  and — for `engineering.yaml` — parses as numbers rather than strings, which is
  the PyYAML scientific-notation trap.

### Changed

- **Claim C1 rewritten.** v1.0 phrased it "NIST- and HSECoE-validated". The
  repository does not support "HSECoE-validated" and will not: Gate V3 is a
  documented FAIL. C1 now claims the EOS validation and states that the
  system-layer discrepancy is measured, localized and documented.
- **Claim C4 rewritten from absolute to relative.** The planned form — a system
  capacity "a quantified factor below target" — is not defensible from a model
  that places AX-21 activated carbon *above* the DOE 2025 gravimetric target.
  C4 now reads: the best-provenanced reported CNT uptake implies a system
  gravimetric capacity **0.88× that of AX-21**, and no entry passing the
  consistency screen exceeds AX-21. A ratio cancels a bias in the shared
  denominator; a shortfall-against-target does not.
- **Claim C5 quantified**, by a metric fixed before the map was computed:
  material-parameter uncertainty alone blurs the feasibility boundary over
  **32.1 mol/kg in limiting uptake, a quarter of the requirement**, and that is
  a lower bound.
- **CI matrix extended** to `ubuntu-latest` and `macos-latest` on Python 3.11
  and 3.12. Four journal entries had claimed platform coverage the workflow
  never had; they are corrected in place with a dated note.
- **Execution model.** The Class-A human-authorship division that governed
  Weeks 1–3 is retired; `docs/ai_usage_log.md` records the transition with its
  date and what changed. Git authorship is unchanged: Avin Gupta is the sole
  author.
- CI actions bumped off deprecated Node 20 (`checkout` v4→v7,
  `setup-python` v5→v7).

### Fixed

- **Every committed figure was reproducible on one machine only.** Matplotlib
  takes `font.family` and `text.hinting` from whichever configuration the host
  supplies, and the development container injects
  `font.family = Inter, sans-serif, DejaVu Sans` and
  `text.hinting = no_hinting` into `rcParamsDefault` itself — values no
  dependency here declares. Every label was drawn in a font no other machine
  has, moving every tight bounding box and so every pixel, while leaving every
  plotted number correct. The Stage 6 clean room found all nine headline
  numbers reproducing to the last digit and all nine PNGs differing; forcing
  those two values in the clean-room environment reproduced the committed bytes
  exactly, which is what identified the cause. `viz.FIGURE_RCPARAMS` now pins
  the rendering configuration to Matplotlib's stock defaults, naming the
  wheel-bundled DejaVu Sans rather than reaching it through the `sans-serif`
  alias, and `tests/test_viz_style.py` asserts every public plotting function
  carries the pin. The reproducibility claim in `README.md` and
  `docs/known_limitations.md` had rested on repeat runs inside a single
  environment, which cannot detect output that depends on the environment; it
  is corrected to what a cross-environment comparison actually shows.
- **Executing notebook 02 replaced the published F2 with a different figure.**
  Every notebook wrote its figure into `figures/`, which was harmless for six of
  them and wrong for two. Notebook 02 saved `F2_ax21_isotherm.png` built from
  the *unconstrained* refit — whose parameters the uncertainty layer
  deliberately does not use, as `make_all_figures.py`'s own docstring states —
  and notebook 01 saved an F1 with its isotherms in a different order. The
  figure script is now the sole writer of `figures/`; notebooks show their
  figures inline. `tests/test_notebook_hygiene.py` enforces it.
- **Notebook 02 could not execute off one machine.** It asserted that the
  working directory ended in `/research/h2star`. Notebook 03 asserted the
  directory was *named* `h2star`, so it failed from any clone with another
  name, and its committed output had an absolute container path printed into
  it. All eight notebooks now resolve paths from the repository root with the
  same fallback and run from the root or from `notebooks/`.
- **Notebook 07 had never been executed.** It was committed with zero outputs
  while every other notebook carried its results, and nothing checked. It now
  runs — 393 s, the probability maps being the cost — and a test asserts that
  every notebook is committed with outputs.
- **F1's legend was ordered by filename, not temperature.** The isotherms were
  loaded with `sorted(glob(...))`, which orders `100, 160, 298, 77` as strings,
  so the published figure's legend ran out of temperature sequence and the
  scatter overlay order was a property of how the files were named.
- **`data/targets/doe_targets.yaml` never parsed as YAML.** Committed on Day 1
  with `source:` at column 0 and `targets:` indented three spaces, which PyYAML
  rejects. It went unnoticed for four months because nothing had ever loaded
  it — the DOE targets were read off the screen and retyped into prose. Only
  whitespace changed; the parsed values are identical to the Day 1 commit.
- **Sobol confidence intervals were not reproducible.** SALib's `seed` reaches
  the point estimates but not the bootstrap behind `S1_conf` and `ST_conf`: two
  identical calls returned `ST_conf` values of 0.108 and 0.078, a 38% swing in a
  published error bar. The point estimates were always deterministic, so F7's
  bars were stable and only its whiskers moved.
- **Unvalidated material parameter values.** `SWEEPABLE_PARAMETERS` validated
  parameter *names* but nothing validated *values*, so a grid node at negative
  limiting uptake and negative packing density inverted the sign of the sorbent
  mass and returned a gravimetric capacity of 0.99 kg/kg — which the
  feasibility mask marked as clearing every DOE target.
- **`constants.bar_to_pa` and `pa_to_bar` raised `NotImplementedError`** while
  `constants.py` was the designated single source of truth for units; every
  conversion in the package was an inline literal.
- **Test modules imported `tests.conftest`**, which resolves under
  `python -m pytest` but not under the bare `pytest` that CI runs. All four
  matrix jobs went red. The convention of always invoking `python3 -m` was
  itself what hid it.
- Eighteen unfilled template placeholders in committed documentation, including
  three inside the canonical pre-registration record and a commit hash
  (`a1b2c3d`) that is not a valid object in this repository.

### Validation

- **Gate V1 (EOS) — PASS.** Maximum relative density error 4.992e-5 against
  the NIST reference tables, pre-registered floor <0.1%.
- **Gate V2 (isotherm) — CLOSED.** Part 1 (curve) PASS at 1.109 mol/kg against
  a 1.5 mol/kg threshold. Part 2 (parameter recovery) **FAIL by design**: the
  single-isotherm likelihood is a ridge and the parameter vector is not
  identifiable. Part 3 (isosteric heat) PASS, 4.24–5.33 kJ/mol inside the
  4–7 kJ/mol carbon band, matching the analytic D–A limit to ~1e-15.
- **Gate V3 (system) — documented FAIL**, localized to the engineering-mass
  block, which is light by a factor of about 4.2 against the HSECoE AX-21
  anchor. Recorded as a strict xfail so a future upgrade cannot turn it into an
  unexamined pass. Not chased to a PASS.
- **Gate V4 (UQ and sensitivity) — PASS on all clauses.** Analytic
  linear-Gaussian propagation within every pre-registered bound; Ishigami
  indices within 0.0008% at 2¹⁸ with error falling monotonically across the
  pre-registered 2¹⁴→2¹⁶→2¹⁸ ladder; half-sample convergence at 1.1% against a
  2% tolerance.

### Findings not anticipated by the plan

- **The requirement sits at the edge of physical coherence.** The adsorbed phase
  grows with limiting uptake by two independent accounts, and must fit the pore
  volume the packing leaves. That caps uptake at 104.9 mol/kg (fit correlation)
  or 124.1 (A-ISO-4) — both at or below the 125.6 mol/kg requirement the map
  identifies. The requirement needs uptake *and* pore volume together.
- **The consistency screen rejects exactly the two contested CNT values.** Liu
  1999's 4.2 wt% implies 163 mol/kg, beyond both pore-volume limits; Wang Qikun
  2002's 8.0 wt% is reproduced by no limiting uptake at all. Neither rejection
  uses the experimental evidence raised against those values at the time, and
  the four entries the screen accepts are the four with reversible isotherms and
  calibrated apparatus.
- **The CNT corpus does not record what a system model needs.** None of the
  seven papers states whether its uptake is excess or absolute; one reports a
  bulk density; reported uptake spans a factor of 160 on nominally the same
  material class. That is claim C5's argument reached from the literature side,
  independently of the fit covariance.

## [0.1.0] — 2026-08-26

Initial release: the validated forward model.

### Added

- Real-gas hydrogen thermodynamics via CoolProp, NIST-validated (Gate V1).
- Modified Dubinin–Astakhov isotherm with the excess/absolute conversion,
  isosteric heat by Clausius–Clapeyron, and least-squares fitting with Jacobian
  covariance (Gate V2).
- Tank inventory with the dual-bookkeeping invariant, pressure-vessel sizing by
  hoop stress with a performance-factor cross-check, and the system mass and
  volume budget with MLI heat-leak insulation sizing.
- Figures F1–F4 and notebooks 01–04.
- Pre-registered validation plan, progress journal, and AI usage log.

### Validation

- Gate V1 PASS; Gate V2 CLOSED (part 2 a documented FAIL by design); Gate V3 a
  documented FAIL localized to the engineering-mass block.

[Unreleased]: https://github.com/AvinGupta-ship-it/h2star/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/AvinGupta-ship-it/h2star/compare/v0.1...v0.2.0
[0.1.0]: https://github.com/AvinGupta-ship-it/h2star/releases/tag/v0.1
