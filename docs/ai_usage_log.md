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

## [2026-08-17] — Day 12 — Pressure-vessel layer (vessel.py)
Tool: Claude Code (Session [N], implementer) — [model string]
Purpose: Implement src/h2star/vessel.py and tests/test_vessel.py from my
specification, after I had independently sourced and verified all six
data/engineering.yaml vessel parameters myself.
What I provided: A spec giving the six verified engineering.yaml values
(safety_factor 2.25; sigma_allow 1.836e+9 Pa as effective composite stress
with knockdowns already folded in and NOT to be re-applied in code;
aspect_ratio_LR 3.0; composite_density 1609 kg/m^3; liner_areal_mass
4.667 kg/m^2 already pressure-scaled 700->100 bar; performance_factor
73500 Pa*m^3/kg for cross-check only); the hoop-stress sizing relations
(t = SF*P_max*r/sigma_allow, capsule geometry radius_from_volume/surface_area);
the PF cross-check formula; explicit MAY-edit / MUST-NOT-edit file lists; a ban
on running git, tests, ruff, CI edits, or any shell command inside the session;
and a TODO[AVIN]-and-stop rule for any missing constant.
What it produced: src/h2star/vessel.py (VesselParams.from_yaml,
radius_from_volume, surface_area, wall_thickness, vessel_mass_hoop,
vessel_mass_performance_factor) and tests/test_vessel.py (five tests including
the 35% hoop-vs-PF cross-check, none marked validation).
What I verified: Read the full output before accepting. Confirmed sigma_allow is
used as-is with no re-applied knockdowns, SF enters only in wall_thickness, and
the loader reads the vessel: block by key. Ran the suite myself: 5/5 in the new
file, 40/40 overall, validation subset unchanged at 18, ruff clean, CI green on
9ef84fe. Verified every commit author is my identity via git log.
What I changed: The cross-check first failed because the unscaled 700-bar liner
dominated hoop mass. This was my Class-A diagnosis, not the session's: I
pressure-scaled the liner (32.67 x 100/700 = 4.667 kg/m^2) in engineering.yaml
by hand and widened the cross-check band 30%->35% to reflect Type III vs Type IV
vessel classes. The session did not touch engineering.yaml or the band.

## [2026-08-18] — Day 13 — System-budget layer (system.py)
Tool: Claude Code (Session [N], implementer) — [model string]
Purpose: Implement src/h2star/system.py and tests/test_system.py from my
specification, after I had independently sourced and verified the insulation and
BOP values and made every Class-A modeling call myself.
What I provided: A spec giving the verified engineering.yaml insulation/bop
values (mli_k_eff 5.2e-4 W/(m*K), mli_density 59.3 kg/m^3, heat_leak_budget
5.0 W, T_env 300 K, bop_fixed 16.0 kg, bop_scaling 0.0 with TODO[AVIN]); the
EngineeringParams and SystemDesign dataclass fields; the budget composition
(m_sys = m_h2_full + m_s + m_vessel + m_insulation + m_bop); the insulation
sizing by inverting Q = k_eff*A*DeltaT/t_ins for t_ins then
m_insulation = A*t_ins*mli_density, reusing the vessel geometry; the GC/VC
definitions with the deliberate m_usable-over-m_sys(with-m_h2_full) asymmetry;
size_for_usable via scipy brentq on usable_h2(V) - 5.6; the verified callee
signatures (VesselParams.from_yaml, tank.usable_h2, isotherm.ModifiedDA);
explicit MAY-edit / MUST-NOT-edit file lists; a ban on git, tests, ruff, CI
edits, or any shell command; and a TODO[AVIN]-and-stop rule for missing
constants.
What it produced: src/h2star/system.py (EngineeringParams.from_yaml,
SystemDesign, evaluate(V_internal) returning the budget dict, module-level
evaluate, size_for_usable) and tests/test_system.py (five machinery/sanity
tests, none marked validation).
What I verified: Read the full output before accepting. Confirmed the insulation
sizing reuses the vessel's own radius->area->wall-thickness geometry rather than
recomputing it, that the GC numerator is m_usable while m_sys carries
m_h2_full, and that from_yaml reads the insulation/bop blocks by key with unit
strings validated. Ran the suite myself: 5/5 in the new file, 45/45 overall,
validation subset unchanged at 18, ruff clean, CI green on 60eb986. Drove the
sized reference design myself and recorded the Gate V3 prior (GC ~= 0.0652,
VC ~= 0.0260 kg/L) in the progress journal. Verified every commit author is my
identity via git log.
What I changed: Nothing in the generated code. The Class-A modeling choices (5 W
HSECoE heat-leak assumption over the <7 W DOE ceiling; BOP fixed-only;
bop_scaling left as a TODO[AVIN] rather than a placeholder number) were mine,
made before the session and encoded in the spec.

