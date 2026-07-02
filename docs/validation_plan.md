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
   Target: my system GC and VC reproduce the published MOF-5 cryo-adsorbent system (HSECoE/NREL).
   Envelope: fill 77 K / 100 bar, discharge 160 K / 5 bar; 5.6 kg usable H2 basis.
   Pass: |my GC - published GC| / published GC <= 15%  AND  the same for VC.
   Rationale: system models legitimately differ in balance-of-plant detail; 15% is the agreement band.

  ## Gate V4 — Uncertainty & sensitivity machinery
   Target 1: Monte Carlo reproduces an analytic linear-Gaussian propagation within Monte Carlo error.
   Target 2: Sobol indices on the Ishigami test function match published values within 5%.