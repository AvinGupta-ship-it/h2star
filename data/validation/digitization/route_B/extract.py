#!/usr/bin/env python3
"""
extract.py -- scripted digitization of Fig 1(a), Richard, Benard & Chahine,
Adsorption 15 (2009): excess H2 adsorption on AX-21, 11 isotherms.

Pipeline (fully algorithmic detection; thresholds tuned by visual audit):
 1. Axis calibration: detect y-axis column / x-axis row as the longest dark
    lines; detect major ticks (x: protrusions below axis matched to digit-label
    centroids; y: protrusions left of axis matched to label rows); least-squares
    affine pixel->data fit.
 2. Legend templates: the 11 marker exemplars are cut from the legend box
    (detected as the two tall vertical lines right of the plot), 53x53 px each.
 3. Greedy matching pursuit: iteratively take the globally best
    TM_CCOEFF_NORMED score over all 11 templates, gate it by ink coverage
    (fraction of the template's own ink dark in the window), accept, erase the
    template footprint, and locally refresh all correlation maps.  Two passes:
    strict thresholds, then relaxed thresholds (accepted points flagged).
 4. Post rules (each verified in the zoom audit):
    - filled-marker (30-45 K) detections in the zero cluster (n<10, P<1.2)
      rejected in-loop: those isotherms have no data there;
    - asterisk detections with n>4.5 rejected (298 K chain stays below ~3);
    - on-axis thin-stroke detections (cx<515) re-arbitrated between + and x
      with the axis band masked out (the axis line fakes the asterisk's
      vertical bar; 298 K visibly has n<1 near P=0, so cross-family on-axis
      detections at n~2-6 belong to 77 K);
    - same-family re-arbitration on the original image (radius 10 px, margin
      0.08): fixes greedy mislabels such as the 35 K triangle at P~4.4 that a
      square template claimed after merging with the 113 K open triangle.
 5. Quality: partial_overlap if another accepted center is within 30 px or the
    point lies in the audited dense zones; uncertain if score<0.62, pass 2, or
    relabeled; else ok.
Outputs: digitized_B.csv, overlay_final.png, prints per-isotherm counts.
"""
import numpy as np, cv2
from PIL import Image, ImageDraw
from collections import Counter

IMG = 'fig1a_crop.png'
gray = np.array(Image.open(IMG).convert('L')).astype(np.float32)
H, W = gray.shape
dark = gray < 128

# ----------------------------------------------------------------- calibration
def runs(idx, gap=4):
    out = []
    if len(idx) == 0: return out
    s = p = idx[0]
    for v in idx[1:]:
        if v - p > gap: out.append((s, p)); s = v
        p = v
    out.append((s, p))
    return out

colsum = dark.sum(axis=0)
tallcols = np.where(colsum > 700)[0]
# y-axis = leftmost tall-column run; legend box = next two runs
colruns = runs(tallcols)
yaxis_x = int(np.mean(colruns[0]))
leg_x0, leg_x1 = int(np.mean(colruns[1])), int(np.mean(colruns[2]))
rowsum = dark.sum(axis=1)
xaxis_y = int(np.argmax(rowsum))          # 1065

# x major ticks: digit labels below axis define which protrusions are majors
band = dark[xaxis_y + 25:xaxis_y + 135, :].astype(np.uint8)
n, lab, stats, cents = cv2.connectedComponentsWithStats(band, 8)
labx = sorted(cents[i][0] for i in range(1, n)
              if stats[i][4] > 300 and stats[i][3] > 40 and 440 < cents[i][0] < leg_x0 - 20)
assert len(labx) == 7, labx
tickband = dark[xaxis_y + 3:xaxis_y + 17, :]
cand = [(a + b) / 2 for a, b in runs(np.where(tickband.sum(axis=0) >= 10)[0])]
xticks = []
for lx in labx:
    best = min(cand, key=lambda c: abs(c - lx))
    assert abs(best - lx) < 12, (lx, best)
    xticks.append(best)
# y major ticks: protrusions left of axis matched to label rows
band = dark[:, 300:yaxis_x - 20].astype(np.uint8)
n, lab, stats, cents = cv2.connectedComponentsWithStats(band, 8)
labrows = [cents[i][1] for i in range(1, n) if stats[i][4] > 300 and stats[i][3] > 40
           and 140 < cents[i][1] < xaxis_y + 10 and cents[i][0] + 300 > yaxis_x - 120]
