# Quantum Teleportation on Real IBM Hardware: Six-State Benchmark Across Heron and Nighthawk Processors

**Mahara Taylor (ManyMoons), independent researcher**
October 2026 · IBM Quantum / Qiskit

---

## Abstract

A six-state quantum teleportation protocol using dynamic circuits —
mid-circuit measurement with classically-controlled X and Z
feed-forward corrections — was benchmarked in simulation and then
executed on three IBM Quantum processors. In simulation, the protocol
achieved an ideal corrected fidelity of 1.0, a tomography-style mean
fidelity of 0.9031 under a modeled noise channel, and agreement with
analytic depolarizing-noise theory to within 0.0037. On hardware, the
protocol reached a mean matching-basis success of 0.9008 on ibm_fez
(156-qubit Heron r2, two replicated runs, 1,200 shots), a full
three-basis tomography mean fidelity of 0.9606 on ibm_kingston
(156-qubit Heron r2, 1,024 shots per basis), and a mean success of
0.9583 on ibm_phoenix (120-qubit Nighthawk r2), which improved on the
ibm_fez result for every test state. The phase-sensitive ±i states
were the hardest to teleport in every dataset, simulated and real. A
bare control experiment on ibm_fez (preparation and readout only, mean
0.9733) decomposes the error budget: state preparation and measurement
set a ceiling of ≈ 0.973, and the teleportation machinery itself
costs ≈ 7 fidelity points beyond it. The simulator proved
conservative — both Heron tomography and the Nighthawk run exceeded
its predictions. A first ibm_phoenix run contained a readout-design
flaw (Z-basis readout for all states) that rendered its superposition
data uninformative; it is documented here as a case study, and the
corrected re-run is the result reported above.

## 1. Protocol

The circuit is full dynamic-circuit teleportation, not a
deferred-measurement textbook equivalent:

1. Alice prepares one of six test states: |0⟩, |1⟩, |+⟩, |−⟩, |+i⟩,
   |−i⟩ (the eigenstates of the Z, X, and Y Pauli axes).
2. A Bell pair is created between Alice's second qubit and Bob's
   qubit.
3. Alice performs a Bell-basis measurement on her two qubits,
   mid-circuit, producing two classical bits.
4. Bob applies an X correction conditioned on one bit and a Z
   correction conditioned on the other (`if_test` feed-forward), then
   his qubit is measured.

Two estimators are used, and they are not interchangeable:

- **Matching-basis success rate** (ibm_fez, ibm_phoenix): Bob is read
  in the eigenbasis of the state Alice prepared. For these axis
  states, the fraction of correct outcomes is a single-basis fidelity
  estimate.
- **Full state tomography** (ibm_kingston): Bob is read in the X, Y,
  and Z bases; the Bloch vector is reconstructed from the three basis
  means and fidelity is computed against the target state.

Sanity checks run alongside the protocol: Alice's measurement
marginals sat at ≈ 50/50 in every teleportation job, as the protocol
requires, and a standalone Bell-pair check on ibm_fez returned raw
counts {00: 49, 01: 2, 11: 47, 10: 2} — ≈ 96% of shots in the two
correct outcomes before any teleportation took place.

## 2. Simulator benchmark

Before any hardware run, the protocol was characterized in simulation
(the datasets ship with the companion *Quantum Teleportation Lab
Pack*):

- **Ideal case:** corrected fidelity **1.0** across the six states.
- **Noisy tomography-style study** (1,024 shots per basis, modeled
  noise): reconstructed mean fidelity **0.9031**; exact noisy fidelity
  **0.9246**. The ≈ −0.021 gap is a documented reconstruction bias of
  the estimator, reported rather than hidden.
- **Depolarizing channel:** simulated fidelities matched the analytic
  theory with a maximum gap of **0.0037** (mean gap 0.0008, 35 rows,
  10,000 shots) — the implementation agrees with the math.
- **Four-channel noise sweep** to p = 0.5: mean fidelity at p = 0.5
  was 0.750 (amplitude damping), 0.708 (bit flip), 0.680 (phase flip),
  0.556 (depolarizing, harshest).
- **Pattern:** the ±i states were the lowest-fidelity states in the
  simulator study (0.8837 / 0.8838 estimated), foreshadowing the
  hardware results below.

## 3. Hardware results

### 3.1 ibm_fez (Heron r2) — October 19, 2026

The full protocol ran as **two independent six-state replication
jobs** at 100 shots per state, plus a bare control and supporting
single-state jobs — 12 jobs in total, all retrievable from IBM's
records by job ID (raw counts: `data/oct19_results.json`).

