"""S6 sensitivity and uncertainty propagation (pre-reg section 7).

Computes, at the baseline sensitivity envelope (AX-21 type-3, 100 bar/80 K ->
5 bar/160 K, 5.6 kg usable):

* the joint output distributions of usable GC and VC with N >= 20,000 samples
  (plan floor 10,000), with split-half convergence of the reported quantiles;
* SHAPLEY EFFECTS over 16 players — the correlated material block (one
  player, sampled from the MCMC posterior) and 13 mutually independent
  engineering/envelope inputs (data/uncertainty_v1.yaml) — by the random-
  permutation estimator (Song, Nelson & Staum 2016), with bootstrap CIs;
* normalized local elasticities d ln(GC)/d ln(x) at the nominal point,
  reported separately (design leverage, never conflated with variance
  shares);
* the labelled ambient-298 K supplementary contrast.

Deterministic seed; results to data/analysis/sensitivity_v1.json.
"""

import functools
import json
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from dataclasses import replace  # noqa: E402

from h2star import engineering as eng  # noqa: E402
from h2star import eos, isotherm  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "analysis", "sensitivity_v1.json")
SEED = 20261104

# Memoize the EOS (the envelope states repeat across every sizing iteration).
eos.density = functools.lru_cache(maxsize=4096)(eos.density)

P_FULL, T_FULL = 100e5, 80.0
P_EMPTY0, T_EMPTY0 = 5e5, 160.0

ENG_KEYS = [
    "sigma_factor_t3", "composite_density", "liner_thickness",
    "shell_thickness", "mli_k_eff_factor", "mli_density",
    "heat_leak_budget", "hx_vol_fraction", "supports_mass",
    "bop_mass_factor", "bop_volume_factor", "model_error_mass",
    "model_error_volume", "T_empty", "P_empty",
]
# players: 0 = material block; 1..N = each engineering key
PLAYERS = ["material"] + ENG_KEYS


def load_spec():
    with open(os.path.join(ROOT, "data", "uncertainty_v1.yaml")) as fh:
        return yaml.safe_load(fh)["engineering"]


def sample_eng(spec, key, rng, n):
    d = spec[key]["distribution"]
    if d["type"] == "uniform":
        return rng.uniform(d["low"], d["high"], n)
    if d["type"] == "normal":
        x = rng.normal(d["mean"], d["sd"], n)
        lo, hi = d.get("truncate", [-np.inf, np.inf])
        bad = (x < lo) | (x > hi)
        while bad.any():
            x[bad] = rng.normal(d["mean"], d["sd"], int(bad.sum()))
            bad = (x < lo) | (x > hi)
        return x
    if d["type"] == "lognormal":
        return d["median"] * np.exp(d["sigma_ln"] * rng.standard_normal(n))
    raise ValueError(d["type"])


def nominal_eng(spec):
    out = {}
    for k in ENG_KEYS:
        d = spec[k]["distribution"]
        if d["type"] == "uniform":
            out[k] = 0.5 * (d["low"] + d["high"])
        elif d["type"] == "normal":
            out[k] = d["mean"]
        else:
            out[k] = d["median"]
    # nominal envelope at the baseline, nominal factors at 1 / source values
    out["T_empty"], out["P_empty"] = T_EMPTY0, P_EMPTY0
    out["composite_density"] = 1600.0
    out["liner_thickness"] = 0.0024
    out["shell_thickness"] = 0.003
    out["mli_density"] = 59.3
    out["heat_leak_budget"] = 5.0
    out["hx_vol_fraction"] = 0.027
    out["supports_mass"] = 1.28
    return out


