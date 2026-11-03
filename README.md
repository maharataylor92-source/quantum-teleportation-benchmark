# Quantum Teleportation Benchmark — Real IBM Hardware, Three Processors

**Author:** Mahara Taylor (ManyMoons), independent researcher
**Platform:** IBM Quantum / Qiskit — ibm_fez, ibm_kingston, ibm_phoenix

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23809804.svg)](https://doi.org/10.5281/zenodo.23809804)

## How to cite

Taylor, M. (2026). *Six-state quantum teleportation benchmark on real IBM
hardware (ibm_fez, ibm_kingston, ibm_phoenix)* (v1.0.0). Zenodo.
https://doi.org/10.5281/zenodo.23809804

The concept DOI https://doi.org/10.5281/zenodo.23809803 always resolves to
the latest version of this record.

## Summary

A six-state quantum teleportation protocol — full dynamic circuits with
mid-circuit measurement and classically-controlled X/Z feed-forward
corrections — benchmarked first in simulation and then run on three real
IBM Quantum processors: ibm_fez (156-qubit Heron r2), ibm_kingston
(156-qubit Heron r2), and ibm_phoenix (120-qubit Nighthawk r2). The
real devices matched or beat the simulator benchmark everywhere: the
Heron teleportation runs landed within two-tenths of a point of the
simulator's tomography figure, full hardware tomography on ibm_kingston
reached a mean fidelity of 0.9606, and the newest Nighthawk processor
beat the Heron result on every one of the six test states. Every number
here is traceable to an IBM job ID printed next to it, and the raw
counts are in [`data/`](data/).

## Headline results

### ibm_fez — teleportation, matching-basis readout (Oct 19, 2026)

100 shots per state, two independent replication jobs combined
(1,200 shots total). Replication jobs: `dbbb6qgc77vs73841d1g`,
`dbbb4uvi0auc73938670`. Bare control (prep + readout only):
`dbbb9f8c77vs73841i9g`.

| State | Combined success | Bare control |
|-------|------------------|--------------|
| \|0⟩  | 0.930 | 0.99 |
| \|1⟩  | 0.900 | 0.97 |
| \|+⟩  | 0.925 | 1.00 |
| \|−⟩  | 0.925 | 0.92 |
| \|+i⟩ | 0.865 | 0.99 |
| \|−i⟩ | 0.860 | 0.97 |
| **Mean** | **0.9008** | **0.9733** |

The control sets the prep-and-readout ceiling at 0.9733, so
teleportation itself costs ≈ 7 fidelity points on ibm_fez.

### ibm_kingston — full 3-basis tomography (Oct 28, 2026)

1,024 shots per basis, 3,072 shots per state. Job:
`dbh7rtpt9uhs73c9m0tg`.

| State | Fidelity |
|-------|----------|
| \|0⟩  | 0.9658 |
| \|1⟩  | 0.9541 |
| \|+⟩  | 0.9727 |
| \|−⟩  | 0.9707 |
| \|+i⟩ | 0.9541 |
| \|−i⟩ | 0.9463 |
| **Mean** | **0.9606** |

### ibm_phoenix — teleportation, matching-basis readout (Oct 28, 2026)

100 shots × 6 states, corrected readout design (see the case study in
[RESULTS.md](RESULTS.md)). Job: `dbh8et4dgr2s73ct0mv0`.

| State | Success |
|-------|---------|
| \|0⟩  | 0.96 |
| \|1⟩  | 0.94 |
| \|+⟩  | 0.99 |
| \|−⟩  | 0.98 |
| \|+i⟩ | 0.94 |
| \|−i⟩ | 0.94 |
| **Mean** | **0.9583** |

Nighthawk beat ibm_fez on every state, with the biggest gains on the
phase-sensitive ±i states (+0.075 / +0.08).

### Simulator benchmark (for comparison)

| Quantity | Value |
|----------|-------|
| Tomography-style mean fidelity (sim) | 0.9031 |
| Exact noisy fidelity (sim) | 0.9246 |
| Ideal corrected fidelity | 1.0 |
| Depolarizing sim vs. analytic theory, max gap | 0.0037 |

## Methods in brief

Alice prepares one of six axis states (|0⟩, |1⟩, |+⟩, |−⟩, |+i⟩,
|−i⟩), a Bell pair is shared with Bob, Alice performs a Bell-basis
measurement mid-circuit, and Bob applies X and Z corrections
conditioned on Alice's two classical bits — real feed-forward, not a
deferred-measurement equivalent. For the fez and phoenix runs, Bob was
read in each state's matching basis, so the fraction of correct
outcomes is a single-basis fidelity estimate for these axis states.
The kingston run measured all three bases per state and reconstructed
full single-qubit tomography fidelities. The simulator benchmark used
the same protocol under a modeled noise channel, with a four-channel
noise sweep (amplitude damping, bit flip, phase flip, depolarizing) in
the companion Lab Pack datasets. Full details: [RESULTS.md](RESULTS.md).

## Honest limits

- **Estimators differ.** The fez/phoenix figures are matching-basis
  success rates; the kingston figure is a full tomography fidelity;
  the simulator figure is a tomography-style reconstruction under a
  noise model. They are comparable, not identical, quantities — the
  write-up says so wherever they appear side by side.
- **Single runs, modest shots.** One run per device; 100 shots per
  state on fez/phoenix means binomial error bars of roughly ±2 points.
  Small per-state differences are weather, not climate.
- **kingston vs. fez is not a clean device verdict** — different days,
  circuit builds, and shot counts. The phoenix-vs-fez comparison uses
  the identical protocol on both, but still spans different days.
- **A flawed run is included, labeled.** The first phoenix run
  (`dbh7te4dgr2s73csvfe0`) read Bob in the Z basis for all six states;
  its |0⟩/|1⟩ results are valid, its superposition results are
  measurement artifacts. It is documented as a case study in
  RESULTS.md, and its data file carries the caveat in its filename
  and contents.

## Repository layout

- `README.md` — this file
- `RESULTS.md` — the full results write-up
- `data/` — raw counts and per-state result files (CSV + JSON) for
  every run cited, including the five November 2, 2026 ibm_phoenix
  follow-up datasets (`postselection_phoenix_results.json`,
  `tomography_phoenix_results.json`,
  `interleaved_phoenix_results.json`, `bobfirst_phoenix_results.json`,
  `dd_phoenix_results.json`)
- `notebooks/` — the Colab notebooks used for the Oct 28 kingston
  tomography and corrected phoenix runs (API key entered via
  `getpass` at runtime; no credentials are stored in them), plus the
  five November 2 ibm_phoenix follow-up run scripts
  (`postselection_phoenix.py`, `tomography_phoenix.py`,
  `interleaved_phoenix.py`, `bobfirst_phoenix.py`, `dd_phoenix.py`;
  instance CRN left as a placeholder and the API token read from
  stdin, so they default to `MODE = "test"` and cannot submit to
  hardware unattended)

## How to cite

> Taylor, M. (2026). *Quantum Teleportation Benchmark: Six-State
> Protocol on IBM Heron and Nighthawk Processors.* Independent
> research. https://github.com/ — repository URL to be added on
> publication.

When citing a specific number, please also cite the IBM job ID listed
with it — every result in this repository is traceable to one.

## License

- **Code** (notebooks and any scripts): MIT License — see
  [`LICENSE`](LICENSE).
- **Data and documentation** (everything in `data/`, `README.md`,
  `RESULTS.md`): Creative Commons Attribution 4.0 International
  (CC BY 4.0). You may share and adapt them with attribution to
  Mahara Taylor.

## Affiliation note

Independent research. Not affiliated with or endorsed by IBM. Qiskit
and IBM Quantum are trademarks of IBM. Results were obtained on
shared public-access processors; results on the same machines will
vary.
