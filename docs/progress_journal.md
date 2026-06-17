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