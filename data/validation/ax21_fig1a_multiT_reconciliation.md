# Reconciliation of Fig. 1a digitization routes A and B

Rule: docs/preregistration_v1.0.md section 5 (frozen).
Axis resolution: 0.00492 MPa/px, 0.0616 (mol/kg)/px.

Inputs and reproducibility (S8 referee M7 fix, 2026-11-03): the two route
CSVs, their calibration notes, route B's extraction script and the shared
600-dpi source crop are committed under `data/validation/digitization/`,
and the single re-inspection documented below is encoded point-by-point in
`digitization/reinspection_decisions.csv`. The published dataset
regenerates byte-for-byte from these inputs via
`scripts/reconcile_digitization.py` (enforced by
`tests/test_digitization_pipeline.py`). The two routes are two isolated
extraction processes (one visual reading, one scripted template matching)
over the SAME source image and glyph conventions, so shared-mode error is
possible — the documented triangle-marker-centre offset at 35 K and 113 K
is exactly such a case, caught because the per-point route readings are
embedded in the dataset; "independent" below means independent extraction
routes, not independent sources.

Matched and reconciled: 140
Flagged for the single re-inspection: 58

REVIEW 35 K: route-A point P=0.642, n=46.94 (ok) unmatched/disagreeing
REVIEW 35 K: route-A point P=0.947, n=46.57 (ok) unmatched/disagreeing
REVIEW 35 K: route-A point P=1.163, n=45.03 (ok) unmatched/disagreeing
REVIEW 35 K: route-A point P=1.626, n=36.16 (ok) unmatched/disagreeing
REVIEW 35 K: route-A point P=1.902, n=26.60 (uncertain) unmatched/disagreeing
REVIEW 35 K: route-A point P=3.038, n=18.90 (ok) unmatched/disagreeing
REVIEW 35 K: route-A point P=3.407, n=18.10 (ok) unmatched/disagreeing
REVIEW 35 K: route-A point P=5.164, n=15.76 (ok) unmatched/disagreeing
REVIEW 35 K: route-A point P=5.622, n=15.39 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=0.638, n=46.56 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=0.944, n=46.20 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=1.161, n=44.68 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=1.530, n=39.27 (partial_overlap) unmatched/disagreeing
REVIEW 35 K: route-B point P=1.622, n=35.81 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=1.899, n=26.19 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=3.036, n=18.52 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=3.405, n=17.73 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=5.160, n=15.42 (ok) unmatched/disagreeing
REVIEW 35 K: route-B point P=5.621, n=15.03 (ok) unmatched/disagreeing
REVIEW 40 K: route-A point P=0.027, n=28.82 (partial_overlap) unmatched/disagreeing
REVIEW 45 K: route-A point P=1.547, n=39.42 (partial_overlap) unmatched/disagreeing
REVIEW 60 K: route-A point P=3.621, n=30.85 (partial_overlap) unmatched/disagreeing
REVIEW 77 K: route-A point P=0.000, n=1.89 (partial_overlap) unmatched/disagreeing
REVIEW 77 K: route-A point P=1.872, n=25.37 (uncertain) unmatched/disagreeing
REVIEW 77 K: route-B point P=-0.009, n=1.93 (partial_overlap) unmatched/disagreeing
REVIEW 93 K: route-A point P=0.219, n=10.42 (partial_overlap) unmatched/disagreeing
REVIEW 93 K: route-A point P=0.411, n=13.17 (partial_overlap) unmatched/disagreeing
REVIEW 93 K: route-A point P=0.499, n=14.09 (uncertain) unmatched/disagreeing
REVIEW 113 K: route-A point P=0.206, n=5.40 (uncertain) unmatched/disagreeing
REVIEW 113 K: route-A point P=0.457, n=8.11 (uncertain) unmatched/disagreeing
REVIEW 113 K: route-A point P=0.824, n=10.76 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=1.011, n=11.50 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=1.316, n=12.67 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=1.656, n=13.84 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=2.118, n=14.58 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=2.487, n=15.39 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=2.856, n=16.13 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=3.255, n=16.49 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=3.683, n=16.93 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=4.426, n=17.30 (partial_overlap) unmatched/disagreeing
REVIEW 113 K: route-A point P=4.825, n=17.67 (ok) unmatched/disagreeing
REVIEW 113 K: route-A point P=5.592, n=17.67 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=0.177, n=4.32 (partial_overlap) unmatched/disagreeing
REVIEW 113 K: route-B point P=0.821, n=10.42 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=1.008, n=11.17 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=1.313, n=12.34 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=1.653, n=13.51 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=2.115, n=14.25 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=2.484, n=15.04 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=2.853, n=15.79 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=3.252, n=16.16 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=3.682, n=16.57 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=4.822, n=17.32 (ok) unmatched/disagreeing
REVIEW 113 K: route-B point P=5.590, n=17.37 (ok) unmatched/disagreeing
REVIEW 153 K: route-A point P=0.359, n=2.32 (uncertain) unmatched/disagreeing
REVIEW 213 K: route-B point P=0.502, n=0.99 (partial_overlap) unmatched/disagreeing
REVIEW 298 K: route-A point P=0.270, n=0.10 (uncertain) unmatched/disagreeing
REVIEW 298 K: route-A point P=0.489, n=0.41 (uncertain) unmatched/disagreeing

