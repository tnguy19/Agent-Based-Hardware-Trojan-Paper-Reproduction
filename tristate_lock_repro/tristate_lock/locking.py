"""Locked design = original netlist (+ driver-polarity fixes) + key-gates, and
a bit-parallel simulator that evaluates it under many (key, vector) trials.

Key-gate placement: a key-gate is put on the *output net* of an existing gate
``g`` (never on primary-input nets, which have no driver to absorb an
inversion).  All sinks of ``g`` (gates and primary outputs) read the key-gate
output.  If the key-gate has to act as an inverter under the correct key, the
driver gate is replaced by its complement (NAND->AND, ...), exactly as in the
paper's Fig. 1 example, so the correct key restores the original function.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .keygates import (BUF, INV, KeyGate, TRI_TYPES, tri_correct_key)
from .netlist import COMPLEMENT, Gate, Netlist
from .sim import Compiled, eval_op, simulate


@dataclass
class LockedDesign:
    original: Netlist
    base: Netlist                 # original with polarity-compensated drivers
    keygates: List[KeyGate]
    scheme: str                   # "xor" | "tri"

    @property
    def n_key_bits(self) -> int:
        return sum(len(k.key_idx) for k in self.keygates)

    def correct_key(self) -> List[int]:
        key = [0] * self.n_key_bits
        for kg in self.keygates:
            for pos, b in zip(kg.key_idx, kg.correct_bits()):
                key[pos] = b
        return key


def lock_netlist(nl: Netlist, nets: Sequence[str], scheme: str,
                 behaviours: Sequence[str], rng: random.Random) -> LockedDesign:
    """Insert one key-gate per net in ``nets``.

    ``behaviours[i]`` (BUF/INV) is the *correct* behaviour of key-gate i; it is
    drawn by the caller so that XOR and tristate locking can share it.
    ``rng`` draws XOR/XNOR kinds or tristate types.
    """
    assert scheme in ("xor", "tri")
    assert len(nets) == len(behaviours)
    assert len(set(nets)) == len(nets), "duplicate key-gate locations"
    base = nl.copy()
    kgs: List[KeyGate] = []
    nxt = 0
    for net, beh in zip(nets, behaviours):
        if net not in base.gates:
            raise ValueError(f"cannot lock primary input / unknown net {net}")
        if beh == INV:  # driver absorbs the inversion
            g = base.gates[net]
            base.gates[net] = Gate(COMPLEMENT[g.op], g.fanins)
        if scheme == "xor":
            kgs.append(KeyGate(net, "xor", beh, (nxt,),
                               xor_kind=rng.choice(("XOR", "XNOR"))))
            nxt += 1
        else:
            kgs.append(KeyGate(net, "tri", beh, (nxt, nxt + 1),  # (k1, k0)
                               tri_type=rng.choice((1, 2, 3, 4))))
            nxt += 2
    base._topo = None
    return LockedDesign(nl, base, kgs, scheme)


# --------------------------------------------------------------- simulation
@dataclass
class Models:
    """How non-Boolean tristate states are interpreted in simulation.

    hiz: output retains its previous (pre-test) charge.  The gate stays in
         Hi-Z for the whole test (the key is fixed), so the node never gets
         re-driven: 'const' = a random constant per (key, gate)  [default]
                    'zero'  = constant 0
                    'vec'   = re-randomised for every vector (noisy float)
    unk: contention -> intermediate voltage read by downstream gates:
         'const' = one random logic value per (key, gate)  [default]
         'pin'   = each sink pin reads its own random constant (different
                   thresholds, as noted in the paper)
         'vec'   = random per vector (worst case)
         'buf'   = buffer wins (o = i),  'inv' = inverter wins (o = not i)
    """
    hiz: str = "const"
    unk: str = "const"


class _Trial:
    """Packing helpers: trial t = key_index * n_vec + vec_index."""

    def __init__(self, n_keys: int, n_vec: int):
        self.n_keys, self.n_vec = n_keys, n_vec
        self.T = n_keys * n_vec
        self.mask = (1 << self.T) - 1
        self.block = (1 << n_vec) - 1
        self.R = 0
        for j in range(n_keys):
            self.R |= 1 << (j * n_vec)

    def replicate(self, pattern: int) -> int:
        """pattern (n_vec bits) -> same pattern in every key block."""
        return pattern * self.R

    def per_key_mask(self, bits: Sequence[int]) -> int:
        """bit j (one per key trial) -> whole block j set/clear."""
        sel = 0
        for j, b in enumerate(bits):
            if b:
                sel |= 1 << (j * self.n_vec)
        return sel * self.block

    def random_per_key(self, rng: random.Random) -> int:
        return self.per_key_mask([rng.getrandbits(1) for _ in range(self.n_keys)])


def simulate_locked(design: LockedDesign, comp: Compiled, pi_pats: List[int],
                    keys: Sequence[Sequence[int]], n_vec: int,
                    models: Models, rng: random.Random) -> List[int]:
    """Simulate ``design`` for every (key, vector) pair.

    ``pi_pats``: n_vec-bit pattern per primary input (shared by all keys).
    ``keys``:    list of key vectors.  Returns one T-bit integer per primary
                 output; bit (j*n_vec + v) = output under keys[j], vector v.
    """
    tr = _Trial(len(keys), n_vec)
    mask = tr.mask
    nk = design.n_key_bits
    kmask = [tr.per_key_mask([keys[j][p] for j in range(tr.n_keys)])
             for p in range(nk)]

    kg_at: Dict[int, KeyGate] = {comp.idx[kg.net]: kg for kg in design.keygates}
    vals = [tr.replicate(p) for p in pi_pats] + [0] * (comp.n - comp.n_in)
    op, fanin = comp.op, comp.fanin
    pin_over: Dict[tuple, int] = {}
    slow_gates = set()
    out_pos: Dict[int, List[int]] = {}
    for k, o in enumerate(comp.out_idx):
        out_pos.setdefault(o, []).append(k)
    out_over: Dict[int, int] = {}
    if design.scheme == "tri" and models.unk == "pin":
        for i in kg_at:
            for s in comp.fanout[i]:
                slow_gates.add(s)

    for i in range(comp.n_in, comp.n):
        if i in slow_gates:
            args = [pin_over.get((i, pos), vals[f]) for pos, f in enumerate(fanin[i])]
        else:
            args = [vals[f] for f in fanin[i]]
        v = eval_op(op[i], args, mask)
        kg = kg_at.get(i)
        if kg is not None:
            if kg.scheme == "xor":
                v ^= kmask[kg.key_idx[0]]
                if kg.xor_kind == "XNOR":
                    v ^= mask
            else:
                v = _apply_tri(kg, v, kmask, mask, tr, models, rng, comp, i,
                               pin_over, out_over, out_pos)
        vals[i] = v
    return [out_over.get(k, vals[o]) for k, o in enumerate(comp.out_idx)]


def _apply_tri(kg: KeyGate, v: int, kmask, mask: int, tr: _Trial, m: Models,
               rng: random.Random, comp: Compiled, i: int,
               pin_over, out_over, out_pos) -> int:
    k1m, k0m = kmask[kg.key_idx[0]], kmask[kg.key_idx[1]]
    buf_hi, inv_hi = TRI_TYPES[kg.tri_type]
    buf_en = k0m if buf_hi else k0m ^ mask
    inv_en = k1m if inv_hi else k1m ^ mask
    buf_only = buf_en & (inv_en ^ mask)
    inv_only = inv_en & (buf_en ^ mask)
    hiz = (buf_en | inv_en) ^ mask
    unk = buf_en & inv_en

    if m.hiz == "const":
        h = tr.random_per_key(rng)
    elif m.hiz == "zero":
        h = 0
    elif m.hiz == "vec":
        h = rng.getrandbits(tr.T)
    else:
        raise ValueError(m.hiz)

    if m.unk == "const":
        u = tr.random_per_key(rng)
    elif m.unk == "vec":
        u = rng.getrandbits(tr.T)
    elif m.unk == "buf":
        u = v
    elif m.unk == "inv":
        u = v ^ mask
    elif m.unk == "pin":
        u = tr.random_per_key(rng)  # default for non-overridden readers
    else:
        raise ValueError(m.unk)

    out = (buf_only & v) | (inv_only & (v ^ mask)) | (hiz & h) | (unk & u)

    if m.unk == "pin":
        keep = out & (unk ^ mask)
        for s in comp.fanout[i]:
            for pos, f in enumerate(comp.fanin[s]):
                if f == i:
                    pin_over[(s, pos)] = keep | (unk & tr.random_per_key(rng))
        for k in comp_out_positions(out_pos, i):
            out_over[k] = keep | (unk & tr.random_per_key(rng))
    return out


def comp_out_positions(out_pos, i):
    return out_pos.get(i, [])


def golden_outputs(comp_orig: Compiled, pi_pats: List[int], n_vec: int) -> List[int]:
    mask = (1 << n_vec) - 1
    vals = simulate(comp_orig, pi_pats, mask)
    return [vals[o] for o in comp_orig.out_idx]
