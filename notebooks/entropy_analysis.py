# ENTROPY ANALYSIS of the teleportation archive -- no hardware.
#
# Source formula: S = k * log(W) (Grand Unification of Being,
# Formula Codex, Vol I, Statistical Physics). Its quantum heir is
# the von Neumann entropy S(rho) = -Tr(rho log2 rho). The inputs
# already exist on disk: the 2026-11-03 Bell-pair autopsy saved the
# pair's full correlator set, from which rho is reconstructed, and
# every published run saved its raw counts, whose Shannon entropy
# H is the classical shadow of the same ledger.
#
# Pair quantities computed:
#   S_AB  -- entropy of the two-qubit pair state (0 = pure)
#   S_A, S_B -- single-qubit marginal entropies (1 bit each for a
#               perfect Bell pair)
#   I(A:B) = S_A + S_B - S_AB -- total correlations (2 bits max)
#   E_F   -- entanglement of formation from the saved concurrence
#            (Wootters), the entanglement-only share of I
# Reconstruction check: Tr(rho^2) from the correlator-only rebuild
# is compared against the purity saved by the autopsy script
# (which used the measured single-qubit marginals as well);
# marginals were <= 0.027, so agreement to ~1e-3 is expected.
#
# Count entropies: every "counts" object in the arc's result files
# gets its Shannon entropy in bits, with its file and path, so the
# ledger covers the published runs without re-running anything.

import json
import numpy as np
from pathlib import Path

BASE = Path(__file__).parent / ".." / "data"
I2 = np.eye(2, dtype=complex)
PAULI = {
    "I": I2,
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}


def vn_entropy(rho):
    w = np.linalg.eigvalsh((rho + rho.conj().T) / 2)
    w = np.clip(np.real(w), 0, None)
    w = w[w > 1e-12]
    return float(-np.sum(w * np.log2(w)))


def physical(rho):
    w, v = np.linalg.eigh((rho + rho.conj().T) / 2)
    w = np.clip(np.real(w), 0, None)
    rho2 = (v * w) @ v.conj().T
    return rho2 / np.trace(rho2)


def partial_trace_b(rho):  # trace out qubit B (second), keep A
    r = rho.reshape(2, 2, 2, 2)
    return np.trace(r, axis1=1, axis2=3)


def partial_trace_a(rho):  # trace out qubit A (first), keep B
    r = rho.reshape(2, 2, 2, 2)
    return np.trace(r, axis1=0, axis2=2)


# ---- the Bell pair, from the autopsy correlators ----
bell = json.load(open(BASE / "bellpair_phoenix_results.json"))
corr = bell["correlators"]
rho = np.zeros((4, 4), dtype=complex)
for a in "IXYZ":
    for b in "IXYZ":
        if a == "I" and b == "I":
            coef = 1.0
        elif a == "I" or b == "I":
            coef = 0.0  # marginals ~0 (<=0.027 measured); see check
        else:
            coef = corr[a + b]
        rho += coef * np.kron(PAULI[a], PAULI[b])
rho /= 4.0
purity_rebuilt = float(np.real(np.trace(rho @ rho)))
rho_phys = physical(rho)
s_ab = vn_entropy(rho_phys)
s_a = vn_entropy(partial_trace_b(rho_phys))
s_b = vn_entropy(partial_trace_a(rho_phys))
mutual = s_a + s_b - s_ab
conc = bell["concurrence"]
xf = (1 + np.sqrt(max(0.0, 1 - conc ** 2))) / 2
e_f = float(-xf * np.log2(xf) - (1 - xf) * np.log2(1 - xf)) if 0 < xf < 1 else 0.0

print("=== The Bell pair (autopsy, job dbl92nl8mdtc73d5mqmg) ===")
print(f"Purity check: rebuilt Tr(rho^2) = {purity_rebuilt:.4f} "
      f"vs autopsy-saved {bell['purity']:.4f}")
print(f"S_AB (pair entropy)      = {s_ab:.4f} bits   (pure pair: 0)")
print(f"S_A = S_B (marginals)    = {s_a:.4f} / {s_b:.4f} bits   (perfect pair: 1 each)")
print(f"I(A:B) mutual information= {mutual:.4f} bits   (perfect pair: 2)")
print(f"E_F (from concurrence {conc:.4f}) = {e_f:.4f} bits of entanglement")
print(f"Correlations that are NOT entanglement (I - 2*E_F scale): "
      f"I = {mutual:.4f}, E_F = {e_f:.4f}")

pair_block = {"purity_rebuilt": purity_rebuilt,
              "purity_saved": bell["purity"],
              "S_AB_bits": s_ab, "S_A_bits": s_a, "S_B_bits": s_b,
              "mutual_information_bits": mutual,
              "concurrence": conc, "entanglement_of_formation_bits": e_f,
              "fidelity_raw": bell["fidelity_raw"]}


# ---- Shannon entropy of every saved count distribution ----
def shannon(counts):
    n = sum(counts.values())
    if not n:
        return None
    h = 0.0
    for v in counts.values():
        if v:
            p = v / n
            h -= p * np.log2(p)
    return float(h)


def walk(obj, path, out, fname):
    if isinstance(obj, dict):
        if obj and all(isinstance(v, (int, float)) for v in obj.values()) \
                and all(set(str(k)) <= {"0", "1"} for k in obj.keys()) \
                and sum(obj.values()) > 100:
            h = shannon({k: int(v) for k, v in obj.items()})
            if h is not None:
                out.append({"file": fname, "path": path, "shots": int(sum(obj.values())),
                            "outcomes": len(obj), "H_bits": h})
            return
        for k, v in obj.items():
            walk(v, f"{path}.{k}", out, fname)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, f"{path}[{i}]", out, fname)


count_rows = []
for fname in ["holdsweep_phoenix_results.json", "dd_phoenix_results.json",
              "postselection_phoenix_results.json",
              "interleaved_phoenix_results.json",
              "bobfirst_phoenix_results.json",
              "tomography_phoenix_results.json"]:
    p = BASE / fname
    if p.exists():
        walk(json.load(open(p)), "$", count_rows, fname)

print(f"\n=== Shannon entropy of saved count distributions "
      f"({len(count_rows)} distributions) ===")
for r in count_rows[:48]:
    print(f"{r['file'][:28]:<30} {r['path'][:44]:<46} "
          f"H = {r['H_bits']:.4f} bits ({r['outcomes']} outcomes, {r['shots']} shots)")

out = {"pair": pair_block, "count_entropies": count_rows}
with open(BASE / "entropy_analysis_results.json", "w") as f:
    json.dump(out, f, indent=2)
print("\nSaved entropy_analysis_results.json")
