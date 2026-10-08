# H2STAR — known limitations

Written to be read by someone deciding whether to trust a number from this
project. Nothing here is hedging: each entry states what the limitation is, how
large it is where that is known, and what it forbids the model from claiming.

The two that matter most are first. If you read nothing else, read those.

---

## 1. The system mass model is optimistic by about a factor of 4.2

**This is the project's largest known error and it is a measured one, not an
estimate.**

Gate V3 compared the model's full-state system capacities against the HSECoE
AX-21 activated-carbon baseline (Tamburello et al., SRNL, DOE AMR project ID
ST044, 2013). The result is a documented FAIL against a tolerance pre-registered
in Week 1 and never edited:

```
GC_full = 0.0777 kg/kg  vs anchor 0.0312  ->  2.49x high
VC_full = 0.0363 kg/L   vs anchor 0.0194  ->  1.87x high
```

Because the two metrics share a numerator and miss by different factors, the
discrepancy is localized to the mass denominator. Back-solving: matching the
anchor needs a system mass of about 188.5 kg against the 75.7 kg modelled, and
the well-anchored core (sorbent plus hydrogen, 40.7 kg) is sound, so the
vessel-plus-insulation-plus-balance-of-plant block would have to be about
147.8 kg against the 35.0 kg modelled — light by a factor of about 4.2.

The cause is named: the vessel is an idealized thin-wall composite sized by
hoop stress, and the balance of plant is a single lumped 16 kg constant. A real
Type-3 200 bar tank carries end-dome and boss hardware, a full liner, valves,
lines and cryogenic support structure that this model either omits or lumps.

**What this forbids.** Any claim that H2STAR reproduces published system
capacities. Any absolute system gravimetric or volumetric capacity quoted
without this factor attached. In particular the model places AX-21 activated
carbon *above* the DOE 2025 gravimetric target at the baseline envelope, which
AX-21 does not achieve in reality — so a reader who took the absolute numbers at
face value would conclude that a 1980s activated carbon already solves onboard
hydrogen storage.

**What survives.** Relative comparisons at a fixed envelope, because a bias in a
shared denominator cancels in a ratio. The shape and ordering of the response
surfaces. The inventory physics itself, which reproduces the reference. This is
why claim C4 is reported as a ratio against AX-21 rather than as a shortfall
against the DOE target.

The gate was not chased to a pass. Re-sourcing the vessel model after seeing the
147.8 kg it would have to produce would be fitting to a known answer. It is
recorded as a strict xfail so that if a future upgrade closes the gap, the suite
goes red and forces Gate V3 to be re-adjudicated rather than letting a
documented FAIL quietly become an unexamined pass.

---

## 2. The material parameters are not identifiable from one published isotherm

Gate V2 refit the modified Dubinin–Astakhov parameters to 11 digitized points on
a single 77 K AX-21 isotherm. All four free parameters came back outside their
pre-registered recovery bands, and the optimizer terminated with log₁₀(p₀) on
its lower bound.

Implementation error is excluded: synthetic-data tests recover known parameters
within 2σ, and the refit RMSE improves on the published-parameter RMSE as it
must. The likelihood is a ridge — pairwise correlations 0.91–0.99, cond(JᵀJ)
≈ 1e14.

**Scope, stated carefully.** This establishes *practical* non-identifiability
from a single-temperature isotherm of the kind the literature routinely
publishes. It does **not** establish that the D–A model is structurally
non-identifiable, and the repository's own diagnostic rules that reading out:
with p₀ also fixed at the published value, the remaining parameters return to
within 6% of published. The curve is identifiable; the parameter vector is not,
under the data the field reports.

**Quantified consequence.** Propagating the fixed-p₀ conditional covariance
through the system model blurs the DOE-2025 feasibility boundary over **32.1
mol/kg in limiting uptake, a quarter of the requirement itself** (5–95% range
109.4 to 141.5 mol/kg, median crossing 125.6). A point prediction of "the
required limiting uptake" would quote three significant figures for a quantity
whose own range spans a quarter of its value.

**And that figure is a lower bound.** It is conditional on p₀ being fixed, so it
understates the spread a single isotherm really implies. Every interval and
probability band this project reports carries that caveat in its own metadata.

---

## 3. The uncertainty layer quantifies spread, not bias

Follows directly from the two above, and is stated separately because conflating
them is the easiest mistake to make with this project's outputs.

`data/uncertainty.yaml` declares input ranges of ±15% to ±50%. Gate V3 measured
a bias of about 4.2× in the mass denominator. The bias is an order of magnitude
larger than the widest declared band.

