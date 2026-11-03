# Known limitations (v1.0)

Scope statement, binding: H2STAR is a state-point equilibrium model validated
against published data and published models. It is not a hardware
demonstration. The v0.2.0 edition of this file is preserved in the git
history; this edition is organized around what the v1.0 analyses actually
establish and what they do not.

## 1. The held-out engineering gate failed, and every absolute capacity is conditional

The component-resolved engineering model was calibrated on one published
HSECoE system and evaluated once against frozen held-out targets
(pre-registration 10.5281/zenodo.23931242 §4). Three of four comparisons
passed; the 200-bar type-3 gravimetric prediction missed by +41% against a
±20% band (full record in `docs/validation_plan.md`). Consequences, applied
throughout:

- No absolute system GC or VC is claimed anywhere in this project.
- Relative statements beyond monotone orderings appear only with the
  two-model robustness demonstration (the observable-axis map is drawn under
  both the v1.0 and the superseded v0.2 engineering models, and the boundary
  shift is shown, not absorbed). The two models are structurally different
  (netting vs hoop-only sizing, component-resolved vs lumped, different
  ambient temperatures) but share several source anchors — the ST001 MLI
  properties and BOP anchor, the T700S fibre class — so they are NOT
  independently parameterized in the source sense, and the displayed
  two-model shift is a lower bound on engineering-model dependence. A
  genuinely independent published second model is future work.
- The AX-21 D–A parameter set is evaluated at 200 bar (20 MPa) in the E2
  H1/H2 systems — 3.3× beyond the 0–6 MPa range of the data it was fitted
  to (ax21.yaml valid_range). The HSECoE anchors themselves model 200 bar,
  so the comparison is like-for-like in that respect, but the extrapolation
  was previously undisclosed and belongs here: it is a further uncertainty
  the 200-bar comparisons carry that the 60-bar case does not (the
  mass-sided failure pattern and the volumetric pass still localize the
  dominant miss to the composite mass accounting).
- The anchor family itself is part of the uncertainty: the HSECoE AX-21
  baseline moved 21% across report years (0.039 → 0.03665 → 0.0312 kg/kg for
  the same nominal configuration), the 2012/2013 slides do not state their
  capacity basis, and the 60 bar/40 K case's tank type is unlabelled on its
  slide. These are disclosed where used; they do not excuse the FAIL.
- Candidate physical causes of the mass-side miss, for future work: boss
  build-up, doilies and protective layers absent from pure netting sizing;
  possible non-structural masses inside the anchor's accounting. The
  volumetric agreement (VC ratios 0.93–1.15 across anchors) and the exact
  60 bar/40 K mass agreement bound the problem to the high-pressure
  composite mass accounting.
- A post-adjudication audit found the BOP interpolation's 16 kg anchor
  mis-attributed to a 100-bar system (its source states it, with a 10 L
  volume, as a fixed assumption of a 150-atm-storage analysis). The gate
  record stands as adjudicated; re-anchoring at the source's own pressures
  moves the failed comparison between +37% and +51% and flips no verdict
  (`data/analysis/bop_anchor_sensitivity.json`; correction record in
  `docs/validation_plan.md`). The BOP pressure law itself — two
  component-class points, linear — is the weakest-sourced part of the model
  either way, and its declared uncertainty is carried in the UQ.

## 2. What the identifiability result is, and is not

