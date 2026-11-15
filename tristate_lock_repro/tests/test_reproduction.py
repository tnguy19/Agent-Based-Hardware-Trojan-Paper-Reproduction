"""Unit / integration tests.  Run:  python -m unittest discover -s tests -v"""
import os, random, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from tristate_lock.insertion import ALGORITHMS
from tristate_lock.keygates import BUF, HIZ, INV, UNK, tri_correct_key, tri_mode
from tristate_lock.locking import Models, lock_netlist, simulate_locked, golden_outputs
from tristate_lock.metrics import corruption_metrics, correct_key_equivalent, draw_behaviours
from tristate_lock.netlist import Netlist, read_netlist, _blif_logical_lines
from tristate_lock.sat_attack import equivalent, netlist_from_inversions, sat_attack
from tristate_lock.sim import Compiled, random_patterns, simulate

B = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmarks")
PUBLISHED_GATES = {"c432": 160, "c1355": 546, "c1908": 880, "c3540": 1669, "c5315": 2307, "c7552": 3512}
FILES = {"c432": "c432.bench", "c1355": "c1355.bench", "c1908": "c1908.bench", "c3540": "c3540.bench",
         "c5315": "c5315.bench", "c7552": "c7552.bench", "i8": "i8.blif", "apex4": "apex4.blif"}


def tiny():
    nl = Netlist("tiny")
    for i in "ab": nl.add_input(i)
    nl.add_gate("y", "AND", ["a", "b"]); nl.add_output("y")
    return nl


class TestParsers(unittest.TestCase):
    def test_iscas_gate_counts_match_published(self):
        for n, g in PUBLISHED_GATES.items():
            self.assertEqual(len(read_netlist(f"{B}/{FILES[n]}").gates), g, n)

    def test_blif_sop_mapping_matches_direct_cover_evaluation(self):
        for name in ("i8", "apex4"):
            path = f"{B}/{FILES[name]}"
            nl = read_netlist(path); comp = Compiled(nl)
            rng = random.Random(3); nv = 64; mask = (1 << nv) - 1
            pats = random_patterns(comp.n_in, nv, rng)
            sim = simulate(comp, pats, mask)
            # independent reference: evaluate every .names cover directly
            val = {n: p for n, p in zip(nl.inputs, pats)}
            nodes, cur = [], None
            for line in _blif_logical_lines(path):
                t = line.split()
                if t[0] == ".names":
                    cur = (t[1:-1], t[-1], []); nodes.append(cur)
                elif not t[0].startswith("."):
                    cur[2].append((t[0] if len(cur[0]) else "", t[-1]))
            pending = list(nodes)
            while pending:
                rest = []
                for ins, out, cov in pending:
                    if not all(i in val for i in ins): rest.append((ins, out, cov)); continue
                    acc = 0
                    for pat, v in cov:
                        term = mask
                        for ch, i in zip(pat, ins):
                            if ch == "1": term &= val[i]
                            elif ch == "0": term &= val[i] ^ mask
                        acc |= term
                    on = (cov[0][1] == "1") if cov else True
                    val[out] = acc if on else acc ^ mask
                    if not cov: val[out] = 0
                pending = rest
            for o in nl.outputs:
                self.assertEqual(sim[comp.idx[o]], val[o], f"{name}:{o}")