## Single re-inspection (prescribed by pre-registration section 5) — adjudications

Triangle-offset verification: three isolated 35 K triangles measured with fit lines
morphologically removed; glyph bounding-box centers (n = 18.775, 16.864, 15.693) lie
between the two routes, within 0.08 mol/kg of the pair means. The 21 triangle-isotherm
disagreeing pairs are a marker-center convention offset (~6 px); pair means kept with the
full inter-route deviation as sigma.

Singletons kept (with basis):
- 60 K, P=3.621 MPa: plus stem visible behind 45K square (route-A decode, corroborated by crop)
- 77 K, P=1.872 MPa: cross under 35K triangle; both routes locate it, only A decoded it
- 93 K, P=0.219 MPa: ring chain visibly continuous in crop; B NMS merged it
- 93 K, P=0.411 MPa: ring chain visibly continuous in crop
- 93 K, P=0.499 MPa: ring chain visibly continuous in crop
- 113 K, P=0.457 MPa: open triangle above the declared-ambiguous <0.20 MPa zone
- 113 K, P=4.426 MPa: marker present (both routes); decode disagrees A 17.3 vs B-note 16.3; sigma spans both
- 153 K, P=0.359 MPa: diamond just above the declared-buried <0.35 MPa zone
- 298 K, P=0.489 MPa: asterisk strokes visible in origin crop
- 213 K, P=0.502 MPa: open squares visible in origin crop (route-B point)

Excluded as not unambiguously present/identifiable (pre-registered exclusion, counts reported):
- 40 K, P=0.027 MPa: rise markers 35/40/45K stacked on the y-axis; species identity not unambiguous
- 45 K, P=1.547 MPa: contested identity: route A read two merged 45K squares, route B read a 35K triangle; crop shows merged mass, not separable
- 35 K, P=1.53 MPa: same contested mass as above (route-B reading)
- 298 K, P=0.27 MPa: origin-corner mass (axis + ticks + fit lines); marker not unambiguously separable

Final dataset: 172 points. Axis resolution 0.00492 MPa/px, 0.0616 (mol/kg)/px.

On-axis handling: 2 points whose reconciled pressure lies within one pixel of the
P = 0 axis are recorded at the half-pixel bound P = 0.0025 MPa with quality "on_axis";
their sigma_P is the larger of the route per-point uncertainty and the half-pixel bound
(here 0.0100 and 0.0400 MPa — the route sigmas dominate, the conservative direction).
Their abscissa is unresolved below one pixel, and the errors-in-P measurement model
(pre-registration section 6) weights them accordingly.