labrows = sorted(np.mean(g) for g in
                 [[labrows[i] for i in range(len(labrows)) if abs(labrows[i] - r) < 20]
                  for r in sorted(set(round(v, -1) for v in labrows))])
labrows = sorted(set(round(r, 1) for r in labrows))
grp = []
for r in labrows:
    if not grp or r - grp[-1][-1] > 25: grp.append([r])
    else: grp[-1].append(r)
labrows = [np.mean(g) for g in grp]
assert len(labrows) == 6, labrows
tb = dark[:, yaxis_x - 22:yaxis_x - 3]
candy = [(a + b) / 2 for a, b in runs(np.where(tb.sum(axis=1) >= 12)[0])]
yticks = []
for lr in labrows:
    best = min(candy, key=lambda c: abs(c - lr))
    assert abs(best - lr) < 15, (lr, best)
    yticks.append(best)

xv = np.arange(7.0); yvv = np.arange(50.0, -1, -10)  # labels read 50..0 top to bottom
axf = np.polyfit(xv, xticks, 1)      # px = axf[0]*MPa + axf[1]
ayf = np.polyfit(yvv, yticks, 1)     # px = ayf[0]*molkg + ayf[1]
def to_data(cy, cx): return (cx - axf[1]) / axf[0], (cy - ayf[1]) / ayf[0]
def to_px(P, nn):    return ayf[0] * nn + ayf[1], axf[0] * P + axf[1]

print(f"calibration: x ticks px={['%.1f'%t for t in xticks]}")
print(f"             y ticks px={['%.1f'%t for t in yticks]}")
print(f"  x: px = {axf[0]:.3f}*P[MPa] + {axf[1]:.2f}   -> {1/axf[0]*1000:.3f} kPa/px")
print(f"  y: px = {ayf[0]:.3f}*n[mol/kg] + {ayf[1]:.2f} -> {abs(1/ayf[0]):.4f} (mol/kg)/px")

# ------------------------------------------------------------ legend templates
names = ["30K_fcirc","35K_ftri","40K_fdia","45K_fsq","60K_plus","77K_cross",
         "93K_ocirc","113K_otri","153K_odia","213K_osq","298K_ast"]
temps = [30,35,40,45,60,77,93,113,153,213,298]
FILLED, OPEN, THIN = {0,1,2,3}, {6,7,8,9}, {4,5,10}
family = {**{i:'f' for i in FILLED}, **{i:'o' for i in OPEN}, **{i:'t' for i in THIN}}

legband = dark[95:1240, leg_x0+6:leg_x0+120].astype(np.uint8)
n, lab, stats, cents = cv2.connectedComponentsWithStats(legband, 8)
marks = sorted((cents[i][1]+95, cents[i][0]+leg_x0+6) for i in range(1, n)
               if stats[i][4] > 400 and stats[i][2] > 30 and stats[i][3] > 30)
assert len(marks) == 11, marks
T, R = 53, 26
tpls, imasks, emasks = [], [], []
for (cy, cx) in marks:
    cy, cx = int(round(cy)), int(round(cx))
    t = 255.0 - gray[cy-R:cy+R+1, cx-R:cx+R+1]
    tpls.append(t.astype(np.float32))
    core = (t > 127).astype(np.uint8)
    imasks.append(core.astype(bool))
    emasks.append(cv2.dilate(core, np.ones((5,5),np.uint8)).astype(bool))

# ------------------------------------------------------- greedy matching pursuit
inv = 255.0 - gray
X0, X1, Y0, Y1 = 445, leg_x0 - 4, 120, 1125
roi = inv[Y0:Y1, X0:X1].copy()
S = np.stack([cv2.matchTemplate(roi, t, cv2.TM_CCOEFF_NORMED) for t in tpls])
valid = np.ones_like(S, dtype=bool)

