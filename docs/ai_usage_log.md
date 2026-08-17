# H2STAR — AI Usage Log

## 2026-06-30 — Day 2 concepts and excess/absolute derivation
Tool: Claude (chat)
Purpose: Learn the four §5.3 concepts; derive the excess/absolute relation; get journal templates.
What I provided: The H2STAR manual (§5.3, §5.4, §3.4C) and my Day-2 deliverable list.
What it produced: Concept explanations, a line-by-line walkthrough of the derivation,
  and journal/log templates with examples.
What I verified: I derived the excess/absolute relation myself on paper and confirmed it
  matches §3.4C; I cross-checked the key concept claims against NIST (hydrogen's 33 K
  critical temperature and the 77 K/100 bar real-gas density, the latter matching my Day-0
  CoolProp check) and the manual's §3.4D literature band for the 4–7 kJ/mol isosteric heat.
What I changed/owned: I wrote all four concept summaries and the derivation in my own words;
  no scientific content was taken verbatim from the AI.

## 2026-06-30 - EOS wrapper (Gate V1)
Tool: Claude Code (implementer session)
Purpose: Implement eos.py + test_eos.py + notebook 01 + viz parity fn from Prompt CC-2.
What I provided: The CC-2 spec plus the exact NIST-CSV format and directory constraints.
What it produced: src/h2star/eos.py, tests/test_eos.py, notebooks/01_eos_validation.ipynb,
  a parity function in src/h2star/viz.py, and a pytest marker registration in pyproject.toml.
What I verified: Read every line of eos.py and test_eos.py focusing on unit handling
  (bar->Pa conversion, P/T argument order, 'Hydrogen' species, 'D' vs 'Dmolar'); ran
  `ruff` and the validation tests myself; confirmed the NIST tables are normal hydrogen.
What I changed: none

## 2026-06-30 — Day 4: Gate V1 execution
Tool: Claude (chat, Opus) — planning/instruction only; no code-generation session.
Purpose: Convert Execution Manual §5.4/§3.8/§3.10 into an unambiguous Day 4 checklist (kernel setup, figure generation, verdict recording).
What I provided: The frozen H2STAR manual and my Day 1–3 repo state.
What it produced: Paste-ready terminal commands, a .vscode/settings.json fix, a throwaway max-relative-error script mirroring test_eos.py's logic, and templates for the validation_plan verdict, journal, and this log.
What I verified: Ran every command in my own h2star venv; confirmed pytest -m validation → 4 passed and the measured max error (0.031%) independently via the script; eye-checked F1 against the parity line; cross-checked the ideal-gas density anchor (31.49 kg/m³) by hand. The Gate V1 verdict, its tolerance, and all interpretive prose are mine.
What I changed: Wrote the validation_plan verdict, journal entry, and Day-0 correction in my own words; no AI text was pasted into any provenance file.

## 2026-07-01 — Day 5 (Week 1 review) planning
Tool: Claude (chat; Opus 4.8)
Purpose: Turn manual §5.4/§5.7 into a step-by-step Day-5 review checklist; rehearse §5.3 concepts
  (supercritical adsorption; excess vs. absolute) for the spoken self-check.
What I provided: The H2STAR manual, the Days 0–4 state, and my required instruction style.
What it produced: The Day-5 task sequence, the §5.7 QC status-table structure, concept rehearsal
  rubrics, and journal/log templates. No code; no scientific decisions.
What I verified: Ran every QC command myself and read each result; confirmed CI green on GitHub;
  authored the weekly review and this log in my own words; checked both concept explanations against
  §5.3 and §3.4C, not the chat's summary alone.
What I changed: none

## 2026-07-01 — Gate V2 part 1: RMSE metric, F2, gated excess-maximum
Tool: Claude Code (Session D7-implementer)
Purpose: Add a pure rmse() helper and its tests to isotherm.py; add the F2 plotting
  function to viz.py; promote the 77 K excess-maximum test to @pytest.mark.validation.
What I provided: Exact function signatures, the rmse body, the F2 panel spec, and the
  instruction to mark only the excess-maximum test — all from my Day 7 plan.
What it produced: rmse() + 3 tests; plot_ax21_isotherm(); the @pytest.mark.validation
  decorator on the excess-maximum test.
What I verified: Read the full diff; confirmed no edits to n_absolute/n_excess/pressure_at_loading,
  to the F1 function, or to any docs/ file; ran `python3 -m pytest -q` and
  `python3 -m pytest -m validation -v` myself — all green; confirmed the rmse hand value
  (1.15470 for [1,2,3] vs [1,2,5]).
What I changed: None

## 2026-07-02 — Isotherm refit implementation (Session D8)
Tool: Claude Code
Purpose: Implement fitting.py (least-squares refit of the modified D-A excess isotherm
with parameter covariance), extend plot_ax21_isotherm for the refit curve, and write
the fitting unit tests, against my specification.
What I provided: The full spec from the day plan — theta = (n_max, alpha, log10 p0,
v_a) with beta fixed at 18.9 (my identifiability decision, D1), bounds, x_scale,
covariance definition, fit_report layout, and the four tests. The recovery bands were
mine, pre-registered and committed before this session ran.
What it produced: src/h2star/fitting.py (fit_modified_da, FitResult, fit_report),
the plot_ax21_isotherm extension in viz.py, tests/test_fitting.py (4 tests).
What I verified: Read the full diff — s² = SSR/dof factor present, p0 reconstructed
via 10**log10_p0, beta absent from the fit vector, no validation marker on the tests,
no files touched in docs/, data/, or notebooks/. Ran ruff and the full pytest suite
myself (all green, +4 tests).
What I changed: Ratified CC's proposal to replace my prescribed cov = s²·pinv(JᵀJ)
with the SVD-of-J route after it showed the pinv form failed the noisy-recovery test
at 7σ. I verified the two are analytically identical ((JᵀJ)⁻¹ = V S⁻² Vᵀ), that
forming JᵀJ squares the condition number, and that scipy's curve_fit uses the same
SVD method, then required the 2σ test pass unmodified — it did.

