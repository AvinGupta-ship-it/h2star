"""Reconcile the two digitization routes of Richard et al. (2009) Fig. 1a.

Fully reproducible from committed inputs (referee round-1 M7 fix): the two
route CSVs and calibration notes are archived under
``data/validation/digitization/`` together with the shared 600-dpi source
crop (identical file in both routes, md5 561313e1d49ac47ba922d119dbaa1fa2),
and the single documented re-inspection is encoded as data in
``reinspection_decisions.csv`` so this script regenerates the published
dataset byte-for-byte. Verify with ``--check``.

The frozen rule (docs/preregistration_v1.0.md section 5,
DOI 10.5281/zenodo.23931242):

    "per isotherm, points are matched across routes by nearest pressure; a
    matched pair agreeing within twice the larger route's stated per-point
    resolution in both coordinates is reconciled to the coordinate-wise mean;
    disagreeing pairs and unmatched points are re-inspected against the figure
    once, and kept only if a marker is unambiguously present, with the larger
    route deviation recorded as their uncertainty; points neither route
    resolves ... are excluded with their count reported."

The re-inspection (performed once, 2026-11-03, documented in
``data/validation/ax21_fig1a_multiT_reconciliation.md``) re-read the flagged
markers from the crop — for the two triangle-marker isotherms (35 K, 113 K)
after measuring the marker-centre convention offset from isolated glyphs —
and recorded, per flagged reading: keep as a pair (coordinate-wise mean of
the re-read values, uncertainty = the full inter-route deviation, floored at
the route class sigma and the pixel), keep as a single-route point (with its
re-inspection uncertainty), clamp to the half-pixel on-axis bound, or
exclude. Those recorded outcomes are the decisions file; this script applies
them mechanically.

Route per-point uncertainties (from the routes' own calibration notes):
  A: ok +/-0.010 MPa, +/-0.10 mol/kg; uncertain +/-0.017, +/-0.20;
     partial_overlap +/-0.027, +/-0.33
  B: ok +/-0.009 MPa, +/-0.07 mol/kg; uncertain/partial +/-0.04, +/-0.50
Matching tolerance: twice the larger route uncertainty for the pair, per the
frozen rule. Axis resolution floor (both routes agree): 0.00492 MPa,
0.0616 mol/kg per pixel.
"""

import csv
import os
import sys

DIG = os.path.join(os.path.dirname(__file__), "..", "data", "validation",
                   "digitization")
A_CSV = os.path.join(DIG, "route_A", "digitized_A.csv")
B_CSV = os.path.join(DIG, "route_B", "digitized_B.csv")
DECISIONS = os.path.join(DIG, "reinspection_decisions.csv")
OUT = os.path.join(
    os.path.dirname(__file__), "..", "data", "validation",
    "ax21_fig1a_multiT.csv",
)
REPORT = os.path.join(DIG, "reconciliation_machine_report.md")

PX_P, PX_N = 0.00492, 0.0616  # axis resolution per pixel (both routes)
ON_AXIS_P = 0.0025            # half-pixel bound for on-axis points

SIG = {
    ("A", "ok"): (0.010, 0.10),
    ("A", "uncertain"): (0.017, 0.20),
    ("A", "partial_overlap"): (0.027, 0.33),
    ("B", "ok"): (0.009, 0.07),
    ("B", "uncertain"): (0.040, 0.50),
    ("B", "partial_overlap"): (0.040, 0.50),
}


def load(path, route):
    rows = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            q = r["quality"].strip()
            sp, sn = SIG[(route, q)]
            rows.append({
                "T": float(r["temperature_K"]),
                "P": float(r["pressure_MPa"]),
                "n": float(r["n_excess_molkg"]),
                "P_raw": r["pressure_MPa"].strip(),
                "q": q, "sp": sp, "sn": sn,
            })
    return rows


def load_decisions():
    with open(DECISIONS) as fh:
        return list(csv.DictReader(fh))


def pop_reading(pool, T, P_raw, where):
    """Remove and return the raw reading referenced by a decision row."""
    for i, r in enumerate(pool):
        if abs(r["T"] - T) < 1e-9 and r["P_raw"] == P_raw:
            return pool.pop(i)
    raise SystemExit(
        f"decision references a reading not in route {where}: "
        f"T={T} P_raw={P_raw}")