Replication jobs: `dbbb6qgc77vs73841d1g` (mean 0.9017) and
`dbbb4uvi0auc73938670` (mean 0.9000). Combined (1,200 shots):

| State | Rep 1 | Rep 2 | Combined | Binomial σ |
|-------|-------|-------|----------|------------|
| \|0⟩  | 0.93 | 0.93 | 0.930 | 0.018 |
| \|1⟩  | 0.91 | 0.89 | 0.900 | 0.021 |
| \|+⟩  | 0.92 | 0.93 | 0.925 | 0.019 |
| \|−⟩  | 0.94 | 0.91 | 0.925 | 0.019 |
| \|+i⟩ | 0.85 | 0.88 | 0.865 | 0.024 |
| \|−i⟩ | 0.86 | 0.86 | 0.860 | 0.025 |
| **Mean** | 0.9017 | 0.9000 | **0.9008** | |

Two independent runs of a teleportation protocol on a real, noisy,
shared processor landed within two-tenths of a point of each other
and of the simulator benchmark (0.9031). The ±i states were lowest,
exactly as in simulation.

### 3.2 ibm_kingston (Heron r2) — full tomography, October 28, 2026

Job `dbh7rtpt9uhs73c9m0tg` (free Open instance). All six states × X,
Y, Z readout bases, 1,024 shots per basis — 3,072 shots per state,
18,432 total.

| State | Bloch (x, y, z) | Fidelity | Sim estimate | Diff |
|---|---|---|---|---|
| \|0⟩  | (−0.021, −0.004, 0.932) | 0.9658 | 0.9151 | +0.051 |
| \|1⟩  | (−0.006, −0.037, −0.908) | 0.9541 | 0.9143 | +0.040 |
| \|+⟩  | (0.945, 0.064, −0.004) | 0.9727 | 0.9106 | +0.062 |
| \|−⟩  | (−0.941, −0.096, −0.010) | 0.9707 | 0.9111 | +0.060 |
| \|+i⟩ | (−0.055, 0.908, 0.012) | 0.9541 | 0.8837 | +0.070 |
| \|−i⟩ | (0.049, −0.893, 0.010) | 0.9463 | 0.8838 | +0.063 |
| **Mean** | | **0.9606** | 0.9031 | **+0.058** |

Real hardware beat the simulation — and beat even the simulator's
*exact* noisy fidelity (0.9246). The noise model was more pessimistic
than the device. Reconstructed Bloch vectors are clean: dominant
component 0.89–0.95 on the correct axis, cross-talk ≤ 0.096. At 1,024
shots per basis the per-fidelity statistical error is ≈ 0.005, so the
+0.058 margin over the simulator benchmark is far outside shot noise.
The ±i states are again the hardest (0.9541 / 0.9463).

### 3.3 ibm_phoenix (Nighthawk r2) — corrected run, October 28, 2026

Job `dbh8et4dgr2s73ct0mv0` (pay-as-you-go instance). The exact October
19 protocol and register layout, 100 shots × 6 states, with per-state
matching-basis readout. The circuits were validated in an ideal
simulator (perfect 1.000 / 0.000 on all six states) before submission.

| State | ibm_fez (Oct 19) | ibm_phoenix (Oct 28) | Diff |
|-------|------------------|----------------------|------|
| \|0⟩  | 0.930 | 0.96 | +0.03 |
| \|1⟩  | 0.900 | 0.94 | +0.04 |
| \|+⟩  | 0.925 | 0.99 | +0.065 |
| \|−⟩  | 0.925 | 0.98 | +0.055 |
| \|+i⟩ | 0.865 | 0.94 | +0.075 |
| \|−i⟩ | 0.860 | 0.94 | +0.08 |
| **Mean** | 0.9008 | **0.9583** | **+0.058** |

Nighthawk won every state. The mean gap (+0.058) is roughly 4–5× the
combined shot-noise error (≈ 0.012), so the headline difference is
statistically solid; individual small gaps (|0⟩, |1⟩) should be read
as suggestive. The largest gains land exactly on the ±i
phase-sensitive states — the states that were hardest on Heron,
hardest in the simulator, hardest everywhere in this study. The ±i
states remain phoenix's lowest (0.94 / 0.94): the phase-fragility
pattern survives the new chip, but it shrank.

Consistency checks: phoenix's |0⟩/|1⟩ repeated almost exactly across
its two runs that evening (0.96 / 0.95 in the flawed run below, 0.96 /
0.94 here), and the phoenix single-basis mean (0.9583) sits beside the
independent kingston tomography mean (0.9606) — two estimators, two
chips, same neighborhood.