A Monte Carlo interval from this project is therefore **an interval about an
optimistic central estimate**. It does not bracket the truth, and no sample size
changes that. Three of the five declared engineering ranges are labelled
`MODELING ASSUMPTION` in the data file because their sources report no
uncertainty at all; only the heat-leak budget and the balance-of-plant mass have
sourced ranges.

---

## 4. The requirement sits at the edge of physical coherence

Found while building the uncertainty layer, and not anticipated.

The acceptability map sweeps limiting uptake while holding the adsorbed-phase
volume fixed. That is not a neutral choice: the Gate V2 fit's own covariance
implies dv_a/dn_max = 4.41e-5 m³/mol and assumption A-ISO-4's liquid-hydrogen
argument implies 2.80e-5 m³/mol, so the adsorbed phase grows with uptake by two
independent accounts. It has to fit inside the pore volume the packing leaves,
1/ρ_bulk − 1/ρ_skel = 2.900e-3 m³/kg for AX-21, which caps the uptake at:

```
fit correlation : n_max = 104.9 mol/kg
A-ISO-4         : n_max = 124.1 mol/kg
```

Both fall at or below the median requirement crossing of 125.6 mol/kg, and the
fit's limit falls below even the 5% crossing of 109.4.

**Consequence.** The requirement the map identifies is not reachable at AX-21's
packing density: a sorbent with enough limiting uptake to meet the DOE targets
would have an adsorbed phase larger than its own pore volume. This sharpens
rather than invalidates the map — the requirement needs uptake *and* pore volume
together, which means packing less densely, which costs the volumetric capacity
that is already the binding constraint. The `(n_max, ρ_bulk)` panel of F6 shows
that trade with the coherence curve drawn through the probability band.

---

## 5. The Sobol indices are of an independent-input surrogate

Saltelli sampling requires a box, so each declared distribution is widened to a
uniform over its support and the material correlation — up to 0.97 — is
discarded. The indices therefore answer "which parameter would matter most if
these could be varied independently?", which is the actionable question for a
materials chemist, and they are **not** a decomposition of the Monte Carlo
variance computed with the correlations intact. Every widened parameter is
reported in the result's `widened` field rather than left implicit.

Three parameters are excluded from the sensitivity analysis entirely, with
reasons recorded in `data/uncertainty.yaml`: the vessel performance factor,
because it is a cross-check that never enters the budget and would report a
zero index implying the cross-check had been exercised; and the composite
density and liner areal mass, because declaring a second unsourced band on the
same vessel-mass term would double-count the idealization the σ_allow band
already represents.

---

## 6. The CNT case study rests on an inference chain, not measurements

The literature reports one uptake at one temperature and pressure. The system
model needs a full parameter vector plus two densities. Bridging that gap means
keeping AX-21's characteristic energy, pseudo-saturation pressure,
adsorbed-phase volume and densities, and solving only for the limiting uptake
that reproduces the reported point.

Four assumptions, each a link that could break:

1. The D–A form describes a nanotube sample. Untested — no CNT paper in the
   corpus reports an isotherm shape.
2. α, β and p₀ transfer from an activated carbon. These set the temperature and
   pressure dependence, so every extrapolation away from the reported state
   depends on them, and one entry is extrapolated 212 K.
3. v_a, ρ_bulk and ρ_skel transfer too. **No CNT paper in the corpus reports a
   packed bulk density at all**, and the Sobol study ranks v_a as the single
   largest contributor to system-capacity variance.
4. The measurement basis is assumed, because **none of the seven papers states
   whether its uptake is Gibbsian excess or absolute**. On the primary entry
   that ambiguity alone moves the inferred limiting uptake from 53.5 to
   95.2 mol/kg, a factor of 1.78 — larger than any engineering uncertainty in
   the cascade, which is why it is drawn as F8's whisker.

The corpus itself: reported uptake spans 0.050 to 8.0 wt% across the five
physisorption entries with a room-temperature value, a factor of 160 on
nominally the same material class. Two of those five fail the pore-volume
consistency screen. Two of seven print no DOI.

---

## 7. Out of scope by design

Named so their absence is not mistaken for an oversight.

- **Charging and discharging dynamics.** The model is a state-point equilibrium
  model throughout. Equilibrium states bound achievable capacity, which is what
  a screening model needs, but no filling time, no thermal transient and no
  dormancy analysis exists here.
- **Spatial gradients.** A single (P, T) describes the bed at each state point.
- **Cost and techno-economics.** Out of scope deliberately: cost-model
  parameters are negotiated rather than derived, and a student techno-economic
  analysis is the least defensible model class under expert questioning.
