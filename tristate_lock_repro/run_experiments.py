#!/usr/bin/env python3
"""Reproduce the experiments of Section V of

  S. Dupuis et al., "Logic Locking: Exploration of a New Key-Gate Based on
  Tristate Logic", IEEE LATS 2024.

Experiments
  main   : Table II / Fig. 5  - XOR/XNOR vs tristate key-gates, 5 % key-gates,
                                FLL and (improved) FpLL insertion.
  half   : Table III          - tristate with 2.5 % key-gates (same key size).
  model  : sensitivity        - how Hi-Z / UNK are interpreted in simulation.

Usage:  python run_experiments.py --exp main half model [--quick]
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tristate_lock.insertion import ALGORITHMS
from tristate_lock.locking import Models, lock_netlist
from tristate_lock.metrics import (corruption_metrics, correct_key_equivalent,
                                   draw_behaviours)
from tristate_lock.netlist import read_netlist
from tristate_lock.sim import Compiled

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = {  # the 8 circuits of Fig. 5 of the paper
    "c432": "c432.bench", "c1355": "c1355.bench", "c1908": "c1908.bench",
    "c3540": "c3540.bench", "c5315": "c5315.bench", "c7552": "c7552.bench",
    "i8": "i8.blif", "apex4": "apex4.blif",
}
METRICS = ["output_corruptibility", "corruption_rate", "output_coverage",
           "output_coverage_per_key", "output_coverage_maxhd"]


def run_circuit(job):
    """All experiments for one circuit (one process)."""
    (name, algos, seeds, n_vec, n_keys, exps, sel_seed, model_seeds) = job
    nl = read_netlist(os.path.join(HERE, "benchmarks", BENCH[name]))
    co = Compiled(nl)
    N = len(nl.gates)
    K5 = max(1, round(0.05 * N))
    K25 = max(1, round(0.025 * N))
    rows = []

    def one(algo, scheme, nets, seed, tag, models, K_frac, sel_time):
        rng = random.Random(f"{name}|{algo}|{seed}|beh")
        beh = draw_behaviours(len(nets), rng)         # shared by XOR / tristate
        trng = random.Random(f"{name}|{algo}|{seed}|{scheme}|type")
        d = lock_netlist(nl, nets, scheme, beh, trng)
        cl = Compiled(d.base)
        mrng = random.Random(f"{name}|{algo}|{seed}|{scheme}|{tag}|sim")
        eq = correct_key_equivalent(d, co, cl, 512, random.Random(seed), models)
        m = corruption_metrics(d, co, cl, n_vec, n_keys, mrng, models)
        row = dict(circuit=name, gates=N, algo=algo, scheme=scheme, tag=tag,
                   key_gate_pct=K_frac, n_key_gates=len(nets),
                   key_bits=d.n_key_bits, seed=seed, hiz=models.hiz, unk=models.unk,
                   sel_time_s=round(sel_time, 3), correct_key_ok=int(eq))
        row.update(m)
        rows.append(row)

    for algo in algos:
        t0 = time.time()
        nets_full = ALGORITHMS[algo](co, K5, random.Random(sel_seed))
        sel_time = time.time() - t0
        assert len(nets_full) == K5, f'{name}/{algo}: selected {len(nets_full)} of {K5} key-gates'
        nets_half = nets_full[:K25]
        dm = Models()
        if "main" in exps or "half" in exps:
            for seed in seeds:
                if "main" in exps:
                    one(algo, "xor", nets_full, seed, "main", dm, 5.0, sel_time)
                    one(algo, "tri", nets_full, seed, "main", dm, 5.0, sel_time)
                if "half" in exps:
                    one(algo, "tri", nets_half, seed, "half", dm, 2.5, sel_time)
        if "model" in exps and algo == "fll":
            for hiz in ("const", "zero", "vec"):
                for unk in ("const", "pin", "vec", "buf", "inv"):
                    for seed in model_seeds:
                        one(algo, "tri", nets_full, seed, "model",
                            Models(hiz=hiz, unk=unk), 5.0, sel_time)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", nargs="+", default=["main", "half", "model"],
                    choices=["main", "half", "model"])
    ap.add_argument("--circuits", nargs="+", default=list(BENCH))
    ap.add_argument("--algos", nargs="+", default=["fll", "fpll", "fpll_plus", "random"])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--model-seeds", type=int, default=3)
    ap.add_argument("--n-vec", type=int, default=1000)
    ap.add_argument("--n-keys", type=int, default=100)
    ap.add_argument("--sel-seed", type=int, default=1000)
    ap.add_argument("--out", default=os.path.join(HERE, "results"))
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--quick", action="store_true",
                    help="smoke test: 2 circuits, 1 seed, 200x20 trials")
    a = ap.parse_args()
    if a.quick:
        a.circuits, a.seeds, a.model_seeds, a.n_vec, a.n_keys = ["c432", "c1908"], 1, 1, 200, 20
    os.makedirs(a.out, exist_ok=True)
    jobs = [(c, a.algos, list(range(a.seeds)), a.n_vec, a.n_keys, a.exp,
             a.sel_seed, list(range(a.model_seeds))) for c in a.circuits]
    t0 = time.time()
    with Pool(a.procs) as p:
        res = p.map(run_circuit, jobs, chunksize=1)
    rows = [r for rr in res for r in rr]
    path = os.path.join(a.out, "raw_results.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if not r["correct_key_ok"]]
    print(f"{len(rows)} runs in {time.time() - t0:.0f}s -> {path}; "
          f"correct-key equivalence failures: {len(bad)}")


if __name__ == "__main__":
    main()
