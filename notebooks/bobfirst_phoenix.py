# BOB-FIRST readout-order run on ibm_phoenix.
#
# Motivation (suggestion 2, sharpened): the post-selection run removed
# the feed-forward corrections, and the |+i>/|-i> deficit survived --
# so the damage is present while Alice's qubits are being measured.
# This run removes Bob's EXPOSURE to that window entirely: Bob is
# rotated into his readout basis and measured BEFORE Alice's two qubits
# are measured. Operations on different qubits commute, so the joint
# outcome statistics are identical in the ideal case (Aer must return
# exactly 1.000) -- but physically, Bob's outcome is already recorded
# before the neighbours' readout pulses fire, so readout crosstalk or
# measurement-induced dephasing from Alice's measurements cannot touch
# it. Corrections are handled in software (Pauli frame), same parity
# rules as the post-selection analysis; the alice=00 branch is also
# reported.
#
# Pre-registered reading (+-i states are the signal):
#   +-i recovers clearly (toward the 0.995 control, well above 0.94)
#     -> the damage happens DURING Alice's readout, to a still-coherent
#        Bob: measurement-induced dephasing / readout crosstalk,
#        localized in time.
#   +-i stays ~0.94 even measured first
#     -> Bob's state was already degraded BEFORE Alice's measurement:
#        the search moves earlier (Bell pair / entangling step / prep),
#        and the multi-layout repeat becomes the next test.
#
# "test"     = Aer; bar: software-corrected and post-selected analyses
#              exactly 1.000 on all six states.
# "hardware" = ibm_phoenix, pay-as-you-go instance.
MODE = "test"

BACKEND_NAME = "ibm_phoenix"
SHOTS = 4096
INSTANCE_CRN = "PASTE_YOUR_INSTANCE_CRN_HERE"
print("MODE:", MODE, "| backend:", BACKEND_NAME, "| shots/state:", SHOTS)

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
BASES = {"|0>": "Z", "|1>": "Z", "|+>": "X", "|->": "X",
         "|+i>": "Y", "|-i>": "Y"}
TARGET_BIT = {"|0>": 0, "|1>": 1, "|+>": 0, "|->": 1, "|+i>": 0, "|-i>": 1}
POSTSEL_REF = {"|0>": 0.9492, "|1>": 0.9355, "|+>": 0.9580, "|->": 0.9561,
               "|+i>": 0.9512, "|-i>": 0.9492}  # software-corrected, Nov 2

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


def bobfirst_circuit(prep, basis):
    """Teleportation with Bob measured FIRST: basis rotation + measure
    q2 -> c[2] immediately after Alice's Bell rotation, then measure
    q0 -> c[0], q1 -> c[1]. No feed-forward (software frame instead)."""
    qr = QuantumRegister(3, "q")
    cr = ClassicalRegister(3, "c")
    qc = QuantumCircuit(qr, cr)
    prep(qc)
    qc.barrier()
    qc.h(1); qc.cx(1, 2)
    qc.barrier()
    qc.cx(0, 1); qc.h(0)
    qc.barrier()
    if basis == "X":
        qc.h(2)
    elif basis == "Y":
        qc.sdg(2); qc.h(2)
    qc.measure(2, cr[2])           # Bob FIRST
    qc.barrier()
    qc.measure(0, cr[0])           # then Alice's pair
    qc.measure(1, cr[1])
    return qc


circuits = [bobfirst_circuit(PREPS[s], BASES[s]) for s in STATES]
print(f"Built {len(circuits)} Bob-first circuits (one per state).")


def sigma(p, n):
    return float(np.sqrt(p * (1 - p) / n)) if n else float("nan")


def analyze(counts, state):
    basis, target = BASES[state], TARGET_BIT[state]
    kept = kept_ok = all_ok = total = 0
    for bitstring, n in counts.items():
        bob, a1, a0 = (int(ch) for ch in bitstring)
        total += n
        flip = a1 if basis == "Z" else a0 if basis == "X" else a0 ^ a1
        if (bob ^ flip) == target:
            all_ok += n
        if a0 == 0 and a1 == 0:
            kept += n
            if bob == target:
                kept_ok += n
    f_sw, f_ps = all_ok / total, kept_ok / kept
    return (f_sw, sigma(f_sw, total)), (f_ps, sigma(f_ps, kept), kept)


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

rows = []
print(f"\n{'State':<7}{'BobFirst SoftCorr F +- sig':>28}"
      f"{'PostSel branch F +- sig':>26}{'Nov2 SoftCorr':>15}")
for state, pub_result in zip(STATES, result):
    counts = {k: int(v) for k, v in pub_result.data.c.get_counts().items()}
    (f_sw, s_sw), (f_ps, s_ps, kept) = analyze(counts, state)
    rows.append({"state": state, "basis": BASES[state], "counts": counts,
                 "bobfirst_software_corrected_fidelity": f_sw,
                 "bobfirst_software_corrected_sigma": s_sw,
                 "postselected_fidelity": f_ps, "postselected_sigma": s_ps,
                 "kept_shots": kept, "shots": SHOTS,
                 "nov2_software_corrected_reference": POSTSEL_REF[state]})
    print(f"{state:<7}{f_sw:>14.4f} ±{s_sw:.4f}"
          f"{f_ps:>16.4f} ±{s_ps:.4f}{POSTSEL_REF[state]:>15.4f}")

if MODE == "test":
    ok = all(r["bobfirst_software_corrected_fidelity"] == 1.0
             and r["postselected_fidelity"] == 1.0 for r in rows)
    print("VERIFICATION:", "PASS -- Bob-first statistics exactly 1.000 "
          "on all six states (commutation check holds)." if ok
          else "FAIL -- do not submit.")

out_name = ("bobfirst_phoenix_results.json" if MODE == "hardware"
            else "bobfirst_aer_verification.json")
with open(out_name, "w") as f:
    json.dump({"backend": BACKEND_NAME if MODE == "hardware" else "AerSimulator",
               "mode": MODE, "shots_per_state": SHOTS, "rows": rows},
              f, indent=2)
print("Saved", out_name)
