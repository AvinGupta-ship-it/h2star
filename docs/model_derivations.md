# Model Derivations

Each equation of §3.4 with a short derivation or a citation, in my own words. This file grows weekly; sections 1–3 are the isotherm layer.

## 1. Modified Dubinin–Astakhov absolute adsorption (§3.4B)
Absolute loading follows n_abs(P,T) = n_max·exp[−(RT/(α+βT))²·ln²(p0/P)], where n_max (mol/kg) is the limiting adsorption approached as P→p0, α (J/mol) and β (J/(mol·K)) define the characteristic energy E = α+βT, and p0 (Pa) is a pseudo-saturation pressure. This is Dubinin's micropore volume-filling theory adapted for a supercritical adsorbate: above hydrogen's 33 K critical temperature there is no true vapor pressure, so p0 is a fitted reference rather than a physical saturation. Temperature enters twice — explicitly as RT and through E — which is what lets one parameter set span 30–293 K. (RT/E) is dimensionless, my unit check on the prefactor. Values: Richard, Bénard, Chahine (2009), DOI 10.1007/s10450-009-9149-x, Table [n], AX-21.

## 2. Excess-to-absolute conversion (§3.4C)
Excess uptake is the gas present beyond what the same volume would hold at bulk density, so subtracting the bulk-phase contribution of the adsorbed volume v_a (m³/kg) from absolute loading gives n_exc(P,T) = n_abs(P,T) − ρ_molar(P,T)·v_a. Units: ρ_molar [mol/m³]·v_a [m³/kg] = mol/kg, matching n_abs, so n_exc is mol/kg. At low P, ρ_molar is small and n_exc ≈ n_abs; as P rises, n_abs saturates toward n_max while the subtracted ρ_molar·v_a term keeps growing, so n_exc reaches a maximum and declines even though n_abs is still increasing — the signature of a supercritical excess isotherm.

## 3. Isosteric heat via Clausius–Clapeyron (§3.4D)
At fixed loading n, Clausius–Clapeyron applied to the adsorption equilibrium makes ln P linear in 1/T with slope −q_st/R, so q_st = −R·d(lnP)/d(1/T)|_n, positive for exothermic adsorption. I evaluate it numerically by inverting the isotherm for P at fixed n across temperature and centered-differencing lnP against 1/T. The analytic D–A limit (q_st ∝ α·√ln(n_max/n)) is a cross-check on the low-coverage value, which for carbons should fall near 4–7 kJ/mol — my sanity anchor.

## 4. Isotherm refit: least squares, covariance, identifiability

### 4.1 Objective
The digitized 77 K data are excess adsorption, so the fit is on excess residuals:
r_i(theta) = n_exc,model(P_i, 77 K; theta) − n_exc,data,i, minimizing SSR(theta) = sum r_i².
The fitted vector is theta = (n_max, alpha, log10 p0, v_a), with beta held fixed (Sec. 4.3).
The model is nonlinear in theta, so the minimum is found iteratively
(scipy.optimize.least_squares, trust-region reflective), initialized at the published
Table 3 values with bounds. Residuals are unweighted: digitization noise is roughly
constant across points, and the assumption is inspectable in the F2 residual panel.

### 4.2 Covariance from the Jacobian
Near the minimum the model is approximately linear in theta, giving
cov(theta_hat) ≈ s²·(JᵀJ)⁻¹, where J_ij = ∂r_i/∂theta_j at the solution and
s² = SSR/(N − 4) estimates the noise variance (N ≈ 14 points, 4 fitted parameters,
dof = N − 4). Square roots of the diagonal are 1-sigma standard errors; normalized
off-diagonals are parameter correlations. This is a local, linearized estimate under
approximately independent constant-variance errors — reported with the correlation
matrix and the condition number of JᵀJ as honesty diagnostics. This covariance is the
point of the refit: it defines the multivariate normal the material-parameter Monte
Carlo layer samples from later (manual Sec. 3.4J / 3.6), which published point values
alone cannot provide.

### 4.3 Identifiability: the alpha–beta degeneracy at a single temperature
alpha and beta enter the model only through E(T) = alpha + beta·T. Since
∂n_abs/∂alpha = (∂n_abs/∂E)·(∂E/∂alpha) = ∂n_abs/∂E and
∂n_abs/∂beta = (∂n_abs/∂E)·T, at fixed T = 77 K every data point satisfies
∂n_abs/∂beta = 77·∂n_abs/∂alpha: the two Jacobian columns are exactly proportional,
JᵀJ is rank-deficient, the covariance is singular, and the alpha–beta correlation is
−1 by construction. Only the lump E(77) = alpha + 77·beta = 3080 + 1455.3
= 4535.3 J/mol is identifiable from these data. Resolution: beta is fixed at the
published 18.9 J/(mol·K), taken as external prior information from the paper's
multi-temperature global fit, which my single-temperature data cannot inform. The
fitted alpha is therefore conditional on that beta and algebraically equivalent to
fitting E(77) directly. The Gate V2 recovery verdict is scoped to the identifiable
parameters (n_max, alpha | beta fixed, log10 p0, v_a); pass bands pre-registered in
docs/validation_plan.md on 2026-07-02, before the refit was run.

### 4.4 Conditioning: why log10 p0 and parameter scaling
Raw parameter magnitudes span ~12 decades (p0 ~ 1.5e9 Pa against v_a ~ 1.4e-3 m³/kg),
so the fit uses log10 p0 and characteristic scales (x_scale) to keep internal steps
O(1) (manual Sec. 5.9). Separately, p0 is weakly identified: in x = ln P,
ln n_abs = ln n_max − (R·T/E)²·(ln p0 − x)² is a parabola with vertex at ln p0 ≈ 21.1,
while the data occupy x ≈ 10.8–15.6 — about 2.4 decades below the vertex. Observing
only the far tail of a parabola makes its vertex location (p0) and curvature
((R·T/E)²) trade off strongly: ill-conditioned, not degenerate. A decade-scale
uncertainty on log10 p0 is therefore expected, which is why its pre-registered band
is ±0.7 decades.