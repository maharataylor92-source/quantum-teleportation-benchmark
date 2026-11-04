# Decoherence-rate fit -- Vol II Section XXV (density-matrix decay)
# applied to the 2026-11-03 hold-time sweep on ibm_phoenix
# (holdsweep_phoenix_results.json).
#
# Equatorial inputs (|+>, |+i>, |-i>) were measured along their own
# initial axis after a front-half hold t. Under z-precession at
# frequency f plus pure dephasing with coherence time T2*, the
# own-axis fidelity is
#     F(t) = ( 1 + A * exp(-t/T2*) * cos(2*pi*f*t + phi) ) / 2
# with A ~ 0.80 the t=0 contrast (F(0) ~ 0.90, same-day controls ~0.997
# -- the deficit at t=0 is the teleportation circuit itself, not the
# hold). f, T2*, phi are shared across the three equatorial states;
# each state gets its own A. A no-rotation pure-dephasing model is fit
# for comparison -- it cannot produce the sub-0.5 dip at 20 us.
#
# |0> is fit separately with a population-relaxation form; its decay
# mixes T1 of the pair and is reported as a timescale, not a T1.
#
# HONEST LIMIT (from RESULTS.md §10.3): the hold idled all three
# qubits together, so this gamma is the front half's effective rate,
# input precession folded in.

import json

import numpy as np
from scipy.optimize import curve_fit

from pathlib import Path
DATA = Path(__file__).parent / ".." / "data"
d = json.load(open(DATA / "holdsweep_phoenix_results.json"))
t = np.array(d["holds_us"], dtype=float)
EQ = ["|+>", "|+i>", "|-i>"]
F = {s: np.array([d["teleport"][s][str(int(h))]["fidelity"] for h in t])
     for s in EQ}
S = {s: np.array([d["teleport"][s][str(int(h))]["sigma"] for h in t])
     for s in EQ}
y = np.concatenate([F[s] for s in EQ])
sig = np.concatenate([S[s] for s in EQ])
tt = np.tile(t, 3)


def model_rot(tv, f_khz, T2s, phi, A1, A2, A3):
    A = np.concatenate([np.full(6, A1), np.full(6, A2), np.full(6, A3)])
    return (1 + A * np.exp(-tv / T2s)
            * np.cos(2 * np.pi * f_khz / 1000 * tv + phi)) / 2


def model_norot(tv, T2s, A1, A2, A3):
    A = np.concatenate([np.full(6, A1), np.full(6, A2), np.full(6, A3)])
    return (1 + A * np.exp(-tv / T2s)) / 2


p0 = [25.0, 12.0, 0.0, 0.8, 0.8, 0.8]
bounds = ([0, 1, -np.pi, 0.5, 0.5, 0.5], [200, 200, np.pi, 1, 1, 1])
popt, pcov = curve_fit(model_rot, tt, y, p0=p0, bounds=bounds,
                       sigma=sig, absolute_sigma=True, maxfev=20000)
perr = np.sqrt(np.diag(pcov))
resid = (y - model_rot(tt, *popt)) / sig
chi2_rot = float(np.sum(resid**2))

popt2, _ = curve_fit(model_norot, tt, y, p0=[12.0, 0.8, 0.8, 0.8],
                     bounds=([1, 0.5, 0.5, 0.5], [500, 1, 1, 1]),
                     sigma=sig, absolute_sigma=True, maxfev=20000)
chi2_norot = float(np.sum(((y - model_norot(tt, *popt2)) / sig) ** 2))

f_khz, T2s, phi = popt[0], popt[1], popt[2]
print("=== Equatorial fit: rotation + dephasing (shared f, T2*, phi) ===")
print(f"  precession f   = {f_khz:.1f} +/- {perr[0]:.1f} kHz")
print(f"  T2* (effective) = {T2s:.1f} +/- {perr[1]:.1f} us")
print(f"  gamma = 1/T2*  = {1 / T2s:.3f} /us")
print(f"  phase offset   = {phi:.2f} rad; contrasts A = "
      f"{[round(a, 3) for a in popt[3:]]}")
print(f"  chi2 = {chi2_rot:.1f} for {len(y) - 6} dof")
print("=== No-rotation pure dephasing (comparison) ===")
print(f"  T2* = {popt2[0]:.1f} us, chi2 = {chi2_norot:.1f} for "
      f"{len(y) - 4} dof  -> rotation is "
      f"{'REQUIRED' if chi2_norot > 3 * chi2_rot else 'not decisive'}")
print(f"  (pi rotation time from f: {1000 / (2 * f_khz):.1f} us -- the "
      f"20 us dip in the raw data)")

