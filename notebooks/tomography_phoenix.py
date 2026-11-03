# Full tomography of the TELEPORTED state on ibm_phoenix -- the second
# AK2929AK test (r/QuantumComputing, 2026-11-02): is the |+i>/|-i> deficit
# a ROTATION of Bob's Bloch vector (fixed phase offset -- a frame /
# tracking error, correctable) or SHRINKAGE (true decoherence)?
#
# Design: the live protocol exactly as run on 2026-10-28 (feed-forward
# corrections ON), but Bob is read out in X, Y and Z for every input
# state (18 circuits), as in the Kingston tomography run
# (run2_hardware.py). From <X>, <Y>, <Z> we reconstruct Bob's Bloch
# vector r per state and report:
#   fidelity  F = (1 + r . t) / 2   (t = target Bloch vector)
#   length    |r|                   (1 = pure; shrinkage shows here)
#   azimuth   phi = atan2(<Y>, <X>) for the four equatorial states,
#             with the offset from the target angle (rotation shows here)
#
# Reading the result:
#   |r| for +-i comparable to |+>/|-> but phi off target -> ROTATION
#   (frame/tracking error; fixable in calibration or in software).
#   |r| for +-i clearly shorter, phi on target -> SHRINKAGE
#   (true coherence loss; physics, not bookkeeping).
#
# "test"     = local Aer simulator -- verification bar: F = 1.000,
#              |r| = 1.000, phi offset = 0.0 deg for every state.
# "hardware" = real ibm_phoenix on the pay-as-you-go instance.
MODE = "test"

BACKEND_NAME = "ibm_phoenix"   # Nighthawk, 120 qubits
SHOTS = 1024                   # per basis -> 3072 per state (as Kingston)

# Pay-as-you-go instance (QUANTUMCIRCUITV.001) -- hardware mode only
INSTANCE_CRN = "PASTE_YOUR_INSTANCE_CRN_HERE"
print("MODE:", MODE, "| backend:", BACKEND_NAME, "| shots/basis:", SHOTS)

import numpy as np

PREPS = {
    "|0>":  lambda c: None,
    "|1>":  lambda c: c.x(0),
    "|+>":  lambda c: c.h(0),
    "|->":  lambda c: (c.x(0), c.h(0)),
    "|+i>": lambda c: (c.h(0), c.s(0)),
    "|-i>": lambda c: (c.h(0), c.sdg(0)),
}
STATES = list(PREPS.keys())
BASES = ["X", "Y", "Z"]
TARGET_BLOCH = {"|0>": (0, 0, 1), "|1>": (0, 0, -1), "|+>": (1, 0, 0),
                "|->": (-1, 0, 0), "|+i>": (0, 1, 0), "|-i>": (0, -1, 0)}
TARGET_PHI = {"|+>": 0.0, "|->": 180.0, "|+i>": 90.0, "|-i>": -90.0}
# Live-protocol single-basis fidelities on Phoenix, 2026-10-28.
LIVE_REF = {"|0>": 0.96, "|1>": 0.94, "|+>": 0.99, "|->": 0.98,
            "|+i>": 0.94, "|-i>": 0.94}

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


def teleportation_circuit(prep, basis="Z"):
    """The Oct 19 / Oct 28 dynamic teleportation circuit (feed-forward
    ON) with Bob's readout rotated into the requested basis."""
    qr = QuantumRegister(3, "q")
    alice0 = ClassicalRegister(1, "alice0")
    alice1 = ClassicalRegister(1, "alice1")
    bob = ClassicalRegister(1, "bob")
    qc = QuantumCircuit(qr, alice0, alice1, bob)

    prep(qc)
    qc.barrier()
    qc.h(1); qc.cx(1, 2)
    qc.barrier()
    qc.cx(0, 1); qc.h(0)
    qc.measure(0, alice0[0])
    qc.measure(1, alice1[0])
    qc.barrier()
    with qc.if_test((alice1[0], 1)):
        qc.x(2)
    with qc.if_test((alice0[0], 1)):
        qc.z(2)
    qc.barrier()
    if basis == "X":
        qc.h(2)
    elif basis == "Y":
        qc.sdg(2); qc.h(2)
    qc.measure(2, bob[0])
    return qc