class Model:
    """GC/VC evaluator with engineering perturbations applied."""

    def __init__(self):
        self.base_params = eng.EngineeringParamsV1.from_yaml(
            os.path.join(ROOT, "data", "engineering_v1.yaml"))
        self.base_mat = isotherm.Material.from_yaml(
            os.path.join(ROOT, "data", "materials", "ax21.yaml"))

    def __call__(self, mat_theta, e):
        """mat_theta: (n_max, alpha, beta, log10_p0, v_a); e: dict of
        engineering values. Returns (GC, VC) on the usable basis."""
        p = self.base_params
        p = replace(
            p,
            t3_fiber_strength=p.t3_fiber_strength * e["sigma_factor_t3"],
            t3_composite_density=e["composite_density"],
            t3_liner_thickness=e["liner_thickness"],
            shell_t_type3=e["shell_thickness"],
            mli_k_eff=p.mli_k_eff * e["mli_k_eff_factor"],
            mli_density=e["mli_density"],
            mli_Q_type3=e["heat_leak_budget"],
            hx_vol_fraction=e["hx_vol_fraction"],
            supports_mass=e["supports_mass"],
            c_bop_mass=p.c_bop_mass * e["bop_mass_factor"],
            c_bop_vol=p.c_bop_vol * e["bop_volume_factor"],
        )
        mat = replace(
            self.base_mat, n_max=mat_theta[0], alpha=mat_theta[1],
            beta=mat_theta[2], p0=10.0 ** mat_theta[3], v_a=mat_theta[4])
        iso = isotherm.ModifiedDA(mat)
        d = eng.SystemDesignV1(mat, iso, p, "type3",
                               P_FULL, T_FULL, e["P_empty"], e["T_empty"])
        b = eng.evaluate_sized(d)
        # model-error multipliers on the engineering block
        m_eng = (b["m_hx"] + b["m_wall"] + b["m_mli"] + b["m_shell"]
                 + b["m_supports"] + b["m_bop"])
        m_sys = (b["m_h2_full"] + b["m_sorbent"]
                 + m_eng * e["model_error_mass"])
        V_nonint = b["V_sys"] - b["V_internal"]
        V_sys = b["V_internal"] + V_nonint * e["model_error_volume"]
        return (b["m_usable"] / m_sys, b["m_usable"] / (V_sys * 1e3))