## 2026-07-02 — Fixed-p0 identifiability diagnostic (Session D8b)
Tool: Claude Code
Purpose: Add a fix_p0 option to fit_modified_da for a post-hoc diagnostic, after the
real-data refit failed the pre-registered Gate V2 recovery bands at a corner solution
(log10 p0 pinned at the fit bound).
What I provided: The FAIL diagnosis (identifiability ridge, corner solution) and the
decision to run a fixed-p0 refit as a labeled post-hoc diagnostic, not a gate — both
mine. Exact spec: 3-parameter theta, sliced bounds/x_scale, dof = N−3, default path
byte-for-byte unchanged, one noise-free recovery test.
What it produced: fix_p0 keyword in fitting.py, dual-case fit_report, one new test.
What I verified: Diff showed only fitting.py and test_fitting.py touched; 3-parameter
dof branch present; ran the full suite myself (19 passed) and pytest -m validation
(5 passed). Ran the diagnostic in notebook 02 and interpreted the result myself
(n_max −5.3%, alpha +6.0%, v_a −0.5% of published, supporting the ridge explanation).
What I changed: Nothing in the code; the Gate V2 FAIL verdict and its interpretation
in validation_plan.md are my own.

## 2026-08-10 — Isosteric heat: F3 plotting function, tests, notebook 03

Tool: Claude Code (two sessions)

### Session 1 — viz function + heats tests
Purpose: Add a pure-plotting F3 function and two Gate-V2 tests, from my specification.
What I provided: Explicit MAY/MUST-NOT file lists (viz.py and test_heats.py only), the
  function signature and behavior, and the pre-registered anchor bounds from
  validation_plan.md.
What it produced: plot_isosteric_heat(...) in viz.py (numerical q_st curve + analytic
  D–A overlay + shaded 4–7 kJ/mol band, no physics beyond the alpha·sqrt(ln) overlay);
  test_isosteric_heat_matches_da_analytic (machinery) and
  test_isosteric_heat_low_coverage_anchor (@pytest.mark.validation).
What I verified: Read the full diff before accepting; confirmed only the two permitted
  files changed; ran `python3 -m pytest tests/test_heats.py -v` (4 passed) and
  `python3 -m pytest -m validation -q` (6 passed) myself; confirmed no non-Avin git author.
What I changed: Nothing in the generated code. Separately fixed the validation marker
  description in pyproject.toml (my edit, not the AI's).

### Session 2 — notebook 03 scaffold
Purpose: Create notebooks/03_isosteric_heat.ipynb as narrative + figure calls only.
What I provided: MAY-create-only-this-file constraint, the exact cell list, and the
  no-physics-in-notebooks rule.
What it produced: A six-cell notebook (imports + repo-root check, model build, F3 save)
  with three markdown placeholders left for me to write.
What I verified: Read the cell plan; confirmed no physics in the notebook and that the
  package entry points matched; ran it myself on the .venv kernel (Restart + Run All) and
  produced F3; confirmed no commit was made in-session.
What I changed: Wrote all three markdown cells (intro, method note, verdict) myself in my
  own words; ran ruff clean over the repo.

Scientific decisions (mine alone): the pre-registered anchor window and band, the pass/fail
criteria, the verdict, and all interpretation prose.

## 2026-08-17 — Tank inventory layer (tank.py)

Tool: Claude Code (Opus 4.8), fresh implementer session (CC-5, modified).

Purpose: Implement src/h2star/tank.py and its bookkeeping test from my
specification, after I had sourced rho_skel and confirmed all callee
signatures myself.

What I provided: A spec giving the verified Material fields, the ModifiedDA
method signatures (n_absolute, n_excess, both (P,T)), molar_density(P,T) ->
mol/m^3, and M_H2 from constants; the two bookkeeping formulas (absolute route
with V_void = V_in - m_s/rho_skel - m_s*v_a; excess route with V_gas = V_in -
m_s/rho_skel); explicit MAY-edit / MUST-NOT-edit file lists; a ban on running
git, tests, or CI edits; and a TODO[AVIN]-and-stop rule for any missing
constant.

What it produced: src/h2star/tank.py (total_h2_mass, total_h2_mass_via_excess,
usable_h2, plus private guards _sorbent_mass and _check_void) and
tests/test_tank_bookkeeping.py (dual-bookkeeping invariant marked validation,
plus two machinery tests).

What I verified: Read the full diff before accepting. Confirmed the absolute
route uses n_absolute and the full V_void, the excess route uses n_excess and
V_gas without the v_a term, molar_density is called (P,T), and M_H2 comes from
constants. Ran the suite myself: 14/14 in the new file, 35/35 overall, the
validation subset at 18, ruff clean, CI green on 0b6534c. Confirmed the
invariant holds to 1e-9 across the P/T grid, which is the real check that the
excess/absolute conversion is consistent. Verified every commit author is my
identity via git log.

What I changed: Nothing in the generated code. Separately (by hand, not this
session) I made the isotherm.py loader edit and the ax21.yaml skeletal-density
entry; the session was forbidden from touching either.

Note: The session proposed guarding the excess route on V_gas - m_s*v_a (the
same void as the absolute route) rather than on V_gas alone. I checked the
reasoning and accepted it: the packing is inconsistent when skeleton plus
adsorbed phase overfill the tank, independent of bookkeeping route.