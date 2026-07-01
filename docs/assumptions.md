# Assumptions

Each assumption carries one sentence of justification and one on what changes if it is relaxed (§3.3).

## Isotherm layer (added Week 2, Day 1)

### A-ISO-1: Modified Dubinin–Astakhov describes absolute adsorption over the full envelope
The modified D–A form is the established description of supercritical hydrogen adsorption on activated carbons and fits AX-21 across 30–293 K in the source paper, so I adopt it as the isotherm model over my whole envelope. If relaxed (e.g. a Tóth form instead): the functional-form residuals against the digitized data enter the uncertainty budget, and the Day-8 structural-sensitivity swap tests whether any conclusion depends on this choice.

### A-ISO-2: n_max and v_a are temperature-independent
I treat the limiting loading n_max and adsorbed-phase volume v_a as constants, consistent with the D–A treatment where temperature dependence is carried entirely by E = α+βT, which keeps the parameter set to five. If relaxed: a temperature-dependent v_a would shift the excess conversion most at high density (deep cryo, high P), where the ρ_molar·v_a subtraction is largest, slightly moving the excess maximum.

### A-ISO-3: Normal hydrogen for the gas-phase density in the excess conversion
The molar density in n_exc = n_abs − ρ_molar·v_a is evaluated for normal hydrogen, matching the EOS layer validated in Gate V1, so conversion and density validation use one consistent fluid. If relaxed: at deep cryogenic temperatures the equilibrium para-fraction rises and para-hydrogen is denser, raising the subtracted term and slightly lowering predicted excess near 77 K; I treat this as a bounded sensitivity check with CoolProp's parahydrogen fluid rather than modeling conversion kinetics.

### A-ISO-4: v_a is estimated as n_max × liquid-H2 molar volume
Per the provenance in ax21.yaml, v_a is estimated as n_max times the liquid-hydrogen molar volume (~2.8e-5 m³/mol), fixing the adsorbed-phase volume without an extra fit degree of freedom. If relaxed: v_a becomes a free parameter recovered in the Day-8 least-squares refit, and its fitted covariance then feeds the material-uncertainty layer.

## 2026-07-01 — Isotherm and isosteric-heat implementation
Tool: Claude Code (Opus 4.8)
Purpose: Implement isotherm.py (Material, ModifiedDA) and heats.py from my CC-3 spec.
What I provided: The CC-3 prompt plus my model_derivations.md and assumptions.md to read first.
What it produced: src/h2star/isotherm.py, heats.py, tests/test_isotherm.py, tests/test_heats.py.
What I verified: Read every diff line before accepting; checked the D-A equation, the MPa->Pa
  conversion in from_yaml, the p0 clamp / no-NaN guards, molar (not mass) density in n_excess,
  and the -R sign in q_st; ran all six tests and ruff myself; eyeballed the overlay vs my points.
What I changed: nothing