## [2026-08-21]] — Day 14 — Gate V3 anchor sourcing + validation reframe
Tool: ChatGPT 5.6 Sol and Claude Code Opus 5
Purpose: Source a verifiable HSECoE AX-21 system-capacity anchor for Gate V3, and
work out an honest validation basis when the record proved incomplete.
What I provided: Minimal-source sourcing prompts (source-to-variable map first,
three-source cap, no invented citations, [NOT FOUND] required over guessing). For
the reframe, I provided the Day 13 diagnostic numbers and the pre-registered V3
block and made every scientific call myself.
What it produced: Pass 1 returned an AX-21 system pair (0.039 kg/kg, 0.024 kg/L,
Anton FY2011 APR Table 1) but no verifiable empty state. Pass 2 (ST044 2013)
returned one internally consistent case: AX-21, 80 K/200 bar full, GC 0.0312,
VC 0.0194 (unit printed "gH2/Lsys"), empty state [NOT FOUND], BOP [NOT FOUND] as
a baseline-specific statement. Pass 3 (NREL/MP-5400-73571 2019 + SRNL final)
returned [NOT FOUND] for any AX-21-specific discharge state. Planning assistant
produced the reframe scaffold, the diagnostic scripts, and the provenance
templates.
What I verified: I opened the ST044 PDF and confirmed slides 18/19 myself before
using the numbers. I confirmed the report number is NREL/MP-5400-73571 (not TP).
I ran every diagnostic myself and read GC_full/VC_full and the mass breakdown off
real output. I confirmed the core (rho_bulk 300, rho_skel 2308, m_sorbent =
rho_bulk*V_internal, usable = 5.600 kg) before accepting the FAIL as vessel+BOP
scope. I rejected splicing any cross-document empty state onto the AX-21 case.
What I changed / decided (all mine): reframed Gate V3 from usable-swing MOF-5 to
full-state AX-21 inventory; amended the pre-registration in a dated commit
(fcbd6b2) BEFORE running gate code; read the ST044 volumetric unit as kg/L by
triangulation and documented it; rendered Gate V3 = FAIL (documented) rather than
chasing a PASS by re-sourcing the vessel after seeing the 147.8 kg target;
recorded the diagnosis in issue #1.

## 2026-08-26 — Day 15: Gate V3 artifacts (system-validation test, F4, notebook 04)

Tool: Claude Code (three separate implementer sessions, one per file; fresh session each, /exit between)

Purpose: Turn the Day 14 Gate V3 adjudication into committed artifacts — a marked
validation test recording the FAIL, the F4 system-validation figure, and notebook 04
reproducing the comparison — without any of them defining physics or touching git.

What I provided: For each session, an explicit implementer prompt with a MAY-edit /
MUST-NOT-edit file list, a hard ban on git, CI/.github edits, and running any shell,
pytest, ruff, or python command. I supplied the real function signatures I had grepped
myself from system.py (SystemDesign positional args, size_for_usable defaults) and
viz.py (the per-function fig/ax style), and the real nested keys from
hsecoe_reference.yaml. I forbade hardcoding the anchor numbers (0.0312, 0.0194, 15)
and required a TODO[AVIN] with a stop on any missing value rather than a guess.

What it produced:
- tests/test_system_validation.py — loads the anchor from YAML at runtime, sizes the
  AX-21 tank to 5.6 kg usable, computes GC_full = m_h2_full/m_sys and
  VC_full = m_h2_full/(V_sys*1000) at 80 K/200 bar, asserts each within the ±15%
  band, marked @pytest.mark.validation and @pytest.mark.xfail(strict=True) with a
  reason string pointing at the vessel+BOP scope gap and issue #1.
- plot_system_validation appended to src/h2star/viz.py — F4, two panels, the ±15%
  band drawn around the anchor with the model points outside it; receives precomputed
  numbers only, no model calls.
- notebooks/04_system_validation_hsecoe.ipynb — drives system.py, computes the
  full-state metrics, compares to the anchor, calls F4; calls and narrative only.

What I verified: I read every generated file before running anything. I ran the new
test alone (1 xfailed, exit 0) and the full suite (45 passed, 1 xfailed, no
PytestUnknownMarkWarning). I ran ruff on the repo (clean). I smoke-rendered F4 with
the Day 14 numbers and opened the PNG to confirm the band sits around the anchor and
the model points read as a visible FAIL. I executed notebook 04 headlessly with
nbconvert and read back its printed outputs: GC_full = 0.0777 kg/kg, VC_full = 0.0363
kg/L, both labeled OUTSIDE the ±15% band, and the mass budget (m_sys 75.73, m_h2_full
5.882) matching the Day 14 diagnosis exactly. I confirmed the notebook and the test
compute the metrics identically. After each commit I confirmed the author was
Avin Gupta <iamavingupta@gmail.com>.

What I changed: I did not modify the generated code substantively. I accepted the F4
session's judgment call to omit a redundant anchor marker (the line plus band already
carry the anchor) after checking it read correctly in the rendered figure. The
Gate V3 limitation write-up in docs/validation_plan.md is my own prose, not generated.

