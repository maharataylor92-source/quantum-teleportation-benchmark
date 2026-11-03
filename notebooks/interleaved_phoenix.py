# INTERLEAVED live-vs-post-selection run on ibm_phoenix.
#
# Why: the 2026-11-02 post-selection job (dbkcb6gnceqs73aljkfg) ran five
# days after the live-correction reference (2026-10-28), so a cross-day
# calibration drift confound hangs over the comparison. This job removes
# it: for each of the six states, BOTH circuits -- the live dynamic
# protocol (feed-forward ON, matching-basis readout, exactly as Oct 28)
# and the post-selection circuit (no corrections, joint outcomes) -- go
# in ONE submission, same calibration window, same hour.
#
# 4096 shots per circuit: the post-selected branch keeps ~1024 shots,
# putting its binomial sigma under a point. Every fidelity is reported
# WITH its 1-sigma binomial error (suggestion 3 -- error bars everywhere).
#
# Pre-registered reading (per state, +-i states are the signal):
#   live F and post-selected F both ~0.94 in the SAME job -> the deficit
#   is real, same-day, and not a feed-forward cost (replicates Nov 2).
#   post-selected F clearly above live F same-day -> feed-forward does
#   cost something after all, and the Nov 2 gap was drift.
#
# "test"     = Aer; bar: every analysis exactly 1.000 on all six states.
# "hardware" = ibm_phoenix, pay-as-you-go instance.
MODE = "test"

BACKEND_NAME = "ibm_phoenix"
SHOTS = 4096
INSTANCE_CRN = "PASTE_YOUR_INSTANCE_CRN_HERE"
print("MODE:", MODE, "| backend:", BACKEND_NAME, "| shots/circuit:", SHOTS)

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

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


def live_circuit(prep, basis):
    """Oct 28 protocol verbatim: named registers, feed-forward ON."""
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


def postsel_circuit(prep, basis):
    """Nov 2 post-selection circuit verbatim: no corrections, one
    register c[0]=alice0, c[1]=alice1, c[2]=bob."""
    qr = QuantumRegister(3, "q")
    cr = ClassicalRegister(3, "c")
    qc = QuantumCircuit(qr, cr)
    prep(qc)
    qc.barrier()
    qc.h(1); qc.cx(1, 2)
    qc.barrier()
    qc.cx(0, 1); qc.h(0)
    qc.measure(0, cr[0])
    qc.measure(1, cr[1])
    qc.barrier()
    if basis == "X":
        qc.h(2)
    elif basis == "Y":
        qc.sdg(2); qc.h(2)
    qc.measure(2, cr[2])
    return qc


plan = []       # (kind, state)
circuits = []
for s in STATES:
    plan.append(("live", s)); circuits.append(live_circuit(PREPS[s], BASES[s]))
    plan.append(("postsel", s)); circuits.append(postsel_circuit(PREPS[s], BASES[s]))
print(f"Built {len(circuits)} circuits (6 live + 6 post-selection).")


def sigma(p, n):
    return float(np.sqrt(p * (1 - p) / n)) if n else float("nan")


def analyze_postsel(counts, state):
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
    f_ps, f_sw = kept_ok / kept, all_ok / total
    return (f_ps, sigma(f_ps, kept), kept), (f_sw, sigma(f_sw, total), total)


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

live_rows, ps_rows = {}, {}
for (kind, state), pub_result in zip(plan, result):
    if kind == "live":
        counts = pub_result.data.bob.get_counts()
        ok = counts.get(str(TARGET_BIT[state]), 0)
        f = ok / SHOTS
        live_rows[state] = {"fidelity": f, "sigma": sigma(f, SHOTS),
                            "counts": {k: int(v) for k, v in counts.items()}}
    else:
        counts = {k: int(v) for k, v in pub_result.data.c.get_counts().items()}
        (f_ps, s_ps, kept), (f_sw, s_sw, total) = analyze_postsel(counts, state)
        ps_rows[state] = {"postselected_fidelity": f_ps, "postselected_sigma": s_ps,
                          "kept_shots": kept,
                          "software_corrected_fidelity": f_sw,
                          "software_corrected_sigma": s_sw, "counts": counts}

print(f"\n{'State':<7}{'Live F +- sig':>17}{'PostSel F +- sig':>19}{'SoftCorr F +- sig':>20}")
for s in STATES:
    L, P = live_rows[s], ps_rows[s]
    print(f"{s:<7}{L['fidelity']:>8.4f} ±{L['sigma']:.4f}"
          f"{P['postselected_fidelity']:>11.4f} ±{P['postselected_sigma']:.4f}"
          f"{P['software_corrected_fidelity']:>12.4f} ±{P['software_corrected_sigma']:.4f}")

if MODE == "test":
    ok = all(live_rows[s]["fidelity"] == 1.0
             and ps_rows[s]["postselected_fidelity"] == 1.0
             and ps_rows[s]["software_corrected_fidelity"] == 1.0
             for s in STATES)
    print("VERIFICATION:", "PASS -- all three analyses exactly 1.000 on "
          "all six states." if ok else "FAIL -- do not submit.")

out_name = ("interleaved_phoenix_results.json" if MODE == "hardware"
            else "interleaved_aer_verification.json")
with open(out_name, "w") as f:
    json.dump({"backend": BACKEND_NAME if MODE == "hardware" else "AerSimulator",
               "mode": MODE, "shots_per_circuit": SHOTS,
               "live": live_rows, "postselection": ps_rows}, f, indent=2)
print("Saved", out_name)
