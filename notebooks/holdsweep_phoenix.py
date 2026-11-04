# HOLD-TIME SWEEP on ibm_phoenix: does the +-i fidelity fall as the
# entangled front half is made to wait?
#
# Context (2026-11-02 arc + DD test): the +-i deficit is phase
# SHRINKAGE accrued in the entangled front half. AK2929AK's objection
# was arithmetic: the protocol's natural wait is ~1 us and T2 >= 100
# us, which should cost < 1 point, yet +-i lose ~6. Rather than argue
# from spec-sheet T2, this job MEASURES the dose-response: insert a
# controlled hold of D us on all three qubits immediately after
# Bell-pair creation (the pair, and the input, cannot proceed without
# each other, so all three wait), for D in {0, 5, 10, 20, 40, 80} us,
# then run the live protocol verbatim.
#
# States chosen as instruments, not coverage:
#   |+i>, |-i> : the signal states (phase-sensitive, Y basis).
#   |+>        : equatorial but X -- phase-sensitive on a different
#                axis; a pure phase-damping bath hits Y states when
#                the wait is in the equatorial plane generally, so
#                |+> should fall too if the mechanism is dephasing.
#   |0>        : the pole -- phase-INSENSITIVE. If |0> stays flat
#                while the equator falls, the loss is phase noise,
#                not population/T1 or generic error. If |0> falls
#                equally, the mechanism is not phase-specific.
# Same-day bare controls (prep + matching readout, no hold) set the
# day's ceiling, same convention as the whole arc.
#
# Pre-registered reading:
#   +-i falls steeply with D, |0> flat -> idle phase decoherence is
#     real and now QUANTIFIED: the D=0 intercept vs the control gives
#     the non-idle (gate/prep) share; the slope gives the idle share
#     per us, comparable against 1/T2 from the day's calibration.
#   Everything flat in D -> the front-half loss is NOT idle time at
#     any scale up to 80 us; it sits inside the operations
#     themselves (pair autopsy + this result would isolate the
#     entangling gates).
#   |0> falls with the equator -> not phase-specific; revisit.
#
# "test"     = Aer; bar: every (state, D) fidelity exactly 1.000
#              (delays are no-ops in a noiseless simulator).
# "hardware" = ibm_phoenix, pay-as-you-go instance.
MODE = "test"

BACKEND_NAME = "ibm_phoenix"
SHOTS = 4096
INSTANCE_CRN = "PASTE_YOUR_INSTANCE_CRN_HERE"
print("MODE:", MODE, "| backend:", BACKEND_NAME, "| shots/circuit:", SHOTS)

import numpy as np

PREPS = {
    "|0>":  lambda c: None,
    "|+>":  lambda c: c.h(0),
    "|+i>": lambda c: (c.h(0), c.s(0)),
    "|-i>": lambda c: (c.h(0), c.sdg(0)),
}
STATES = list(PREPS.keys())
BASES = {"|0>": "Z", "|+>": "X", "|+i>": "Y", "|-i>": "Y"}
TARGET_BIT = {"|0>": 0, "|+>": 0, "|+i>": 0, "|-i>": 1}
HOLDS_US = [0, 5, 10, 20, 40, 80]

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


def bob_readout(qc, basis):
    if basis == "X":
        qc.h(2)
    elif basis == "Y":
        qc.sdg(2); qc.h(2)


def live_circuit_hold(prep, basis, hold_us):
    """Live protocol verbatim (DD script base), plus a hold of
    hold_us on all three qubits right after Bell-pair creation."""
    qr = QuantumRegister(3, "q")
    alice0 = ClassicalRegister(1, "alice0")
    alice1 = ClassicalRegister(1, "alice1")
    bob = ClassicalRegister(1, "bob")
    qc = QuantumCircuit(qr, alice0, alice1, bob)
    prep(qc)
    qc.barrier()
    qc.h(1); qc.cx(1, 2)
    qc.barrier()
    if hold_us:
        for q in (0, 1, 2):
            qc.delay(hold_us, q, unit="us")
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
    bob_readout(qc, basis)
    qc.measure(2, bob[0])
    return qc


def control_circuit(prep, basis):
    qc = QuantumCircuit(1, 1)
    prep(qc)
    if basis == "X":
        qc.h(0)
    elif basis == "Y":
        qc.sdg(0); qc.h(0)
    qc.measure(0, 0)
    return qc


