# Post-selection teleportation on ibm_phoenix -- the AK2929AK discriminator.
#
# Question (from u/AK2929AK, r/QuantumComputing, 2026-11-02): is the ~5-6
# point fidelity deficit of the |+i>/|-i> states on Phoenix caused by the
# mid-circuit MEASUREMENT itself (readout crosstalk onto the idling Bob
# qubit), or by the FEED-FORWARD path (classical latency + conditional
# gates)? Idle-T2 math cannot explain it (a ~us window vs T2 in the
# hundreds of us costs <1 point).
#
# Design: circuits identical to the 2026-10-28 corrected Phoenix run
# (run1_hardware_v2.py, job dbh8et4dgr2s73ct0mv0, mean fidelity 0.9583) --
# same six state preps, same Bell pair, same mid-circuit measurements of
# Alice's two qubits in the same position, same per-state matching-basis
# readout of Bob -- EXCEPT the two classically-controlled corrections are
# removed. Bob is never touched after the Bell pair is made. All three
# outcomes (alice0, alice1, bob) are recorded per shot in ONE classical
# register so their correlations survive.
#
# Two analyses from the same data:
#   1) POST-SELECTED: keep only shots with alice0=alice1=0 (the branch
#      where no correction would have fired). Bob's raw outcome gives
#      the fidelity with measurement present but feed-forward absent.
#   2) SOFTWARE-CORRECTED (Pauli frame): use every shot; flip Bob's
#      readout bit in post-processing by the parity the hardware
#      correction would have applied, given the readout basis:
#         Z readout: flip iff alice1   (X correction flips Z outcomes)
#         X readout: flip iff alice0   (Z correction flips X outcomes)
#         Y readout: flip iff alice0 XOR alice1 (both flip Y outcomes)
#      This isolates gate/latency effects of the conditional operations
#      from the measurement exposure, which both analyses share.
#
# Reading the result against the live-correction run (per state):
#   live 0.96/0.94/0.99/0.98/0.94/0.94 (|0>,|1>,|+>,|->,|+i>,|-i>).
#   If post-selected +-i stays ~0.94 -> the measurement itself (crosstalk)
#   is the culprit. If it recovers toward the 0.995 control -> the
#   feed-forward path was the cost.
#
# "test"     = local Aer simulator (free, no account) -- run this first.
#              Verification bar: BOTH analyses must return fidelity
#              exactly 1.000 (zero wrong outcomes) for all six states.
# "hardware" = real ibm_phoenix on the pay-as-you-go instance.
MODE = "test"

BACKEND_NAME = "ibm_phoenix"   # Nighthawk, 120 qubits
SHOTS = 1024                   # per state; post-selection keeps ~1/4 (~256),
                               # vs 100 total/state in the live-correction run

# Pay-as-you-go instance (QUANTUMCIRCUITV.001) -- used only in hardware mode
INSTANCE_CRN = "PASTE_YOUR_INSTANCE_CRN_HERE"
print("MODE:", MODE, "| backend:", BACKEND_NAME, "| shots/state:", SHOTS)

import numpy as np

# The six standard test states (same set as all previous runs).
PREPS = {
    "|0>":  lambda c: None,
    "|1>":  lambda c: c.x(0),
    "|+>":  lambda c: c.h(0),
    "|->":  lambda c: (c.x(0), c.h(0)),
    "|+i>": lambda c: (c.h(0), c.s(0)),
    "|-i>": lambda c: (c.h(0), c.sdg(0)),
}
STATES = list(PREPS.keys())

# Bob's matching readout basis per state (fixed 2026-10-28 design).
BASES = {"|0>": "Z", "|1>": "Z", "|+>": "X", "|->": "X",
         "|+i>": "Y", "|-i>": "Y"}
# The outcome bit that means "Bob holds the target state" per state.
TARGET_BIT = {"|0>": 0, "|1>": 1, "|+>": 0, "|->": 1, "|+i>": 0, "|-i>": 1}
# Live-correction Phoenix results, 2026-10-28 (job dbh8et4dgr2s73ct0mv0).
LIVE_REF = {"|0>": 0.96, "|1>": 0.94, "|+>": 0.99, "|->": 0.98,
            "|+i>": 0.94, "|-i>": 0.94}

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


