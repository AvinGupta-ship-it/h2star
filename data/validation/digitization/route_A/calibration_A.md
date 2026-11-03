# Calibration and digitization notes — Figure 1(a), Richard, Bénard & Chahine, Adsorption 15 (2009) 43–51

Source image: `fig1a_crop.png`, 2350 x 1550 px, 600-dpi scan crop.
Excess adsorption isotherms of H2 on activated carbon AX-21; markers digitized, model lines ignored.

## 1. Axis calibration

### Tick positions located (pixel coordinates)

X axis (major ticks, identified as the longest tick strokes below the axis line, depth 16 px):

| P (MPa) | x_px   |
|---------|--------|
| 0       | 500.0  |
| 1       | 706.0  |
| 2       | 906.0  |
| 3       | 1112.0 |
| 4       | 1313.0 |
| 5       | 1519.0 |
| 6       | 1719.0 |

Y axis (major ticks, depth-15 strokes left of the axis line at x = 499):

| n (mol/kg) | y_px   |
|------------|--------|
| 0          | 1065.0 |
| 10         | 903.0  |
| 20         | 741.0  |
| 30         | 578.0  |
| 40         | 416.0  |
| 50         | 254.0  |

Plot frame: y-axis line at x = 499–501; x-axis line at y = 1064–1066 (the y = 0 gridline coincides with the x-axis).

### Affine transform (least-squares fit through all major ticks)

- P [MPa]     = 0.00492085 * x_px − 2.465662
- n [mol/kg]  = −0.06163052 * y_px + 65.645330

Fit residuals at the ticks: |ΔP| ≤ 0.009 MPa (x), |Δn| ≤ 0.023 mol/kg (y). The small
residuals come from the alternating 200/206-px major-tick spacing of the scanned
figure (scan raster/rounding), not from skew; no rotation correction was needed
(axis lines are parallel to the pixel grid within 1 px over their full length).

### Resolution

- 1 px = 0.004921 MPa  (203.17 px per MPa)
- 1 px = 0.061631 mol/kg  (162.25 px per 10 mol/kg; 16.22 px per mol/kg)

## 2. Marker identification method

Templates for all 11 marker types were cut from the figure's own legend
(markers at x = 1810–1852, same rendering size as in the plot; outer size 37 px for
circle/square, 43 px for triangle/diamond/plus/cross/asterisk).
Centers were then located by combining, per marker family:

1. Normalized cross-correlation (cv2 TM_CCOEFF_NORMED) against the legend template,
   with competition between templates at each candidate site;
2. Morphological opening (17-px disc) + connected components + distance transform
   for the filled markers (the distance-transform inradius separates square 19.0,
   circle 17.6–18.2, diamond 15.4–16.4, triangle 14.2–14.6 px and is insensitive to
   the 4–6 px fit lines through the markers);
3. Hough circle transform (r = 14–18 px) and white-interior ("hole"/crescent)
   centroids for the heavily overlapped 93 K ring chain;
4. Directional stroke tests (fraction of dark pixels along vertical / horizontal /
   both diagonals through the candidate center) to separate plus, cross (x) and
   asterisk from each other and from fit-line crossings;
5. Zoomed visual inspection (4x–9x crops, including printed binary pixel maps) of
   every congested region; every recorded point corresponds to a marker located in
   the image, and disputed detections were accepted or rejected on the pixel maps.

False positives rejected by structure: axis ticks + axis line (mimic plus),
open-square sides + fit line (mimic plus at +-15 px of each 213 K square),
fit-line segments at 45 deg (mimic single diagonals of x), line-crossing "boxes"
(mimic open squares at (1501,762), (1605,793), (1628-1721, 637-645) etc.).

## 3. Per-point digitization uncertainty

Estimated from (a) the spread between independent center estimates for the same
marker (template NCC vs. distance transform vs. visual decode of apex/base rows:
typically 1–2 px for clean markers, 3–6 px where markers overlap), plus (b) the
calibration residuals above. In data units:

- quality = ok:              ±0.010 MPa, ±0.10 mol/kg  (±1.5 px center, ±tick residual)
- quality = uncertain:       ±0.017 MPa, ±0.20 mol/kg  (±3 px center)
- quality = partial_overlap: ±0.027 MPa, ±0.33 mol/kg  (±5 px center)

