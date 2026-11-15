"""Bit-parallel logic simulation using Python arbitrary-precision integers.

Every net carries one big integer; bit ``t`` of that integer is the value of
the net in simulation *trial* ``t``.  One pass over the netlist therefore
evaluates all trials at once.  (For the paper's metric: 1000 vectors x 100
keys = 100,000 trials -> 100,000-bit integers.)
"""
from __future__ import annotations

import random
from typing import Dict, List

from .netlist import Netlist

# integer op codes (faster than string compares in the inner loop)
(OP_AND, OP_NAND, OP_OR, OP_NOR, OP_XOR, OP_XNOR, OP_NOT, OP_BUF,
 OP_C0, OP_C1) = range(10)
_OPCODE = {"AND": OP_AND, "NAND": OP_NAND, "OR": OP_OR, "NOR": OP_NOR,
           "XOR": OP_XOR, "XNOR": OP_XNOR, "NOT": OP_NOT, "BUF": OP_BUF,
           "CONST0": OP_C0, "CONST1": OP_C1}


class Compiled:
    """Index-based view of a Netlist (nets numbered: inputs first, then gates
    in topological order)."""

    def __init__(self, nl: Netlist):
        self.nl = nl
        self.names: List[str] = list(nl.inputs) + nl.topo_order()
        self.idx: Dict[str, int] = {n: i for i, n in enumerate(self.names)}
        self.n_in = len(nl.inputs)
        self.n = len(self.names)
        self.op = [None] * self.n
        self.fanin = [()] * self.n
        for i in range(self.n_in, self.n):
            g = nl.gates[self.names[i]]
            self.op[i] = _OPCODE[g.op]
            self.fanin[i] = tuple(self.idx[f] for f in g.fanins)
        self.out_idx = [self.idx[o] for o in nl.outputs]
        # fanout lists (gate sinks only) -----------------------------------
        self.fanout: List[List[int]] = [[] for _ in range(self.n)]
        for i in range(self.n_in, self.n):
            for f in set(self.fanin[i]):
                self.fanout[f].append(i)
        self._cone_cache: Dict[int, List[int]] = {}

    # structural fan-out cone (gate indices, topologically sorted, excludes
    # the net itself)
    def cone(self, i: int) -> List[int]:
        c = self._cone_cache.get(i)
        if c is None:
            seen = set()
            stack = list(self.fanout[i])
            while stack:
                g = stack.pop()
                if g in seen:
                    continue
                seen.add(g)
                stack.extend(self.fanout[g])
            c = sorted(seen)  # index order == topological order
            self._cone_cache[i] = c
        return c

    def reach_outputs(self) -> List[int]:
        """reach[i] = bitmask over primary outputs structurally reachable
        from net i (including i itself if it is an output)."""
        reach = [0] * self.n
        for k, o in enumerate(self.out_idx):
            reach[o] |= 1 << k
        for i in range(self.n - 1, -1, -1):
            r = reach[i]
            for s in self.fanout[i]:
                r |= reach[s]
            reach[i] = r
        return reach


def eval_op(op: int, args: List[int], mask: int) -> int:
    if op == OP_AND or op == OP_NAND:
        v = args[0]
        for a in args[1:]:
            v &= a
        return v ^ mask if op == OP_NAND else v
    if op == OP_OR or op == OP_NOR:
        v = args[0]
        for a in args[1:]:
            v |= a
        return v ^ mask if op == OP_NOR else v
    if op == OP_XOR or op == OP_XNOR:
        v = args[0]
        for a in args[1:]:
            v ^= a
        return v ^ mask if op == OP_XNOR else v
    if op == OP_NOT:
        return args[0] ^ mask
    if op == OP_BUF:
        return args[0]
    if op == OP_C0:
        return 0
    return mask  # OP_C1


def simulate(comp: Compiled, in_vals: List[int], mask: int) -> List[int]:
    """Plain (key-free) simulation.  Returns values of *all* nets."""
    vals = list(in_vals) + [0] * (comp.n - comp.n_in)
    op, fanin = comp.op, comp.fanin
    for i in range(comp.n_in, comp.n):
        vals[i] = eval_op(op[i], [vals[f] for f in fanin[i]], mask)
    return vals


def random_patterns(n_inputs: int, n_vec: int, rng: random.Random) -> List[int]:
    """n_inputs integers of n_vec random bits each."""
    return [rng.getrandbits(n_vec) for _ in range(n_inputs)]


def popcount(x: int) -> int:
    return x.bit_count()
