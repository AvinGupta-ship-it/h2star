# Model Derivations

Each governing equation with a short derivation or citation. Sections 1-4 are the isotherm layer (v0.2, corrected); sections 5-12 cover every remaining layer (v1.0).

## 1. Modified Dubinin–Astakhov absolute adsorption (§3.4B)
Absolute loading follows n_abs(P,T) = n_max·exp[−(RT/(α+βT))²·ln²(p0/P)], where n_max (mol/kg) is the limiting adsorption approached as P→p0, α (J/mol) and β (J/(mol·K)) define the characteristic energy E = α+βT, and p0 (Pa) is a pseudo-saturation pressure. This is Dubinin's micropore volume-filling theory adapted for a supercritical adsorbate: above hydrogen's 33 K critical temperature there is no true vapor pressure, so p0 is a fitted reference rather than a physical saturation. Temperature enters twice — explicitly as RT and through E — which is what lets one parameter set span 30–293 K. (RT/E) is dimensionless, my unit check on the prefactor. Values: Richard, Bénard, Chahine (2009), DOI 10.1007/s10450-009-9149-x, Table 3, AX-21.

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
s² = SSR/(N − 4) estimates the noise variance (N = 11 points, 4 fitted parameters,
dof = N − 4 = 7). Square roots of the diagonal are 1-sigma standard errors; normalized
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
## 5. Real-gas EOS layer

All gas densities come from CoolProp's implementation of the Leachman et al.
(2009) reference equation of state for normal hydrogen (LEACHMAN-2009);
`eos.density(P, T)` is a unit-guarded wrapper (Pa, K, kg/m^3) with validity
floors at T = 33.2 K (the critical temperature; below it the gas-phase call
is rejected, which also excludes the 30 K isotherm from every fit) and
P > 0. Gate V1 checks the wrapper against the NIST WebBook tables generated
from the same EOS, so it is a units-and-plumbing test, not physics
validation, and is described as such wherever cited.

## 6. Tank inventory and usable capacity

For sorbent mass m_s = rho_bulk * V_bed packed at bulk density rho_bulk:
V_void = V_bed - m_s/rho_skel - m_s*v_a, and
m_H2(P,T) = M_H2 * [ m_s*n_abs(P,T) + rho_molar(P,T)*V_void ].
The identity m_s*n_abs + rho*V_void = m_s*n_exc + rho*(V_void + m_s*v_a)
holds by construction (absolute + void gas = excess + pore-and-void gas); the
suite enforces it as a code-consistency check — it cannot detect a wrong
conversion (review minor 20), which is instead constrained by the
multi-temperature fit reproducing the source's own excess curves.
Usable capacity: m_usable = m_H2(P_full, T_full) - m_H2(P_empty, T_empty).
GC = m_usable/m_sys and VC = m_usable/V_sys (usable basis, the DOE/HSECoE
convention); m_sys carries the FULL inventory because residual hydrogen is
still carried mass.

## 7. Component-resolved engineering model (v1.0)

Geometry: a capsule of radius r and cylindrical length L_cyl = LR*r;
V = pi r^2 L_cyl + (4/3) pi r^3. Design pressure P_design = 1.25 P_full
(dormancy vent set-point; AHLUWALIA-2009), with each source's safety factor
re-expressed as SF_eff = SF_source/1.25 so sizing equals source practice.

Type-1 (aluminium): hoop-governed thin wall t = SF_eff P_design r / sigma,
sigma = 400 MPa back-derived exactly from the FEDSM2017 Table 5 HexCell
design (TAMBURELLO-2017); von Mises for a closed cylinder is sqrt(3)/2 of
hoop, so hoop governs.

Type-3 (Al-lined CF overwrap), netting analysis: helical plies carry the
axial load, sigma t_h cos^2(a) = P r / 2; hoop equilibrium
sigma (t_th + t_h sin^2 a) = P r. Total cylinder composite
t_h + t_th = 1.5 P r / sigma exactly, independent of the winding angle a
(the +50% over hoop-only sizing the 2026-10-27 review required). Domes carry
the helical plies (area of the closing sphere at t_h). Effective stress
sigma = 2550 MPa * 0.90 quality * translation(P_full), translation linear
82.5% @350 bar to 63% @700 bar (AHLUWALIA-2009), capped at 0.90. Liner:
fixed 2.4 mm Al 2024 (a permeation barrier, not pressure-scaled).

