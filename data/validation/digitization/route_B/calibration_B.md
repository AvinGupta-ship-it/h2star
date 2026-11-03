# Calibration & extraction notes — Fig. 1(a), Richard, Bénard & Chahine, *Adsorption* 15 (2009)

Digitization B: fully scripted template-matching extraction from `fig1a_crop.png`
(600 dpi crop, 2350 x 1550 px). Excess adsorption isotherms of H2 on AX-21,
11 temperatures. Script: `extract.py` (deterministic; re-running reproduces
`digitized_B.csv` and `overlay_final.png` exactly).

## 1. Axis calibration

Axis lines detected as the longest dark pixel runs:
y-axis at column x = 500 (run 499–501), x-axis at row y = 1065 (run 1064–1066).

Major-tick pixel coordinates (tick protrusions matched to tick-label glyph
centroids found by connected-component analysis):

| P (MPa) | x px  |   | n (mol/kg) | y px  |
|--------:|------:|---|-----------:|------:|
| 0 | 500.0 | | 0  | 1065.0 |
| 1 | 706.0 | | 10 |  903.0 |
| 2 | 906.0 | | 20 |  741.0 |
| 3 | 1112.0 | | 30 |  578.0 |
| 4 | 1313.0 | | 40 |  416.0 |
| 5 | 1519.0 | | 50 |  254.0 |
| 6 | 1719.0 | |    |        |

Least-squares affine transform (image px -> data):

```
x_px = 203.214 * P[MPa]    + 501.07      =>  P = (x_px - 501.07) / 203.214
y_px = -16.226 * n[mol/kg] + 1065.14     =>  n = (1065.14 - y_px) / 16.226
```

Fit residuals: x ticks RMS 1.4 px (max 1.9 px — the renderer snapped ticks to
an alternating 200/206 px raster); y ticks RMS 0.24 px.

**Per-pixel resolution:** 1 px = 0.00492 MPa (4.921 kPa) in P;
1 px = 0.0616 mol/kg (61.6 mmol/kg) in n.

## 2. Marker templates

The 11 legend exemplars were cut from the legend box (vertical borders detected
at x = 1769/2069) as 53 x 53 px tiles centred on the connected-component
centroids at x ~ 1830, y = 138, 254, 347, 450, 553, 659, 756, 871, 965, 1068,
1171 (top to bottom: ●30 K, ▲35 K, ◆40 K, ■45 K, +60 K, x77 K, ○93 K,
△113 K, ◇153 K, □213 K, ✱298 K). All templates share one size, so their
TM_CCOEFF_NORMED maps align pixel-to-pixel.

## 3. Detection pipeline (reproducible)

1. **Greedy matching pursuit** over the plot ROI (x 445–1765, y 120–1125):
   repeatedly take the globally best normalized cross-correlation score over
   all 11 templates, gate by *ink coverage* (fraction of the template's own
   ink that is dark in the image window; curves crossing a marker only add
   ink, so genuine markers keep coverage ~1), accept, erase the accepted
   template's dilated footprint, locally refresh all 11 correlation maps.
   Subpixel peak refinement by 1-D quadratic fits.
   - Pass 1 thresholds: score 0.50 (filled/open), 0.55 (+, x, ✱); coverage
     0.80 (filled), 0.70 (others).
   - Pass 2 (relaxed): score 0.44/0.42/0.47, coverage 0.60/0.52/0.58;
     + and x disabled (their only pass-2 hit was a curve-crossing artifact).
   - Pass 3: open markers and ✱ only, score 0.40–0.42, coverage 0.40–0.45,
     restricted to n < 23.5 (audited: all missing open/✱ points lie below the
     filled-marker bands).
2. **Dense-region recovery**: in eight visually audited boxes where markers of
   one known type overlap so heavily that greedy erasure destroys later ones,
   the type's template is matched against the *original* image; NMS local
   maxima above a per-box threshold with coverage >= 0.90 and no accepted
   same-type detection within 14 px are accepted (boxes: 93 K low-P chain and
   its top; 93 K circles at 3.9–4.9 MPa under the 40/45 K chains; early 113 K,
   153 K, 213 K points; 298 K asterisks crossed by the x-axis; the 35 K
   triangle merged between 40 K diamonds at ~1.34 MPa).