- **Ortho/para conversion kinetics.** Normal hydrogen is used throughout. The
  para fraction rises at deep cryogenic temperatures and para-hydrogen is
  denser; this is treated as a bounded sensitivity rather than modelled.
- **The Streamlit explorer** from the v1.0 manual. Never built, and removed from
  the plan rather than left as an unmet promise.

---

## 8. Smaller items, recorded for completeness

- **The D–A isosteric heat diverges as coverage goes to zero** (√ln form). An
  artifact of the functional form, not a physical zero-coverage heat. The Gate
  V2 anchor is therefore evaluated at finite low coverage and F3 is plotted over
  n/n_max ∈ [0.02, 0.60].
- **`bop_scaling` is 0.0**, so balance-of-plant mass does not scale with tank
  size. No sourced coefficient was found and one was deliberately not invented;
  the omission is absorbed by the ±50% BOP uncertainty band.
- **The vessel cross-check compares different vessel classes.** The hoop-stress
  route models an aluminium-lined Type 3 vessel and the performance-factor
  benchmark is a plastic-lined Type 4 figure of merit, so the two are expected
  to agree only within about 35%.
- **The ST044 volumetric anchor required a unit reinterpretation.** The slide
  prints "gH2/Lsys" at a magnitude that is dimensionally impossible; it is read
  as kg/L, triangulated against an independent HSECoE pair, and recorded as a
  transcription-error correction with the reasoning written down before the
  comparison was run.
- **Figure byte-identity holds within a Matplotlib and FreeType version, not
  across versions.** Under a fixed seed every number behind every figure is
  deterministic. The images are byte-identical too, verified by regenerating
  them from a fresh clone in a separate virtual environment and comparing
  SHA-256: nine of nine identical across Python 3.11 vs 3.13, NumPy 2.4.6 vs
  2.5.3 and SciPy 1.17.1 vs 1.18.1. What that does not cover is a different
  Matplotlib or FreeType, which rasterise glyphs differently between releases.
  Text is the whole of the difference, so the numbers survive a version change
  and the bytes need not. Sibling project RamanUQ claims byte-reproducibility
  outright; this project claims it only within a rendering stack.
- **The figures shipped before v0.2.0 were reproducible on one machine only,
  and the project's own reproducibility claim did not notice.** Matplotlib
  takes `font.family` and `text.hinting` from whatever configuration the host
  supplies, and the container this work was developed in injects
  `font.family = Inter, sans-serif, DejaVu Sans` and
  `text.hinting = no_hinting` into `rcParamsDefault` itself, so even a fresh
  install inside it inherits them. Neither value is declared by any dependency
  this repository names. Every label was drawn in a font no other machine has,
  which moved every tight bounding box and therefore every pixel. The Stage 6
  clean room caught it: all nine headline numbers reproduced to the last digit
  and all nine images differed. Forcing those two values in the clean-room
  environment reproduced the committed bytes exactly, which is what established
  that the cause was the font configuration and nothing numerical.

  The claim that was wrong said the figures were byte-identical *on repeat runs
  on this platform*. That was true, and it was the wrong test: repeat runs in
  one environment cannot detect output that depends on the environment. Only a
  comparison across environments can, which is the reason the clean-room gate
  exists and the reason it is run from a fresh clone rather than the working
  tree. `viz.FIGURE_RCPARAMS` now pins the rendering configuration to
  Matplotlib's own stock defaults, naming DejaVu Sans — which ships inside the
  Matplotlib wheel — rather than reaching it through the `sans-serif` alias, so
  the figures depend on no system font. `tests/test_viz_style.py` asserts that
  every public plotting function carries the pin, because the defect returns
  the moment a new plotting function forgets it.
- **One commit carries a non-Avin committer.** The initial commit `ed2a3cf` was
  created through the GitHub web UI, so its committer is
  `GitHub <noreply@github.com>` while its author is Avin. Not an AI identity,
  and not worth rewriting history to remove.

---

## What would most improve this project

In order, with the largest first:

1. **A design-level vessel mass model** and a size-scaled balance-of-plant
   correlation. This is the single change that would move the Gate V3 FAIL, and
   it would turn every absolute capacity in the project from an optimistic
   bound into a defensible estimate.
2. **Multi-temperature isotherm data** for the reference material. The
   non-identifiability in §2 is a property of single-temperature reporting, not
   of the model, and multi-temperature data would collapse the ridge and
   sharpen every uncertainty band that follows from it.
3. **Any CNT measurement that reports its basis and its packing density.** §6's
   inference chain exists only because no paper in the corpus reports them.