plan = [(s, b) for s in STATES for b in BASES]
circuits = [teleportation_circuit(PREPS[s], basis=b) for s, b in plan]
print(f"Built {len(circuits)} circuits: {len(STATES)} states x {len(BASES)} bases.")

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
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)
    isa_circuits = pm.run(circuits)
    from qiskit_ibm_runtime import SamplerV2 as RuntimeSampler
    sampler = RuntimeSampler(mode=backend)
    job = sampler.run([(isa,) for isa in isa_circuits], shots=SHOTS)
    print("Job ID:", job.job_id(), flush=True)
    result = job.result()
else:
    from qiskit_aer import AerSimulator
    from qiskit.primitives import BackendSamplerV2
    backend = AerSimulator()
    sampler = BackendSamplerV2(backend=backend)
    result = sampler.run([(c,) for c in circuits], shots=SHOTS).result()
    print(f"Aer test run done: {SHOTS} shots x {len(circuits)} circuits.")

import json

expect = {}
for (state, basis), pub_result in zip(plan, result):
    counts = pub_result.data.bob.get_counts()
    expect[(state, basis)] = (counts.get("0", 0) - counts.get("1", 0)) / SHOTS

rows = []
print(f"\n{'State':<7}{'<X>':>8}{'<Y>':>8}{'<Z>':>8}{'|r|':>8}"
      f"{'Fidelity':>10}{'Phi off':>9}")
for state in STATES:
    r = np.array([expect[(state, "X")], expect[(state, "Y")],
                  expect[(state, "Z")]])
    t = np.array(TARGET_BLOCH[state], dtype=float)
    fidelity = float(0.5 * (1.0 + r @ t))
    length = float(np.linalg.norm(r))
    phi_off = None
    if state in TARGET_PHI:
        phi = float(np.degrees(np.arctan2(r[1], r[0])))
        phi_off = (phi - TARGET_PHI[state] + 180) % 360 - 180
    rows.append({"state": state, "expect_x": float(r[0]),
                 "expect_y": float(r[1]), "expect_z": float(r[2]),
                 "bloch_length": length, "fidelity": fidelity,
                 "phi_offset_deg": phi_off,
                 "live_correction_reference": LIVE_REF[state]})
    print(f"{state:<7}{r[0]:>8.3f}{r[1]:>8.3f}{r[2]:>8.3f}{length:>8.3f}"
          f"{fidelity:>10.4f}"
          f"{('%+.1f' % phi_off) if phi_off is not None else '-':>9}")

mean_f = float(np.mean([row["fidelity"] for row in rows]))
print(f"\nMean tomographic fidelity: {mean_f:.4f} "
      f"(live single-basis reference: 0.9583)")
if MODE == "test":
    ok = all(abs(row["fidelity"] - 1.0) < 0.02
             and abs(row["bloch_length"] - 1.0) < 0.02
             and (row["phi_offset_deg"] is None
                  or abs(row["phi_offset_deg"]) < 3.0) for row in rows)
    print("VERIFICATION:", "PASS -- tomography reconstructs all six "
          "states at |r| ~ 1, phi on target (shot-noise tolerances)."
          if ok else "FAIL -- do not submit until this passes.")

out_name = ("tomography_phoenix_results.json" if MODE == "hardware"
            else "tomography_aer_verification.json")
with open(out_name, "w") as f:
    json.dump({"backend": BACKEND_NAME if MODE == "hardware" else "AerSimulator",
               "mode": MODE, "shots_per_basis": SHOTS,
               "mean_fidelity": mean_f, "rows": rows}, f, indent=2)
print("Saved", out_name)