def postselection_circuit(prep, basis="Z"):
    """Teleportation layout identical to run1_hardware_v2.py but with NO
    feed-forward: Alice's qubits are measured mid-circuit exactly as
    before; the if_test corrections are simply absent. Outcomes land in
    one register: c[0]=alice0 (q0), c[1]=alice1 (q1), c[2]=bob (q2).
    Count bitstrings therefore read 'bob alice1 alice0' left to right."""
    qr = QuantumRegister(3, "q")
    cr = ClassicalRegister(3, "c")
    qc = QuantumCircuit(qr, cr)

    prep(qc)                       # 1) prepare the state to teleport (q0)
    qc.barrier()
    qc.h(1); qc.cx(1, 2)           # 2) Bell pair q1-q2
    qc.barrier()
    qc.cx(0, 1); qc.h(0)           # 3) Alice's Bell-basis rotation
    qc.measure(0, cr[0])           #    mid-circuit measurements (kept --
    qc.measure(1, cr[1])           #    their exposure is the variable)
    qc.barrier()
    # 4) NO corrections. (This is the entire point of the run.)
    if basis == "X":               # 5) Bob's readout in the chosen basis
        qc.h(2)
    elif basis == "Y":
        qc.sdg(2); qc.h(2)
    qc.measure(2, cr[2])
    return qc


circuits = [postselection_circuit(PREPS[s], basis=BASES[s]) for s in STATES]
print(f"Built {len(circuits)} post-selection circuits (one per state).")


def analyze(counts, state):
    """counts: {'bob alice1 alice0': n}. Returns (post-selected fidelity,
    software-corrected fidelity, kept shots)."""
    basis = BASES[state]
    target = TARGET_BIT[state]
    kept = kept_ok = 0
    all_ok = total = 0
    for bitstring, n in counts.items():
        bob, a1, a0 = (int(ch) for ch in bitstring)  # left-to-right: c2 c1 c0
        total += n
        # software correction (Pauli frame) on every shot
        if basis == "Z":
            flip = a1
        elif basis == "X":
            flip = a0
        else:  # Y
            flip = a0 ^ a1
        if (bob ^ flip) == target:
            all_ok += n
        # post-selection: only the no-correction branch
        if a0 == 0 and a1 == 0:
            kept += n
            if bob == target:
                kept_ok += n
    return kept_ok / kept, all_ok / total, kept


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
print(f"\n{'State':<7}{'Basis':>6}{'PostSel F':>11}{'SoftCorr F':>12}"
      f"{'Kept':>7}{'Live(10-28)':>12}")
for state, pub_result in zip(STATES, result):
    counts = {k: int(v) for k, v in pub_result.data.c.get_counts().items()}
    f_ps, f_sw, kept = analyze(counts, state)
    rows.append({"state": state, "basis": BASES[state], "counts": counts,
                 "postselected_fidelity": f_ps,
                 "software_corrected_fidelity": f_sw,
                 "kept_shots": kept, "shots": SHOTS,
                 "live_correction_reference": LIVE_REF[state]})
    print(f"{state:<7}{BASES[state]:>6}{f_ps:>11.4f}{f_sw:>12.4f}"
          f"{kept:>7}{LIVE_REF[state]:>12.2f}")

mean_ps = float(np.mean([r["postselected_fidelity"] for r in rows]))
mean_sw = float(np.mean([r["software_corrected_fidelity"] for r in rows]))
print(f"\nMean post-selected fidelity:       {mean_ps:.4f}")
print(f"Mean software-corrected fidelity:  {mean_sw:.4f}")
print(f"Live-correction reference (Phoenix 2026-10-28): "
      f"{float(np.mean(list(LIVE_REF.values()))):.4f}")
if MODE == "test":
    ok = all(r["postselected_fidelity"] == 1.0
             and r["software_corrected_fidelity"] == 1.0 for r in rows)
    print("VERIFICATION:", "PASS -- both analyses exactly 1.000 on all "
          "six states." if ok else
          "FAIL -- an ideal simulator must return exactly 1.000; "
          "do not submit to hardware until this passes.")

out_name = ("postselection_phoenix_results.json" if MODE == "hardware"
            else "postselection_aer_verification.json")
with open(out_name, "w") as f:
    json.dump({"backend": BACKEND_NAME if MODE == "hardware" else "AerSimulator",
               "mode": MODE, "shots_per_state": SHOTS,
               "mean_postselected": mean_ps, "mean_software_corrected": mean_sw,
               "rows": rows}, f, indent=2)
print("Saved", out_name)