## 2026-08-26 — Day 15 (Week 3, Day 5)

### Hours worked
2

### Objectives
Turn the Day 14 Gate V3 adjudication into committed artifacts and close Week 3:
a marked validation test, the F4 figure, notebook 04, the limitation write-up,
and the v0.1 tag.

### Work completed
- tests/test_system_validation.py — Gate V3 recorded as a strict xfail; loads the
  anchor from YAML, sizes the AX-21 tank to 5.6 kg usable, computes GC_full and
  VC_full at 80 K/200 bar, asserts each within the pre-registered ±15% band
  (commit eab9923).
- plot_system_validation (F4) appended to src/h2star/viz.py and
  notebooks/04_system_validation_hsecoe.ipynb driving system.py and calling F4
  (commit 5487d5d); figures/F4_system_validation.png regenerated.
- Gate V3 result-and-limitation write-up appended to docs/validation_plan.md
  (commit b645031).
- Tagged and pushed v0.1 — validated forward model with Gate V3 as a documented FAIL.
- Full suite 45 passed / 1 xfailed; ruff clean; CI green on b645031; v0.1 on origin.

### Gates/tests advanced
Gate V3 moved from a Day-14 adjudication written in prose to a recorded, executable
result. The physical understanding the fix required: an xfail is not a way to hide a
failure but a way to assert one — the assertion still runs against the untouched ±15%
band, the FAIL is the expected state, and strict=True means that if a future vessel
model ever closes the gap the test xpasses and breaks the suite on purpose, forcing me
to re-judge the gate rather than letting it drift to green unnoticed. A skip would have
erased the gate; the xfail keeps it on the record. This is the same shape as the Gate V2
parameter-recovery FAIL-by-design.

### Problems encountered
- nbconvert/nbformat were not in the venv, so I couldn't execute the notebook headlessly.
  Installed them as local dev tooling, deliberately not added to pyproject.toml since
  they aren't a package runtime dependency.
- The handoff described viz.py as having "a single rcParams block," but the real file
  styles each figure function inline with no module-level rcParams. I read the actual
  file first and had F4 match the real per-function convention rather than the handoff's
  description — a reminder to trust the bytes over the summary.
- [anything else that actually came up for you.]

### AI tools used
Three Claude Code implementer sessions (test file, F4 function, notebook 04), each a
fresh session with an explicit MAY/MUST-NOT file list and a ban on git/CI/tests/ruff/shell.
Cross-reference: docs/ai_usage_log.md, 2026-08-26 entry.

### Lessons learned
Grepping the real function signatures and the real nested YAML keys before writing any
code is what kept the test, the notebook, and the figure consistent — the notebook and
the test compute GC_full/VC_full with identical arithmetic because I pinned both to the
same source bytes, and executing the notebook reproduced the Day 14 numbers to the digit
(GC_full 0.0777, VC_full 0.0363). The larger lesson is that the localized FAIL is the
result: the forward physics reproduces HSECoE at the inventory level, and I can name
exactly which idealization (thin-wall vessel + fixed BOP, ~4.2× light on dead mass)
breaks the system gate. That is a finding I can defend, not a gap I have to apologize for.

### Next actions
1. Week 4: implement envelope.py and inverse.py — forward GC/VC maps over (P_full, T_full)
   for AX-21, then first acceptability maps in (n_max, alpha) and (n_max, rho_bulk).

### Open questions
- Would a design-level vessel-mass model (end-dome, liner, hardware beyond hoop-stress
  wall) plus a sized BOP correlation raise the engineering-mass block toward the ~147.8 kg
  the anchor implies, and if so would Gate V3 xpass? Track this against the strict marker.

## Week of 2026-08-24 — Weekly Review (Week 3)

### Phase
Week 3 complete. Tank, vessel, and system-budget layers implemented and tested; Gate V3
adjudicated as a documented FAIL localized to the engineering-mass block; v0.1 released
as the validated forward model.

### What advanced
The week built the whole materials-to-system spine: tank inventory with the dual-bookkeeping
invariant (absolute-route and excess-route totals agreeing to 1e-9), the pressure vessel
with the liner pressure-scaling fix that resolved the hoop-mass domination, and the system
mass/volume budget with MLI heat-leak insulation sizing. The hardest part was Gate V3: I
found the pre-registered anchor was built on the wrong reference case (MOF-5, a usable-swing
basis, against my AX-21 stack), and rather than invent an empty state I reframed the gate
onto the full-state system inventory the HSECoE ST044 record actually specifies, amended the
pre-registration in a dated commit before any gate code ran, kept the ±15% tolerance, and
preserved the original block as superseded. The gate then failed honestly, and I localized
the failure to the mass denominator by back-solving what m_sys would have to be.

### Next week
Week 4: forward maps and the inverse acceptability engine (envelope.py, inverse.py; F5, F6 draft).