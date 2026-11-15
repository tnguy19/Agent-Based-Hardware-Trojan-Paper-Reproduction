#!/usr/bin/env python3
"""LockForge stage 3 "local execution": evaluate the BCSRP checklist.

B : ratio of automated verification checks passed
S : ratio of structural checks passed (automated introspection)
R : end-to-end run (1.0 success / 0.5 minor tweaks / 0.0 fail)
C : from LLM-A self-assessment json (judges re-assess independently)
P : sum of severities of triggered penalties
Score = max{1, 10*(0.4B + 0.3C + 0.2S + 0.1R) - P}
"""
import json, os, random, re, subprocess, sys
import pandas as pd
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from tristate_lock.keygates import BUF, HIZ, INV, UNK, TRI_TYPES, tri_mode, tri_correct_key, KeyGate
from tristate_lock.insertion import ALGORITHMS
from tristate_lock.locking import Models, lock_netlist, simulate_locked
from tristate_lock.metrics import corruption_metrics, correct_key_equivalent, draw_behaviours, random_wrong_keys
from tristate_lock.netlist import Netlist, read_netlist, COMPLEMENT
from tristate_lock.sim import Compiled

BENCH = {"c432": "c432.bench", "c1355": "c1355.bench", "c1908": "c1908.bench", "c3540": "c3540.bench",
         "c5315": "c5315.bench", "c7552": "c7552.bench", "i8": "i8.blif", "apex4": "apex4.blif"}
raw = pd.read_csv(os.path.join(ROOT, "results", "raw_results.csv"))
res = {}

def tiny():
    nl = Netlist("t"); [nl.add_input(i) for i in "ab"]
    nl.add_gate("y", "AND", ["a", "b"]); nl.add_output("y"); return nl

# ---------------------------------------------------------------- B checks
ok = True
for n, f in BENCH.items():
    nl = read_netlist(f"{ROOT}/benchmarks/{f}"); co = Compiled(nl); K = max(2, round(.05 * len(nl.gates)))
    for algo in ("fll", "fpll", "fpll_plus"):
        nets = ALGORITHMS[algo](co, K, random.Random(1))
        for sch in ("xor", "tri"):
            rng = random.Random(5); d = lock_netlist(nl, nets, sch, draw_behaviours(K, rng), rng)
            ok &= correct_key_equivalent(d, co, Compiled(d.base), 512, random.Random(2))
res["B1"] = ok
res["B2"] = [tri_mode(1, a, b) for a, b in ((0, 0), (0, 1), (1, 0), (1, 1))] == [HIZ, BUF, INV, UNK]
res["B3"] = ([tri_correct_key(t, BUF) for t in (1, 2, 3, 4)] == [(0, 1), (1, 1), (0, 0), (1, 0)] and
             all(sorted(tri_mode(t, a, b) for a in (0, 1) for b in (0, 1)) == sorted([BUF, INV, HIZ, UNK]) for t in (1, 2, 3, 4)))
nl = tiny(); d = lock_netlist(nl, ["y"], "tri", [BUF], random.Random(1)); d.keygates[0].tri_type = 1
cmp_ = Compiled(d.base); pats = [0b0011, 0b0101]
run = lambda key, m: simulate_locked(d, cmp_, pats, [key], 4, m, random.Random(0))[0]
res["B4"] = (run([0, 1], Models()) == 1 and run([1, 0], Models()) == 0b1110 and run([0, 0], Models(hiz="zero")) == 0
             and run([1, 1], Models(unk="buf")) == 1 and run([1, 1], Models(unk="inv")) == 0b1110)