def model_gauss(tv, f_khz, Tg, phi, A1, A2, A3):
    A = np.concatenate([np.full(6, A1), np.full(6, A2), np.full(6, A3)])
    return (1 + A * np.exp(-(tv / Tg) ** 2)
            * np.cos(2 * np.pi * f_khz / 1000 * tv + phi)) / 2


pg, _ = curve_fit(model_gauss, tt, y, p0=[20.0, 24.0, 0.5, 0.8, 0.8, 0.8],
                  bounds=bounds, sigma=sig, absolute_sigma=True,
                  maxfev=20000)
chi2_gauss = float(np.sum(((y - model_gauss(tt, *pg)) / sig) ** 2))
print("=== Gaussian-envelope variant (inhomogeneous dephasing) ===")
print(f"  f = {pg[0]:.1f} kHz, T_gauss = {pg[1]:.1f} us, "
      f"chi2 = {chi2_gauss:.1f} (vs exp-envelope {chi2_rot:.1f})")
print("  READING: both envelope models fit poorly in absolute chi2 "
      "(shot-noise sigmas only). What is robust: rotation is required "
      "(no-rotation chi2 ~4888); ~pi of phase accrues in ~17-20 us; "
      "fringe visibility is gone by 40 us. Effective T2* is in the "
      "~10-25 us range, NOT the 182 us Hahn-echo T2. The Ramsey "
      "hardware run (2 quadratures x 14 waits) separates phase from "
      "envelope properly -- this fit is the estimate it must beat.")

F0 = np.array([d["teleport"]["|0>"][str(int(h))]["fidelity"] for h in t])


def model_pop(tv, Finf, A, T):
    return Finf + A * np.exp(-tv / T)


pp, _ = curve_fit(model_pop, t, F0, p0=[0.6, 0.39, 60],
                  bounds=([0.4, 0.1, 5], [0.99, 0.6, 1000]), maxfev=20000)
print("=== |0> population relaxation (separate) ===")
print(f"  F(t) -> {pp[0]:.3f} + {pp[1]:.3f} * exp(-t/{pp[2]:.0f} us)")

out = {
    "source": "holdsweep_phoenix_results.json (job dbl92nt8mdtc73d5mqn0)",
    "equatorial_fit": {
        "model": "F=(1+A exp(-t/T2*) cos(2 pi f t+phi))/2, shared f/T2*/phi",
        "f_khz": float(f_khz), "f_khz_err": float(perr[0]),
        "T2star_us": float(T2s), "T2star_us_err": float(perr[1]),
        "gamma_per_us": float(1 / T2s), "phi_rad": float(phi),
        "contrasts": [float(a) for a in popt[3:]],
        "chi2": chi2_rot, "dof": int(len(y) - 6),
    },
    "gaussian_envelope_fit": {"f_khz": float(pg[0]),
                              "T_gauss_us": float(pg[1]),
                              "chi2": chi2_gauss},
    "reading": "Rotation required (no-rotation chi2 ~4888). ~pi phase "
               "in ~17-20 us. Fringe visibility gone by 40 us; "
               "effective T2* ~10-25 us (model-dependent), vs 182 us "
               "Hahn-echo T2. Single-exponential T2* 43.8 us is the "
               "exp-envelope fit value and should not be quoted alone "
               "(chi2/dof ~55). Ramsey hardware run is the proper "
               "measurement.",
    "no_rotation_fit": {"T2star_us": float(popt2[0]), "chi2": chi2_norot},
    "pop0_fit": {"F_inf": float(pp[0]), "A": float(pp[1]),
                 "T_us": float(pp[2])},
    "limit": "Hold idled all three qubits together; gamma is the "
             "front-half effective rate with input precession folded in.",
}
with open(DATA / "decoherence_fit_results.json", "w") as f:
    json.dump(out, f, indent=2)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5))
tf = np.linspace(0, 80, 400)
for i, s in enumerate(EQ):
    ax.errorbar(t, F[s], yerr=S[s], fmt="o", label=f"{s} data")
    curve = (1 + popt[3 + i] * np.exp(-tf / T2s)
             * np.cos(2 * np.pi * f_khz / 1000 * tf + phi)) / 2
    ax.plot(tf, curve, "-", alpha=0.7)
ax.axhline(0.5, color="gray", ls=":")
ax.set_xlabel("front-half hold (µs)")
ax.set_ylabel("own-axis fidelity")
ax.set_title(f"Hold sweep: precession {f_khz:.0f} kHz + dephasing "
             f"T2* {T2s:.0f} µs (fit)")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(DATA / "decoherence_fit.png", dpi=150)
print("\nSaved decoherence_fit_results.json and decoherence_fit.png")