Established: PRACTICAL non-identifiability of the modified D–A parameter
vector from a single 77 K excess isotherm of ordinary literature quality
(95% profile region: n_max 37–142 mol/kg; log10 P0 unbounded above within
[6.78, 12]; β undetermined at one temperature by construction), together
with its quantitative repair by multi-temperature fitting (n_max 61.2–62.6
at seven temperatures). Three conditionality statements that must travel
with those intervals: (i) the 77 K n_max interval endpoints are conditional
on the frozen log10 P0 ≤ 12 bound — raising the bound to 14 widens 37–142
to 38–263 (sens_77K_upper_bound_14 in the analysis record), which
strengthens, not weakens, the non-identifiability conclusion; (ii) the
multi-temperature ±1.2% is WITHIN-MODEL precision under m = 2 and the
supercritical fit set — the model-form/fit-set spread (free-m 54.4, with
35–45 K 69.2, source global 71.6) is ±13% and dominates; (iii) the
s2-inflated intervals (±2%) are the decisive ones given the
overdispersion of section 3. Not established and not claimed: structural
non-identifiability of the D–A model; novelty of the degeneracy itself
(ε = α + βT makes the single-T α–β trade exact, and the source paper's own
Table 3 shows alternative parameter sets fitting comparably).

The α–β degeneracy means the single-isotherm profile intervals for α alone
are conditional on the β bound; the identifiable single-T combination is
E(77) = α + 77β.

## 3. Digitized data, and the residual misspecification

The multi-temperature dataset is figure-digitized (dual independent routes,
reconciled under a frozen rule, per-point uncertainties floored at the pixel
size: 0.0049 MPa, 0.062 mol/kg). Two Henry-region points sit within one
pixel of the pressure axis and are recorded at the half-pixel bound with
matching uncertainty; the errors-in-P model discounts them accordingly —
the v0.2 headline's dependence on three sub-pixel points cannot recur by
construction. Even so, the weighted residuals are overdispersed
(objective/dof = 3.33): the m = 2 D–A form is the dominant residual error
(free-m fit prefers m = 2.65), so the frozen profile threshold and the
s²-inflated threshold are both reported, and no interval narrower than the
inflated one is treated as decisive. The 30 K isotherm lies below the EOS
validity floor (33.2 K) and enters no fit.

## 4. UQ scope

The posterior covers the five isotherm parameters under the stated error
model; model-form uncertainty enters as the three-form comparison (m = 2,
free-m, Tóth), not as a posterior over forms. The engineering input
distributions are declared ranges with cited bases
(`data/uncertainty_v1.yaml`), several resting on single data (the internal-
HX fraction; the assigned 100-bar BOP volume anchor) with correspondingly
wide bands — and the Shapley analysis says precisely these dominate the
output variance, which is the finding, not a defect to hide. The
omitted-component model-error term is calibrated from the E1 residuals
(0–6%) per the frozen plan; it does NOT cover the E2 miss, which is handled
by the fork rule, not by inflation after the fact.

## 5. Physics out of scope

Charging/discharging dynamics and spatial gradients (state-point,
uniform-bed model); ortho/para conversion kinetics (density contrast
reported as a sensitivity only); cost; cycle life, purity, and the other
non-capacity DOE targets. The heater energy, delivery-warming duty and a
dormancy lower bound are computed as reported metrics under A-USE-1..3 in
`data/analysis/supplementary_metrics_v1.json`
(`scripts/run_supplementary_metrics.py`), not validated against hardware;
the heater metric carries the sorbent heat capacity as a declared 0.2--1.0
J/(g K) range because no verified cryogenic cp is held for either sorbent
(the only verified anchor is Ming et al. 2014's MOF-5 powder 0.72 J/(g K)
at 300 K).

## 6. CNT evidence

The only traceable 77 K high-pressure CNT isotherm in the corpus reconciles
to five points — below the pre-registered eight-point floor — so no CNT
system-level claim is made; the notebook example is presented as consistency
with the established literature (Tibbetts 2001; Panella 2005; Zhou 2004).
The v0.2 CNT case study, its screen, its F8 waterfall and the "strongest
validation" language are withdrawn in full.

## 7. Reproducibility boundaries

Figure BYTES depend on the FreeType build, not only on library versions
(observed directly: identical matplotlib/FreeType/Pillow versions, different
builds, different bytes). v1.0 figure tests therefore compare figure DATA;
byte-level reproduction is scoped to the locked CI environment
(`requirements-lock.txt`). The MCMC and Shapley records carry fixed seeds;
the Shapley estimator's sampling error is reported per player.