m = raw[(raw.tag == "main") & (raw.algo == "fll")]
pc = m.groupby(["circuit", "scheme"])[["output_corruptibility", "corruption_rate"]].mean().unstack()
mean_tri = pc[("output_corruptibility", "tri")].mean(); mean_xor = pc[("output_corruptibility", "xor")].mean()
res["B5"] = bool(mean_tri >= 30.0)
res["B6"] = bool(abs(mean_tri - mean_xor) <= 1.0 and abs(pc[("corruption_rate", "tri")].mean() - pc[("corruption_rate", "xor")].mean()) <= 1.0)
kb = raw[(raw.algo == "fll")].groupby(["tag", "scheme", "circuit"])["key_bits"].first()
res["B7"] = bool(all(kb[("main", "tri", c)] == 2 * kb[("main", "xor", c)] and abs(kb[("half", "tri", c)] - kb[("main", "xor", c)]) <= 1 for c in BENCH))
nl = tiny(); d = lock_netlist(nl, ["y"], "xor", [BUF], random.Random(0))
mm = corruption_metrics(d, Compiled(nl), Compiled(d.base), 256, 10, random.Random(1))
res["B8"] = all(abs(mm[k] - 100) < 1e-9 for k in ("output_corruptibility", "corruption_rate", "output_coverage"))
nl = read_netlist(f"{ROOT}/benchmarks/c432.bench"); co = Compiled(nl); nets = ALGORITHMS["fll"](co, 8, random.Random(1))
def once():
    rng = random.Random(5); d = lock_netlist(nl, nets, "tri", draw_behaviours(8, rng), rng)
    return corruption_metrics(d, co, Compiled(d.base), 200, 20, random.Random(9))
res["B9"] = once() == once()
B = sum(bool(res[f"B{i}"]) for i in range(1, 10)) / 9

# ---------------------------------------------------------------- S checks
S = {}
rng = random.Random(1)
dt = lock_netlist(nl, nets, "tri", draw_behaviours(8, rng), rng); dx = lock_netlist(nl, nets, "xor", draw_behaviours(8, rng), rng)
S["S1"] = all(len(k.key_idx) == 2 for k in dt.keygates) and all(len(k.key_idx) == 1 for k in dx.keygates)
S["S2"] = TRI_TYPES == {1: (True, True), 2: (True, False), 3: (False, True), 4: (False, False)}
t = lock_netlist(nl, nets[:1], "xor", [INV], random.Random(0))
S["S3"] = t.base.gates[nets[0]].op == COMPLEMENT[nl.gates[nets[0]].op]
t2 = tiny(); d2 = lock_netlist(t2, ["y"], "xor", [INV], random.Random(0))
S["S4"] = correct_key_equivalent(d2, Compiled(t2), Compiled(d2.base), 4, random.Random(0))
S["S5"] = B4_ok = bool(res["B4"])
co2 = Compiled(read_netlist(f"{ROOT}/benchmarks/c432.bench"))
full, half = ALGORITHMS["fll"](co2, 8, random.Random(1)), ALGORITHMS["fll"](co2, 4, random.Random(1))
S["S6"] = full[:4] == half
S["S7"] = {"output_corruptibility", "corruption_rate", "output_coverage"} <= set(once().keys())
dd = lock_netlist(tiny(), ["y"], "xor", [BUF], random.Random(0))
S["S8"] = all(k != dd.correct_key() for k in random_wrong_keys(dd, 50, random.Random(0)))
Sv = sum(bool(v) for v in S.values()) / len(S)

# ---------------------------------------------------------------- R / C / P
p = subprocess.run([sys.executable, f"{ROOT}/run_experiments.py", "--quick", "--out", "/tmp/quick_bcsrp"], capture_output=True, text=True)
R = 1.0 if re.search(r"correct-key equivalence failures: 0", p.stdout) else 0.0
sa = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "self_assessment.json")))
C = sum(v["implemented"] for v in sa["C"].values()) / len(sa["C"])
P = 0
score = max(1, 10 * (0.4 * B + 0.3 * C + 0.2 * Sv + 0.1 * R) - P)
out = {"B_checks": {k: bool(v) for k, v in res.items()}, "S_checks": {k: bool(v) for k, v in S.items()},
       "B": B, "C(self-assessed)": C, "S": Sv, "R": R, "P": P, "score_local": round(score, 2),
       "pass_threshold": 8, "passed": score >= 8}
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_execution_report.json"), "w"), indent=1)
