"""S6 posterior sampling and model-form comparison (pre-reg section 7).

Outputs data/analysis/uq_posterior_v1.npz (thinned posterior samples) and
data/analysis/uq_mcmc_v1.json (diagnostics: ESS per parameter, split R-hat,
split-half quantile agreement; the Laplace comparison; free-m and Toth
model-form fits with their objectives and baseline-envelope predictions).
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import emcee  # noqa: E402
from scipy.optimize import differential_evolution  # noqa: E402

from h2star import identifiability as ident  # noqa: E402
from h2star import uq_v1  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data", "validation", "ax21_fig1a_multiT.csv")
OUTD = os.path.join(ROOT, "data", "analysis")

SEED = 20261103


def main():
    rng = np.random.default_rng(SEED)
    D = ident.load_dataset(DATA)
    fd = uq_v1.FastData(*D)

    theta0 = np.array([61.91283, 3560.11345, 16.60159, 9.14954, 1.1570e-3])

    # ---- MCMC ---------------------------------------------------------
    nwalk, nstep, burn, thin = 40, 30000, 5000, 5
    p0 = theta0 * (1.0 + 1e-3 * rng.standard_normal((nwalk, 5)))
    p0 = np.clip(p0, uq_v1.LO * 1.0001, uq_v1.HI * 0.9999)
    sampler = emcee.EnsembleSampler(
        nwalk, 5, uq_v1.log_posterior, args=(fd,))
    # Seed emcee's own RNG too (not just walker init), so the chain is
    # bit-reproducible — S8 re-derivation finding 6.
    sampler.random_state = np.random.RandomState(SEED).get_state()
    sampler.run_mcmc(p0, nstep, progress=False)
    chain = sampler.get_chain(discard=burn)  # (nstep-burn, nwalk, 5)

    diag = {"n_walkers": nwalk, "n_steps": nstep, "burn": burn,
            "thin": thin, "seed": SEED, "params": list(uq_v1.PARAM_ORDER),
            "ess": {}, "rhat": {}, "split_half_q": {}}
    for j, name in enumerate(uq_v1.PARAM_ORDER):
        ess, rhat = uq_v1.ess_and_rhat(chain[:, :, j].T)
        diag["ess"][name] = ess
        diag["rhat"][name] = rhat
        flat = chain[:, :, j].reshape(-1)
        h1, h2 = flat[: flat.size // 2], flat[flat.size // 2:]
        diag["split_half_q"][name] = {
            q: [float(np.quantile(h1, q)), float(np.quantile(h2, q))]
            for q in (0.05, 0.5, 0.95)}
        print(f"{name}: ESS {ess:.0f}, R-hat {rhat:.4f}, "
              f"median {np.median(flat):.6g}, "
              f"90% [{np.quantile(flat, .05):.6g}, "
              f"{np.quantile(flat, .95):.6g}]")

    flat = chain[::thin].reshape(-1, 5)
    os.makedirs(OUTD, exist_ok=True)
    np.savez_compressed(os.path.join(OUTD, "uq_posterior_v1.npz"),
                        samples=flat, params=list(uq_v1.PARAM_ORDER))
    diag["n_samples_saved"] = int(flat.shape[0])
    mean = flat.mean(axis=0)
    cov = np.cov(flat.T)
    diag["posterior_mean"] = [float(x) for x in mean]
    diag["posterior_cov"] = [[float(x) for x in row] for row in cov]

    # ---- Laplace comparison ------------------------------------------
    # Curvature of -logpost at the optimum (numeric Hessian, log-space for
    # scale) reported alongside, as the pre-registration requires.
    def nlp(x):
        return -uq_v1.log_posterior(x, fd)
    h = theta0 * 1e-4
    H = np.zeros((5, 5))
    for i in range(5):
        for j in range(i, 5):
            ei = np.zeros(5)
            ei[i] = h[i]
            ej = np.zeros(5)
            ej[j] = h[j]
            H[i, j] = H[j, i] = (
                nlp(theta0 + ei + ej) - nlp(theta0 + ei - ej)
                - nlp(theta0 - ei + ej) + nlp(theta0 - ei - ej)
            ) / (4 * h[i] * h[j])
    try:
        lap_cov = np.linalg.inv(H)
        diag["laplace_sd_over_mcmc_sd"] = [
            float(np.sqrt(max(lap_cov[i, i], 0)) / np.sqrt(cov[i, i]))
            for i in range(5)]
    except np.linalg.LinAlgError:
        diag["laplace_sd_over_mcmc_sd"] = None

    # ---- Model-form fits ---------------------------------------------
    # (a) free-m modified D-A
    def obj_freem(x):
        return uq_v1.mda_objective(x[:5], fd, m=x[5])
    r_m = differential_evolution(
        obj_freem,
        bounds=[(uq_v1.LO[i], uq_v1.HI[i]) for i in range(5)] + [(1.0, 4.0)],
        seed=SEED, tol=1e-10, maxiter=400, polish=True)
    # (b) Toth
    def obj_toth(x):
        return uq_v1.toth_objective(x, fd)
    r_t = differential_evolution(
        obj_toth,
        bounds=[(1.0, 300.0), (1e-12, 1e-4), (0.0, 10000.0), (0.05, 2.0),
                (1e-5, 5e-3)],
        seed=SEED, tol=1e-10, maxiter=600, polish=True)
    diag["model_forms"] = {
        "mda_m2": {"objective": uq_v1.mda_objective(theta0, fd),
                   "theta": [float(x) for x in theta0]},
        "mda_free_m": {"objective": float(r_m.fun),
                       "theta": [float(x) for x in r_m.x],
                       "m": float(r_m.x[5])},
        "toth": {"objective": float(r_t.fun),
                 "theta": [float(x) for x in r_t.x]},
    }
    print("model forms: m2", round(diag['model_forms']['mda_m2']['objective'], 1),
          " free-m", round(float(r_m.fun), 1), f"(m={r_m.x[5]:.3f})",
          " toth", round(float(r_t.fun), 1))

    with open(os.path.join(OUTD, "uq_mcmc_v1.json"), "w") as fh:
        json.dump(diag, fh, indent=1)
    print("wrote", os.path.join(OUTD, "uq_mcmc_v1.json"))


if __name__ == "__main__":
    main()
