# DD TEST on ibm_phoenix: does dynamical decoupling on Bob rescue the
# +-i phase?
#
# Context (2026-11-02 arc): four experiments localized the +-i deficit
# to phase SHRINKAGE accrued in the entangled front half of the circuit:
# not feed-forward (post-selection), not a frame rotation (tomography:
# |r| ~0.87-0.89 for +-i, plus a ~+5 deg offset worth only ~0.2 pt),
# not cross-day drift (interleaved same-job replication), and not
# Alice's readout window (Bob-first ordering). What remains is slow
# dephasing while Bob's half of the entangled state waits.
#
# This job is the A/B test of the standard cure, all in ONE submission
# on ONE pinned physical triple:
#   base = the live protocol verbatim (Oct 28 / interleaved script).
#   dd   = identical, plus an XY4 dynamical-decoupling sequence on Bob
#          (q2) spanning the window between Bell-pair creation and the
#          feed-forward corrections: delays 0.4/0.8/0.8/0.8/0.4 us
#          around X-Y-X-Y pulses (~3.2 us of delays). XY4 is a net
#          identity (up to a global phase), so the analysis is
#          unchanged; the pulses refocus slow (low-frequency) phase
#          noise on Bob while Alice measures.
#   ctrl = same-day bare control (prep + matching-basis readout) on
#          Bob's physical qubit alone -- the day's ceiling.
#
# PINNED LAYOUT: chosen from the day's calibration (backend.properties)
# as the connected triple minimizing (two-qubit gate error on both
# links + Bob readout error). This also closes the interleaved run's
# open caveat (independent transpilations may have used different
# physical qubits per circuit type): here every 3-qubit circuit uses
# the SAME triple, and the control uses Bob's qubit from that triple.
#
# Pre-registered reading (+-i states are the signal):
#   DD lifts +-i by >= 2 points toward the pole band while base
#     replicates ~0.94 -> slow dephasing confirmed AND mitigated.
#   DD changes nothing anywhere -> the loss is fast/Markovian or sits
#     inside the entangling gates; DD is not the lever, gate/layout is.
#   DD lifts everything equally -> generic idle-noise win, not
#     phase-specific.
#
# "test"     = Aer; bar: base, dd and ctrl all exactly 1.000, all six.
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
PM_STATES = ["|+i>", "|-i>"]
DD_GAPS_US = [0.4, 0.8, 0.8, 0.8, 0.4]   # delays around the 4 pulses

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister


def bob_readout(qc, basis):
    if basis == "X":
        qc.h(2)
    elif basis == "Y":
        qc.sdg(2); qc.h(2)


def live_circuit(prep, basis, dd=False):
    """Live protocol verbatim; dd=True inserts XY4 + delays on Bob
    between the Bell pair and Alice's measurement/correction block."""
    qr = QuantumRegister(3, "q")
    alice0 = ClassicalRegister(1, "alice0")
    alice1 = ClassicalRegister(1, "alice1")
    bob = ClassicalRegister(1, "bob")
    qc = QuantumCircuit(qr, alice0, alice1, bob)
    prep(qc)
    qc.barrier()
    qc.h(1); qc.cx(1, 2)
    qc.barrier()
    if dd:
        qc.delay(DD_GAPS_US[0], 2, unit="us")
        qc.x(2)
        qc.delay(DD_GAPS_US[1], 2, unit="us")
        qc.y(2)
        qc.delay(DD_GAPS_US[2], 2, unit="us")
        qc.x(2)
        qc.delay(DD_GAPS_US[3], 2, unit="us")
        qc.y(2)
        qc.delay(DD_GAPS_US[4], 2, unit="us")
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
    """Bare control: prep + matching-basis readout, one qubit."""
    qc = QuantumCircuit(1, 1)
    prep(qc)
    if basis == "X":
        qc.h(0)
    elif basis == "Y":
        qc.sdg(0); qc.h(0)
    qc.measure(0, 0)
    return qc


# structural check: DD circuit carries exactly X,Y,X,Y on Bob at top level
_dd_probe = live_circuit(PREPS["|+i>"], "Y", dd=True)
_dd_xy = [op.operation.name for op in _dd_probe.data
          if op.qubits and _dd_probe.find_bit(op.qubits[0]).index == 2
          and op.operation.name in ("x", "y")]
