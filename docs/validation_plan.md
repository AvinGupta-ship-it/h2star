# H2STAR Validation Plan (pre-registered)

   Declared BEFORE any model output exists. Tolerances are not edited after a gate is run;
   the saved history of this file is the pre-registration record.

   ## Gate V1 — Equation of State (EOS) wrapper
   Target: my CoolProp wrapper reproduces NIST WebBook hydrogen density.
   Conditions: T = 77, 100, 160, 298 K; P = 1-200 bar (normal hydrogen).
   Pass: relative density error < 0.1% at every tabulated point.
   Rationale: both use the same reference EOS, so this tests my units/wrapper, not the physics.
   Result — 2026-06-30 (AG): Gate V1 PASS. Measured global maximum relative density error between the CoolProp normal-hydrogen wrapper and the NIST WebBook isotherms = 4.992e-5 (~0.005%), taken over all four isotherms (77/100/160/298 K) at every tabulated pressure across 1–201 bar, computed row-by-row at each row's exact pressure. Pre-registered floor <0.1% — unchanged since Day 1. Verification: python3 -m pytest tests/test_eos.py -m validation → 4 passed; figures/F1_eos_parity.png shows all points on the parity diagonal. Scope: this certifies unit handling (bar→Pa) and PropsSI pairing in the wrapper, not the reference EOS itself, which CoolProp and NIST share.

   ## Gate V2 — Isotherm model
   Target: modified Dubinin-Astakhov reproduces published AX-21 excess isotherms (Richard et al. 2009).
   Pass (visual): my 77 K excess curve overlays the digitized AX-21 points with no systematic bias.
   Pass (quantitative): RMSE of excess uptake < 0.3 wt% absolute across the digitized points.
   Refit check: refitting the digitized points recovers each parameter within 20% of the paper.
   Physical check: the 77 K excess isotherm shows an interior maximum between 1 and 200 bar.
   ### Gate V2 (isotherm) — part 1: excess-RMSE threshold  [PRE-REGISTERED]
- Date declared: 2026-07-01
- Metric: RMSE between modified-D–A excess at the PUBLISHED AX-21 parameters and my
  digitized 77 K excess points (data/validation/ax21_digitized.csv), evaluated at the
  digitized pressures over the 0–6 MPa data range, in mol/kg.
- Pre-registered threshold: RMSE < 1.5 mol/kg. PASS if below; FAIL if at or above.
- Rationale: Set at 1.5 mol/kg ≈ 2× the paper's reported H2 standard error of estimate (0.79 mol/kg). My digitized points carry the original fit residual plus digitization scatter (~0.3–0.6 mol/kg), so doubling σ_est is a principled allowance for the latter; at ~6% of the ~27 mol/kg peak the bar still fails a units error, an excess/absolute confusion, or a wrong-figure error, so it tests reproduction rather than rubber-stamping it.
- Declared BEFORE the RMSE was computed; the commit adding this line precedes the commit
  recording the measured RMSE (git log is the proof).
- Author: Avin (Class-A).
  ### Gate V2 (isotherm) — part 1: VERDICT
- Date: 2026-07-01
- Pre-registered threshold (UNCHANGED): RMSE < 1.5 mol/kg
- Measured: RMSE = 1.11 mol/kg -> PASS
- Excess-maximum gated test (tests/test_isotherm.py, @pytest.mark.validation): green via `pytest -m validation`
  ### Gate V2 — parameter recovery (pre-registered 2026-07-02). 
  Beta fixed at 18.9 J/(mol·K) (single-T: alpha, beta enter only as alpha+beta·T). PASS iff n_max in 53.7–89.5 mol/kg, alpha in 2156–4004 J/mol, v_a in 9.30e-4–1.93e-3 m³/kg, log10(p0/Pa) in 8.467–9.867, and refit RMSE ≤ Day 7 published-parameter RMSE. 
  Verdict (2026-07-02): FAIL. Recovered n_max 29.9 mol/kg (band 53.7–89.5), alpha 1705 J/mol
