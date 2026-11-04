# H2STAR documentation index

Where to start, depending on what you want. This index describes the v1.0
claim surface; the superseded v0.2 record is kept, clearly labelled, at the
bottom.

## Read these first

| Document | What it is |
|---|---|
| [`known_limitations.md`](known_limitations.md) | **Start here if you are deciding whether to trust a number from this project.** Every limitation with its magnitude, and what each one forbids the model from claiming. Section 1 (the held-out gate FAILED, and what that fork rule forbids) matters most. |
| [`preregistration_v1.0.md`](preregistration_v1.0.md) | The externally deposited frozen plan (Zenodo 10.5281/zenodo.23931242): gate targets, tolerances, fork rule, analysis plans, amendment A1. |
| [`validation_plan.md`](validation_plan.md) | The canonical gate record: E1 calibration, the once-run held-out Gate E2 (**FAIL**, fork rule in force), the D6 CNT-drop adjudication, the post-adjudication S8 correction record, and the superseded v0.2 gates V1–V4. |

## The v1.0 claims (README "Findings" carries the full statements)

1. Single-isotherm practical non-identifiability of the modified D–A
   parameters (bound-conditional, as stated), repaired by multi-temperature
   fitting *within the m = 2 model* — the model-form/fit-set spread is
   carried alongside.
2. Loose parameters, tight predictions: system capacity varies by a few per
   cent across the single-isotherm ridge.
3. Requirements belong in observable axes (deliverable excess uptake,
   packing density), drawn under two structurally different engineering
   models that share several source anchors.
4. Engineering inputs, not material-parameter uncertainty, dominate
   predicted-capacity variance (Shapley effects).
5. The pre-registered held-out engineering gate FAILED at 200 bar; no
   absolute system capacity is claimed anywhere in this project.

## The scientific record

| Document | What it is |
|---|---|
| [`model_derivations.md`](model_derivations.md) | Every governing equation with its derivation or citation. |
| [`assumptions.md`](assumptions.md) | Each physical assumption with one sentence of justification and one on what changes if it is relaxed. |
| [`references.md`](references.md) | Sources, with DOIs and access dates. |

## Process and provenance

| Document | What it is |
|---|---|
| [`clean_room_log.md`](clean_room_log.md) | Clean-room reproductions, dated and against a named commit, including the two that failed (v0.2 era; the v1.0 entry is added at release). |
| [`history/progress_journal.md`](history/progress_journal.md) | Day-by-day v0.2 process narrative (moved out of the claim surface). |
| [`ai_usage_log.md`](ai_usage_log.md) | AI-use disclosure: tool, scope, responsibility, and where the contemporaneous records live. |

## Outside `docs/`

| Path | What it is |
|---|---|
| [`../CHANGELOG.md`](../CHANGELOG.md) | Release history, with gate verdicts and the claims that were revised against evidence. |
| [`../data/`](../data/) | Every input, each number carrying a citation. `uncertainty_v1.yaml` labels each declared range `SOURCED` or `MODELING ASSUMPTION`. |
| [`../data/validation/digitization/`](../data/validation/digitization/) | The dual-digitization inputs: both route CSVs, calibration notes, the shared source crop, and the re-inspection decisions file the published dataset regenerates from byte-for-byte. |
| [`../data/analysis/`](../data/analysis/) | Machine-readable S5/S6 records: identifiability, MCMC diagnostics, sensitivity, observable map, supplementary metrics, the BOP-anchor correction sensitivity. |
| [`../scripts/`](../scripts/) | One script per analysis record, plus `make_figures_v1.py` (all figures) and `reproduce_paper.py` (regenerates every manuscript number; `--check` compares). |
| [`../manuscript/`](../manuscript/) | The preprint source; every number is a machine-generated macro. |
| [`../requirements-lock.txt`](../requirements-lock.txt) | Archival environment lock. |

---

## Superseded v0.2 record (kept for history; NOT the live claim surface)

The v0.2 gates below and the claims C1–C5 were the claim surface of release
0.2.0. They were retired by the v1.0 rebuild under the pre-registered plan;
several are contradicted by the v1.0 record and are retained only so the
project's history is auditable. In particular: C2's "requirements map over
material-property space" is superseded by the observable-axis map (Finding
3); **C4's CNT ratio is WITHDRAWN in full** — the D6 adjudication drops the
CNT case study (fewer reconciled points than the pre-registered floor) and
no system-level CNT statement is made in any public artifact; C5's
covariance statement is superseded by the profile-likelihood analysis. The
v0.2 notebooks and figure scripts referenced by old entries were deleted in
the v1.0 supersession (commit `cff3a6a`); the only notebook now present is
`../notebooks/cnt_example.ipynb`.

| Gate (v0.2) | What it tested | Verdict |
|---|---|---|
| V1 | EOS wrapper against NIST hydrogen density | **PASS** — max error 4.992e-5 vs a <0.1% floor |
| V2 part 1 | Isotherm curve against digitized AX-21 | **PASS** — RMSE 1.109 vs 1.5 mol/kg |
| V2 part 2 | Parameter recovery from one isotherm | **FAIL (pre-registered recovery bands not met)** — the likelihood is a ridge; superseded by the v1.0 profile-likelihood analysis |
| V2 part 3 | Isosteric heat against the carbon band | **PASS** — 4.24–5.33 kJ/mol, analytic to ~1e-15 |
| V3 | System capacity against the HSECoE AX-21 anchor | **documented FAIL** — mass block ~4.2× light; superseded by the v1.0 component-resolved model and Gate E2 |
| V4 | UQ and sensitivity machinery | **PASS** on all clauses (the Ishigami primary text remained unread; disclosed) |

| Claim (v0.2, retired) | Status in v1.0 |
|---|---|
| C1 open, tested implementation with measured system-layer discrepancy | Superseded by the component-resolved model and the E1/E2 record |
| C2 requirements map over material-property space | Superseded by the observable-axis map (Finding 3) |
| C3 binding energetics matter more at ambient | Not re-adjudicated in v1.0; the ambient contrast survives only as a labelled SI metric |
| C4 CNT 0.88× AX-21 system ratio | **Withdrawn in full** (D6 adjudication) |
| C5 feasibility-boundary blur from parameter covariance | Superseded by the profile-likelihood and Shapley records |