Markers centered on the y axis (first points of several isotherms) have pressures
indistinguishable from 0 at this resolution; computed values between −0.01 and
0 MPa were clipped to 0.000.

## 4. Points per isotherm (174 total)

| T (K) | points | ok | uncertain | partial_overlap |
|-------|--------|----|-----------|-----------------|
| 30    | 5      | 5  | 0         | 0               |
| 35    | 13     | 10 | 1         | 2               |
| 40    | 20     | 19 | 0         | 1               |
| 45    | 17     | 14 | 1         | 2               |
| 60    | 15     | 12 | 2         | 1               |
| 77    | 11     | 8  | 1         | 2               |
| 93    | 25     | 12 | 1         | 12              |
| 113   | 22     | 14 | 6         | 2               |
| 153   | 18     | 15 | 3         | 0               |
| 213   | 13     | 13 | 0         | 0               |
| 298   | 15     | 13 | 2         | 0               |

Notable resolved features:
- 30 K has only 5 markers; its model line ends at ~0.68 MPa (near-saturation isotherm).
- 45 K contains two badly overlapped squares at P = 1.42 and 1.55 MPa (n = 39.4);
  the merged silhouette is 62 px wide at exact square height, which only two
  squares can produce.
- At P ≈ 0 a filled triangle (35 K) and filled diamond (40 K) are stacked at
  n ≈ 28.6–29.3; both recorded as partial_overlap.
- At x = 1400 px (P = 4.42 MPa) the 113 K open triangle (center y 784.5) sits
  concentric over the 35 K filled triangle (center y 796.5); both decoded from the
  binary pixel map (open apex row 763, filled base row 818).
- A 60 K plus at (1237, 564) px is hidden behind the 45 K square at P = 3.62 MPa;
  its vertical stem is visible above the square.
- The two 77 K crosses at P ≈ 0 (n = 1.95 and 5.46) sit on the y-axis line
  (Henry-region points); the axis masks any distinction between their vertical
  strokes and the axis itself.

## 5. Ambiguous / unresolved regions (markers NOT individually recorded)

1. 93 K, P ≈ 0.13–0.50 MPa (x = 525–600 px): the open circles form a continuous
   chain with ~6–10 px spacing (ring diameter 37 px). Ten ring positions were
   recovered from interior-crescent centroids + Hough + arc inspection and are
   recorded as partial_overlap, but the exact COUNT in this stretch is uncertain
   by ±1 ring (an additional ring near x ≈ 566–571 px, P ≈ 0.33, and/or near
   x ≈ 545 px cannot be excluded or confirmed; adjacent crescent spacing falls
   to ~5 px there).
2. 113 K, P < 0.20 MPa (x = 500–540 px, y = 980–1010 px): the open-triangle chain
   continues into a solid mass next to the y axis; 1–2 further triangles (e.g.
   near (530, 988) and (520, 996) px) are likely present but individually
   unresolvable. The six recorded chain members at x = 543–594 px were decoded
   from apex pixels, base strokes and paired side strokes (uncertain quality).
3. 153 K, P < 0.35 MPa (x = 500–570 px): any open diamonds below the first
   recorded one at (574, 1027.5) px are buried in the origin-corner mass
   (diamonds + asterisks + 4 fit lines + axis); none recorded.
4. 213 K, P < 0.80 MPa (x = 500–660 px): possible open squares left of the first
   recorded one at (665.5, 1043.5) px are buried in the same origin-corner mass;
   none recorded.
5. 298 K, P < 0.25 MPa: possible asterisks left of (556, 1063.5) px are
   unresolvable against the x axis, ticks and the origin-corner mass; none
   recorded.
6. The origin corner itself (x = 500–560, y = 1020–1066 px) contains at least one
   unassignable open-diamond-like outline near (550, 1040) px; not recorded.

## 6. Output

`digitized_A.csv` — 174 rows, columns: temperature_K, pressure_MPa,
n_excess_molkg, quality (ok | uncertain | partial_overlap).
`overlay_final.png` — audit overlay with every recorded center marked on the scan.