def main():
    check = "--check" in sys.argv
    A = load(A_CSV, "A")
    B = load(B_CSV, "B")
    decisions = load_decisions()

    out_rows, n_excluded = [], 0
    # ---- stage 2 data applied first: pull decided readings out of the pools
    for d in decisions:
        T = float(d["temperature_K"])
        ra = (pop_reading(A, T, d["routeA_P_raw"], "A")
              if d["routeA_P_raw"] else None)
        rb = (pop_reading(B, T, d["routeB_P_raw"], "B")
              if d["routeB_P_raw"] else None)
        act = d["action"]
        if act == "exclude":
            n_excluded += 1
            continue
        if act == "keep_single":
            r = ra or rb
            P = float(d["routeA_P"] or d["routeB_P"])
            n = float(d["routeA_n"] or d["routeB_n"])
            out_rows.append((
                r["T"], P, n, float(d["sigma_P"]), float(d["sigma_n"]),
                "reinspected_single",
                d["routeA_P"], d["routeA_n"], d["routeB_P"], d["routeB_n"]))
            continue
        # keep_pair / keep_pair_on_axis: coordinate-wise mean of the re-read
        # values; the uncertainty is the per-point value RECORDED at the
        # re-inspection (generally the full inter-route deviation or the
        # re-assessed route class, whichever is larger, floored at the
        # pixel), taken verbatim from the decisions file.
        aP, an = float(d["routeA_P"]), float(d["routeA_n"])
        bP, bn = float(d["routeB_P"]), float(d["routeB_n"])
        P, n = 0.5 * (aP + bP), 0.5 * (an + bn)
        up, un = float(d["sigma_P"]), float(d["sigma_n"])
        if act == "keep_pair_on_axis":
            P = ON_AXIS_P
            q = "on_axis"
        else:
            q = "reinspected_pair"
        out_rows.append((ra["T"], P, n, up, un, q,
                         d["routeA_P"], d["routeA_n"],
                         d["routeB_P"], d["routeB_n"]))

    # ---- stage 1: the frozen automatic matching on the remaining pools
    temps = sorted({r["T"] for r in A} | {r["T"] for r in B})
    n_match = n_unresolved = 0
    for T in temps:
        a = sorted([r for r in A if r["T"] == T], key=lambda r: r["P"])
        b = sorted([r for r in B if r["T"] == T], key=lambda r: r["P"])
        used_b = set()
        for ra in a:
            best, best_d = None, None
            for j, rb in enumerate(b):
                if j in used_b:
                    continue
                dd = abs(rb["P"] - ra["P"])
                if best is None or dd < best_d:
                    best, best_d = j, dd
            if best is not None:
                rb = b[best]
                tol_p = 2.0 * max(ra["sp"], rb["sp"])
                tol_n = 2.0 * max(ra["sn"], rb["sn"])
                if abs(rb["P"] - ra["P"]) <= tol_p and \
                        abs(rb["n"] - ra["n"]) <= tol_n:
                    used_b.add(best)
                    n_match += 1
                    P = 0.5 * (ra["P"] + rb["P"])
                    n = 0.5 * (ra["n"] + rb["n"])
                    up = max(ra["sp"], rb["sp"],
                             abs(rb["P"] - ra["P"]) / 2.0, PX_P)
                    un = max(ra["sn"], rb["sn"],
                             abs(rb["n"] - ra["n"]) / 2.0, PX_N)
                    q = ("ok" if ra["q"] == rb["q"] == "ok"
                         else "overlap_region")
                    out_rows.append((T, P, n, up, un, q,
                                     f"{ra['P']:.4f}", f"{ra['n']:.4f}",
                                     f"{rb['P']:.4f}", f"{rb['n']:.4f}"))
                    continue
            n_unresolved += 1
        for j, rb in enumerate(b):
            if j not in used_b:
                n_unresolved += 1
    if n_unresolved:
        raise SystemExit(
            f"{n_unresolved} flagged reading(s) have no entry in "
            f"{DECISIONS}; the decisions file must be complete.")

    out_rows.sort(key=lambda r: (r[0], r[1]))

    def render():
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([
            "temperature_K", "pressure_MPa", "n_excess_molkg",
            "sigma_P_MPa", "sigma_n_molkg", "quality",
            "routeA_P", "routeA_n", "routeB_P", "routeB_n",
        ])
        for r in out_rows:
            vals = [f"{r[0]:.0f}"] + [f"{x:.4f}" for x in r[1:5]] + [r[5]]
            for x in r[6:]:
                vals.append(f"{float(x):.4f}" if x != "" else "")
            w.writerow(vals)
        return buf.getvalue()

    text = render()
    if check:
        with open(OUT, newline="") as fh:
            committed = fh.read()
        if committed != text:
            sys.exit("regenerated dataset differs from the committed "
                     "ax21_fig1a_multiT.csv")
        print("regenerated dataset is byte-identical to the committed one")
    else:
        with open(OUT, "w", newline="") as fh:
            fh.write(text)
        print("wrote", OUT)

    counts = {}
    for r in out_rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    qcounts = {}
    for r in out_rows:
        qcounts[r[5]] = qcounts.get(r[5], 0) + 1
    print(f"auto-matched: {n_match}; decisions applied: {len(decisions)} "
          f"(excluded: {n_excluded}); total points: {len(out_rows)}")
    print("per-isotherm counts:",
          {int(k): v for k, v in sorted(counts.items())})
    with open(REPORT, "w") as fh:
        fh.write(
            "# Machine reconciliation report (regenerated by "
            "scripts/reconcile_digitization.py)\n\n"
            f"Rule: docs/preregistration_v1.0.md section 5 (frozen). "
            f"Axis resolution: {PX_P} MPa/px, {PX_N} (mol/kg)/px.\n\n"
            f"Auto-matched pairs: {n_match}\n"
            f"Re-inspection decisions applied: {len(decisions)} "
            f"(of which excluded: {n_excluded})\n"
            f"Total points: {len(out_rows)}\n"
            f"Quality counts: {qcounts}\n\n"
            "The narrative adjudication record (marker-convention "
            "measurement, per-point notes) is the hand-written document "
            "data/validation/ax21_fig1a_multiT_reconciliation.md; this "
            "machine report only restates the counts.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