(band 2156–4004), log10(p0/Pa) 7.000 — the imposed lower fit bound (band 8.467–9.867),
v_a 3.83e-4 m³/kg (band 9.30e-4–1.93e-3): all four outside the pre-registered bands. The
RMSE criterion alone passed (0.802 ≤ 1.109 mol/kg). Bands unchanged.
Interpretation: implementation error is excluded — synthetic-data tests recover known
parameters within 2σ, and the refit RMSE improves on the published-parameter RMSE as it
structurally must. The failure is a property of the data: with 11 points on a single 77 K
isotherm the four-parameter likelihood is a ridge (pairwise correlations 0.91–0.99,
cond(JᵀJ) ≈ 1e14, anticipated in model_derivations §4.4), and the optimizer, started at
the published values, descended it to a corner solution at the p0 bound, gaining
~0.3 mol/kg RMSE mostly at the low-pressure knee. Reported 1σ values are additionally
invalid at an active bound. The gate establishes practical non-identifiability of the
individual parameters from one isotherm; the curve is identifiable (part 1 PASS), the
parameter vector is not.
Post-hoc diagnostic (labeled, no band applied): with p0 also fixed at the published
1.47e9 Pa, the refit recovers n_max 67.8 mol/kg (−5.3%), alpha 3266 J/mol (+6.0%),
v_a 1.42e-3 m³/kg (−0.5%), RMSE 0.907 mol/kg — supporting the ridge explanation: pin the
flattest direction and the remaining parameters return to near-published values.
Consequence logged for Week 5: this single-isotherm covariance cannot naively seed the
material-parameter Monte Carlo; candidate resolutions (fixed-p0 conditional covariance,
published multi-temperature information) recorded as an open question.

  ## Gate V3 — System model
     ### SUPERSEDED (pre-registered Week 1, retained for provenance):
  ### Target: my system GC and VC reproduce the published MOF-5 cryo-adsorbent system (HSECoE/NREL).
  ### Envelope: fill 77 K / 100 bar, discharge 160 K / 5 bar; 5.6 kg usable H2 basis.
  ### Pass: |my GC - published GC| / published GC <= 15% AND the same for VC.
  ###
  ### AMENDED [2026-08-19], Day 14, before any Gate V3 code was run.
  ### Reason for amendment: on sourcing the anchor I found the original block was
  ### built on the wrong reference case. (1) Material: my entire system stack is
  ### AX-21 activated carbon, so the MOF-5 target was a parameter-provenance error.
  ### (2) Empty state: no primary HSECoE source I could locate (SRNL ST044 2013;
  ### Anton FY2011 APR; Thornton et al. NREL/MP-5400-73571 2019 final report) pins
  ### an AX-21-specific discharge state. Published AX-21 discharge assumptions vary
  ### across the program (4 bar; ~5 bar/140 K for a Phase-2 MOF-5 design; 150 K/5 bar
  ### in a 2015 GM report) and none is attached to the AX-21 baseline. A usable-swing
  ### gate would therefore require me to invent an empty state and call the result a
  ### reproduction, which overclaims (FM7). (3) Basis: HSECoE ST044 slide 18 DOES
  ### publish AX-21 full-state system GC and VC at a documented full state, with no
  ### empty-state dependence. I therefore validate the full-state system inventory,
  ### which is what the reference actually specifies. The +/-15% tolerance is
  ### unchanged from the original pre-registration.

  Target: my system GC_full and VC_full reproduce the published HSECoE AX-21
    activated-carbon full-state system capacities.
  Reference: HSECoE End-of-Phase-1 activated-carbon (AX-21) baseline, Type-3 tank.
    Tamburello/SRNL, DOE AMR Project ID ST044, 2013, slide 18 (capacities) and
    slide 19 (full state). Corroborating: Anton/SRNL FY2011 APR Table 1 (0.039
    kg/kg, 0.024 kg/L, same material class).
  Full state: 80 K, 200 bar (ST044 slide 19).
  Published values: GC_full = 0.0312 kg H2 / kg system; VC_full = 0.0194 kg H2 / L
    system. The ST044 slide prints the volumetric unit as "gH2/Lsys", which is
    dimensionally impossible for the printed magnitude (0.0194 g/L is ~1000x too
    low for any real H2 system). I read the intended unit as kg/L (19.4 g/L),
    triangulated against the FY2011 pair (0.024 kg/L, same material class) and
    against H2 density limits. Recorded as a transcription-error correction, not a
    value change to pass the gate.
  Basis: FULL-STATE system inventory, GC_full = m_h2_full / m_sys,
    VC_full = m_h2_full / V_sys. No usable-swing / empty-state term enters this gate.
  Empty state: null. The primary record does not pin an AX-21 discharge state;
    the usable-swing layer is validated separately (dual-bookkeeping invariant,
    already green) and its empty-state sensitivity is a documented study, not a
    reproduced published value.
  BOP: unclear for this baseline. ST044's waterfall includes BOP but does not tie
    it to the printed baseline denominator. Treated as a disclosed contributor to
    the 15% band, not a claimed fact.
  Pass: |my GC_full - 0.0312| / 0.0312 <= 15% AND |my VC_full - 0.0194| / 0.0194 <= 15%.
  Rationale: system models legitimately differ in BOP and insulation detail and in
    envelope definition; 15% is the pre-registered agreement band, unchanged.

    ### Gate V3 — Result and Limitation (Day 15, 08/26/2026)

**Verdict: documented FAIL, localized to the engineering-mass block.**

