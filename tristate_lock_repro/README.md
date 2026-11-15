# Reproduction of "Logic Locking: Exploration of a New Key-Gate Based on Tristate Logic"

Paper: S. Dupuis, N. Riadi, C. Moroukian, F. Azaïs, M.-L. Flottes, *IEEE LATS 2024*, DOI 10.1109/LATS62223.2024.10534598.
Method of reproduction: the **LockForge** paper-to-code framework (Saha et al., arXiv:2511.18531), run by AI agents (Claude). The agent trail is in [`AGENT_LOG.md`](AGENT_LOG.md).

## TL;DR - what was and was not reproduced

| Paper claim | Reproduced? | Our number (FLL, 8 circuits) | Paper |
|---|---|---|---|
| Tristate key-gates corrupt outputs as much as XOR/XNOR (corruptibility) | **Yes** | 46.0 vs 46.1 (Δ 0.11) | 42.0 vs 41.9 (Δ < 0.3) |
| ... same for corruption rate | **Yes** | 99.5 vs 99.7 (Δ 0.21) | 99.6 vs 99.7 |
| Per-circuit corruption rate (Fig. 5b) | **Yes** (r = 1.00, only c432 < 100 %) | | |
| Result holds for a 2nd insertion algorithm | **Yes** (Δ ≤ 0.25 for FpLL and FpLL+) | | Δ < 0.3 |
| Halving the tristate gates (2.5 %) costs corruptibility on all 8 circuits (Table III) | **Yes** | −4.8 pts (46.1 → 41.3) | −4.7 pts (41.9 → 37.2) |
| ... but "almost no degradation" on the 4 largest circuits | **No** | −4.5 pts (45.5 → 41.0, same 4 circuits) | 41.9 → 40.8 |
| Absolute corruptibility level / per-circuit ordering (Fig. 5a) | **Partly** - level +4 pts, ordering uncorrelated (r ≈ 0) | 46.1 | 41.9 |
| Tristate improves output coverage by 2.5-3.5 pts | **Depends on the coverage definition** - 0.0 with the paper's wording, +13 with a per-key reading (see below) | 99.2 / 99.2 (D1) | 66.6 → 70.1 |

The headline claim (*tristate ≈ XOR in corruption at equal gate count; key size doubles*) is reproduced and is robust to every simulation-model variation tested. Absolute values and the coverage metric are **not** matched, mostly because the paper under-specifies the insertion algorithms and the coverage definition (details below). Nothing was tuned to hit the paper's numbers.

## Repository layout

```
tristate_lock/        library
  netlist.py          netlist, .bench / .blif parsers (BLIF SOP -> AND/OR/NOT)
  sim.py              bit-parallel simulator (Python big ints: 1 bit per (key, vector) trial)
  keygates.py         XOR/XNOR + tristate key-gate semantics (types 1-4, BUF/INV/HiZ/UNK)
  locking.py          locked-design builder + simulator for 100,000 (key,vector) trials
  insertion.py        location selection: random, FLL, FpLL (as published), FpLL+ (our "improved")
  metrics.py          output corruptibility / corruption rate / output coverage
  sat_attack.py       supplementary SAT attack (pysat)
run_experiments.py    Table II / Fig. 5 / Table III / sensitivity experiments  -> results/raw_results.csv
analyze.py            aggregates, compares with the paper, draws figures      -> results/
run_sat_attack.py     supplementary SAT-attack scenarios                      -> results/sat_attack.csv
benchmarks/           c432 c880 c1355 c1908 c3540 c5315 c7552 (.bench), i8 apex4 (.blif)
reference/            paper numbers: Table II/III (json) and Fig. 5 bars digitised from the image
tests/                11 unit/integration tests
lockforge/            LockForge artefacts: Forethought, BCSRP YAML, local scoring, judge/examiner reports
results/              all outputs (CSV, tables in report_tables.md, PNG figures)
docs/                 paper figure page used for digitising; raw event log
AGENT_LOG.md          prompts, errors, refinements
```

## How to run

