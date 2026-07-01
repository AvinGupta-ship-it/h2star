# Model Derivations

Each equation of §3.4 with a short derivation or a citation, in my own words. This file grows weekly; sections 1–3 are the isotherm layer.

## 1. Modified Dubinin–Astakhov absolute adsorption (§3.4B)
Absolute loading follows n_abs(P,T) = n_max·exp[−(RT/(α+βT))²·ln²(p0/P)], where n_max (mol/kg) is the limiting adsorption approached as P→p0, α (J/mol) and β (J/(mol·K)) define the characteristic energy E = α+βT, and p0 (Pa) is a pseudo-saturation pressure. This is Dubinin's micropore volume-filling theory adapted for a supercritical adsorbate: above hydrogen's 33 K critical temperature there is no true vapor pressure, so p0 is a fitted reference rather than a physical saturation. Temperature enters twice — explicitly as RT and through E — which is what lets one parameter set span 30–293 K. (RT/E) is dimensionless, my unit check on the prefactor. Values: Richard, Bénard, Chahine (2009), DOI 10.1007/s10450-009-9149-x, Table [n], AX-21.

## 2. Excess-to-absolute conversion (§3.4C)
Excess uptake is the gas present beyond what the same volume would hold at bulk density, so subtracting the bulk-phase contribution of the adsorbed volume v_a (m³/kg) from absolute loading gives n_exc(P,T) = n_abs(P,T) − ρ_molar(P,T)·v_a. Units: ρ_molar [mol/m³]·v_a [m³/kg] = mol/kg, matching n_abs, so n_exc is mol/kg. At low P, ρ_molar is small and n_exc ≈ n_abs; as P rises, n_abs saturates toward n_max while the subtracted ρ_molar·v_a term keeps growing, so n_exc reaches a maximum and declines even though n_abs is still increasing — the signature of a supercritical excess isotherm.

## 3. Isosteric heat via Clausius–Clapeyron (§3.4D)
At fixed loading n, Clausius–Clapeyron applied to the adsorption equilibrium makes ln P linear in 1/T with slope −q_st/R, so q_st = −R·d(lnP)/d(1/T)|_n, positive for exothermic adsorption. I evaluate it numerically by inverting the isotherm for P at fixed n across temperature and centered-differencing lnP against 1/T. The analytic D–A limit (q_st ∝ α·√ln(n_max/n)) is a cross-check on the low-coverage value, which for carbons should fall near 4–7 kJ/mol — my sanity anchor.