## 4. Error-budget analysis

A single fidelity number does not say where the error lives. The
control experiment does.

**ibm_fez — budget closed.** A bare control job
(`dbbb9f8c77vs73841i9g`) ran state preparation and matching-basis
readout *without* the teleportation step — same states, same machine,
same day:

| \|0⟩ | \|1⟩ | \|+⟩ | \|−⟩ | \|+i⟩ | \|−i⟩ | **Mean** |
|------|------|------|------|-------|-------|----------|
| 0.99 | 0.97 | 1.00 | 0.92 | 0.99 | 0.97 | **0.9733** |

Decomposition of the fez result:

- Preparation + readout ceiling: **0.9733** (2.7 points lost before
  teleportation begins)
- Teleportation result: **0.9008**
- Cost of the teleportation machinery itself — Bell pair, mid-circuit
  measurements, feed-forward latency: **≈ 7 points**

When a hardware teleportation number is quoted anywhere, the honest
question is "compared to what control?" The gap between the two *is*
the protocol's price.

**ibm_phoenix — budget closed.** The matching bare-control run
(job `dbhb93sdgr2s73ct6i4g`, Oct 28, 2026; preparation + matching-basis
readout only, 100 shots per state) returned:

| \|0⟩ | \|1⟩ | \|+⟩ | \|−⟩ | \|+i⟩ | \|−i⟩ | **Mean** |
|------|------|------|------|-------|-------|----------|
| 0.99 | 1.00 | 1.00 | 0.99 | 1.00 | 0.99 | **0.9950** |

Decomposition of the phoenix result:

- Preparation + readout ceiling: **0.9950** (0.5 points lost before
  teleportation begins — a cleaner floor than fez's 0.9733)
- Teleportation result: **0.9583**
- Cost of the teleportation machinery itself: **≈ 3.7 points** —
  about half the fez figure (≈ 7 points)

With both budgets closed, the cross-generation comparison is complete:
Nighthawk loses less at every stage — almost nothing to preparation
and readout (0.5 vs 2.7 points), and roughly half as much to the
teleportation machinery itself (3.7 vs 7.2 points). On phoenix the
remaining error sits overwhelmingly in the machinery (Bell-pair
fidelity, two-qubit gates, mid-circuit measurement and feed-forward),
not in state preparation or readout. The phase-sensitive (±i) states
remain the most expensive through the machinery specifically: perfect
or near-perfect in the phoenix control (1.00 / 0.99), yet the lowest
teleportation scores (0.94 / 0.94) — consistent with dephasing during
the measurement-and-correction window.

## 5. Case study: the first Nighthawk run and the readout flaw

The first ibm_phoenix run (job `dbh7te4dgr2s73csvfe0`, Oct 28, 2026)
read Bob's qubit in the **Z basis for all six states**, instead of
rotating into each state's matching basis first. A Z-basis readout of
a perfectly teleported |+⟩ state returns 0 or 1 with equal
probability — a coin flip containing no information about whether the
teleportation worked. The data shows exactly that signature:

| \|0⟩ | \|1⟩ | \|+⟩ | \|−⟩ | \|+i⟩ | \|−i⟩ |
|------|------|------|------|-------|-------|
| 0.96 | 0.95 | 0.57 | 0.51 | 0.52 | 0.55 |

(fraction of outcome 0 / success for Z-basis states, 100 shots each)

- The |0⟩ and |1⟩ results **are valid** — those states are read in Z
  anyway — and both beat the Oct 19 ibm_fez values.
- The four superposition values **are not fidelities** and are never
  presented as such anywhere in this project. An "average" over all
  six (≈ 0.66) would be meaningless.
- The flaw was in the run notebook's readout design, not in the
  teleportation circuit, which was complete and correct. It was found
  on review of the saved outputs the same evening, and the run was
  repeated with the corrected readout (Section 3.3) after ideal-
  simulator validation.
- The flawed dataset is preserved in this repository
  (`data/run1_phoenix_result_zreadout.json`) with its interpretation
  note attached, as a teaching artifact.

**Lesson:** when a hardware result looks surprising, check the
measurement basis before blaming the machine. Readout design is part
of the experiment.

## 6. Cross-cutting patterns

1. **Phase-sensitive states are the bottleneck, everywhere.** The ±i
   (Y-basis) pair scored lowest in the simulator study, on ibm_fez,
   in ibm_kingston tomography, and on ibm_phoenix. The noise sweep
   agrees from the theory side: phase-flip and depolarizing channels
   damage this protocol most; amplitude damping least.
2. **The simulator was conservative.** Its state-difficulty pattern
   transferred to hardware exactly, but its magnitudes were
   pessimistic — real devices beat the modeled fidelities (kingston
   0.9606 vs. 0.9031 estimated / 0.9246 exact).
3. **Replication beats any single number.** The two fez replication
   jobs agreed to 0.0017 in the mean; per-state differences all sat
   within binomial error bars. That agreement, more than any headline
   figure, is what validates the benchmark.
4. **The newest hardware improved most where the protocol hurts
   most.** Nighthawk's largest gains were on the ±i states — the
   phase-fragility pattern persisted but shrank on the newer
   processor.

## 7. Honest limits

- **Single runs per device.** Each hardware figure comes from one
  run (fez: two replications) on one day. Device performance drifts
  with calibration; these are measurements of these machines on these
  days, not permanent specifications.
- **Modest shot counts on fez/phoenix.** At 100 shots per state,
  binomial error bars are roughly ±2 points; per-state differences
  smaller than that should not be over-read. The kingston tomography
  (1,024 shots/basis, σ ≈ 0.005) is the statistically tightest
  dataset here.
- **kingston > fez is not a clean device verdict.** Different days,
  different circuit builds, different shot counts, different
  estimators. It demonstrates device/day variation of several points,
  nothing stronger.
- **Estimators differ across sections.** Matching-basis success
  (fez, phoenix) and tomography fidelity (kingston) are cousins, not
  twins; they are labeled wherever they appear.
- **The phoenix error budget is open** until its control job
  completes (Section 4).

## 8. Conclusions

The teleportation protocol is verified end to end: analytically (gap
≤ 0.0037 against theory), in simulation (ideal fidelity 1.0, noisy
tomography benchmark 0.9031), and on three real processors, by two
different estimators, with replication and a control experiment. Real
hardware matched the simulator where the comparison is tightest (fez:
0.9008 vs. 0.9031) and exceeded it where the estimator is strictest
(kingston tomography: 0.9606). IBM's Nighthawk processor improved on
Heron for every state, most strongly on the phase-sensitive states
that limit this protocol. The remaining open item is deliberately
small and named: the ibm_phoenix control run that will close its
error budget the way the ibm_fez budget is already closed.

## Data and reproducibility

All raw counts and per-state results are in `data/`:

| File | Contents |
|------|----------|
| `oct19_results.json` | Raw counts for all 12 Oct 19 ibm_fez jobs, by job ID |
| `hardware_oct19_six_state_results.csv` | Oct 19 six-state summary, control, sim comparison |
| `run2_result.json` / `hardware_tomography_results.csv` | ibm_kingston tomography (job `dbh7rtpt9uhs73c9m0tg`) |
| `run1_phoenix_result.json` | Corrected ibm_phoenix run (job `dbh8et4dgr2s73ct0mv0`) |
| `run1_phoenix_result_zreadout.json` | Flawed first phoenix run (job `dbh7te4dgr2s73csvfe0`) — see Section 5 |
| `postselection_phoenix_results.json` | Post-selection test, ibm_phoenix Nov 2, 2026 (job `dbkcb6gnceqs73aljkfg`) — see Section 9.1 |
| `tomography_phoenix_results.json` | Teleportation tomography, ibm_phoenix Nov 2, 2026 (job `dbkcbo9kdqps73926160`) — see Section 9.2 |
| `interleaved_phoenix_results.json` | Interleaved live vs. post-selected, single job, ibm_phoenix Nov 2, 2026 (job `dbkcf1pffo6c73bb7v9g`) — see Section 9.3 |
| `bobfirst_phoenix_results.json` | Bob-first readout ordering, ibm_phoenix Nov 2, 2026 (job `dbkcg0t6p51s73cmc3vg`) — see Section 9.4 |
| `dd_phoenix_results.json` | XY4 dynamical decoupling + pinned layout, ibm_phoenix Nov 2, 2026 (job `dbkd7mhkdqps73927g6g`) — see Section 9.5 |

The notebooks for the Oct 28 runs are in `notebooks/`. They take the
IBM Quantum API key via `getpass` at runtime; no credentials are
stored in them. Anyone with an IBM Quantum account can re-run the
protocol and compare against these tables — and should expect their
numbers to differ somewhat, because device variance is part of what
this benchmark measures.

## 9. November 2, 2026 — the ±i follow-up arc

The October budget closed with one unexplained residue: on
ibm_phoenix the ±i states were at or near the ceiling in the bare
control (1.00 / 0.99) yet the lowest in teleportation (0.94 / 0.94).
A reader's objection sharpened the problem — the mid-circuit window
is ~1 µs against T2 ≥ 100 µs, so idle dephasing in that window
cannot cost ~6 points. Five follow-up experiments ran on
ibm_phoenix on November 2, 2026, each designed against a
pre-registered decision rule. Scripts for all five are in
`notebooks/`; raw results in `data/`.

### 9.1 Post-selection — is it the feed-forward?

Job `dbkcb6gnceqs73aljkfg`. The October circuits with the live
feed-forward corrections removed: Alice is still measured
mid-circuit, and the corrections are applied afterwards in software
(Pauli-frame tracking). Software-corrected fidelities: |+i⟩ 0.9512,
|−i⟩ 0.9492 — indistinguishable from the live protocol (0.94 /
0.94) and ~4.5 points below the 0.995 bare control. Removing the
corrections changed nothing. **The feed-forward path is
exonerated**; the loss is already present before any correction
could act.

### 9.2 Tomography — rotation or shrinkage?

Job `dbkcbo9kdqps73926160`. Full three-basis tomography of Bob's
output under the live protocol (1,024 shots per basis). The
reconstructed Bloch vectors came back with lengths |r| of
0.87–0.94 across the six states (mean fidelity 0.9468): the
vectors are *shorter*, not twisted. Three of the four equatorial
states also showed a consistent phase offset of +5 to +7.6°, but a
pure rotation of that size costs only ≈ 0.2 fidelity points. The
deficit is **shrinkage — true coherence loss** — with at most a
small frame offset on top.

### 9.3 Interleaved replication — same job, same calibration

Job `dbkcf1pffo6c73bb7v9g`. Live-correction and post-selection
circuits interleaved in a single submission (4,096 shots per
circuit): live |+i⟩ 0.9431 / |−i⟩ 0.9412; post-selected (Alice = 00
branch) 0.9468 / 0.9461. The deficit replicates inside one
calibration window, so it is not cross-day drift and does not
depend on how the corrections are delivered. (Method note: the two
circuit types were transpiled independently in this job, so their
physical layouts may differ; the ±i gaps are under 1σ, and the
follow-up in 9.5 pins a single layout for exactly this reason.)

### 9.4 Bob-first ordering — does the loss precede the readout?

Job `dbkcg0t6p51s73cmc3vg`. Bob is rotated and measured *before*
Alice's qubits are measured, so his outcome is recorded before
the neighbouring readout pulses ever fire: |+i⟩ 0.9521, |−i⟩
0.9451, while the pole states in the same job reached 0.969. No
recovery. **The coherence is already gone before Alice's readout
window opens** — readout crosstalk during that window is not the
mechanism.

### 9.5 Pinned layout + dynamical decoupling — what actually helps

Job `dbkd7mhkdqps73927g6g`. Two changes, A/B-tested inside one
job: (i) the physical triple was pinned to the day's best
calibration — qubits [81, 91, 92], CZ errors ≈ 0.1% on both links,
Bob T2 of 173 µs; (ii) half the circuits added an XY4
dynamical-decoupling sequence on Bob across his idle window.

On the pinned triple the unmodified protocol posted mean 0.9708
(|+i⟩ 0.9702, |−i⟩ 0.9570) against a same-day bare control of
0.9969 — a total teleportation cost of **2.6 points**, down from
3.7 in October. The DD variant was slightly *worse* on all six
states (−0.3 to −1.0 points): the echo pulses and their added
circuit time cost more than the refocusing recovered, which says
the dephasing behaves Markovian — a steady T2-rate leak — rather
than slow and refocusable. The practical prescription is
unfashionable and clear: **pin the best-calibrated triple and
keep the circuit short.** Physical-qubit selection alone was
worth ~2 points on the ±i pair — more than any pulse-level trick
tried here.

### 9.6 Verdict

Across the arc: the ±i deficit is phase decoherence accrued in
the entangled front half of the circuit — state preparation,
Bell-pair creation, and Alice's entangling gates. It is not the
feed-forward corrections (9.1), not a frame rotation (9.2), not
calibration drift (9.3), and not Alice's readout window (9.4).
The ±i states are simply the canary: they live on the equator of
the Bloch sphere, and the phase is what dies first.

---

*Independent research; not affiliated with or endorsed by IBM.
Qiskit and IBM Quantum are trademarks of IBM.*
*Code: MIT License. Data and text: CC BY 4.0 (Mahara Taylor).*