```bash
pip install -r requirements.txt          # numpy pandas matplotlib tabulate python-sat (Python >= 3.10)
./run_all.sh                             # everything, ~1-2 min on 2 cores
# or step by step
python -m unittest discover -s tests -v
python run_experiments.py --exp main half model          # paper protocol, 5 seeds (840 runs)
python run_experiments.py --quick --out /tmp/quick       # smoke test (seconds)
python analyze.py                        # tables (results/report_tables.md) + figures
python run_sat_attack.py                 # supplementary
python lockforge/evaluate_bcsrp.py       # LockForge local-execution score
```

Options: `--circuits c432 c7552`, `--algos fll fpll fpll_plus random`, `--seeds 5`, `--n-vec 1000 --n-keys 100`, `--procs 2`.
All randomness is seeded; reruns give identical numbers.

## What was implemented (paper → code)

* **Tristate key-gate** (Sec. III, Fig. 3, Table I): tristate inverter (enable = k1) ∥ tristate buffer (enable = k0), two key bits; modes BUF, INV, Hi-Z, UNK; types 1-4 = active-high/low enables. Mapping verified against Table I and the BUF combinations in the text, (k1,k0) = (0,1),(1,1),(0,0),(1,0) (`tests/`). Each gate's correct key is chosen so it acts as BUF or INV (50/50); an inverting gate is compensated in its driver (NAND→AND as in Fig. 1), so the correct key restores the function (checked for all 8 circuits × 2 schemes × 4 algorithms).
* **Baseline**: XOR/XNOR key-gates with the *same locations and same BUF/INV pattern*.
* **Protocol** (Sec. V): 5 % extra key-gates, 1000 random vectors × 100 random *incorrect* keys, 8 circuits (c432, c1355, c1908, c3540, c5315, c7552, i8, apex4 - read from Fig. 5), the three metrics, 2.5 % tristate variant.
* **Table III "4 largest"** = c7552, c5315, i8, apex4 by our gate count.
* Results are averaged over 5 seeds (keys, gate types, test vectors); location selection is fixed per (circuit, algorithm).

## Assumptions and deviations (the paper does not specify these)

1. **FLL** is only cited. Implemented as a greedy, masking-aware selection by *inversion-flip impact* (a wrong key bit inverts the net), with lazy (CELF) re-evaluation - an approximation of exact greedy. Rajendran's original uses stuck-at impact; the choice may explain level differences vs the paper.
2. **FpLL** is implemented as published in SKG-Lock+ (probability propagation, OCS = Δp₀·n₀ + Δp₁·n₁, one-shot ranking, skip equal scores). It performs poorly on XOR-dominated circuits (c1355/c1908) because signal probabilities stay 0.5. The paper uses an *"improved FpLL"* that is not described; **FpLL+** is *our* interpretation (one-shot flip-observability ranking as a pool + masking-aware greedy inside the pool). Treat FpLL+ results as ours, not the paper's.
3. **Hi-Z / UNK in simulation**: Hi-Z = a random constant per (key, gate) (the gate stays floating for the whole test, so the node never gets re-driven); UNK = a random logic value per (key, gate). Chosen *before* looking at results. Sensitivity (`results/model_sensitivity.csv`, 15 combinations): UNK model changes corruptibility by ≤ 0.5 pt; Hi-Z = stuck-0 lowers it by ≈ 2 pts; conclusions unchanged.
4. **Output coverage** is ambiguous. Paper text: "% of outputs corrupted at least once"; the authors' earlier SKG-Lock+ paper defines max-Hamming-distance/m. We report three readings: **D1** (primary, literal text: over all 100,000 trials), **D2** (per wrong key, averaged over keys), **D3** (max HD / m). D1 saturates at ≈ 99 % (paper ≈ 67-70 %); D2 gives the paper's qualitative trend (tristate > XOR) but with a larger gap (+13 vs +3.5 pts). We could not determine which one the authors used.
5. **Netlists**: ISCAS-85 gate counts equal the published ones. For the MCNC circuits (BLIF) we map every `.names` cover to AND/OR/NOT gates (i8 → 2048 gates, apex4 → 1760), so their 5 % budget may differ from the authors' synthesized netlists.
6. Key-gates go on gate-output nets only (never primary inputs).
7. The paper's Fig. 5 values were **digitised** by pixel analysis (`reference/paper_fig5_digitised.csv`); the means of the digitised bars match the paper's Table II to ≤ 0.2 pt, bar-level accuracy ≈ ±0.5 pt.

