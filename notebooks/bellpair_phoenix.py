# BELL-PAIR AUTOPSY on ibm_phoenix: is the pair itself already shrunk
# before Alice's entangling gates ever fire?
#
# Context (2026-11-02 arc + DD test): the +-i deficit is phase
# SHRINKAGE accrued in the entangled front half (prep / Bell pair /
# Alice's entangling gates). Post-selection exonerated feed-forward,
# tomography showed shrinkage not rotation, Bob-first exonerated
# Alice's readout window, and XY4 DD did not rescue it (Markovian-
# flavored). Open question (posed to u/AK2929AK): the Bell pair
# itself, or Alice's gates?
#
# This job builds the pair EXACTLY as the live protocol does --
# h(alice); cx(alice, bob) -- then stops. No input qubit, no Bell
# measurement, no corrections. It tomographs the pair: 9 measurement
# settings (X/Y/Z on each qubit), full two-qubit density matrix by
# Pauli expansion, fidelity to |phi+>, concurrence, purity, and the
# three stabilizer correlators <XX> (target +1), <YY> (target -1),
# <ZZ> (target +1) for |phi+>.
#
# The pair lives on the (alice, bob) qubits of the day's best pinned
# triple -- the same selection rule and the same physical pair the
# teleportation runs use, so the numbers are directly comparable:
#   corrected phoenix teleportation (Oct 28): cost 3.7 pts total
#   DD-day baseline (Nov 2): cost 2.6 pts, control 0.9969
#
# Pre-registered reading:
#   F(pair) >= ~0.99, concurrence ~1 -> the pair is clean; the
#     front-half loss sits in Alice's entangling gates (cx + h on the
#     input/alice pair) or the input prep, NOT in the pair.
#   F(pair) ~ 0.95-0.97 with XX/YY correlator magnitudes ~0.9 ->
#     the pair itself carries the deficit; prep/pair window is the
#     culprit and gate-focused fixes will not recover it.
#   Correlators shrunk roughly equally (XX ~ YY ~ ZZ < 1) ->
#     depolarizing-flavored pair noise. XX/YY shrunk but ZZ ~ 1 ->
#     phase damping signature specifically.
#
# "test"     = Aer; bar: F > 0.99 and concurrence > 0.98 (sampled
#              counts cannot be exact for tomography).
# "hardware" = ibm_phoenix, pay-as-you-go instance.
MODE = "test"

BACKEND_NAME = "ibm_phoenix"
SHOTS = 4096
INSTANCE_CRN = "PASTE_YOUR_INSTANCE_CRN_HERE"
print("MODE:", MODE, "| backend:", BACKEND_NAME, "| shots/circuit:", SHOTS)

import numpy as np

AXES = ["X", "Y", "Z"]
SETTINGS = [(a, b) for a in AXES for b in AXES]

from qiskit import QuantumCircuit

I2 = np.eye(2, dtype=complex)
PAULI = {
    "I": I2,
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
}


def rotate(qc, q, axis):
    """Rotate qubit q so a Z measurement reads the given axis."""
    if axis == "X":
        qc.h(q)
    elif axis == "Y":
        qc.sdg(q); qc.h(q)


def pair_circuit(axis_a, axis_b):
    """Bell prep verbatim from the live protocol, then tomography
    rotations. Logical qubit 0 = Alice's pair half, 1 = Bob."""
    qc = QuantumCircuit(2, 2)
    qc.h(0); qc.cx(0, 1)
    qc.barrier()
    rotate(qc, 0, axis_a)
    rotate(qc, 1, axis_b)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


circuits = [pair_circuit(a, b) for (a, b) in SETTINGS]
print(f"Built {len(circuits)} tomography circuits (9 settings).")


def choose_layout(backend):
    """Same rule as the teleportation arc: best connected triple
    (q_in, q_alice, q_bob) by gate errors + Bob readout. This job
    uses (alice, bob) = triple[1], triple[2]."""
    props = backend.properties()
    edges = set()
    for a, b in backend.coupling_map.get_edges():
        edges.add((a, b))
    gate_name = None
    for cand in ("cz", "ecr", "cx"):
        try:
            props.gate_error(cand, list(next(iter(edges))))
            gate_name = cand
            break
        except Exception:
            continue
    if gate_name is None:
        return None, {}
    best = None
    for a, mid in edges:
        for mid2, b in edges:
            if mid2 != mid or b == a:
                continue
            try:
                ge1 = props.gate_error(gate_name, [a, mid])
                ge2 = props.gate_error(gate_name, [mid, b])
                ro = props.readout_error(b)
            except Exception:
                continue
            score = ge1 + ge2 + ro
            if best is None or score < best[0]:
                best = (score, [a, mid, b],
                        {"gate": gate_name, "ge_in_alice": ge1,
                         "ge_alice_bob": ge2, "readout_bob": ro,
                         "t2_bob_us": props.t2(b) * 1e6,
                         "t1_bob_us": props.t1(b) * 1e6})
    if best is None:
        return None, {}
    return best[1], best[2]


