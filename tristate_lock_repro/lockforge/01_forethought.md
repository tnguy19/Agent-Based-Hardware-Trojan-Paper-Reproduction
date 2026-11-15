# LockForge stage 1 - Forethought (LLM-A, PDF access)

**Prompt 1 (LockForge representative prompt):** "Read the paper and explain the logic locking scheme in it briefly."
**Prompt 2:** "Can you list the crucial concepts of the logic locking scheme?"

## 1. Brief explanation of the scheme (LLM-A)

The paper (Dupuis et al., LATS 2024) proposes a *new key-gate* for classical
"pre-SAT" logic locking (key-gates dispersed in the netlist, not a point-function
block).  The key-gate is a **tristate buffer and a tristate inverter in
parallel**, with their enable inputs driven by **two different key bits**
(k0 -> buffer enable, k1 -> inverter enable).  Depending on the combination of
the two key bits the gate has four modes: BUF (o = i), INV (o = ~i), Hi-Z
(both disabled, floating, keeps its previous value) and UNK (both enabled,
contention, intermediate voltage).  Four gate **types** (1-4) differ by whether
each enable is active-high or active-low, so the key combination that gives BUF
or INV is different for each type (type 1: BUF=(k1,k0)=(0,1); type 2: (1,1);
type 3: (0,0); type 4: (1,0)).  The designer inserts gates of all four types
(layout-camouflaged so they look alike), sets the correct 2-bit key so that each
gate behaves as BUF or INV (like XOR/XNOR key-gates, some gates must invert and
the driver gate is changed to compensate, Fig. 1), and any wrong key may
additionally produce Hi-Z / UNK, which the authors expect to keep corruption
high.  Area is claimed equal to an XOR key-gate (14 transistors), key size is
doubled (2 bits/gate), so a variant with half as many gates keeps the key size.
The claimed contributions are: (1) output corruption at the level of XOR/XNOR
key-gates (evaluated, Section V), (2) immunity to approximate and removal
attacks (argued), (3) SAT resilience as long as the cell type/function stays
hidden (argued, no experiment).

## 2. Crucial concepts (N = 12)  -> drives the C criterion

| id | concept |
|----|---------|
| C1 | key-gate = tristate buffer || tristate inverter, two independent key bits (k1 inverter-enable, k0 buffer-enable) |
| C2 | four operating modes: BUF, INV, Hi-Z (retains previous value), UNK (contention, intermediate voltage) |
| C3 | four gate types 1-4 = enable polarities (active high/low); BUF combination (k1,k0) = (0,1),(1,1),(0,0),(1,0) |
| C4 | correct key chosen so each gate acts as BUF or INV; an inverting gate is compensated in the driver (NAND->AND, Fig. 1) |
| C5 | location selection with FLL (fault-analysis based) |
| C6 | location selection with (improved) FpLL |
| C7 | 5 % extra key-gates budget; tristate has 2 key bits per gate, XOR/XNOR 1 |
| C8 | evaluation protocol: 1000 random vectors x 100 random *incorrect* keys, 8 benchmarks (c432,c1355,c1908,c3540,c5315,c7552,i8,apex4) |
| C9 | three metrics: output corruptibility (avg % Hamming distance), corruption rate (% vectors corrupted), output coverage (% outputs corrupted at least once) |
| C10 | half-key-gate experiment (2.5 % tristate gates = same key size as 5 % XOR) incl. the "4 largest circuits" subset |
| C11 | simulation semantics for the non-Boolean states Hi-Z / UNK (paper: previous value / threshold-dependent interpretation) |
| C12 | SAT-attack discussion: attacker knowing the type adds constraints (k0 != k1 for type 1) and breaks it; resilience needs hidden functionality |

## 3. Artifact-level expectations derived from the paper

* Netlist-level code that locks ISCAS/MCNC benchmarks with both schemes using the *same* locations.
* Simulation that handles a 4-mode, 2-key-bit gate with BUF/INV/Hi-Z/UNK.
* Reproduction targets: Table II (means over 8 circuits, FLL & FpLL), Fig. 5 (per circuit, FLL), Table III (half key-gates).
* Qualitative claims to check: |XOR - tristate| < 0.3 points in corruptibility and corruption rate; +2.5..3.5 points coverage for tristate; halving the gates degrades corruption on small circuits but not on the 4 largest.

## 4. Ambiguities detected at this stage (carried into README "Assumptions")
1. FLL and FpLL are only cited -> re-implemented from public descriptions.
2. "Improved FpLL" is not described.
3. Hi-Z / UNK simulation semantics not given.
4. Output coverage defined two ways in the literature (see README).
5. Random seeds, the exact 8-circuit netlists (esp. i8/apex4 synthesis) not given.
