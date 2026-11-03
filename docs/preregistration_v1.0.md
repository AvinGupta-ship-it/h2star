# H2STAR v1.0 — Pre-registration of gates, tolerances, calibration/validation split, and analysis plan

Author: Avin Gupta (ORCID 0009-0009-4133-2275)
Date frozen: 2026-11-03
Repository: https://github.com/AvinGupta-ship-it/h2star, frozen against the v0.2.0 baseline `42f29a1`.
External timestamp: this document is deposited on Zenodo as its own record before any code
implementing the gates below is committed or run. The Zenodo DOI, once minted, is added to this
header by a dated amendment commit that changes nothing else.

Status of this document: FROZEN at deposit. Amendments after deposit are permitted only as dated
commits that preserve the original text as SUPERSEDED, state the reason, and land before the code
for the affected gate has run. A documented FAIL is a valid result. No tolerance in this document
is edited after the corresponding gate has run.

---

## 1. Scope and relationship to v0.2.0

The v0.2.0 gates (V1–V4) and their adjudications are historical record and are not re-opened:
Gate V2.2 (parameter recovery) and Gate V3 (system anchor) stand as documented FAILs against their
own pre-registrations. The 2026-10-27 adversarial review found the v0.2.0 claims C1–C5
unsupportable; the v1.0 rebuild replaces them. This document freezes, before implementation,
everything in the v1.0 rebuild that could otherwise be tuned to pass: the engineering
calibration/validation split, the held-out gate and its tolerances, the fork rule, the data
(digitization) protocol, the identifiability and uncertainty-quantification analysis plans, the
case-study decision rule, and the disclosure of every known v0.2 deviation (§9).

## 2. Verified inputs this plan builds on

All anchor values below were read from the primary artifacts (the cited PDFs) in this session and
confirmed against the sources by the author on 2026-11-03. The ledger with full context is
`docs/history/verified_values.md` (committed alongside this document).

- DOE/U.S. DRIVE system targets (Target Explanation Document, May 2017): gravimetric
  0.045/0.055/0.065 kg H2 per kg system and volumetric 0.030/0.040/0.050 kg H2/L for
  2020/2025/Ultimate; capacities are usable, end-of-life; delivery 5–12 bar; delivery
  temperature −40 to 85 °C.
- Richard, Bénard & Chahine, Adsorption 15 (2009) 43–51 (DOI 10.1007/s10450-009-9149-x, printed on
  the paper), Table 3: AX-21 modified D–A global fit n_max 71.6 mol/kg, P0 1470 MPa, α 3080 J/mol,
  β 18.9 J/(mol·K), Va 1.43e-3 m³/kg; reduced (77+298 K) fit 65.4 / 1090 / 3310 / 16.8 / 1.38e-3.
  Fig. 1a: H2/AX-21 excess isotherms at 30, 35, 40, 45, 60, 77, 93, 113, 153, 213, 298 K, 0–6 MPa
  (data of Bénard & Chahine, Langmuir 17 (2001) 1950–1955, which tabulates no numeric isotherms).
- HSECoE anchors:
  - FY2011 APR ch. IV.D.1 Table 1, adsorbent column: 0.039 kg/kg, 0.024 kg/L (AX-21, Type III,
    200 bar, 80 K, 5 W heat leak).
  - DOE AMR ST044-2012 slide 17 row A (activated carbon, composite tank, full 80 K/200 bar):
    0.03665 kg/kg, 0.02265 kg/L. Slide 12 (full 60 bar/40 K, empty ~5 bar/100–120 K), carbon row:
    m_sys 99.8 kg, V_sys 206.6 L (tank type not labelled on the slide for this row).
  - DOE AMR ST044-2013 slide 18 "End of Phase 1 Baseline" (activated carbon, Type 3 tank, full
    80 K/200 bar per slide 19): 0.0312 kg/kg and 0.0194 kg/L (the slide prints "gH2/Lsys", a
    dimensionally impossible unit read as kg/L, consistent with the FY2011/2012 values).
  - DOE AMR ST044-2013 slide 27: component-resolved tank breakdown of the powder-MOF-5 HexCell
    Type-1 system (4.4:1 L/D, 100 bar/80 K): pressure vessel 62.45 kg / 23.45 L; LN2 channel
    19.24 kg / 16.42 L; insulation 8.01 kg / 67.84 L; outer shell 15.35 kg / 5.77 L;
    boss/plug/support rings 1.28 kg; tank-only totals 106.33 kg / 303.36 L; with full geometry.
