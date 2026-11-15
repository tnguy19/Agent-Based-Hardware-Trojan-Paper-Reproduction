#!/usr/bin/env python3
"""SUPPLEMENTARY: SAT attack on XOR vs tristate locking under several attacker
knowledge models (the paper discusses this only qualitatively, Sec. IV)."""
import csv, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tristate_lock.insertion import select_fll
from tristate_lock.locking import Models, lock_netlist, simulate_locked, golden_outputs
from tristate_lock.metrics import draw_behaviours
from tristate_lock.netlist import read_netlist
from tristate_lock.sat_attack import equivalent, netlist_from_inversions, sat_attack
from tristate_lock.sim import Compiled, random_patterns

HERE = os.path.dirname(os.path.abspath(__file__))
CIRCUITS = ["c432.bench", "c880.bench", "c1908.bench"]
SCENARIOS = [("xor", "xor"), ("tri", "tri_known"), ("tri", "tri_assume1"),
             ("tri", "tri_family"), ("tri", "tri_free")]

def run(seed=0, out=os.path.join(HERE, "results", "sat_attack.csv")):
    rows = []
    for cf in CIRCUITS:
        nl = read_netlist(os.path.join(HERE, "benchmarks", cf)); co = Compiled(nl)
        K = round(0.05 * len(nl.gates))
        nets = select_fll(co, K, random.Random(1000))
        for scheme, model in SCENARIOS:
            rng = random.Random(f"sat|{cf}|{seed}")
            beh = draw_behaviours(K, rng)
            d = lock_netlist(nl, nets, scheme, beh, random.Random(f"sat|{cf}|{seed}|{scheme}"))
            cap = 40 if model == "tri_free" else 400
            res = sat_attack(d, nl, model, max_iter=cap, timeout=180)
            func_ok = key_ok = exact = None
            if res.recovered_inversions is not None:
                func_ok = equivalent(netlist_from_inversions(d, res.recovered_inversions), nl)
                cl = Compiled(d.base)
                r = random.Random(7)
                pats = random_patterns(co.n_in, 2000, r)
                gold = golden_outputs(co, pats, 2000)
                o = simulate_locked(d, cl, pats, [res.key], 2000, Models(), r)
                key_ok = (o == gold)
                exact = (res.key == d.correct_key())
            rows.append(dict(circuit=cf.split(".")[0], scheme=scheme, attacker_model=model,
                             key_gates=K, key_bits=d.n_key_bits, iterations=res.iterations,
                             seconds=round(res.seconds, 2), converged=int(res.converged),
                             function_recovered=func_ok, key_works_on_real_chip=key_ok,
                             exact_key=exact, note=res.reason))
            print(rows[-1], flush=True)
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

if __name__ == "__main__":
    run()