THR1 = np.array([.50,.50,.50,.50,.55,.55,.50,.50,.50,.50,.55])
COV1 = np.array([.80,.80,.80,.80,.70,.70,.70,.70,.70,.70,.70])
THR2 = np.array([.44,.44,.44,.44,2.0,2.0,.42,.42,.42,.42,.47])  # +/x pass-1 only (audited)
COV2 = np.array([.60,.60,.60,.60,.58,.58,.52,.52,.52,.52,.58])
THR3 = np.array([2.0,2.0,2.0,2.0,2.0,2.0,.40,.40,.40,.40,.42])  # open + asterisk only
COV3 = np.array([.60,.60,.60,.60,.45,.45,.40,.40,.40,.40,.45])

detections = []   # [score, cy, cx, type, cov, pass_id]
def run_pass(thr, cov_req, pass_id, max_iter, n_cap=None):
    global S, valid, roi
    taken = 0
    th = thr[:, None, None]
    for _ in range(max_iter):
        Sm = np.where(valid, S, -2.0) - th
        ti, py, px = np.unravel_index(np.argmax(Sm), Sm.shape)
        if Sm[ti, py, px] <= 0: break
        score = float(S[ti, py, px])
        cy, cx = py + R, px + R
        icy, icx = cy + Y0, cx + X0
        P, nn = to_data(icy, icx)
        win = roi[cy-R:cy+R+1, cx-R:cx+R+1] > 100
        cov = (win & imasks[ti]).sum() / imasks[ti].sum()
        reject = cov < cov_req[ti]
        # audited in-loop guards:
        if not reject and ti in FILLED and nn < 13:
            reject = True          # audited: lowest filled-marker point is 35 K tail at n~15
        if not reject and ti == 10 and nn > 4.5:
            reject = True          # 298 K chain stays below ~3 mol/kg
        if not reject and n_cap is not None and nn > n_cap:
            reject = True          # audited: pass-3 targets lie below the filled bands
        if reject:
            valid[ti, max(0,py-1):py+2, max(0,px-1):px+2] = False
            continue
        # subpixel peak refinement (quadratic, each axis)
        dy = dx = 0.0
        if 0 < py < S.shape[1]-1 and 0 < px < S.shape[2]-1:
            c = S[ti]
            d1 = (c[py,px+1]-c[py,px-1])/2; d2 = c[py,px+1]-2*c[py,px]+c[py,px-1]
            if d2 < 0: dx = np.clip(-d1/d2, -1, 1)
            d1 = (c[py+1,px]-c[py-1,px])/2; d2 = c[py+1,px]-2*c[py,px]+c[py-1,px]
            if d2 < 0: dy = np.clip(-d1/d2, -1, 1)
        detections.append([score, icy+dy, icx+dx, ti, cov, pass_id])
        taken += 1
        roi[cy-R:cy+R+1, cx-R:cx+R+1][emasks[ti]] = 0.0
        ry0, ry1 = max(0, cy-2*T), min(roi.shape[0], cy+2*T)
        rx0, rx1 = max(0, cx-2*T), min(roi.shape[1], cx+2*T)
        patch = roi[ry0:ry1, rx0:rx1]
        for j in range(11):
            pr = cv2.matchTemplate(patch, tpls[j], cv2.TM_CCOEFF_NORMED)
            S[j, ry0:ry0+pr.shape[0], rx0:rx0+pr.shape[1]] = pr
    return taken

n1 = run_pass(THR1, COV1, 1, 600)
n2 = run_pass(THR2, COV2, 2, 300)
n3 = run_pass(THR3, COV3, 3, 100, n_cap=23.5)
print(f"pass1 accepted {n1}, pass2 accepted {n2}, pass3 accepted {n3}")

# ------------------------------------------------- post arbitration & rules
def ncc(win, tpl, mask=None):
    w = win.astype(np.float64); t = tpl.astype(np.float64)
    if mask is not None: w = w[mask]; t = t[mask]
    w = w - w.mean(); t = t - t.mean()
    d = np.sqrt((w*w).sum()*(t*t).sum())
    return float((w*t).sum()/d) if d > 0 else 0.0