layout, layout_metrics = None, {}
if MODE == "hardware":
    import sys
    from qiskit_ibm_runtime import QiskitRuntimeService
    token = "".join(sys.stdin.read().split())
    service = QiskitRuntimeService(channel="ibm_quantum_platform",
                                   token=token, instance=INSTANCE_CRN)
    backend = service.backend(BACKEND_NAME)
    st = backend.status()
    print(BACKEND_NAME, "operational:", st.operational,
          "| pending:", st.pending_jobs, flush=True)
    if not st.operational:
        raise SystemExit(f"{BACKEND_NAME} is not operational; nothing "
                         "submitted, no charge.")
    print("Connected:", backend.name, "-", backend.num_qubits,
          "qubits (PAY-AS-YOU-GO instance)", flush=True)
    try:
        layout, layout_metrics = choose_layout(backend)
    except Exception as e:
        print("Layout selection failed, transpiler will choose:", e)
    print("Pinned triple (in, alice, bob):", layout, layout_metrics,
          flush=True)
    pair_layout = [layout[1], layout[2]] if layout else None
    print("Pair layout (alice, bob):", pair_layout, flush=True)
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend,
                                      initial_layout=pair_layout)
    isa = pm.run(circuits)
    from qiskit_ibm_runtime import SamplerV2 as RuntimeSampler
    sampler = RuntimeSampler(mode=backend)
    job = sampler.run([(c,) for c in isa], shots=SHOTS)
    print("Job ID:", job.job_id(), flush=True)
    result = job.result()
else:
    from qiskit_aer import AerSimulator
    from qiskit.primitives import BackendSamplerV2
    backend = AerSimulator()
    sampler = BackendSamplerV2(backend=backend)
    result = sampler.run([(c,) for c in circuits], shots=SHOTS).result()
    print(f"Aer test run done: {SHOTS} shots x {len(circuits)} circuits.")

# ---- analysis: Pauli expansion of the two-qubit density matrix ----
expect = {}   # (axisA, axisB) -> <sigmaA (x) sigmaB>, incl. I terms
for (a, b), pub in zip(SETTINGS, result):
    counts = pub.data.c.get_counts()
    tot = sum(counts.values())
    e_ab = e_a = e_b = 0.0
    for key, n in counts.items():
        # counts key: leftmost char is c1 (Bob), rightmost is c0 (Alice)
        bit_a = int(key[-1])
        bit_b = int(key[0])
        sa = -1.0 if bit_a else 1.0
        sb = -1.0 if bit_b else 1.0
        p = n / tot
        e_ab += sa * sb * p
        e_a += sa * p
        e_b += sb * p
    expect[(a, b)] = e_ab
    expect[(a, "I")] = e_a
    expect[("I", b)] = e_b
expect[("I", "I")] = 1.0

rho = np.zeros((4, 4), dtype=complex)
for a in ["I", "X", "Y", "Z"]:
    for b in ["I", "X", "Y", "Z"]:
        rho += expect[(a, b)] * np.kron(PAULI[a], PAULI[b])
rho /= 4.0

phi_plus = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
fidelity_raw = float(np.real(phi_plus.conj() @ rho @ phi_plus))
purity = float(np.real(np.trace(rho @ rho)))

# project to nearest physical state for a second fidelity estimate
w, v = np.linalg.eigh((rho + rho.conj().T) / 2)
w_clip = np.clip(w, 0, None)
rho_phys = (v * w_clip) @ v.conj().T
rho_phys /= np.trace(rho_phys)
fidelity_phys = float(np.real(phi_plus.conj() @ rho_phys @ phi_plus))

# concurrence from the (projected) physical state
yy = np.kron(PAULI["Y"], PAULI["Y"])
r_mat = rho_phys @ yy @ rho_phys.conj() @ yy
evals = np.sort(np.real(np.linalg.eigvals(r_mat)))[::-1]
evals = np.clip(evals, 0, None)
concurrence = float(max(0.0, np.sqrt(evals[0]) - np.sqrt(evals[1])
                        - np.sqrt(evals[2]) - np.sqrt(evals[3])))

print(f"\nCorrelators for |phi+> (targets: XX +1, YY -1, ZZ +1):")
print(f"  <XX> = {expect[('X','X')]:+.4f}")
print(f"  <YY> = {expect[('Y','Y')]:+.4f}")
print(f"  <ZZ> = {expect[('Z','Z')]:+.4f}")
print(f"Single-qubit expectations (targets ~0): "
      f"A: X {expect[('X','I')]:+.3f} Y {expect[('Y','I')]:+.3f} "
      f"Z {expect[('Z','I')]:+.3f} | "
      f"B: X {expect[('I','X')]:+.3f} Y {expect[('I','Y')]:+.3f} "
      f"Z {expect[('I','Z')]:+.3f}")
print(f"\nPair fidelity to |phi+>: raw {fidelity_raw:.4f} | "
      f"physical-projected {fidelity_phys:.4f}")
print(f"Purity Tr(rho^2): {purity:.4f} | Concurrence: {concurrence:.4f}")

if MODE == "test":
    ok = fidelity_phys > 0.99 and concurrence > 0.98
    print("VERIFICATION:", "PASS -- pair reconstructs as |phi+> on Aer."
          if ok else "FAIL -- do not submit.")

import json
out_name = ("bellpair_phoenix_results.json" if MODE == "hardware"
            else "bellpair_aer_verification.json")
with open(out_name, "w") as f:
    json.dump({"backend": BACKEND_NAME if MODE == "hardware" else "AerSimulator",
               "mode": MODE, "shots_per_circuit": SHOTS,
               "layout_triple_in_alice_bob": layout,
               "layout_metrics": layout_metrics,
               "correlators": {f"{a}{b}": expect[(a, b)]
                               for (a, b) in SETTINGS},
               "fidelity_raw": fidelity_raw,
               "fidelity_physical": fidelity_phys,
               "purity": purity, "concurrence": concurrence},
              f, indent=2)
print("Saved", out_name)