## Results (full tables: `results/report_tables.md`)

Table II analogue, mean over 8 circuits, 5 seeds (± std over seeds):

| algorithm | metric | XOR/XNOR | tristate | paper XOR / tri |
|---|---|---|---|---|
| FLL | corruptibility | 46.1 ± 0.2 | 46.0 ± 0.2 | 41.9 / 42.0 |
| FLL | corruption rate | 99.7 ± 0.2 | 99.5 ± 0.2 | 99.7 / 99.6 |
| FLL | coverage D1 | 99.2 | 99.2 | 66.6 / 70.1 |
| FLL | coverage D2 (per key) | 77.2 | 90.5 | - |
| FpLL (published) | corruptibility | 32.1 | 31.9 | 43.5 / 43.4 (paper uses improved FpLL) |
| FpLL+ (ours) | corruptibility | 39.4 | 39.3 | 43.5 / 43.4 |
| FpLL+ (ours) | corruption rate | 99.5 | 99.3 | 98.5 / 98.8 |
| random insertion (extra) | corruptibility | 25.3 | 25.3 | - |

Figures: `results/fig5_fll_reproduced.png` (Fig. 5 with the paper's bars overlaid as diamonds), `results/fig5_fpllplus.png`, `results/table3_halved_keygates.png`.

**Supplementary SAT-attack analysis** (`results/sat_attack.csv`; the paper discusses SAT resilience qualitatively and has no SAT experiment; one seed, FLL locations, c432/c880/c1908):

| attacker knowledge | outcome |
|---|---|
| XOR/XNOR locking, standard attack | exact key in 3-19 DIPs |
| tristate, cell types known (+ "no Hi-Z/UNK" constraint) | exact key (the paper concedes this) |
| tristate, types unknown but *family* known (types as extra unknown bits) or all assumed type 1 | **function fully recovered** (SAT-equivalent netlist), though the recovered key does not work on the real chip |
| Hi-Z/UNK modelled as unconstrained outputs | does not converge (stopped at 40 DIPs) |

So the "SAT resilience" argument holds only against an attacker who cannot treat the cell as a programmable BUF/INV; a family-aware attacker recovers the original function without needing the key. This is our observation, with a small sample, not a claim of the paper.

## LockForge process (how the agents were used)

Stages from the LockForge paper, applied here (details and prompts in `AGENT_LOG.md`, artefacts in `lockforge/`):

1. **Forethought** - LLM-A (coder, PDF access) summarised the scheme and extracted 12 key concepts (`lockforge/01_forethought.md`).
2. **Implementation** - code written and smoke-tested on the benchmarks.
3. **Refinement loop** - BCSRP checklist in YAML (`lockforge/tristate_BCSRP.yaml`) + local execution (`lockforge/evaluate_bcsrp.py`). This loop caught a real bug (FpLL+ returned 61 instead of 88 key-gates on apex4; fixed, everything rerun).
4. **Validation** - an isolated Judge (LLM-B, Claude Opus) and Examiner (LLM-C, Claude Haiku) saw **only the code**: Judge score **9.15/10 (pass ≥ 8)**; Examiner **10/10 true/false correct (pass ≥ 8)**; Examiner's holistic score 6/10 (driven by the isolated package lacking benchmark files). Their defect lists led to docstring fixes, a 512-vector equivalence check, a duplicate-location assertion and the documentation above.

Limitations of the process: the original LockForge PDF was not among the uploads, so the framework was taken from the arXiv version and its public artifact repo; all agents are Claude models (LockForge recommends different model *families* per role to reduce bias); the local B/C/S/R score (10/10) is self-assessed and should not be read as independent evidence.

## Limitations

* Absolute numbers differ from the paper (+4 pts corruptibility under FLL; coverage D1 far above the paper) because the exact FLL/FpLL, the Hi-Z/UNK simulation, the coverage definition and the MCNC netlists are not given.
* "Improved FpLL" is our guess; FpLL vs FLL ordering in the paper is not reproduced.
* No physical (transistor-level / layout-camouflage) evaluation; the area claim (14 transistors, XOR-equivalent) is taken from the paper, not tested.
* SAT results are a supplementary, single-seed illustration.