relabels = []
# (a) on-axis thin-stroke arbitration between + and x with axis band masked
axband = np.ones((T, T), dtype=bool)
for det in detections:
    s, cy, cx, ti, cov, pid = det
    if ti in THIN and cx < yaxis_x + 15:
        iy, ix = int(round(cy)), int(round(cx))
        win = inv[iy-R:iy+R+1, ix-R:ix+R+1]
        m = axband.copy()
        c0 = int(round(yaxis_x - (ix - R)))
        m[:, max(0,c0-5):c0+6] = False
        sc = {j: ncc(win, tpls[j], m) for j in (4, 5)}   # plus, cross
        new = max(sc, key=sc.get)
        if new != ti:
            relabels.append((temps[ti], temps[new], to_data(cy,cx), 'axis-masked'))
            det[3] = new; det[5] = 9
# (b) same-family re-arbitration on the original image (radius 10, margin 0.08)
RAD, MARGIN = 10, 0.08
for det in detections:
    s, cy, cx, ti, cov, pid = det
    if ti in THIN and cx < yaxis_x + 15:
        continue   # axis-masked arbitration already decided
    iy, ix = int(round(cy)), int(round(cx))
    sub = inv[iy-R-RAD:iy+R+RAD+1, ix-R-RAD:ix+R+RAD+1]
    if sub.shape != (T+2*RAD, T+2*RAD): continue
    best_t, best_s, best_pos = ti, -2, (cy, cx)
    for j in range(11):
        if family[j] != family[ti]: continue
        r = cv2.matchTemplate(sub, tpls[j], cv2.TM_CCOEFF_NORMED)
        k = np.unravel_index(np.argmax(r), r.shape)
        if r[k] > best_s:
            best_t, best_s, best_pos = j, float(r[k]), (iy-RAD+k[0], ix-RAD+k[1])
    own = cv2.matchTemplate(sub, tpls[ti], cv2.TM_CCOEFF_NORMED).max()
    if best_t != ti and best_s > own + MARGIN:
        relabels.append((temps[ti], temps[best_t], to_data(cy,cx), f'family {best_s:.2f}>{own:.2f}'))
        det[3] = best_t; det[1], det[2] = best_pos; det[5] = 9
for r in relabels: print("RELABEL:", r)


# (b2) dense-region recovery: in five visually audited boxes the markers of a
#     single known type overlap each other so heavily that greedy erasure
#     destroys the later ones.  There we match the type's template against the
#     ORIGINAL image (no erasure shadows), take NMS local maxima above a
#     per-box threshold with ink coverage >= 0.90, and accept any peak that is
#     not within 14 px of an already accepted detection.  All recovered points
#     are flagged partial_overlap via the neighbour rule or the dense-zone rule.
from scipy.ndimage import maximum_filter
BOXES = [  # (type idx, x0, y0, x1, y1, thr)
    (6, 525, 845, 600, 925, 0.33),   # 93 K low-P chain
    (7, 525, 930, 625, 995, 0.33),   # 113 K early triangles
    (8, 585, 1000, 625, 1028, 0.35), # 153 K early diamonds
    (9, 590, 1035, 645, 1065, 0.33), # 213 K early squares
    (10, 605, 1035, 790, 1078, 0.45),# 298 K asterisks crossed by the x-axis
    (1, 745, 330, 815, 410, 0.50),   # 35 K triangle merged between 40 K diamonds at ~1.34 MPa
    (6, 600, 805, 650, 845, 0.45),   # 93 K circle at ~0.59 MPa (chain top)
    (6, 1290, 690, 1515, 720, 0.42), # 93 K circles at 3.9-4.9 MPa under the 40/45 K chains
]
for ti, bx0, by0, bx1, by1, bthr in BOXES:
    sub = inv[by0-R:by1+R, bx0-R:bx1+R]
    res = cv2.matchTemplate(sub, tpls[ti], cv2.TM_CCOEFF_NORMED)
    mx = maximum_filter(res, size=9)
    ys, xs = np.where((res == mx) & (res > bthr))
    cand = sorted(zip(res[ys, xs], ys, xs), reverse=True)
    newpts = []
    for s, y, x in cand:
        cy, cx = by0 - R + y + R, bx0 - R + x + R
        if not (by0 <= cy < by1 and bx0 <= cx < bx1): continue
        win = inv[cy-R:cy+R+1, cx-R:cx+R+1] > 100
        if (win & imasks[ti]).sum() / imasks[ti].sum() < 0.90: continue
        if any(d[3] == ti and (d[1]-cy)**2 + (d[2]-cx)**2 < 14**2 for d in detections): continue
        if any((py-cy)**2 + (px-cx)**2 < 9**2 for _,py,px in newpts): continue
        newpts.append((float(s), cy, cx))
    for s, cy, cx in newpts:
        P0, n0 = to_data(cy, cx)
        print(f"RECOVER {temps[ti]}K P={P0:.3f} n={n0:.2f} s={s:.3f}")
        detections.append([s, float(cy), float(cx), ti, 1.0, 4])