assert _dd_xy == ["x", "y", "x", "y"], f"DD structure wrong: {_dd_xy}"
print("DD structure check: Bob carries X-Y-X-Y plus",
      sum(DD_GAPS_US), "us of spacing delays.")

plan, circuits3, circuits1 = [], [], []
for s in STATES:
    plan.append(("base", s)); circuits3.append(live_circuit(PREPS[s], BASES[s], dd=False))
    plan.append(("dd", s));   circuits3.append(live_circuit(PREPS[s], BASES[s], dd=True))
    plan.append(("ctrl", s)); circuits1.append(control_circuit(PREPS[s], BASES[s]))
print(f"Built {len(circuits3)} teleportation circuits (6 base + 6 DD) "
      f"+ {len(circuits1)} controls.")


def sigma(p, n):
    return float(np.sqrt(p * (1 - p) / n)) if n else float("nan")


def choose_layout(backend):
    """Best connected triple (q_in, q_alice, q_bob) from calibration:
    minimize gate_error(q_in->q_alice) + gate_error(q_alice->q_bob)
    + readout_error(q_bob). Returns (layout_list, metrics) or
    (None, {}) if properties are unavailable."""
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

rows = {k: {} for k in ("base", "dd", "ctrl")}
ordered_results = []
if MODE == "hardware":
    it3, it1 = iter(range(len(circuits3))), iter(range(len(circuits1)))
    idx3 = idx1 = 0
    seq = []
    for kind, _s in plan:
        if kind in ("base", "dd"):
            seq.append(idx3); idx3 += 1
        else:
            seq.append(len(circuits3) + idx1); idx1 += 1
    ordered_results = [result[i] for i in seq]
else:
    idx3 = idx1 = 0
    seq = []
    for kind, _s in plan:
        if kind in ("base", "dd"):
            seq.append(idx3); idx3 += 1
        else:
            seq.append(len(circuits3) + idx1); idx1 += 1
    ordered_results = [result[i] for i in seq]

for (kind, state), pub_result in zip(plan, ordered_results):
    if kind == "ctrl":
        counts = pub_result.data.c.get_counts()
    else:
        counts = pub_result.data.bob.get_counts()
    ok = counts.get(str(TARGET_BIT[state]), 0)
    f = ok / SHOTS
    rows[kind][state] = {"fidelity": f, "sigma": sigma(f, SHOTS),
                         "counts": {k: int(v) for k, v in counts.items()}}

print(f"\n{'State':<7}{'Ctrl F':>9}{'Base F +- sig':>17}{'DD F +- sig':>17}{'DD-Base':>10}")
for s in STATES:
    b, d = rows["base"][s], rows["dd"][s]
    print(f"{s:<7}{rows['ctrl'][s]['fidelity']:>9.4f}"
          f"{b['fidelity']:>9.4f} ±{b['sigma']:.4f}"
          f"{d['fidelity']:>9.4f} ±{d['sigma']:.4f}"
          f"{(d['fidelity'] - b['fidelity']) * 100:>+9.2f}p")

mean_pm_base = float(np.mean([rows["base"][s]["fidelity"] for s in PM_STATES]))
mean_pm_dd = float(np.mean([rows["dd"][s]["fidelity"] for s in PM_STATES]))
print(f"\n+-i mean: base {mean_pm_base:.4f} -> DD {mean_pm_dd:.4f} "
      f"({(mean_pm_dd - mean_pm_base) * 100:+.2f} points)")

if MODE == "test":
    ok = all(rows[k][s]["fidelity"] == 1.0 for k in rows for s in STATES)
    print("VERIFICATION:", "PASS -- base, DD and control all exactly "
          "1.000 on all six states." if ok else "FAIL -- do not submit.")

out_name = ("dd_phoenix_results.json" if MODE == "hardware"
            else "dd_aer_verification.json")
with open(out_name, "w") as f:
    json.dump({"backend": BACKEND_NAME if MODE == "hardware" else "AerSimulator",
               "mode": MODE, "shots_per_circuit": SHOTS,
               "layout_in_alice_bob": layout, "layout_metrics": layout_metrics,
               "dd_gaps_us": DD_GAPS_US,
               "base": rows["base"], "dd": rows["dd"], "ctrl": rows["ctrl"]},
              f, indent=2)
print("Saved", out_name)
