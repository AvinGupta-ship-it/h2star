# Assumptions

Each assumption carries one sentence of justification and one on what changes if it is relaxed (§3.3).

## Isotherm layer (added Week 2, Day 1)

### A-ISO-1: Modified Dubinin–Astakhov describes absolute adsorption over the full envelope
The modified D–A form is the established description of supercritical hydrogen adsorption on activated carbons and fits AX-21 across 30–293 K in the source paper, so I adopt it as the isotherm model over my whole envelope. If relaxed: the v1.0 model-form study fits the same multi-temperature data with a free-m D-A form (best fit m = 2.65, objective 313.6 vs 379.7 for m = 2) and a Toth form (objective 2880.8, clearly inferior); the m = 2 restriction is the dominant residual misspecification and is carried in the reported overdispersion, not ignored.

### A-ISO-2: n_max and v_a are temperature-independent
I treat the limiting loading n_max and adsorbed-phase volume v_a as constants, consistent with the D–A treatment where temperature dependence is carried entirely by E = α+βT, which keeps the parameter set to five. If relaxed: a temperature-dependent v_a would shift the excess conversion most at high density (deep cryo, high P), where the ρ_molar·v_a subtraction is largest, slightly moving the excess maximum.

### A-ISO-3: Normal hydrogen for the gas-phase density in the excess conversion
The molar density in n_exc = n_abs − ρ_molar·v_a is evaluated for normal hydrogen, matching the EOS layer validated in Gate V1, so conversion and density validation use one consistent fluid. If relaxed: at deep cryogenic temperatures the equilibrium para-fraction rises and para-hydrogen is denser, raising the subtracted term and slightly lowering predicted excess near 77 K; I treat this as a bounded sensitivity check with CoolProp's parahydrogen fluid rather than modeling conversion kinetics.

### A-ISO-4: v_a is a fitted parameter (v1.0 correction)
The v0.2 text of this assumption ("v_a estimated as n_max x liquid-H2 molar
volume") contradicted the reference material's own fitted value (2.0e-5
m^3/mol per n_max against the liquid 2.845e-5) and fed the "edge of physical
coherence" construct the 2026-10-27 review rejected (M8); both are
withdrawn. In v1.0, v_a is simply the fifth fitted parameter, bounded
[1e-5, 5e-3] m^3/kg, and no physical-coherence screen derived from fit
covariance exists anywhere in the project.

## EOS layer (v1.0)

### A-EOS-1: Normal hydrogen throughout; validity floor at 33.2 K
All gas densities use the Leachman normal-H2 reference EOS; calls below
33.2 K are rejected, which excludes the 30 K isotherm from every fit. If
relaxed: para-enriched hydrogen at deep cryo is denser; the para/normal
density difference at the envelope states is computed and reported with the
model-form sensitivities rather than modelled kinetically.

## Engineering layer (v1.0; data/engineering_v1.yaml carries per-value sources)

### A-ENG-1: Capsule geometry with hemispherical caps, LR = 4 (L/D = 2)
From the calibration source's own convention (exact wall-thickness back-out).
If relaxed: the LR sensitivity is quantified in the elasticity table
(|d ln GC / d ln LR| small); the type-3 family's LR is unpublished and this
is disclosed with the gate record.

### A-ENG-2: Netting analysis sizes the composite; domes carry helical plies
Total cylinder thickness 1.5 P r / sigma is angle-independent (tested);
boss build-up, doilies and external protective layers are NOT modelled, and
the E2 FAIL records that a pure netting wall is substantially lighter than
the HSECoE Phase-1 baseline implies.

### A-ENG-3: Design pressure = 1.25 x P_full, SF re-expressed
Vent set-point practice of the sources; sizing numerically equals each
source's own practice. If relaxed: sizing scales linearly with the product
SF_eff * vent_ratio; any alternative is a disclosed re-scaling.

### A-ENG-4: Fixed-thickness liner and shell; MLI by design value or budget
Liner 2.4 mm Al 2024 (A&P), shells 2.0/3.0 mm, MLI 25.4 mm (type-1 design
value) or sized to 5 W at 60 C ambient (type-3). All varied in the declared
uncertainty study.

### A-ENG-5: Internal HX structure = 2.7 vol% aluminium of bed
Single small-scale HexCell datum, applied to both families; factor-2
uncertainty band declared. The type-3 "generic resistance heater" has no
published mass.

### A-ENG-6: BOP interpolates two published anchors in design pressure
16 kg @ 100 bar and 30 kg/25 L @ 350 bar, components per FEDSM Table 3;
the delivery-warming heat exchanger (M10) lives inside this block. The two
calibration factors on it are the model's only fitted values.

## Usable-capacity physics (v1.0)

### A-USE-1: Electric resistance heating; no onboard H2 consumed for the swing
The reference designs heat with electric resistance elements; the heater
ENERGY per discharge is computed and reported, and an H2-fuelled variant
would subtract its fuel from usable capacity (stated, not modelled).

### A-USE-2: Delivered gas warmed to >= -40 C by a BOP heat exchanger
Mass and volume carried in the BOP block; the duty uses fuel-cell waste heat
per the reference designs.

### A-USE-3: Dormancy sets the design pressure; 60 C ambient sizes insulation
Vent at 1.25 P_full; worst-case ambient 333.15 K for heat-leak sizing and
the reported dormancy metric.

## Statistical layer (v1.0)

### A-STAT-1: Gaussian error model with errors in P and n
Per-point sigmas from the dual digitization, floored at one pixel;
first-order abscissa propagation. If relaxed: the overdispersion
(objective/dof = 3.33) shows residual model-form error beyond digitization
noise; both the frozen and the s^2-inflated intervals are reported.

### A-STAT-2: Uniform priors on the frozen bounds
Pre-registered; the log10 P0 lower bound is the data maximum, and the
bound-relaxation sensitivity is reported.