3. **Audited post rules** (each verified on zoomed crops):
   - Filled-marker detections with n < 13 rejected (lowest filled point in the
     figure is the 35 K tail at n ~ 15; blobs in the zero cluster otherwise
     fake triangles/circles).
   - ✱ detections with n > 4.5 rejected (the 298 K chain stays below ~3).
   - On-axis thin-stroke detections (centre within 15 px of the y-axis)
     re-arbitrated between + and x with a ±5 px vertical band through the axis
     masked out: the axis line fakes the asterisk's vertical bar. The two
     on-axis cross-family markers at n ~ 1.9 and 5.4 are assigned to 77 K
     (visible in the figure: the 298 K chain is below n ~ 1 near P = 0, while
     the 77 K rise passes through these heights).
   - Same-family re-arbitration of every accepted detection on the original
     image (radius 10 px, margin 0.08).
   - Isotherm-consistency check: a point deviating > 3 mol/kg from the median
     of >= 3 same-type neighbours within ±0.6 MPa is re-arbitrated across all
     11 templates (radius 12 px); a confirmed-shape point with score < 0.55 is
     dropped as a blob artifact (this removed four false squares the relaxed
     passes had placed on curve crossings / axis gaps); filled shapes that
     "win" in dense blobs where no filled isotherm exists are refused.
     Merged filled markers additionally get a top-half-template tiebreak
     (apex vs flat top), which reassigned the 35 K triangle at P = 4.42
     (merged with the 113 K open triangle) that a square template had claimed.

## 4. Per-point uncertainty (basis)

- Calibration: x-fit RMS 1.4 px, y-fit RMS 0.24 px.
- Peak localisation of clean markers: ~±1 px (subpixel-refined NCC peak).
- Combined for `ok` points: **±0.009 MPa in P, ±0.07 mol/kg in n** (~1.7 px
  and ~1.1 px in quadrature).
- `partial_overlap` points: neighbouring markers bias the correlation peak by
  up to ~5–8 px, so **±0.03–0.04 MPa and ±0.3–0.5 mol/kg**.
- `uncertain` points: match score < 0.62 or accepted in a relaxed pass /
  after re-arbitration; positional accuracy as `partial_overlap`, and the
  marker-type assignment, while audited, carries residual risk.

## 5. Per-isotherm point counts (164 total)

| T (K) | points | ok | uncertain | partial_overlap |
|------:|-------:|---:|----------:|----------------:|
| 30  | 5  | 3  | 0 | 2 |
| 35  | 14 | 9  | 1 | 4 |
| 40  | 19 | 15 | 0 | 4 |
| 45  | 16 | 12 | 0 | 4 |
| 60  | 14 | 13 | 0 | 1 |
| 77  | 10 | 7  | 0 | 3 |
| 93  | 22 | 9  | 0 | 13 |
| 113 | 20 | 11 | 1 | 8 |
| 153 | 17 | 16 | 0 | 1 |
| 213 | 14 | 9  | 0 | 5 |
| 298 | 13 | 9  | 0 | 4 |

## 6. Ambiguous / unresolved regions (markers present but not reported)

- **Zero cluster (P < ~0.6 MPa, n < ~6):** first points of 113/153/213/298 K
  plus x-arms overlap into a solid blob. Recovered: 113 K down to 0.18 MPa,
  153 K to 0.49, 213 K to 0.50, ✱ to 0.89. Visually ~2–4 further markers
  (153 K below 0.49, 213 K below 0.50, ✱ below 0.85) remain merged and are
  **not** reported.
- **93 K rise below P ~ 0.45:** circles overlap 60–80 %. Nine chain points
  recovered down to P = 0.16; 1–3 intermediate circles closer than the NMS
  radius could not be separated.
- **30–45 K steep rise at P < ~0.15:** markers stack on the y-axis. First
  points of 30/35/45 K at P ~ 0.01–0.02 are reported (flagged); any further
  rise markers of 35/40/45 K between P ~ 0.03 and 0.14 are merged with the
  axis/each other and are not resolvable. (The 40 K point at P = 0.146 is its
  lowest resolvable marker.)
- **77 K x at P ~ 1.9** lies beneath the 35 K filled triangle at (1.90, 26.2)
  and cannot be recovered.
- **113 K open triangle at ~(4.42, 16.3)** is merged with the 35 K filled
  triangle reported at that location; its own centre cannot be separated.
- 77 K has no markers beyond P ~ 5.0 and 93 K none beyond P ~ 5.42
  (verified by probing: no NCC peak > 0.30).

## 7. Files

- `digitized_B.csv` — temperature_K, pressure_MPa, n_excess_molkg, quality.
- `overlay_final.png` — all accepted detections ringed and labelled on the
  original figure (thick ring = ok, thin ring = flagged; "?" suffix on label).
- `extract.py` — the full pipeline; run `python3 extract.py` in this
  directory to reproduce everything.