Run configuration: AX-21 material; tank sized to 5.6 kg usable on a
5 bar / 160 K sizing-only baseline; full-state system inventory read at
80 K / 200 bar (the state the HSECoE ST044 anchor specifies). Metrics on a
full-state basis: GC_full = m_h2_full / m_sys, VC_full = m_h2_full / V_sys.

Result vs. anchor (±15% pre-registered band, unchanged since Week 1):
- GC_full = 0.0777 kg/kg vs anchor 0.0312 → 2.49× high, OUTSIDE band [0.0265, 0.0359]
- VC_full = 0.0363 kg/L  vs anchor 0.0194 → 1.87× high, OUTSIDE band [0.0165, 0.0223]

Mass budget (kg): H2 5.882, sorbent 34.827, vessel 16.685, insulation 2.333,
BOP 16.000, system 75.726.

Diagnosis (physics-first, §5.9): [in your own words —
  1. units clean;
  2. numerator m_h2_full sound;
  3. the GC-vs-VC asymmetry localizes the gap to the mass DENOMINATOR;
  4. back-solve: matching GC 0.0312 needs m_sys ≈ 188.5 kg; the well-anchored
     core (sorbent + H2 ≈ 40.7 kg) is sound, so the vessel+insulation+BOP block
     would need ≈ 147.8 kg vs 35.0 modeled (≈ 4.2×);
  5. interpretation: the thin-wall composite hoop-stress vessel and fixed 16 kg
     BOP idealize away most of a real HSECoE Type-3 200-bar tank's dead mass,
     so the model gives an optimistic upper bound on GC.]

Decision (settled): [in your own words — report the FAIL honestly rather than
re-source the vessel after seeing the 147.8 kg target, which would be fitting to
a known answer; the localized FAIL is the stronger, more defensible result,
mirroring the Gate V2 FAIL-by-design. Recorded as a strict xfail
(tests/test_system_validation.py) and in GitHub issue #1.]

What would change the verdict: [your words — a design-level vessel mass model and
a sized BOP correlation; if a future upgrade closes the gap the xfail xpasses and
forces re-adjudication.]

  ## Gate V4 — Uncertainty & sensitivity machinery
   Target 1: Monte Carlo reproduces an analytic linear-Gaussian propagation within Monte Carlo error.
   Target 2: Sobol indices on the Ishigami test function match published values within 5%.

### Gate V2 — isosteric-heat clause (pre-registered 2026-08-10, before computation)

Rationale. The isosteric heat q_st is the thermodynamic binding energy at tank
scale. For hydrogen on carbons the accepted low-coverage range is 4–7 kJ/mol
(§3.4D, §5.3). This clause tests that the D–A implementation, using the published
AX-21 parameters, reproduces that physical range and behaves correctly with coverage.

PASS requires all three:
  (1) Anchor band. q_st evaluated across n/n_max ∈ [0.05, 0.15] lies within
      [4.0, 7.0] kJ/mol. Reference point n/n_max = 0.10.
  (2) Monotonic decrease. q_st decreases monotonically in n over the evaluated
      window (strong sites fill first).
  (3) Analytic agreement. Numerical q_st matches the closed-form D–A limit
      q_st = alpha·sqrt(ln(n_max/n)) to ≤ 1e-4 relative at n/n_max = 0.10.

Evaluation temperature: 77 K (q_st is T-independent in this model; 77 K matches
the digitized isotherm).

Note (limitation): the D–A form gives q_st → ∞ as n → 0 (sqrt-ln divergence), an
artifact of the functional form, not physical. The anchor is therefore evaluated at
finite low coverage, and F3 is plotted over n/n_max ∈ [0.02, 0.60]. Feeds §3.13.

Verdict: PASS (2026-08-10). Numerical q_st across the pre-registered window
n/n_max ∈ [0.05, 0.15] at 77 K: 5.33, 4.67, 4.24 kJ/mol — all inside [4.0, 7.0].
Monotonically decreasing in n. Numerical matches the analytic D–A limit
q_st = alpha·sqrt(ln(n_max/n)) to ~1e-15 relative (machine precision), consistent
with ln P being exactly affine in 1/T at fixed coverage for this model. F3
(figures/F3_isosteric_heat.png) shows numerical and analytic curves coincident and
the anchor window within the 4–7 kJ/mol carbon band. The √ln rise toward zero
coverage is a D–A functional-form artifact (not a physical zero-coverage heat);
anchor evaluated at finite low coverage, divergence noted as a limitation (§3.13).

Gate V2 — overall status (2026-08-10): CLOSED.
  Part 1 (curve, excess-RMSE < 1.5 mol/kg): PASS, 1.109 mol/kg (Day 7).
  Part 2 (single-isotherm parameter recovery): FAIL by design — likelihood ridge /
    practical non-identifiability, diagnosed Day 8; the curve is identifiable, the
    individual parameters are not.
  Part 3 (isosteric heat): PASS (this entry).