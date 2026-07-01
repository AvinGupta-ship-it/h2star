## 2026-06-16 — H2STAR Day 1
### Hours worked
3.0 focused.
### Objectives
Record DOE targets, the AX-21 isotherm anchor (Richard et al. 2009), and one HSECoE MOF-5 system
case; pre-register V1-V4 tolerances before any model output exists.
### Work completed
- data/targets/doe_targets.yaml: grav 0.045/0.055/0.065 kg/kg, vol 0.030/0.040/0.050 kg/L, min
  delivery 5 bar, max 12 bar. Verified against the energy.gov technical-targets table (parenthetical
  kg-H2 values; ignored kWh forms).
- data/materials/ax21.yaml: modified D-A parameters for H2 on AX-21 from Table [X] of Richard et al.
  Paper reported [unit]; noted the SI conversion to do in code. Valid ~30-293 K, up to ~6 MPa. Chose
  the global fit. Excess-maximum figure to digitize: Fig [#].
- data/validation/hsecoe_reference.yaml: MOF-5 system, case "[exact label]" from NREL/TP-73571,
  system GC ~4.6 wt%, VC ~37 g/L, envelope 77 K/100 bar -> 160 K/5 bar, 5.6 kg usable basis.
  Recorded that Gate V3 uses 77 K (source), NOT the 80 K forward-map baseline.
- docs/validation_plan.md: V1 density <0.1% vs NIST; V2 excess-RMSE <0.3 wt% + excess-maximum check
  + 20% refit recovery; V3 GC and VC within +/-15% at source envelope; V4 linear-Gaussian + Ishigami.
- Committed (hash a1b2c3d), pushed; GitHub Actions green (smoke test only — no physics yet).
### Gates/tests advanced
- All four gate anchors recorded; tolerances pre-registered. Key realization: Gate V2 and V3 use
  DIFFERENT reference materials (AX-21 isotherm vs MOF-5 system) and DIFFERENT conditions (a 77 K
  isotherm vs the 77->160 K swing), and both are within the project's stated validation scope.
### Problems encountered
- Briefly set the V3 envelope to 80 K out of habit; corrected to 77 K after recalling that envelope
  mismatch is the main cause of false Gate V3 failures.
### AI tools used
- Claude Code: created the package skeleton and saved YAML/markdown I supplied. It read no paper and
  supplied no scientific value; I extracted and verified every number from the primary sources.
### Lessons learned
- The system-vs-material gap is the whole point: even a strong MOF-5 *system* lands ~4.6 wt%, below the
  5.5 wt% 2025 target, despite far higher material-level uptake. My CNT case study will quantify exactly
  this gap for nanotubes.
### Next actions
- Day 2: on paper, derive n_excess = n_abs - rho_gas * V_a from the definition of excess; check against
  the manual's Section 3.4C.
- Day 2: journal half-page summaries of the first four Part-2 concepts (supercritical adsorption,
  excess/absolute, real-gas EOS, isosteric heat).
- Day 2: confirm the Richard et al. PDF is fully downloaded for the Week-2 digitization.
### Open questions
- Confirm exactly which figure in Richard et al. I'll digitize in Week 2 (the 77 K excess panel). Not blocking.

## 2026-06-30
### Hours worked
2.5
### Objectives
Work through the first four §5.3 concepts and write a half-page summary of each;
derive the excess/absolute relation by hand and check it against §3.4C.
### Work completed
- Four concept summaries written below (supercritical adsorption; excess vs. absolute;
  real-gas EOS; isosteric heat & Clausius–Clapeyron).
- Excess/absolute relation derived on paper from the definition of excess uptake;
  verified against §3.4C. [photo: docs/derivations/excess_absolute_2026-06-30.jpg]
- No code this session (Day 2 is a concept day per §5.4).
#### Concept 1 — Supercritical adsorption
Every fluid has a critical temperature above which no pressure will condense it into a
liquid. For hydrogen that's ≈ 33 K, and every temperature I'll ever store at — even
cryogenic 77 K — is more than double that, so hydrogen in the tank is always
supercritical. That kills the classical picture of adsorption as gas condensing into a
liquid film that fills the pores: there is no liquid phase to form. What actually happens
is a density enhancement — the carbon's attractive potential pulls gas into a near-surface
layer denser than the bulk, but that layer never becomes a true condensed phase. "Thicker
air near the wall," not "a puddle in the pore."

Two consequences follow. First, I can't use a real saturation/vapor pressure in the
isotherm, because above the critical point condensation never happens and no vapor pressure
exists — which is exactly why the modified Dubinin–Astakhov form uses a pseudo-saturation
pressure P₀ as a fitted parameter, not a looked-up constant. My Day-1 AX-21 fit gave
P₀ = 1470 MPa; that's not a pressure the tank ever sees, it's a curvature-setting fitting
constant, and being supercritical is why that's fine. Second, because hydrogen binds weakly
on carbon, room-temperature physisorption capacities are intrinsically small — the whole
reason this technology needs cryogenic operation, and why my operating-envelope floor sits
at 60 K, safely above the critical region. The trap I have to avoid is treating P₀ as a
physical pressure — trying to look it up or being alarmed that 1470 MPa is "unphysical."
#### Concept 2 — Excess vs. absolute adsorption
This is the most important idea in the project and the field's most common fatal error
(FM1). There are two ways to count "how much hydrogen is adsorbed." Absolute adsorption
(n_abs) is everything in the dense near-surface layer — the model's natural variable.
Excess adsorption (n_exc) is the surplus over what the same volume would hold at bulk gas
density, and it's what an instrument actually measures, because a sorption apparatus can
only detect the gas present beyond the compressed gas that would be there anyway. They're
bridged by n_exc = n_abs − ρ_gas · V_a, where the subtracted term is the gas that would
fill the adsorbed-phase volume at bulk density with no surface attraction.

The pressure dependence is the whole point. At low pressure ρ_gas is tiny, the correction
vanishes, and excess ≈ absolute. At high pressure the bulk density grows, the subtracted
term grows, and excess rises, peaks (≈ 30–40 bar at 77 K), and falls — even though absolute
keeps climbing toward n_max. That hump is the signature of a correct high-pressure excess
isotherm; any code path that gives a monotonically increasing excess isotherm at 77 K to
200 bar is wrong, and the usual cause is v_a being zero or in the wrong units. Practically:
a reported 5 wt% is usually excess and understates the tank inventory (the tank cares about
absolute — the total in the bed), and comparing an excess measurement to an absolute model
is meaningless. I guard FM1 structurally two ways: a unit test that fails if the 77 K excess
isotherm has no interior maximum (CC-3 test b), and a dual-bookkeeping invariant in tank.py
where total H₂ counted as "absolute + void gas" must equal "excess + all-pore-and-void gas"
to 1e-9 (CC-5).
#### Concept 3 — Real-gas equations of state
An equation of state relates pressure, temperature, and density. The ideal-gas law is the
simplest, but it assumes molecules have zero volume and don't interact — only true at low
density. At cryogenic temperature and high pressure, hydrogen molecules are packed close
enough that their finite size and mutual forces matter, and the ideal law fails badly: at
77 K and 100 bar it gives ρ = PM/RT ≈ 31.5 kg/m³ against a real value of ≈ 25 kg/m³, a
~26% overestimate. Since I count compressed gas in the tank's void space, that error would
propagate into every system-capacity number — using ideal gas here is the classic amateur
error this project has to visibly avoid (Assumption 4).

So I never assume ideal gas. I route every gas-density call through a reference
multiparameter EOS (CoolProp) — a fit to decades of precise data that's the accepted
standard. My job isn't to implement the physics; it's to wrap CoolProp without unit errors
and prove the wrapper against NIST tables. The subtle point I have to be able to defend:
Gate V1 validates the wrapper to <0.1% vs NIST, but CoolProp and NIST implement the *same*
reference equation — so Gate V1 isn't testing the physics, it's testing my wrapper and unit
handling, which is where real errors actually live. The bugs to catch are passing bar where
pascals are expected (a factor of 1e5), confusing mol/L with kg/m³ in the NIST parser, and
accidentally selecting parahydrogen (a ~0.3% mismatch). I model normal hydrogen and check
ortho/para as a sensitivity using CoolProp's parahydrogen fluid.
#### Concept 4 — Isosteric heat & Clausius–Clapeyron
The isosteric heat of adsorption q_st is the differential enthalpy released when a little
more hydrogen adsorbs at fixed coverage ("iso-steric" = the same amount is already on the
surface). It's the thermodynamic, tank-scale meaning of binding energy. I don't measure it
directly; I extract it from how the isotherms shift with temperature via Clausius–Clapeyron:
q_st = R · d(ln P)/d(1/T) at constant n. In words, I hold the adsorbed amount fixed and ask
what pressure maintains that loading at each temperature; the slope of ln P versus 1/T,
times R, is q_st.

The sign is the trap, so I have to be clean about it: adsorption is exothermic, so the
enthalpy of adsorption is negative and q_st is reported as a positive magnitude. Physically,
raising T drives gas off, so to hold coverage fixed I must raise P, which means ln P falls
as 1/T rises and the raw derivative is negative — I report its magnitude, which for carbons
at low coverage should be 4–7 kJ/mol. That band is my built-in sanity anchor: 50 or
0.5 kJ/mol means something is broken. q_st matters because it sets the thermal-management
load during filling — every mole adsorbed dumps q_st of heat that must be removed, or the
bed warms and capacity drops. It also cross-checks my D–A parameters, since the analytic
D–A limit predicts q_st ∝ α · √(ln(n_max/n)), so the numerical and analytic routes should
agree. In code, heats.py computes it by centered finite differences on ln P vs 1/T at fixed
n using the inverted isotherm pressure_at_loading(n,T), with a one-time step-size sweep to
confirm the step converges without drowning in floating-point noise; Figure F3 plots it
against the 4–7 kJ/mol band, and the low-coverage check is part of Gate V2.
#### Derivation — excess vs. absolute
Goal: derive n_exc = n_abs − ρ_gas · V_a from the definition of excess uptake, then verify
against §3.4C.

- Step 0 — Setup: sorbent mass m_s in a chamber; gas-accessible (void) volume V_void,
  measured by a helium dead-volume calibration. Split V_void into a thin adsorbed-phase
  shell V_a (denser than bulk, hugging the surface) and a bulk region (V_void − V_a) at bulk
  density ρ_gas. Define n_abs = total moles in the shell. V_a's boundary is a modeling choice
  (the Gibbs dividing surface), which is why §3.4C calls V_a "fitted or estimated."
- Step 1 — Actual total gas as shell + bulk: N_total = n_abs + ρ_gas (V_void − V_a). Pure
  bookkeeping, no approximation.
- Step 2 — Operational definition of excess (what the instrument reports):
  n_exc ≡ N_total − ρ_gas · V_void. Take the gas actually present and subtract what the
  *entire* accessible volume would hold at uniform bulk density.
- Step 3 — Substitute Step 1 into Step 2:
  n_exc = [n_abs + ρ_gas (V_void − V_a)] − ρ_gas · V_void.
- Step 4 — Expand: n_exc = n_abs + ρ_gas·V_void − ρ_gas·V_a − ρ_gas·V_void.
- Step 5 — Cancel (the crux): the +ρ_gas·V_void and −ρ_gas·V_void terms cancel exactly,
  leaving n_exc = n_abs − ρ_gas · V_a. The entire bulk-gas background drops out — excess
  depends only on the surplus inside the adsorbed-phase volume, which is why instruments can
  measure it cleanly.
- Step 6 — Specific form + unit check: divide by m_s so n is in mol/kg and V_a in m³/kg →
  n_exc(P,T) = n_abs(P,T) − ρ_gas(P,T) · V_a. Units: ρ_gas [mol/m³] × V_a [m³/kg] = mol/kg ✓.
  If it doesn't reduce to mol/kg, I used mass density (kg/m³) instead of molar density.
- Step 7 — Limits: low P, ρ_gas → 0 so n_exc → n_abs (CC-3 test a); high P, ρ_gas grows
  while n_abs saturates toward n_max, so n_exc peaks then declines — the 77 K maximum
  (CC-3 test b).
- Step 8 — Order-of-magnitude check on V_a: estimate V_a ≈ n_max × liquid-like molar volume
  of H₂ ≈ 71.6 × 2.85e-5 ≈ 2.0e-3 m³/kg; my fitted v_a was 1.43e-3 m³/kg — agreement within
  ~1.4×, exactly what's expected when V_a is fitted/estimated.

Verification against §3.4C: final form identical (n_exc = n_abs − ρ_g · V_a) ✓; V_a in
m³/kg ✓; V_a estimate matches "n_max × liquid-like molar volume of hydrogen" ✓; sign is
minus, not plus ✓. Load-bearing move is the Step 5 cancellation; the only common failure is
getting the Step 2 excess definition backwards (a + sign), which makes excess depend on the
whole dead volume instead of just V_a.
### Gates/tests advanced
None (no code today). Conceptual readiness advanced: can now explain all four §5.3
concepts and the excess/absolute conversion unaided. Sets up Gate V1 (EOS) on Day 3–4.
### Problems encountered
The isosteric-heat sign convention took the most care — adsorption is exothermic, so the
enthalpy is negative, yet q_st is reported as a positive magnitude. I worked through the
physical chain (warming drives gas off → pressure must rise to hold coverage fixed → ln P
falls as 1/T rises → raw derivative negative) until I could justify reporting the magnitude
rather than just memorizing it. Also briefly read P₀ = 1470 MPa as a physical pressure
before re-reading §3.4B and confirming it's a supercritical fitting constant that only sets
curvature.
### AI tools used
Claude (chat) — taught the four concepts and walked the excess/absolute derivation;
provided journal templates. I authored all summaries and the derivation myself and
cross-checked the key claims against the project manual (§§3.3–3.14, 5.3, 5.4).
See docs/ai_usage_log.md.
### Lessons learned
- Excess vs. absolute is the load-bearing distinction, not a footnote: most reported wt%
  values are excess and understate tank inventory, and the 77 K excess maximum is a
  correctness signature rather than a curiosity.
- The 0.1% NIST validation isn't testing the physics — CoolProp and NIST share the same
  reference EOS — it's testing my wrapper and units; the real bugs live in bar-vs-pascal
  (×1e5) and mol/L-vs-kg/m³, not the equation.
- P₀ in the modified D–A form is a fitting constant, not a pressure — a direct consequence
  of hydrogen being supercritical at every storage temperature, which is also why
  room-temperature carbon capacities are intrinsically small.
### Next actions
1. Day 3: download NIST WebBook H2 isotherm tables (77/100/160/298 K, 1–200 bar)
   into data/validation/.
2. Day 3: run Prompt CC-2 to implement eos.py + tests/test_eos.py; review unit handling.
3. Day 4: run notebook 01, confirm Gate V1 <0.1%, produce F1.
### Open questions
How sensitive are the final system-capacity numbers to the V_a choice — fitted v_a =
1.43e-3 vs the ~2.0e-3 m³/kg estimate from n_max × liquid-like molar volume? Worth a quick
sensitivity check once tank.py is up (and it ties into the FM1 dual-bookkeeping guard).

## 2026-06-30

### Hours worked
3.0

### Objectives
Build the EOS layer (Day 3): download NIST H2 isothermal tables; implement eos.py +
test_eos.py via Claude Code (CC-2); review units; get the EOS validation tests green.

### Work completed
- Downloaded NIST WebBook isothermal tables (normal hydrogen) at 77/100/160/298 K,
  1-201 bar; wrote a converter (dedupes on pressure, stamps provenance) that produced
  data/validation/nist_h2_*.csv. Sanity densities at ~100 bar: 31.56 / 23.20 / 14.18 /
  7.75 kg/m3, each ~5% below ideal gas and decreasing with T.
- Claude Code (CC-2, fresh implementer session) implemented src/h2star/eos.py,
  tests/test_eos.py, notebooks/01_eos_validation.ipynb, and a parity function in viz.py.
  Reviewed both eos.py and test_eos.py line by line before running.
- EOS validation tests: PASS.

### Gates/tests advanced
[After re-running: e.g. "Gate V1 tests moved red->green - eos.density reproduces NIST
normal-hydrogen density to a max relative error of 0.005% (< the 0.1% pre-registered floor)
across all four isotherms. The physical point the review drilled: the test must convert
NIST bar->Pa before calling density because PropsSI expects pascals, and since NIST and
CoolProp both implement Leachman 2009, any error above 0.1% could only be a unit/parsing
bug on my side, not physics."]

### Problems encountered
- CoolProp import failed, then pytest failed to import h2star. Root cause: this shell had
  the RAMANUQ venv active the whole session (pytest header showed
  .../research/ramanuq/.venv/bin/python3), even though the prompt read (.venv). So the
  earlier CoolProp install and the 31.30 kg/m3 check landed in ramanuq's env, not h2star's.
  Fix: activated ~/Documents/research/h2star/.venv, confirmed with `which python3`, then
  `pip install -e .` + CoolProp into the correct env. Lesson logged below.
- Two earlier false alarms I chased (both my mis-reads, not data bugs): (a) triple-counted
  16-bar row in the raw NIST table (NIST prints the ~13 bar critical-pressure point once as
  vapor + twice as supercritical) - fixed by deduping in the converter; (b) I briefly
  thought 31.5 kg/m3 at 77 K/100 bar was too high vs a remembered "~25", but ~31.5 is the
  correct value (near hydrogen's critical density; ideal gas is 31.49).

### AI tools used
Claude Code (implementer session) - CC-2 to implement eos.py/test_eos.py/notebook/viz
parity fn to my specification. I reviewed every line focusing on unit handling (bar->Pa in
the test, P/T argument order, 'D' vs 'Dmolar' key, 'Hydrogen' species), and ran the tests
myself. Claude (chat) - planning + the NIST converter script; also caught the wrong-venv
diagnosis. See docs/ai_usage_log.md.

### Lessons learned
- Always confirm the active environment with `which python3` at the start of a session -
  the shell prompt showing (.venv) does not guarantee it is THIS repo's venv. A cross-repo
  venv leak silently broke both CoolProp and the h2star import today.
- Gate V1 validates the wrapper, not the EOS: NIST and CoolProp share the Leachman 2009
  equation, so the 0.1% tolerance is really a units-and-parsing check.
- My Day-0 journal recorded the CoolProp 77 K/100 bar check as ~25 kg/m3; the correct value
  is ~31.5. That entry needs a correction (real value), since the ~25 was wrong.

### Next actions
1. Re-run the validation tests in the correct h2star venv; confirm 4 passed; commit code + data.
2. Day 4: run notebook 01, produce figures/F1_eos_parity.png.
3. Day 4: record the Gate V1 verdict (measured max error vs <0.1%) in docs/validation_plan.md.

### Open questions
- Does h2star/.venv actually exist from Day 0, or was it never created (Case B)? Resolve
  while fixing the venv, and note which, so the environment state is documented.

  ## 2026-06-30
### Work completed
Registered a named Jupyter kernel bound to h2star/.venv; set jupyter.notebookFileRoot to the workspace root; ran notebook 01_eos_validation end-to-end; produced figures/F1_eos_parity.png; appended the Gate V1 result to validation_plan.md.
### Gates/tests advanced
Gate V1 (EOS) moved red→green. Measured global max relative density error 0.031% vs the pre-registered <0.1% floor, across 77/100/160/298 K over 1–201 bar. The understanding it required: this gate validates my wrapper, not the EOS — CoolProp and NIST both implement Leachman et al., so near-exact agreement is expected and the real thing under test is my bar→Pa conversion and PropsSI pairing. Verified the ideal-gas anchor (31.49 kg/m³ at 100 bar/77 K) so I'd recognize a unit blow-up as units, not physics.
#### Problems encountered
First Run All threw FileNotFoundError on the NIST CSVs — the notebook's CWD was notebooks/, not the repo root. Fixed by setting notebookFileRoot to the workspace folder and restarting the kernel. Also corrected my Day-0 entry, which had logged the 77 K/100 bar density as ~25 kg/m³; the correct value is ≈31.3.
#### Lessons learned
The kernel picker will offer other projects' venvs; a named kernelspec removes that ambiguity permanently. Pre-registration only counts if the tolerance predates the result in git — I appended the verdict rather than editing the threshold, and the diff proves it.

## Week of 2026-06-28
### Phase
Week 1 — Foundations and the EOS layer (Gate V1). Ref: manual §5.4.
### Hours this week
~11.5 focused hours across Days 1–5 (reading/anchors 3, concepts 2, EOS wrapper 2.5, Gate V1 2, review 2).
### Phase deliverables completed
- eos.py: CoolProp wrapper for normal hydrogen — density(P,T), molar_density(P,T), enthalpy/entropy per kg, isothermal_compression_work(P1,P2,T); SI-in guards (P>0, T≥33.2 K). Reviewed line by line. [commit <SHA>]
- data/validation/nist_h2_{77,100,160,298}K.csv — four isotherms, ~41 rows each, 1–201 bar, deduped, `#` provenance headers; raw exports kept as raw_nist_*.txt. [commit <SHA>]
- tests/test_eos.py: loads CSVs, bar→Pa ×1e5, asserts relative density error <0.1% per row, parametrized over four isotherms, @pytest.mark.validation. [commit <SHA>]
- Gate V1 CLOSED: measured max relative density error [X.XXX%] vs the pre-registered <0.1% floor → PASS. Recorded in validation_plan.md beside the unchanged floor (diff = addition only). [commit <SHA>]
- F1 parity figure via viz.py parity function; all four isotherms on the y=x diagonal. figures/F1_eos_parity.png. [commit <SHA>]
### Phase deliverables remaining
- Week 2: isotherm.py (modified D–A: absolute, excess, inverse), heats.py, fitting.py with covariance, Gate V2, tag v0.1-isotherms.
- Weeks 3–8: tank/vessel/system + Gate V3; forward + inverse maps; UQ + Sobol + Gate V4; CNT case study; report; v1.0 + DOI.
### Gates/tests advanced this week
- Gate V1 red→green. Understanding it required: the wrapper and NIST call the same reference EOS, so any >0.1% gap is a wrapper/unit error, not physics — the test is really a unit-handling test, and the live failure mode is forgetting the ×1e5 bar→Pa conversion. Confirmed four-isotherm parity across 1–201 bar.
### Figures or analyses produced
- figures/F1_eos_parity.png (model-vs-NIST parity, four isotherms).
### Key decisions made
- Fluid = normal hydrogen (not para): the envelope floor is 60 K, above the deep-cryo regime where para-enrichment dominates; the ortho/para density difference will be a later sensitivity check (assumptions.md), not modeled as kinetics. Reasoning: matches how the reference data and HSECoE screening are framed.
- Pre-registered the Gate V1 tolerance (<0.1%) on Day 1, before any output — the diff (declaration commit precedes verdict commit) is the pre-registration proof.
- Kept raw NIST exports in-repo alongside parsed CSVs so the parse step is auditable.
### Slip from plan
- None; Week 1 on the §5.4 schedule. Process note: ruff flagged leftover diagnostic cells in notebook 01 on Day 4 and reddened CI; removing them fixed it. Lesson banked: run `python3 -m ruff check .` and strip throwaway cells before every push.
### Plan for next week
- (1) isotherm.py (n_absolute, n_excess, pressure_at_loading) + heats.py; completion = round-trip P→n→P to 1e-6 and the 77 K excess-maximum test both green.
- (2) Gate V2: overlay my AX-21 curve on the digitized paper points; completion = RMSE below the tolerance I pre-register before running, plus the overlay committed as F2-draft.
- (3) fitting.py refit with covariance and tag v0.1-isotherms; completion = recovered params within stated tolerance of published values, table in notebook 02, green CI on the tag.

## 2026-07-01
### Hours worked
2.5
### Objectives
Implement the isotherm layer (Material + ModifiedDA) and heats.py via CC-3; write the D-A
derivation and isotherm assumptions; digitize the 77 K AX-21 excess curve; eyeball the
reproduction. Set up Gate V2 without closing it.
### Work completed
- docs/model_derivations.md (sec. 1-3) and docs/assumptions.md (A-ISO-1..4) written and committed (<hash1>).
- src/h2star/isotherm.py, src/h2star/heats.py, tests/test_isotherm.py, tests/test_heats.py via CC-3 (<hash2>).
- data/validation/ax21_digitized.csv: 14 points off Fig. 1(a) 77 K (x markers), MPa/mol-kg, provenance header.
- Overlay /tmp/ax21_day6_overlay.png: model excess through the points, both peaking ~26 mol/kg near 35 bar.
### Gates/tests advanced
- test_isotherm.py: low-P excess≈absolute, interior excess maximum at 77 K, P->n->P round-trip 1e-6,
  citation-required — all red->green. test_heats.py: positive q_st at low coverage, step-size stable at dT=1 K.
  Understanding the interior-max needed: excess only rolls over because n_excess subtracts *molar* gas density.
### Problems encountered
- from_yaml first assumed flat SI keys; my ax21.yaml is nested {value, unit} with p0 in MPa. Fixed by parsing
  parameters[k]['value'] and converting p0 x1e6 -> 1.47e9 Pa in from_yaml. Caught the citation-guard order too.
### AI tools used
- Claude Code (Opus 4.8) for the CC-3 implementation. Verified: read the full diff, checked the D-A equation,
  the MPa->Pa conversion, the p0 clamp / no-NaN guards, molar density in n_excess, the -R sign in q_st;
  ran all six tests and ruff myself. See docs/ai_usage_log.md.
### Lessons learned
- p0 is ~14,700 bar, far above the envelope, so absolute adsorption stays on its rising branch across 1-200 bar
  and the excess maximum comes entirely from the gas-subtraction term, not from n_abs peaking.
### Next actions
- 1. Build F2 (data + published fit + residuals) in notebook 02.
- 2. Compute Gate V2 RMSE over the 0-6 MPa range vs the pre-registered threshold.
- 3. Promote the excess-maximum test to the @pytest.mark.validation gate.
### Open questions
- Confirm the RMSE threshold I pre-registered is defensible against the paper's 2.2% deviation at 77 K.