# (c) conservative isotherm-consistency check: a point whose n deviates by
#     more than 6 mol/kg from the median of >=3 same-type neighbours within
#     +-0.6 MPa is re-arbitrated across all 11 templates (radius 12); if the
#     winner duplicates an existing same-type point (<20 px) it is dropped;
#     if its own type is confirmed it is dropped only when score < 0.55
#     (a weak blob); on-axis detections are exempt.  Suspects are processed
#     in order of decreasing deviation and deviations are re-evaluated after
#     each fix, so one bad point cannot drag down its genuine neighbours.
def deviation(dets, i):
    s, cy, cx, ti, cov, pid = dets[i]
    P0, n0 = to_data(cy, cx)
    if cx < yaxis_x + 15: return 0.0
    if pid == 4: return 0.0   # box-audited recovery points; steep chains break the median test
    if pid == 9: return 0.0   # already individually re-arbitrated and audited
    nb = [to_data(d[1], d[2])[1] for j, d in enumerate(dets)
          if j != i and d[3] == ti and abs(to_data(d[1], d[2])[0] - P0) <= 0.6]
    if len(nb) < 3: return 0.0
    return abs(n0 - float(np.median(nb)))

exempt = set()
while True:
    devs = [0.0 if id(detections[i]) in exempt else deviation(detections, i)
            for i in range(len(detections))]
    i = int(np.argmax(devs))
    if devs[i] <= 3.0: break
    s, cy, cx, ti, cov, pid = detections[i]
    P0, n0 = to_data(cy, cx)
    iy, ix = int(round(cy)), int(round(cx)); RAD2 = 12
    sub = inv[iy-R-RAD2:iy+R+RAD2+1, ix-R-RAD2:ix+R+RAD2+1]
    if sub.shape != (T+2*RAD2, T+2*RAD2):
        print(f"DROP (outlier, edge): {temps[ti]}K P={P0:.2f} n={n0:.2f}"); del detections[i]; continue
    best = {}
    for j in range(11):
        r = cv2.matchTemplate(sub, tpls[j], cv2.TM_CCOEFF_NORMED)
        k = np.unravel_index(np.argmax(r), r.shape)
        best[j] = (float(r[k]), iy-RAD2+k[0], ix-RAD2+k[1])
    newt = max(best, key=lambda j: best[j][0])
    ns, nyy, nxx = best[newt]
    if newt == ti:
        if s < 0.55:
            print(f"DROP (outlier, weak {temps[ti]}K blob): P={P0:.2f} n={n0:.2f} s={s:.2f}")
            del detections[i]
            continue
        if ti in FILLED:
            # merged-marker tiebreak: the top half (apex vs flat top vs point)
            # separates filled shapes that overlap-blobs confuse
            iy2, ix2 = int(round(cy)), int(round(cx))
            best2 = {}
            for j in FILLED:
                r = cv2.matchTemplate(sub[:R+RAD2+R//2, :], tpls[j][:R, :], cv2.TM_CCOEFF_NORMED)
                k = np.unravel_index(np.argmax(r), r.shape)
                best2[j] = (float(r[k]), iy-RAD2+k[0]+R, ix-RAD2+k[1])
            newt2 = max(best2, key=lambda j: best2[j][0])
            if newt2 != ti and best2[newt2][0] > best2[ti][0] + 0.05:
                ns2 = best2[newt2][0]
                _, nyy2, nxx2 = best[newt2]   # centre from the winner's full-template match
                print(f"RELABEL (top-half tiebreak): {temps[ti]}K -> {temps[newt2]}K at P={P0:.2f} n={n0:.2f} -> P={to_data(nyy2,nxx2)[0]:.2f} n={to_data(nyy2,nxx2)[1]:.2f} ({best2[newt2][0]:.2f} vs {best2[ti][0]:.2f})")
                detections[i][3], detections[i][1], detections[i][2], detections[i][5] = newt2, float(nyy2), float(nxx2), 9
                exempt.add(id(detections[i]))
                continue
        print(f"KEEP (outlier but solid {temps[ti]}K, s={s:.2f}): P={P0:.2f} n={n0:.2f} -- audit!")
        if s < 0.65: detections[i][5] = 9
        exempt.add(id(detections[i]))
        continue
    dup = any(j != i and detections[j][3] == newt and
              (detections[j][1]-nyy)**2 + (detections[j][2]-nxx)**2 < 20**2
              for j in range(len(detections)))
    if dup:
        print(f"DROP (outlier -> dup {temps[newt]}K): was {temps[ti]}K P={P0:.2f} n={n0:.2f}")
        del detections[i]; continue
    if newt in FILLED and to_data(nyy, nxx)[1] < 13:
        # a filled marker cannot exist here (audited); keep the original label,
        # which the box audit supports, and leave the point flagged
        print(f"KEEP (relabel hit filled guard, kept {temps[ti]}K): P={P0:.2f} n={n0:.2f}")
        detections[i][5] = 9
        exempt.add(id(detections[i])); continue
    print(f"RELABEL (outlier): {temps[ti]}K -> {temps[newt]}K at P={P0:.2f} n={n0:.2f} -> P={to_data(nyy,nxx)[0]:.2f} n={to_data(nyy,nxx)[1]:.2f}")
    detections[i][3], detections[i][1], detections[i][2], detections[i][5] = newt, float(nyy), float(nxx), 9

# ------------------------------------------------------------- quality + output
pts = []
for s, cy, cx, ti, cov, pid in detections:
    P, nn = to_data(cy, cx)
    pts.append(dict(T=temps[ti], ti=ti, P=P, n=nn, cy=cy, cx=cx, score=s, cov=cov, pid=pid))
for i, p in enumerate(pts):
    neigh = any(j != i and (q['cy']-p['cy'])**2 + (q['cx']-p['cx'])**2 < 30**2
                for j, q in enumerate(pts))
    dense = (p['P'] < 0.55 and p['n'] < 16) or p['cx'] < yaxis_x + 15
    if neigh or dense: p['q'] = 'partial_overlap'
    elif p['score'] < 0.62 or p['pid'] >= 2: p['q'] = 'uncertain'
    else: p['q'] = 'ok'
pts.sort(key=lambda p: (p['T'], p['P']))
with open('digitized_B.csv', 'w') as f:
    f.write("temperature_K,pressure_MPa,n_excess_molkg,quality\n")
    for p in pts:
        f.write(f"{p['T']},{p['P']:.4f},{p['n']:.3f},{p['q']}\n")

im = Image.open(IMG).convert('RGB')
dr = ImageDraw.Draw(im)
colors = [(230,25,75),(60,180,75),(0,130,200),(245,130,48),(145,30,180),(0,160,160),
          (240,50,230),(130,160,0),(150,75,0),(0,0,160),(200,130,0)]
for p in pts:
    c = colors[p['ti']]; cy, cx = p['cy'], p['cx']
    w = 4 if p['q'] == 'ok' else 2
    dr.ellipse([cx-R, cy-R, cx+R, cy+R], outline=c, width=w)
    dr.line([cx-6, cy, cx+6, cy], fill=c, width=2)
    dr.line([cx, cy-6, cx, cy+6], fill=c, width=2)
    tag = f"{p['T']}" + ("?" if p['q'] != 'ok' else "")
    dr.text((cx+R-6, cy-R-16), tag, fill=c)
im.save('overlay_final.png')

print("\nper-isotherm counts:")
cnt = Counter(p['T'] for p in pts)
qc = Counter((p['T'], p['q']) for p in pts)
for t in temps:
    print(f"  {t:>3} K: {cnt.get(t,0):2d}  (ok {qc.get((t,'ok'),0)}, "
          f"uncertain {qc.get((t,'uncertain'),0)}, overlap {qc.get((t,'partial_overlap'),0)})")
print(f"total {len(pts)}")
print(f"resolution: {1000/axf[0]:.3f} kPa/px, {abs(1/ayf[0])*1000:.1f} (mmol/kg)/px")