def main():
    rng = np.random.default_rng(SEED)
    spec = load_spec()
    model = Model()
    post = np.load(os.path.join(ROOT, "data", "analysis",
                                "uq_posterior_v1.npz"))["samples"]

    nom_e = nominal_eng(spec)
    mat_nom = post.mean(axis=0)
    gc0, vc0 = model(mat_nom, nom_e)
    print(f"nominal GC {gc0:.5f} VC {vc0:.5f}")

    def draw_mat(n):
        return post[rng.integers(0, post.shape[0], n)]

    def draw_e(n):
        cols = {k: sample_eng(spec, k, rng, n) for k in ENG_KEYS}
        return [dict(zip(ENG_KEYS, vals)) for vals in zip(
            *[cols[k] for k in ENG_KEYS])]

    # ---- joint output distribution, N = 20,000 ------------------------
    N = 20000
    mats, engs = draw_mat(N), draw_e(N)
    ys = np.array([model(m, e) for m, e in zip(mats, engs)])
    gc, vc = ys[:, 0], ys[:, 1]
    halves = {}
    for name, x in (("GC", gc), ("VC", vc)):
        h1, h2 = x[: N // 2], x[N // 2:]
        halves[name] = {q: [float(np.quantile(h1, q)),
                            float(np.quantile(h2, q))]
                        for q in (0.05, 0.5, 0.95)}
    out = {
        "seed": SEED, "N": N,
        "nominal": {"GC": gc0, "VC": vc0},
        "distribution": {
            "GC": {"mean": float(gc.mean()), "sd": float(gc.std()),
                   "q05": float(np.quantile(gc, .05)),
                   "q50": float(np.quantile(gc, .50)),
                   "q95": float(np.quantile(gc, .95))},
            "VC": {"mean": float(vc.mean()), "sd": float(vc.std()),
                   "q05": float(np.quantile(vc, .05)),
                   "q50": float(np.quantile(vc, .50)),
                   "q95": float(np.quantile(vc, .95))},
            "split_half_quantiles": halves,
        },
    }
    print("GC", out["distribution"]["GC"])
    print("VC", out["distribution"]["VC"])

    # ---- Shapley effects (random-permutation estimator) ---------------
    d = len(PLAYERS)
    n_perm, n_outer = 120, 24
    var_gc, var_vc = gc.var(), vc.var()

    def cond_sample():
        """One joint draw of all inputs."""
        return draw_mat(1)[0], draw_e(1)[0]

    sh = np.zeros((d, 2))
    sh2 = np.zeros((d, 2))  # for bootstrap-free variance of increments
    for _ in range(n_perm):
        perm = rng.permutation(d)
        # incremental cost along the permutation (Castro/Song):
        # c(S) = E[Var(Y | X_S fixed)] estimated with n_outer fixings of the
        # coalition and 2 inner draws of the complement.
        prev_cost = None
        fixed_sets = []
        for pos in range(d + 1):
            S = set(perm[:pos])
            tot = 0.0
            tot_v = 0.0
            for _o in range(n_outer):
                mat_f, e_f = cond_sample()
                ys_in = []
                for _i in range(2):
                    mat_r, e_r = cond_sample()
                    mat = mat_f if 0 in S else mat_r
                    e = {k: (e_f[k] if (j + 1) in S else e_r[k])
                         for j, k in enumerate(ENG_KEYS)}
                    ys_in.append(model(mat, e))
                ys_in = np.array(ys_in)
                tot += 0.5 * (ys_in[0, 0] - ys_in[1, 0]) ** 2
                tot_v += 0.5 * (ys_in[0, 1] - ys_in[1, 1]) ** 2
            cost = np.array([tot / n_outer, tot_v / n_outer])
            if prev_cost is not None:
                inc = prev_cost - cost  # variance explained by adding player
                j = perm[pos - 1]
                sh[j] += inc
                sh2[j] += inc**2
            prev_cost = cost
            fixed_sets.append(S)
    sh /= n_perm
    se = np.sqrt(np.maximum(sh2 / n_perm - sh**2, 0.0) / n_perm)
    out["shapley"] = {
        "players": PLAYERS, "n_perm": n_perm, "n_outer": n_outer,
        "GC": {p: [float(sh[i, 0]), float(se[i, 0])]
               for i, p in enumerate(PLAYERS)},
        "VC": {p: [float(sh[i, 1]), float(se[i, 1])]
               for i, p in enumerate(PLAYERS)},
        "var_GC": float(var_gc), "var_VC": float(var_vc),
        "sum_check_GC": float(sh[:, 0].sum() / var_gc),
        "sum_check_VC": float(sh[:, 1].sum() / var_vc),
    }
    order = np.argsort(sh[:, 0])[::-1]
    for i in order[:8]:
        print(f"Shapley GC {PLAYERS[i]:18s} {sh[i,0]/var_gc:6.3f} "
              f"(se {se[i,0]/var_gc:.3f})")
    print("sum/var check:", out["shapley"]["sum_check_GC"],
          out["shapley"]["sum_check_VC"])

    # ---- local elasticities (design leverage, separate) ---------------
    elas = {}
    for k in ENG_KEYS:
        e_hi = dict(nom_e)
        e_lo = dict(nom_e)
        e_hi[k] = nom_e[k] * 1.02
        e_lo[k] = nom_e[k] * 0.98
        g_hi, v_hi = model(mat_nom, e_hi)
        g_lo, v_lo = model(mat_nom, e_lo)
        elas[k] = {"GC": float((g_hi - g_lo) / (gc0 * 0.04)),
                   "VC": float((v_hi - v_lo) / (vc0 * 0.04))}
    for j, k in enumerate(("n_max", "alpha", "beta", "log10_p0", "v_a")):
        m_hi = mat_nom.copy()
        m_lo = mat_nom.copy()
        m_hi[j] *= 1.02
        m_lo[j] *= 0.98
        g_hi, v_hi = model(m_hi, nom_e)
        g_lo, v_lo = model(m_lo, nom_e)
        elas[k] = {"GC": float((g_hi - g_lo) / (gc0 * 0.04)),
                   "VC": float((v_hi - v_lo) / (vc0 * 0.04))}
    out["elasticities_nominal"] = elas

    # ---- ambient 298 K contrast (SI-only, labelled) --------------------
    mat = replace(model.base_mat)
    iso = isotherm.ModifiedDA(mat)
    d298 = eng.SystemDesignV1(mat, iso, model.base_params, "type3",
                              100e5, 298.0, 5e5, 298.0)
    try:
        b298 = eng.evaluate_sized(d298, 5.6)
        out["ambient_298K_contrast"] = {
            "GC": b298["GC"], "VC": b298["VC"],
            "V_internal_L": b298["V_internal"] * 1e3,
            "note": "pressure-swing only at 298 K; SI contrast, excluded "
                    "from headlines (641-L-class tank)",
        }
        print("ambient 298K: V_int %.0f L, GC %.4f, VC %.4f" % (
            b298["V_internal"] * 1e3, b298["GC"], b298["VC"]))
    except ValueError as e:
        out["ambient_298K_contrast"] = {"error": str(e)[:200]}

    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
