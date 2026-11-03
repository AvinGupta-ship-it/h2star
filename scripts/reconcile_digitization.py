"""Reconcile the two independent digitizations of Richard et al. (2009) Fig. 1a.

Implements, verbatim, the frozen rule of docs/preregistration_v1.0.md section 5
(DOI 10.5281/zenodo.23931242):

    "per isotherm, points are matched across routes by nearest pressure; a
    matched pair agreeing within twice the larger route's stated per-point
    resolution in both coordinates is reconciled to the coordinate-wise mean;
    disagreeing pairs and unmatched points are re-inspected against the figure
    once, and kept only if a marker is unambiguously present, with the larger
    route deviation recorded as their uncertainty; points neither route
    resolves ... are excluded with their count reported."

Inputs (read-only): the two route CSVs and calibration notes produced by the
isolated digitization agents. Output: data/validation/ax21_fig1a_multiT.csv
with both route readings, the reconciled value, per-point uncertainties and a
quality flag, plus a reconciliation report printed to stdout and saved beside
the CSV.

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

A_CSV = "/home/claude/digitize_A/digitized_A.csv"
B_CSV = "/home/claude/digitize_B/digitized_B.csv"
OUT = os.path.join(
    os.path.dirname(__file__), "..", "data", "validation",
    "ax21_fig1a_multiT.csv",
)
REPORT = os.path.join(
    os.path.dirname(__file__), "..", "data", "validation",
    "ax21_fig1a_multiT_reconciliation.md",
)

PX_P, PX_N = 0.00492, 0.0616  # axis resolution per pixel (both routes)

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
                "q": q, "sp": sp, "sn": sn,
            })
    return rows


def main():
    A = load(A_CSV, "A")
    B = load(B_CSV, "B")
    temps = sorted({r["T"] for r in A} | {r["T"] for r in B})

    out_rows, report = [], []
    n_match = n_only = 0
    for T in temps:
        a = sorted([r for r in A if r["T"] == T], key=lambda r: r["P"])
        b = sorted([r for r in B if r["T"] == T], key=lambda r: r["P"])
        used_b = set()
        for ra in a:
            # nearest-pressure match in B, unused
            best, best_d = None, None
            for j, rb in enumerate(b):
                if j in used_b:
                    continue
                d = abs(rb["P"] - ra["P"])
                if best is None or d < best_d:
                    best, best_d = j, d
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
                    # uncertainty: max(route sigma, half-discrepancy, 1 px)
                    up = max(ra["sp"], rb["sp"],
                             abs(rb["P"] - ra["P"]) / 2.0, PX_P)
                    un = max(ra["sn"], rb["sn"],
                             abs(rb["n"] - ra["n"]) / 2.0, PX_N)
                    q = ("ok" if ra["q"] == rb["q"] == "ok"
                         else "overlap_region")
                    out_rows.append((T, P, n, up, un, q,
                                     ra["P"], ra["n"], rb["P"], rb["n"]))
                    continue
            # unmatched or disagreeing: flag for single re-inspection
            n_only += 1
            report.append(
                f"REVIEW {T:.0f} K: route-A point P={ra['P']:.3f}, "
                f"n={ra['n']:.2f} ({ra['q']}) unmatched/disagreeing"
            )
        for j, rb in enumerate(b):
            if j not in used_b:
                n_only += 1
                report.append(
                    f"REVIEW {T:.0f} K: route-B point P={rb['P']:.3f}, "
                    f"n={rb['n']:.2f} ({rb['q']}) unmatched/disagreeing"
                )

    out_rows.sort(key=lambda r: (r[0], r[1]))
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "temperature_K", "pressure_MPa", "n_excess_molkg",
            "sigma_P_MPa", "sigma_n_molkg", "quality",
            "routeA_P", "routeA_n", "routeB_P", "routeB_n",
        ])
        for r in out_rows:
            w.writerow([f"{r[0]:.0f}"] + [f"{x:.4f}" for x in r[1:5]]
                       + [r[5]] + [f"{x:.4f}" for x in r[6:]])

    counts = {}
    for r in out_rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print(f"matched+reconciled: {n_match}; needing single re-inspection: "
          f"{n_only}")
    print("per-isotherm reconciled counts:",
          {int(k): v for k, v in sorted(counts.items())})
    with open(REPORT, "w") as fh:
        fh.write(
            "# Reconciliation of Fig. 1a digitization routes A and B\n\n"
            f"Rule: docs/preregistration_v1.0.md section 5 (frozen).\n"
            f"Axis resolution: {PX_P} MPa/px, {PX_N} (mol/kg)/px.\n\n"
            f"Matched and reconciled: {n_match}\n"
            f"Flagged for the single re-inspection: {n_only}\n\n"
        )
        fh.write("\n".join(report) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