plan, circuits3, circuits1 = [], [], []
for s in STATES:
    for d in HOLDS_US:
        plan.append(("tele", s, d))
        circuits3.append(live_circuit_hold(PREPS[s], BASES[s], d))
    plan.append(("ctrl", s, 0))
    circuits1.append(control_circuit(PREPS[s], BASES[s]))
print(f"Built {len(circuits3)} teleportation circuits "
      f"({len(STATES)} states x {len(HOLDS_US)} holds) "
      f"+ {len(circuits1)} controls.")


def sigma(p, n):
    return float(np.sqrt(p * (1 - p) / n)) if n else float("nan")


def choose_layout(backend):
    """Same rule as the whole arc: best connected triple by gate
    errors + Bob readout error, from the day's calibration."""
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
    print("Pinned layout (in, alice, bob):", layout, layout_metrics, flush=True)
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    pm3 = generate_preset_pass_manager(optimization_level=1, backend=backend,
                                       initial_layout=layout)
    pm1 = generate_preset_pass_manager(
        optimization_level=1, backend=backend,
        initial_layout=[layout[2]] if layout else None)
    isa = pm3.run(circuits3) + pm1.run(circuits1)
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
    result = sampler.run([(c,) for c in circuits3 + circuits1],
                         shots=SHOTS).result()
    print(f"Aer test run done: {SHOTS} shots x "
          f"{len(circuits3) + len(circuits1)} circuits.")

import json

seq, idx3, idx1 = [], 0, 0
for kind, _s, _d in plan:
    if kind == "tele":
        seq.append(idx3); idx3 += 1
    else:
        seq.append(len(circuits3) + idx1); idx1 += 1
ordered_results = [result[i] for i in seq]

tele, ctrl = {}, {}
for (kind, state, d), pub_result in zip(plan, ordered_results):
    if kind == "ctrl":
        counts = pub_result.data.c.get_counts()
        ok = counts.get(str(TARGET_BIT[state]), 0)
        f = ok / SHOTS
        ctrl[state] = {"fidelity": f, "sigma": sigma(f, SHOTS),
                       "counts": {k: int(v) for k, v in counts.items()}}
    else:
        counts = pub_result.data.bob.get_counts()
        ok = counts.get(str(TARGET_BIT[state]), 0)
        f = ok / SHOTS
        tele.setdefault(state, {})[str(d)] = {
            "fidelity": f, "sigma": sigma(f, SHOTS),
            "counts": {k: int(v) for k, v in counts.items()}}

hdr = f"\n{'State':<7}{'Ctrl':>8}" + "".join(f"{d:>9}us" for d in HOLDS_US)
print(hdr)
for s in STATES:
    row = f"{s:<7}{ctrl[s]['fidelity']:>8.4f}"
    row += "".join(f"{tele[s][str(d)]['fidelity']:>10.4f}" for d in HOLDS_US)
    print(row)

for s in STATES:
    f0 = tele[s]["0"]["fidelity"]
    f80 = tele[s][str(HOLDS_US[-1])]["fidelity"]
    print(f"{s}: D=0 {f0:.4f} -> D={HOLDS_US[-1]}us {f80:.4f} "
          f"({(f80 - f0) * 100:+.2f} points)")

if MODE == "test":
    ok = all(tele[s][str(d)]["fidelity"] == 1.0
             for s in STATES for d in HOLDS_US) and \
         all(ctrl[s]["fidelity"] == 1.0 for s in STATES)
    print("VERIFICATION:", "PASS -- all states, all holds, and controls "
          "exactly 1.000 on Aer." if ok else "FAIL -- do not submit.")

out_name = ("holdsweep_phoenix_results.json" if MODE == "hardware"
            else "holdsweep_aer_verification.json")
with open(out_name, "w") as f:
    json.dump({"backend": BACKEND_NAME if MODE == "hardware" else "AerSimulator",
               "mode": MODE, "shots_per_circuit": SHOTS,
               "layout_in_alice_bob": layout, "layout_metrics": layout_metrics,
               "holds_us": HOLDS_US, "teleport": tele, "ctrl": ctrl},
              f, indent=2)
print("Saved", out_name)
