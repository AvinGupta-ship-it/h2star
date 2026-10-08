# H2STAR documentation index

Where to start, depending on what you want.

## Read these first

| Document | What it is |
|---|---|
| [`known_limitations.md`](known_limitations.md) | **Start here if you are deciding whether to trust a number from this project.** Every limitation with its magnitude, and what each one forbids the model from claiming. The first two entries matter most. |
| [`validation_plan.md`](validation_plan.md) | The canonical pre-registration and gate record. Tolerances were declared before each comparison ran, and the file's git history is the proof. Contains the Gate V1–V4 verdicts, including two documented FAILs. |

## The scientific record

| Document | What it is |
|---|---|
| [`model_derivations.md`](model_derivations.md) | Every governing equation with its derivation or citation. The methods section in embryo. |
| [`assumptions.md`](assumptions.md) | Each physical assumption with one sentence of justification and one on what changes if it is relaxed. |
| [`references.md`](references.md) | Sources, with DOIs and access dates. |

## Process and provenance

| Document | What it is |
|---|---|
| [`progress_journal.md`](progress_journal.md) | Day-by-day record: what advanced, what broke, what was learned. Includes dated correction notes where an earlier entry was wrong. |
| [`ai_usage_log.md`](ai_usage_log.md) | Honest AI-assistance disclosure, session by session, including the dated transition where the division of labour changed. |

## Outside `docs/`

| Path | What it is |
|---|---|
| [`../CHANGELOG.md`](../CHANGELOG.md) | Release history, with gate verdicts and the claims that were revised against evidence. |
| [`../data/`](../data/) | Every input, each number carrying a citation. `uncertainty.yaml` labels each declared range `SOURCED` or `MODELING ASSUMPTION`. |
| [`../notebooks/`](../notebooks/) | Eight executed notebooks, 01–08, mirroring figures F1–F8. Narrative and figure calls only; all physics lives in the package. |
| [`../scripts/make_all_figures.py`](../scripts/make_all_figures.py) | Regenerates all eight figures from the committed data in one command. |

## The validation gates at a glance

| Gate | What it tests | Verdict |
|---|---|---|
| V1 | EOS wrapper against NIST hydrogen density | **PASS** — max error 4.992e-5 vs a <0.1% floor |
| V2 part 1 | Isotherm curve against digitized AX-21 | **PASS** — RMSE 1.109 vs 1.5 mol/kg |
| V2 part 2 | Parameter recovery from one isotherm | **FAIL by design** — the likelihood is a ridge |
| V2 part 3 | Isosteric heat against the carbon band | **PASS** — 4.24–5.33 kJ/mol, analytic to ~1e-15 |
| V3 | System capacity against the HSECoE AX-21 anchor | **documented FAIL** — mass block ~4.2× light |
| V4 | UQ and sensitivity machinery | **PASS** on all clauses |

Two of those are failures, and both are results rather than defects. V2 part 2
establishes that the material parameters are not identifiable from the data the
literature publishes, which is the project's central methodological finding. V3
localizes a model limitation to a named block and quantifies it, which is what
makes every other number in the project interpretable.

## The claims, and what constrains them

| Claim | Statement | Constraint |
|---|---|---|
| C1 | An open, tested implementation of the sorbent system-model class, NIST-validated at the EOS layer, with its system-layer discrepancy measured and documented | Rewritten from v1.0's "HSECoE-validated", which Gate V3 does not support |
| C2 | A requirements map over material-property space with uncertainty-quantified boundaries | Absolute boundary position inherits the Gate V3 bias; shape and ordering do not |
| C3 | Binding energetics matter an order of magnitude more at ambient than at cryogenic conditions | Indices are of an independent-input surrogate |
| C4 | The best-provenanced CNT uptake implies 0.88× the system capacity of AX-21 activated carbon | Reported as a ratio, not a shortfall against the DOE target, because of the Gate V3 bias |
| C5 | Material-parameter uncertainty alone blurs the feasibility boundary over 32.1 mol/kg, a quarter of the requirement | A lower bound: the covariance is conditional on a fixed p₀ |