- Purewal et al., IJHE 44 (2019) 15135–15145 (10.1016/j.ijhydene.2019.04.082): the full-scale
  5.6-kg-usable type-1 MOF-5 system (100 bar/80 K → 5.5 bar/160 K) whose model details are
  Tamburello et al., FEDSM2017-69411 (SRNL-STI-2017-00079).
- Ahluwalia & Peng, IJHE 34 (2009) 5476–5487 (10.1016/j.ijhydene.2009.05.023): netting-analysis
  vessel sizing, MLVSI properties, component inventory, dormancy/vent model for a cryo-adsorption
  AX-21 system.
- Ahluwalia, Peng & Hua, IJHE 40 (2015) 6373–6390 (10.1016/j.ijhydene.2015.03.025), Table 9:
  Argonne Level-1 sorbent targets (excess 120 g-H2/kg at 100 bar/155 K; peak 77 K excess
  190 g/kg; bulk density 420 kg/m³; E1 5–7.5 kJ/mol).

Known anchor limitation, disclosed and folded into the §4 tolerances: the HSECoE AX-21 baseline
moved between reports (0.039 → 0.03665 → 0.0312 kg/kg for the same nominal 80 K/200 bar
composite-tank configuration; 21% relative span), the 2012/2013 slides do not state the usable vs
full-inventory basis of their capacities (arithmetic consistency with a 5.6-kg usable basis
suggests usable), and the slide-12 carbon row's tank type is unlabelled.

## 3. Engineering model: calibration (E1)

The v1.0 engineering block models system mass and volume component by component:
- composite overwrap sized by netting analysis (geodesic/helical plus hoop plies, domes, bosses),
  with pressure- and radius-dependent liner;
- vacuum shell and MLI (MLVSI properties from Ahluwalia & Peng 2009), sized against a declared
  heat-leak budget at a declared worst-case ambient of 60 °C;
- LN2 cooling channel where the reference design has one (type-1 designs);
- internal heat exchanger and support structure;
- balance of plant resolved into named components, each with mass and volume;
- design pressure set by dormancy/venting: P_design = 1.25 × P_full (vent set-point practice of
  Ahluwalia & Peng 2009), applied to vessel sizing;
- usable-capacity physics: heater energy for the thermal swing computed and reported (electric
  resistance heating per the reference designs consumes no onboard H2; an H2-fuelled variant, if
  ever modelled, subtracts its H2 from usable), and delivered-gas warming to −40 °C provided by a
  BOP heat-exchanger component with mass and volume.

Correlations and component values come only from the independent published sources named in §2.
**Calibration case:** the HSECoE powder-MOF-5 HexCell type-1 system (Tamburello 2017 /
Purewal 2019 / ST044-2013 slides 17 and 27), at 100 bar/80 K full, 5.5 bar/160 K empty, sized to
5.6 kg usable, using the HSECoE MOF-5 modified-D–A parameter set of ST044-2013 slide 10.
Calibration means: free scalar factors, at most three, each named, bounded, and physically
interpretable (anticipated: a BOP mass scale, a support/mounting mass term, a packaging/void
volume factor), chosen to reproduce the slide-27 component masses and volumes. Everything else is
fixed by the sources. Calibration quality is disclosed as per-component residuals; if the
calibrated model cannot reproduce the calibration case's tank-only mass and volume within ±10%
with the factors in bounds, that is reported as a calibration shortfall and §4 still proceeds
unchanged.

After E1 the model is frozen for §4: no parameter, correlation, or factor is changed between the
calibration fit and the held-out evaluations.

## 4. Gate E2 — held-out validation (pass/fail)

Honesty statement: the held-out anchor values are public and known to the author and to the
AI system implementing the model, so this is not a blind test. It is a pre-committed out-of-sample
test: the calibration case (a MOF-5 type-1 100-bar system) is disjoint from the held-out cases
(AX-21 type-3 200-bar and 60-bar/40-K systems), no quantity below is used in any fitting step, the
acceptance bands are fixed in this document before the model exists in code, and the gate is run
once and adjudicated.

Held-out predictions, all with the model exactly as frozen at E1, each system sized to 5.6 kg
usable at its stated envelope, capacities on the usable basis (usable H2 divided by total system
mass and by total system external volume), AX-21 represented by the Richard global parameter set
with ρ_bulk 300 kg/m³ and ρ_skel 2300 kg/m³ (Bénard & Chahine 2001; Ahluwalia & Peng 2009); the
MaxSorb/AX-21 labelling of the 2012 slide is treated as AX-21 and disclosed:

- H1/H2 (primary, binding): AX-21, Type-3 composite vessel, full 200 bar/80 K, empty 5 bar/160 K.
  Target values: the midpoint of the 2012 and 2013 anchors, GC* = 0.0339 kg/kg and
  VC* = 0.0210 kg/L.
  **PASS requires |GC_pred/GC* − 1| ≤ 0.20 and |VC_pred/VC* − 1| ≤ 0.20.**
  Tolerance basis: the two anchors sit ±8% about their midpoint; the unstated anchor basis
  (usable vs full) is worth ≲10% at this envelope; media labelling adds residual uncertainty.
- H3 (secondary, binding with disclosed ambiguity): AX-21, Type-1 aluminium vessel (the slide-12
  design narrative), full 60 bar/40 K, empty 5 bar/110 K (midpoint of the slide's 100–120 K).
  Targets: m_sys = 99.8 kg and V_sys = 206.6 L.
  **PASS requires |m_pred/99.8 − 1| ≤ 0.25 and |V_pred/206.6 − 1| ≤ 0.25.**

**Gate E2 passes iff all four comparisons pass.** The adjudication (all four ratios, pass or fail)
is committed verbatim to `docs/validation_plan.md` v1.0 with this document cited.

**Fork rule (frozen):** if Gate E2 fails, the paper drops every claim that uses an absolute system
capacity. It keeps the material-level and identifiability results, and it keeps relative
(between-material or between-envelope) claims only if they are demonstrated robust under at least
two independent engineering models (the rebuilt model and a second, independently parameterized
one), reported in the supplement. Gate E2's FAIL is reported either way.

Secondary, non-binding cross-checks reported with E2 (no pass/fail): the FY2011 0.039/0.024 and
the individual 2012/2013 anchors; the MOF-5 rows of ST044-2012 slide 12 (87.3 kg/182.7 L aluminium
and 74.6 kg/180.6 L composite) using the slide-10 MOF-5 parameters; and the vessel model's
performance-factor cross-check evaluated at both 100 and 200 bar.

## 5. Data protocol: digitization of Richard Fig. 1a (all isotherms)

Two independent digitization routes were launched on 2026-11-03, before this freeze, and neither
route's output has been read, reconciled, or used in any fit at freeze time:
Route A, visual marker reading by an isolated agent; Route B, scripted template-matching
extraction by a second isolated agent; each sees only the 600-dpi figure crop and its own working
directory.

Frozen reconciliation rule, applied after deposit: per isotherm, points are matched across routes
by nearest pressure; a matched pair agreeing within twice the larger route's stated per-point
resolution in both coordinates is reconciled to the coordinate-wise mean; disagreeing pairs and
unmatched points are re-inspected against the figure once, and kept only if a marker is
unambiguously present, with the larger route deviation recorded as their uncertainty; points
neither route resolves (dense overlap below ~0.5 MPa for the 30–45 K isotherms is expected) are
excluded with their count reported. The published dataset records, per point: both route readings,
the reconciled value, the uncertainty (at least the axis resolution, in both P and n), and a
quality flag. The digitization resolution (MPa per pixel, mol/kg per pixel) is stated in the data
file and in every figure that uses the data.

## 6. Identifiability analysis plan (frozen)

- Primary fit set: the supercritical isotherms 60–298 K (seven temperatures). The subcritical
  30–45 K isotherms are excluded from the primary fit and used only in a labelled sensitivity.
- Measurement-error model: per-point Gaussian with effective variance
  σ_eff² = σ_n² + (∂n_model/∂P)²·σ_P², with σ_n and σ_P from the §5 reconciled uncertainties
  (never below the axis resolution). The weighted residual sum of squares under this model is the
  objective for all fits and profiles.
- Parameters and bounds: n_max ∈ (0, 300] mol/kg; α ∈ (0, 20000] J/mol; β ∈ [0, 50] J/(mol·K);
  log10(P0/Pa) ∈ [6.78, 12] — the lower bound is the data maximum (6 MPa), the physical
  requirement that the pseudo-saturation pressure exceed the fitted range; sensitivity of the
  conclusions to removing this bound is reported; v_a ∈ [1e-5, 5e-3] m³/kg.
- Profile likelihood for every parameter (Raue et al. 2009), 95% threshold Δ(objective) = 3.84 on
  the weighted objective; single-isotherm (77 K) profiles computed alongside the multi-temperature
  profiles to quantify how much identifiability the added temperatures restore.
- Fisher information eigenvalue spectrum at the optimum (Gutenkunst et al. 2007), reported in
  log-parameter coordinates.
- Propagation: the 95% profile (or posterior, §7) region is pushed through the frozen engineering
  model at the baseline envelope; the induced range of usable GC and VC is a headline result.
- Raw cond(JᵀJ) in native units is never cited as evidence; any conditioning number reported is
  computed on relative (log-parameter) scaling with its scaling stated.

## 7. Uncertainty quantification and sensitivity plan (frozen)

- Posterior: MCMC on the §6 objective with the §6 bounds as uniform priors; effective sample size
  ≥ 10,000 for every reported distribution; convergence shown by split-half agreement of every
  reported quantile and, where applicable, R̂ < 1.01. A Laplace approximation may be reported only
  alongside, and checked against, the MCMC.
- Conditionality rule: wherever a map, band, or table fixes parameters on its axes, sampled
  quantities are drawn conditionally on the fixed values, or no probability band is shown; the
  sampling scheme is stated in every caption.
- Attribution on dependent inputs: Shapley effects (Song, Nelson & Staum 2016) or Kucherenko
  indices on the joint (material × engineering) input distribution; independence-assuming Sobol
  boxes are not used for any reported ranking. Design leverage is reported separately as
  normalized local elasticities ∂ln(GC)/∂ln(x) at the nominal point, never conflated with
  variance shares.
- Input set (minimum): material parameter posterior including β; isotherm model form (modified
  D–A with m = 2, free-m D–A, and Tóth — the Tóth comparison also discharges the manual §2.9
  promise); an omitted-component model-error term calibrated from the E1 residuals; envelope
  inputs T_empty and P_empty; every engineering input, each with a cited justification recorded in
  `data/uncertainty.yaml` before any propagation run.
- The 298 K ambient configuration appears only as a labelled supplementary contrast with its tank
  volume stated, unless a vehicle-relevant ambient design is introduced and justified.
- Requirement maps are stated in identifiable observables — deliverable material-level uptake
  between the full and empty states, and packing density — with any modified-D–A-parameter version
  presented only as a conditional illustration. No "physical coherence" bound derived from fit
  covariance is used; any physical bound uses literature micropore-volume and adsorbed-phase-
  density limits applied identically to map and screen.

## 8. CNT case-study decision rule (frozen)

The CNT case study appears in the paper iff all of: (a) the Panella et al. 2005 (Carbon 43, 2209;
HyCAN-DB HYC-0001) 77 K high-pressure CNT isotherm(s) are digitized under the §5 dual protocol at
eight or more reconciled points; (b) every corpus entry used passes, or is explicitly flagged by,
a Chahine-rule surface-area consistency check; (c) results are reported on both the excess and
absolute bases wherever a ratio to AX-21 appears. Otherwise the case study is dropped from the
paper and kept only as a documented notebook example. In either case it is presented as agreement
with prior literature (Tibbetts 2001; Panella 2005; Zhou et al. 2004), with no validation claim
for the inverse framework, and the qikun2002 wording and F8 labelling errors of v0.2 are corrected.

## 9. v0.2.0 deviation table (disclosure)

| # | Pre-registered (v0.2) | What was done | Disclosed at the time? |
|---|---|---|---|
| 1 | UQ Monte Carlo N ≥ 10,000 per reported distribution | Gate V4.3 run and declared PASS at N = 600 and N = 2000; notebook 07 used n = 2000 | No |
| 2 | C5/F6 material sampling "jointly from the multivariate normal" | Published F6 and C5 used marginal sampling (`conditional=False`); the reason lived only in a code comment | No |
| 3 | Gate V3 basis: original MOF-5 usable-swing pre-registration | Amended 2026-08-19 (dated, pre-code — a compliant amendment) to AX-21 full-state inventory; the anchors themselves are most consistent with a usable basis, so the comparison basis remained questionable | Amendment yes; basis question no |
| 4 | Vessel two-estimate cross-check, ±30% band | After a 31% miss the band was widened to ±35% and the liner areal mass cut 7× (700→100 bar scaling) | Partially (journal/log entries) |
| 5 | Pre-registration as external evidence | All v0.2 gates were declared and closed same-day in AI-run work; the only record is the repository's own git history | N/A — structural weakness, remedied by this external deposit |

## 10. Process rules

- This document is deposited on Zenodo (Avin Gupta's account) before any commit implementing §3,
  §4, §6, §7 or §8 code. The deposit is irreversible; the DOI is cited in the paper.
- Each gate is run once against its frozen criteria and adjudicated in `docs/validation_plan.md`
  v1.0, PASS or FAIL verbatim, with the commit hash of the run.
- No gate tolerance, target value, split, or decision rule above is modified after its gate's code
  has run. Pre-run amendments follow the dated-SUPERSEDED rule in the header.
- Every headline number is re-derived by an isolated agent from the repository before it is relied
  on; a fresh adversarial referee reviews the finished repository and manuscript without access to
  this project's internal notes.