Radial build-up r -> wall -> (LN2 channel, type-1 only, zeroed for the
FEDSM family whose channels are embedded in the shell) -> MLI -> outer
shell; each layer's mass is its area times thickness times density and its
volume adds to the envelope. MLI: fixed 25.4 mm for the type-1 family
(design input), or sized to the 5 W budget for the type-3 family,
t = k_eff A dT / Q at the 60 C worst-case ambient. Internal HX structure:
2.7 vol% aluminium of bed (ST044-2013 slide 25), displacing bed volume.
Supports 1.28 kg. BOP mass and volume interpolate two published anchors in
design pressure and are scaled by the E1-frozen calibration factors
(c_bop_mass 1.086426, c_bop_vol 2.5 at bound, c_hx 1.0).

## 8. Measurement-error model and weighted objective (v1.0)

Each reconciled data point carries sigma_n and sigma_P from the dual
digitization (floored at the axis resolution). The working error model is
sigma_eff,i^2 = sigma_n,i^2 + (dn_model/dP|_i)^2 sigma_P,i^2 — the standard
first-order errors-in-abscissa propagation — and every fit minimizes
sum_i (model_i - data_i)^2 / sigma_eff,i^2. The derivative is analytic for
the D-A form: dn_abs/dP = n_abs * m (RT/eps)^m |ln(p0/P)|^{m-1} sign(ln(p0/P)) / P,
minus (d rho/dP) v_a for the excess conversion. This weighting is what
handles the sub-pixel low-pressure points that drove the v0.2 C5 artifact:
on the Henry branch dn/dP is large, sigma_eff is large, and the points are
discounted in proportion to what the pixel grid actually resolves.

## 9. Profile likelihood and intervals (v1.0)

For each parameter, the profile is the weighted objective minimized over all
other parameters at fixed values of the target (RAUE-2009); the 95% interval
is Delta(objective) <= 3.84 (chi-square, 1 dof), endpoints located by
bisection. Because the residuals are overdispersed relative to the stated
digitization uncertainties (objective/dof = 3.33, dominated by m = 2 model-
form error), the s^2-inflated threshold 3.84 * (objective/dof) is reported
alongside the frozen one. Bounds: log10(P0/Pa) >= 6.78 — the pseudo-
saturation pressure must exceed the fitted data range (6 MPa); the
sensitivity of every conclusion to relaxing that bound is reported.

## 10. Posterior and sampling (v1.0)

Log-posterior = Gaussian log-likelihood under the section-8 error model
(normalization retained, since sigma_eff depends on theta) plus uniform
priors on the frozen bounds; sampled with emcee (40 walkers, 30,000 steps,
5,000 burn-in). Diagnostics per parameter: ESS > 16,800 and split-chain
R-hat <= 1.003, with split-half quantile agreement recorded
(data/analysis/uq_mcmc_v1.json).

## 11. Sensitivity: Shapley effects and elasticities (v1.0)

Variance attribution uses Shapley effects (SONG-2016) over 16 players: the
correlated material block (one player, drawn from the joint posterior) and
15 mutually independent engineering/envelope inputs with declared
distributions (data/uncertainty_v1.yaml). The random-permutation estimator
averages, over permutations, each player's increment to the explained
variance E[Var(Y|X_S)] (inner/outer sampling; efficiency check: shares sum
to 1.03-1.04 of Var(Y), within estimator noise). Design leverage is a
separate quantity: local elasticities d ln(GC)/d ln(x) at the nominal
point. The two are never conflated (review M6).

## 12. Requirement map in observables (v1.0)

Axes: deliverable uptake u_d (kg H2 per kg sorbent between the stated full
and empty states) and packing density rho_pack. Sizing follows from
V_bed = 5.6 / (u_d rho_pack + g_swing), with g_swing the void-gas swing per
bed volume, (1 - rho_pack/rho_skel - rho_pack v_a)(rho_g,full -
rho_g,empty); the engineering stack then builds mass and volume as in
section 7. No probability band is drawn: the axes are observables, not
sampled parameters (the frozen conditionality rule), and the residual-uptake
carried-mass term and the v_a/rho_skel entering g_swing are reported as a
labelled sensitivity. The map is drawn under both the v1.0 and the
superseded v0.2 engineering models; the boundary shift between them is the
two-model robustness exhibit the fork rule requires.
