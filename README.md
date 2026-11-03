# h2star

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23257816.svg)](https://doi.org/10.5281/zenodo.23257816)

**An open, tested materials-to-system model for cryo-adsorbent hydrogen
storage, with an identifiability analysis of the modified Dubinin–Astakhov
isotherm and system requirements stated in observable quantities.**

Version 1.0.0. The analysis plan, validation gates, tolerances and
calibration/validation split were externally pre-registered before the gate
code existed (Zenodo record
[10.5281/zenodo.23931242](https://doi.org/10.5281/zenodo.23931242)); the gate
outcomes, including one pre-registered FAIL and its consequences, are
recorded in `docs/validation_plan.md`.

## What this repository contains

`h2star` is a Python package that translates measured adsorption properties
of a sorbent into the gravimetric and volumetric capacity of a complete
onboard hydrogen storage system — real-gas hydrogen thermodynamics (CoolProp,
NIST-validated wrapper), the modified Dubinin–Astakhov (D–A) isotherm with
excess/absolute bookkeeping, isosteric heats, and a component-resolved
engineering model (composite or aluminium vessel, liner, MLI, outer shell,
internal heat-exchanger structure, supports, component-class balance of
plant), calibrated on one published HSECoE system and tested out-of-sample on
others. On top of that sit an error-model-weighted fitting and profile-
likelihood layer, an MCMC posterior, Shapley-effect sensitivity analysis for
dependent inputs, and requirement maps drawn in observable axes.

This is a model validated against published data and published models. It is
not a hardware demonstration.

## Findings

**1. Single-isotherm practical non-identifiability.** Fitting the modified
D–A model to the one 77 K AX-21 excess isotherm of the kind the literature
routinely publishes leaves the parameter vector loose: the 95% profile-
likelihood region spans n_max 37–142 mol/kg and more than four decades of
pseudo-saturation pressure, and the temperature coefficient β is wholly
undetermined. Fitting seven temperatures (60–298 K) jointly pins the same
parameters to about ±1% (n_max 61.2–62.6 mol/kg). The underlying degeneracy
at a single temperature follows from ε = α + βT and is visible in the source
data's own published alternative fits (Richard, Bénard & Chahine 2009,
Table 3); the contribution here is its quantification by profile likelihood
with an explicit measurement-error model, and the measurement of how much
identifiability each added temperature restores.

**2. Loose parameters, tight predictions.** Across the full 77 K profile
region — a 3.8× range in n_max — the predicted usable system capacity at the
baseline envelope varies by only ±2.4% (volumetric: ±3.0%). The model is sloppy in the
sense of Gutenkunst et al. (2007): the Fisher-information eigenvalue spectrum
spans many decades. A requirement stated as "n_max = X at fixed α, β, P0" is
therefore conditional on an arbitrary point along a ridge the data do not
resolve.

**3. Requirements belong in observables.** The requirement maps here use
deliverable uptake between the stated full and empty states, together with
packing density, as axes — quantities a laboratory can measure without
inverting an isotherm model — following the practice of the HSECoE Adsorbent
Acceptability Envelope (Hardy, Tamburello & Corgnale 2018) and Argonne's
Level-1 sorbent targets (Ahluwalia, Peng & Hua 2015). The map is drawn under
two independent engineering models, and the shift between them is reported
rather than hidden.

**4. The engineering block is the dominant uncertainty.** With the material
parameters sampled from their joint posterior, Shapley effects attribute most
of the variance of predicted system capacity to engineering inputs (internal
heat-exchanger structure, MLI conductivity, heat-leak budget, balance of
plant), not to material-parameter uncertainty. Design-leverage elasticities
are reported separately from variance attribution.

**5. A pre-registered held-out gate failed, and the paper's claims follow the
pre-registered fork.** The component-resolved engineering model, calibrated
to +0.0% mass / −0.7% volume on the HSECoE HexCell system, was evaluated once
against frozen held-out targets: it matched the 60 bar/40 K AX-21 system to
−0.2% in mass and passed the 200-bar volumetric check (+5.8%), but predicted
200-bar gravimetric capacity 41% above the anchor midpoint, outside the
pre-registered ±20% band (the anchor family itself drifts 21% across HSECoE
report years). Per the fork rule frozen in the pre-registration, no absolute
system-capacity claim is made anywhere in this project; relative statements
appear only where shown robust under two independent engineering models.

## DOE targets used

U.S. DRIVE Target Explanation Document (May 2017), system-level usable
capacities, end of life — Ultimate: 0.065 kg H2/kg system and 0.050 kg/L;
2025: 0.055 and 0.040; 2020: 0.045 and 0.030. Delivery pressure 5–12 bar;
delivery temperature −40 to 85 °C.

## Quickstart

```bash
git clone https://github.com/AvinGupta-ship-it/h2star
cd h2star
python3 -m pip install -e ".[dev]"
python3 -m pytest -q                      # full suite incl. validation gates
python3 scripts/make_figures_v1.py        # rebuild every figure
python3 scripts/run_identifiability.py    # S5 analysis record
```

The archival environment is pinned in `requirements-lock.txt`.

## Data and provenance

Every number in `data/` carries a citation. The multi-temperature AX-21
dataset (`data/validation/ax21_fig1a_multiT.csv`) was digitized from Richard,
Bénard & Chahine, *Adsorption* 15 (2009) 43–51, Fig. 1a by two independent
routes (one visual, one scripted template-matching), reconciled under a rule
frozen before either output was read, with per-point uncertainties and the
axis resolution recorded (`..._reconciliation.md`). The SWCNT dataset from
Panella, Hirscher & Roth, *Carbon* 43 (2005) Fig. 2b was produced the same
way; because it reconciles to five 77 K points against a pre-registered
eight-point floor, the CNT case study appears only as a documented notebook
example, consistent with the established literature result that CNTs do not
exceed high-surface-area activated carbon (Tibbetts et al. 2001; Panella et
al. 2005; Zhou, Zhou & Sun 2004).

H2STAR is the companion model to
[HyCAN-DB](https://doi.org/10.5281/zenodo.23231985), an open corpus of
hydrogen-uptake measurements on carbon materials: the database curates what
is knowable from the literature, and this model converts it into system-level
meaning.

## Validation record

| Gate | Definition | Outcome |
|---|---|---|
| V1 (v0.2) | EOS wrapper vs NIST tables | PASS (4.99e-5 max rel.) |
| V2.1 (v0.2) | isotherm curve RMSE | PASS |
| V2.2 (v0.2) | parameter recovery, single isotherm | FAIL (pre-registered recovery bands not met) — superseded by the v1.0 profile-likelihood analysis |
| V3 (v0.2) | lumped system model vs HSECoE anchor | FAIL (documented) — superseded by E1/E2 |
| E1 (v1.0) | component-model calibration, HexCell | criterion met (+0.0% mass, −0.7% volume) |
| E2 (v1.0) | held-out AX-21 systems, frozen tolerances | **FAIL on H1 (+41% GC at 200 bar); 3 of 4 pass; fork rule in force** |

All v0.2 adjudications stand as records; `docs/validation_plan.md` carries
every block verbatim, including deviations (pre-registration §9).

## AI involvement

This project was built with substantial AI assistance (Anthropic Claude)
under the project's execution manual: implementation, analysis,
derivational reasoning, figure generation and documentation prose, with the
author verifying load-bearing inputs against primary sources, ratifying
every pre-registered decision, and holding the final scientific sign-off on
all claims. The contemporaneous record is `docs/ai_usage_log.md`; the
pre-registration and its deviation table are external and citable
(10.5281/zenodo.23931242). Commits are authored by the repository owner,
who is responsible for every line.

## Citation

See `CITATION.cff`. Cite the concept DOI
[10.5281/zenodo.23257816](https://doi.org/10.5281/zenodo.23257816) for the
software; the paper preprint cites the v1.0.0 version DOI.

## License

MIT.