class TestKeyGateModel(unittest.TestCase):
    def test_table_I_type1(self):
        self.assertEqual([tri_mode(1, k1, k0) for k1, k0 in ((0, 0), (0, 1), (1, 0), (1, 1))],
                         [HIZ, BUF, INV, UNK])

    def test_buf_combinations_per_type_match_paper_text(self):
        # Sec. III: BUF at (k1,k0) = (0,1) / (1,1) / (0,0) / (1,0) for type 1..4
        self.assertEqual([tri_correct_key(t, BUF) for t in (1, 2, 3, 4)], [(0, 1), (1, 1), (0, 0), (1, 0)])

    def test_every_type_has_exactly_one_of_each_mode(self):
        for t in (1, 2, 3, 4):
            modes = sorted(tri_mode(t, a, b) for a in (0, 1) for b in (0, 1))
            self.assertEqual(modes, sorted([BUF, INV, HIZ, UNK]))

    def test_tiny_circuit_all_four_modes(self):
        nl = tiny(); rng = random.Random(1)
        d = lock_netlist(nl, ["y"], "tri", [BUF], rng)
        d.keygates[0].tri_type = 1
        comp = Compiled(d.base)
        pats = [0b0011, 0b0101]; gold = 0b0001           # a, b over 4 vectors
        def run(key, m):
            return simulate_locked(d, comp, pats, [key], 4, m, random.Random(0))[0]
        self.assertEqual(run([0, 1], Models()), gold)                   # BUF
        self.assertEqual(run([1, 0], Models()), gold ^ 0b1111)          # INV
        self.assertEqual(run([0, 0], Models(hiz="zero")), 0)            # Hi-Z -> 0
        self.assertEqual(run([1, 1], Models(unk="buf")), gold)          # UNK, buffer wins
        self.assertEqual(run([1, 1], Models(unk="inv")), gold ^ 0b1111)  # UNK, inverter wins
        self.assertIn(run([0, 0], Models()), (0, 0b1111))               # Hi-Z const per key
        self.assertIn(run([1, 1], Models()), (0, 0b1111))               # UNK const per key


class TestLockingAndMetrics(unittest.TestCase):
    def test_correct_key_restores_function_all_circuits_schemes_algos(self):
        for name, f in FILES.items():
            nl = read_netlist(f"{B}/{f}"); co = Compiled(nl)
            K = max(2, round(0.05 * len(nl.gates)))
            for algo in ("random", "fll", "fpll", "fpll_plus"):
                nets = ALGORITHMS[algo](co, K, random.Random(1))
                self.assertEqual(len(set(nets)), len(nets))
                for scheme in ("xor", "tri"):
                    rng = random.Random(5)
                    d = lock_netlist(nl, nets, scheme, draw_behaviours(len(nets), rng), rng)
                    self.assertTrue(correct_key_equivalent(d, co, Compiled(d.base), 128, random.Random(2)),
                                    f"{name}/{algo}/{scheme}")

    def test_metrics_analytic_single_xor_on_output(self):
        nl = tiny(); co = Compiled(nl)
        for scheme in ("xor",):
            d = lock_netlist(nl, ["y"], scheme, [BUF], random.Random(0))
            m = corruption_metrics(d, co, Compiled(d.base), 256, 10, random.Random(1))
            self.assertAlmostEqual(m["output_corruptibility"], 100.0)   # the only wrong key inverts y
            self.assertAlmostEqual(m["corruption_rate"], 100.0)
            self.assertAlmostEqual(m["output_coverage"], 100.0)

    def test_deterministic(self):
        nl = read_netlist(f"{B}/c432.bench"); co = Compiled(nl)
        nets = ALGORITHMS["fll"](co, 8, random.Random(1))
        def once():
            rng = random.Random(5); d = lock_netlist(nl, nets, "tri", draw_behaviours(8, rng), rng)
            return corruption_metrics(d, co, Compiled(d.base), 200, 20, random.Random(9))
        self.assertEqual(once(), once())


class TestSat(unittest.TestCase):
    def test_equivalence_checker(self):
        a = read_netlist(f"{B}/c432.bench")
        self.assertTrue(equivalent(a, a.copy()))
        b = a.copy(); g = b.gates[b.outputs[0]]
        from tristate_lock.netlist import COMPLEMENT, Gate
        b.gates[b.outputs[0]] = Gate(COMPLEMENT[g.op], g.fanins); b._topo = None
        self.assertFalse(equivalent(a, b))

    def test_sat_attack_recovers_xor_and_known_tristate(self):
        nl = read_netlist(f"{B}/c432.bench"); co = Compiled(nl)
        nets = ALGORITHMS["fll"](co, 8, random.Random(1))
        for scheme, model in (("xor", "xor"), ("tri", "tri_known")):
            rng = random.Random(5)
            d = lock_netlist(nl, nets, scheme, draw_behaviours(8, rng), rng)
            r = sat_attack(d, nl, model, timeout=60)
            self.assertTrue(r.converged)
            self.assertTrue(equivalent(netlist_from_inversions(d, r.recovered_inversions), nl))


if __name__ == "__main__":
    unittest.main()
