"""Oracle-guided SAT attack [Subramanyan et al., HOST 2015] against XOR/XNOR
and tristate-locked designs, under different *attacker knowledge* models.

This is a SUPPLEMENTARY analysis: Section IV of the paper discusses SAT
resilience qualitatively and reports no SAT experiment.  Attacker models:

  xor          : XOR/XNOR design, standard attack.
  tri_known    : tristate design, attacker knows every cell's type and adds the
                 'no Hi-Z / UNK' constraint (the paper concedes this attack).
  tri_assume1  : attacker does NOT know the types and assumes type 1 for all
                 cells (forbidden combos excluded for that assumption).
  tri_family   : attacker knows the *family* of four cell types (it is public
                 in the paper) but not which cell is which; the two enable
                 polarities of every cell become 2 extra unknown bits.
  tri_free     : types known, but Hi-Z/UNK are NOT excluded and are modelled as
                 unconstrained outputs ("they prevent direct CNF modelling").
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from pysat.solvers import Glucose4

from .keygates import BUF, INV, TRI_TYPES
from .locking import LockedDesign
from .netlist import Netlist
from .sim import Compiled, simulate


class Cnf:
    def __init__(self, start: int = 0):
        self.n = start
        self.cl: List[List[int]] = []

    def new(self) -> int:
        self.n += 1
        return self.n

    def add(self, *lits):
        self.cl.append(list(lits))

    def xor2(self, a: int, b: int) -> int:
        o = self.new()
        self.add(-o, a, b); self.add(-o, -a, -b); self.add(o, -a, b); self.add(o, a, -b)
        return o

    def gate(self, op: str, ins: List[int]) -> int:
        o = self.new()
        if op in ("AND", "NAND"):
            t = self.new() if op == "NAND" else o
            for i in ins:
                self.add(-t, i)
            self.add(t, *[-i for i in ins])
            if op == "NAND":
                self.add(o, t); self.add(-o, -t)
        elif op in ("OR", "NOR"):
            t = self.new() if op == "NOR" else o
            for i in ins:
                self.add(t, -i)
            self.add(-t, *ins)
            if op == "NOR":
                self.add(o, t); self.add(-o, -t)
        elif op in ("XOR", "XNOR"):
            cur = ins[0]
            for i in ins[1:]:
                cur = self.xor2(cur, i)
            if op == "XNOR":
                self.add(o, cur); self.add(-o, -cur)
            else:
                self.add(o, -cur); self.add(-o, cur)
        elif op == "NOT":
            self.add(o, ins[0]); self.add(-o, -ins[0])
        elif op == "BUF":
            self.add(-o, ins[0]); self.add(o, -ins[0])
        elif op == "CONST0":
            self.add(-o)
        elif op == "CONST1":
            self.add(o)
        else:
            raise ValueError(op)
        return o


class KeySpace:
    """Variables + constraints describing one candidate key (K1 or K2)."""

    def __init__(self, cnf: Cnf, design: LockedDesign, model: str):
        self.model = model
        self.k = [cnf.new() for _ in range(design.n_key_bits)]
        self.inv_en: Dict[int, int] = {}      # gate idx -> var (tri models)
        self.s: Dict[int, int] = {}           # gate idx -> var 'valid' (tri_free)
        self.tbits: Dict[int, tuple] = {}     # gate idx -> (ab, ai) type bit vars
        for gi, kg in enumerate(design.keygates):
            if kg.scheme != "tri":
                continue
            k1, k0 = self.k[kg.key_idx[0]], self.k[kg.key_idx[1]]
            if model == "tri_family":
                ab, ai = cnf.new(), cnf.new()
                self.tbits[gi] = (ab, ai)
                buf_en, inv_en = cnf.xor2(k0, ab), cnf.xor2(k1, ai)
            else:
                t = kg.tri_type if model in ("tri_known", "tri_free") else 1
                buf_hi, inv_hi = TRI_TYPES[t]
                buf_en = k0 if buf_hi else -k0
                inv_en = k1 if inv_hi else -k1
            self.inv_en[gi] = inv_en
            valid = cnf.xor2(buf_en, inv_en)          # exactly one enabled
            if model == "tri_free":
                self.s[gi] = valid
            else:
                cnf.add(valid)                         # forbid Hi-Z / UNK


def encode_copy(cnf: Cnf, design: LockedDesign, comp: Compiled, ks: KeySpace,
                xvars: List[int]) -> List[int]:
    """CNF of the locked design for one input assignment (xvars) under key ks."""
    net: Dict[str, int] = dict(zip(design.base.inputs, xvars))
    kg_by_net = {kg.net: gi for gi, kg in enumerate(design.keygates)}
    for g in design.base.topo_order():
        gate = design.base.gates[g]
        r = cnf.gate(gate.op, [net[f] for f in gate.fanins])
        gi = kg_by_net.get(g)
        if gi is None:
            net[g] = r
            continue
        kg = design.keygates[gi]
        if kg.scheme == "xor":
            o = cnf.xor2(r, ks.k[kg.key_idx[0]])
            if kg.xor_kind == "XNOR":
                o = -o
            net[g] = o
        else:
            inv = ks.inv_en[gi]
            if ks.model == "tri_free":
                t = cnf.xor2(r, inv)
                o = cnf.new()
                s = ks.s[gi]
                cnf.add(-s, -t, o); cnf.add(-s, t, -o)    # free when not s
                net[g] = o
            else:
                net[g] = cnf.xor2(r, inv)
    return [net[o] for o in design.base.outputs]


@dataclass
class AttackResult:
    model: str
    converged: bool
    iterations: int
    seconds: float
    key: Optional[List[int]] = None
    tbits: Optional[Dict[int, tuple]] = None
    recovered_inversions: Optional[List[int]] = None   # per key-gate: 1 = INV
    reason: str = ""


def sat_attack(design: LockedDesign, orig: Netlist, model: str, max_iter: int = 300,
               timeout: float = 120.0) -> AttackResult:
    t0 = time.time()
    comp = Compiled(design.base)
    comp_o = Compiled(orig)
    cnf = Cnf()
    xv = [cnf.new() for _ in design.base.inputs]
    ks1, ks2 = KeySpace(cnf, design, model), KeySpace(cnf, design, model)
    o1 = encode_copy(cnf, design, comp, ks1, xv)
    o2 = encode_copy(cnf, design, comp, ks2, xv)
    diffs = [cnf.xor2(a, b) for a, b in zip(o1, o2)]
    act = cnf.new()
    cnf.add(-act, *diffs)
    miter, keysol = Glucose4(), Glucose4()
    # clauses so far: everything goes to the miter; key-space-1 part also to keysol
    for c in cnf.cl:
        miter.add_clause(c)
    # keysol only needs ks1 constraints + DIP copies on ks1; replay simply all
    # (harmless: the miter-only part is satisfiable independently)
    for c in cnf.cl:
        keysol.add_clause(c)
    flushed = len(cnf.cl)

    def flush(*solvers):
        nonlocal flushed
        for c in cnf.cl[flushed:]:
            for s in solvers:
                s.add_clause(c)
        flushed = len(cnf.cl)

    it = 0
    reason = "converged"
    while True:
        if time.time() - t0 > timeout:
            reason = "timeout"; break
        if it >= max_iter:
            reason = "iteration cap (no convergence)"; break
        if not miter.solve(assumptions=[act]):
            break
        m = set(l for l in miter.get_model() if l > 0)
        x = [1 if v in m else 0 for v in xv]
        vals = simulate(comp_o, x, 1)
        y = [vals[i] & 1 for i in comp_o.out_idx]
        for ks in (ks1, ks2):
            xs = [cnf.new() for _ in xv]
            for v, b in zip(xs, x):
                cnf.add(v if b else -v)
            outs = encode_copy(cnf, design, comp, ks, xs)
            for v, b in zip(outs, y):
                cnf.add(v if b else -v)
        flush(miter, keysol)
        it += 1
    key = tb = inv = None
    if reason == "converged" or reason.startswith("iteration"):
        if keysol.solve():
            m = set(l for l in keysol.get_model() if l > 0)
            key = [1 if v in m else 0 for v in ks1.k]
            tb = {gi: tuple(1 if v in m else 0 for v in vs) for gi, vs in ks1.tbits.items()}
            inv = []
            for gi, kg in enumerate(design.keygates):
                if kg.scheme == "xor":
                    bit = key[kg.key_idx[0]]
                    inv.append(bit if kg.xor_kind == "XOR" else 1 - bit)
                else:
                    iv = ks1.inv_en[gi]
                    inv.append(1 if (iv in m if iv > 0 else -iv not in m) else 0)
        else:
            reason += " / key solver UNSAT (model cannot explain the oracle)"
    miter.delete(); keysol.delete()
    return AttackResult(model, reason == "converged", it, time.time() - t0, key, tb, inv, reason)


# ------------------------------------------------------------ evaluation
def netlist_from_inversions(design: LockedDesign, inv: List[int]) -> Netlist:
    """Attacker's reconstructed design: every key-gate replaced by BUF/INV."""
    nl = design.base.copy()
    # rename driver nets: net g (post key-gate) = BUF/NOT(g__pre)
    for gi, kg in enumerate(design.keygates):
        g = nl.gates[kg.net]
        pre = kg.net + "__pre"
        nl.gates[pre] = g
        nl.gates[kg.net] = type(g)("NOT" if inv[gi] else "BUF", (pre,))
    nl._topo = None
    nl.validate()
    return nl


def equivalent(a: Netlist, b: Netlist) -> bool:
    """Exact combinational equivalence by SAT miter."""
    assert a.inputs == b.inputs and a.outputs == b.outputs
    cnf = Cnf()
    xv = [cnf.new() for _ in a.inputs]

    def enc(nl):
        net = dict(zip(nl.inputs, xv))
        for g in nl.topo_order():
            gate = nl.gates[g]
            net[g] = cnf.gate(gate.op, [net[f] for f in gate.fanins])
        return [net[o] for o in nl.outputs]

    oa, ob = enc(a), enc(b)
    cnf.add(*[cnf.xor2(p, q) for p, q in zip(oa, ob)])
    s = Glucose4()
    for c in cnf.cl:
        s.add_clause(c)
    r = s.solve()
    s.delete()
    return not r
