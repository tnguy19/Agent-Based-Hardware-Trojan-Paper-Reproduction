"""Key-gate *location* selection algorithms.

The paper (Sec. V) uses two insertion algorithms, both only *cited*:

* FLL  - Fault-analysis based Logic Locking [Rajendran et al., TC 2015]
* FpLL - an *improved* version of the FpLL of SKG-Lock+ [Nguyen et al., 2022]

Neither is spelled out in the paper, so they are re-implemented here from the
public descriptions (see README, "Assumptions").  Every algorithm returns an
ordered list of net names; the first K entries are the K selected nets.  The
selection is sequential; the first K/2 entries of a K-selection are used as the
half-budget selection of the paper's Table III experiment (for FLL / FpLL this is
exactly the K/2 selection; for FpLL+ the candidate pool size depends on K, so the
prefix of the K-selection is used by definition - consistently for all circuits).
"""
from __future__ import annotations

import heapq
import random
from typing import List

from .sim import (Compiled, OP_AND, OP_BUF, OP_C0, OP_C1, OP_NAND, OP_NOR,
                  OP_NOT, OP_OR, OP_XNOR, OP_XOR, eval_op, popcount,
                  random_patterns, simulate)


def candidates(comp: Compiled) -> List[int]:
    """Nets eligible for key-gate insertion: outputs of non-constant gates."""
    return [i for i in range(comp.n_in, comp.n) if comp.op[i] not in (OP_C0, OP_C1)]


# ------------------------------------------------------------------ random
def select_random(comp: Compiled, K: int, rng: random.Random) -> List[str]:
    c = candidates(comp)
    rng.shuffle(c)
    return [comp.names[i] for i in c[:K]]


# --------------------------------------------------------------------- FLL
def _lazy_greedy(comp: Compiled, K: int, rng: random.Random, cand: List[int],
                 n_pat: int = 256) -> List[int]:
    """Masking-aware greedy selection (CELF-style lazy greedy).

    The *impact* of a net is the number of (pattern, output) pairs whose value
    flips when that net is inverted - i.e. what a wrong key bit on an
    XOR/XNOR (or a tristate INV/BUF swap) placed there does.  After every
    insertion the impact of the remaining candidates is re-evaluated *in the
    presence of the already selected (inverted) nets*, so masking between
    key-gates (e.g. two flips cancelling in an XOR tree) is taken into
    account.  NOTE: re-evaluation is lazy (CELF): a stale gain is only
    refreshed when it reaches the top of the heap, which assumes gains rarely
    grow; with masking they can, so this is an approximation of exact greedy
    (chosen for speed).  The impact measure is the inversion-flip count, not
    Rajendran's stuck-at NoP*NoO product (see README, Assumptions).
    """
    mask = (1 << n_pat) - 1
    pats = random_patterns(comp.n_in, n_pat, rng)
    V = simulate(comp, pats, mask)           # fault-free
    cur = list(V)                            # state with chosen nets inverted
    out_set = set(comp.out_idx)
    op, fanin = comp.op, comp.fanin

    def gain(i):
        tmp = {i: cur[i] ^ mask}
        for g in comp.cone(i):
            tmp[g] = eval_op(op[g], [tmp.get(f, cur[f]) for f in fanin[g]], mask)
        d = 0
        for o in out_set:
            if o in tmp:
                d += popcount(tmp[o] ^ V[o]) - popcount(cur[o] ^ V[o])
        return d, tmp

    heap = []
    for i in cand:
        g, _ = gain(i)
        heap.append((-g, i, 0))
    heapq.heapify(heap)
    chosen: List[int] = []
    rnd = 0
    while len(chosen) < K and heap:
        ng, i, ver = heapq.heappop(heap)
        if ver == rnd:
            g, tmp = gain(i)                 # commit
            cur[i] ^= mask
            for n_, v_ in tmp.items():
                cur[n_] = v_
            chosen.append(i)
            rnd += 1
        else:
            g, _ = gain(i)
            heapq.heappush(heap, (-g, i, rnd))
    return chosen


def select_fll(comp: Compiled, K: int, rng: random.Random,
               n_pat: int = 256) -> List[str]:
    """FLL [Rajendran et al.]: greedy fault-impact insertion over ALL nets,
    gains re-evaluated lazily after insertions (cost model quoted in SKG-Lock+
    for FLL: T = t_sim x N x K)."""
    return [comp.names[i] for i in _lazy_greedy(comp, K, rng, candidates(comp), n_pat)]


# -------------------------------------------------------------------- FpLL
def _prob_op(op: int, ps: List[float]) -> float:
    if op in (OP_AND, OP_NAND):
        p = 1.0
        for x in ps:
            p *= x
        return 1 - p if op == OP_NAND else p
    if op in (OP_OR, OP_NOR):
        q = 1.0
        for x in ps:
            q *= 1 - x
        return q if op == OP_NOR else 1 - q
    if op in (OP_XOR, OP_XNOR):
        p = ps[0]
        for x in ps[1:]:
            p = p * (1 - x) + x * (1 - p)
        return 1 - p if op == OP_XNOR else p
    if op == OP_NOT:
        return 1 - ps[0]
    if op == OP_BUF:
        return ps[0]
    return 0.0 if op == OP_C0 else 1.0


def output_corruption_scores(comp: Compiled) -> dict:
    """OCS(net) = dp_sa0 * n_sa0 + dp_sa1 * n_sa1   (SKG-Lock+, Eq. 6-7).

    Signal probabilities are propagated from primary inputs (p=0.5),
    reconvergence ignored.  dp_saf = sum over outputs |p_o - p_o,saf| and
    n_saf = number of outputs whose probability changes.
    """
    P = [0.5] * comp.n
    for i in range(comp.n_in, comp.n):
        P[i] = _prob_op(comp.op[i], [P[f] for f in comp.fanin[i]])
    outs = set(comp.out_idx)
    scores = {}
    for i in candidates(comp):
        total = 0.0
        for sa in (0.0, 1.0):
            tmp = {i: sa}
            for g in comp.cone(i):
                tmp[g] = _prob_op(comp.op[g], [tmp.get(f, P[f]) for f in comp.fanin[g]])
            dp, n = 0.0, 0
            for o in outs:
                if o in tmp:
                    d = abs(P[o] - tmp[o])
                    dp += d
                    if d > 1e-12:
                        n += 1
            total += dp * n
        scores[i] = total
    return scores


def select_fpll(comp: Compiled, K: int, rng: random.Random) -> List[str]:
    """FpLL as published in SKG-Lock+: rank once by OCS (descending) and walk
    down the list, skipping a net whose score equals the previously chosen
    score (structurally adjacent, e.g. separated by a buffer)."""
    sc = output_corruption_scores(comp)
    order = sorted(sc, key=lambda i: (-sc[i], i))
    chosen, last, skipped = [], None, []
    for i in order:
        if len(chosen) == K:
            break
        if last is not None and abs(sc[i] - last) < 1e-12:
            skipped.append(i)
            continue
        chosen.append(i)
        last = sc[i]
    for i in skipped:                         # budget not met -> relax the rule
        if len(chosen) == K:
            break
        chosen.append(i)
    return [comp.names[i] for i in chosen]


def observability_scores(comp: Compiled, rng: random.Random, n_pat: int = 256) -> dict:
    """Simulation-based analogue of the OCS used by FpLL+.

    For every net, invert it (what a wrong key bit does to an XOR/XNOR/tristate
    key-gate) and count, by bit-parallel fault simulation, how often each
    output flips.  score = (expected number of flipped outputs) x (number of
    outputs that can flip)  -- the same "magnitude x spread" shape as the
    probabilistic OCS of FpLL, but exact for reconvergent / XOR-dominated
    logic where probability propagation is blind (p stays 0.5).
    """
    mask = (1 << n_pat) - 1
    pats = random_patterns(comp.n_in, n_pat, rng)
    V = simulate(comp, pats, mask)
    outs = set(comp.out_idx)
    scores = {}
    for i in candidates(comp):
        tmp = {i: V[i] ^ mask}
        for g in comp.cone(i):
            tmp[g] = eval_op(comp.op[g], [tmp.get(f, V[f]) for f in comp.fanin[g]], mask)
        tot, n = 0, 0
        for o in outs:
            if o in tmp:
                c = popcount(tmp[o] ^ V[o])
                if c:
                    tot += c
                    n += 1
        scores[i] = (tot / n_pat) * n
    return scores


def select_fpll_plus(comp: Compiled, K: int, rng: random.Random,
                     pool_factor: int = 8, n_pat: int = 256) -> List[str]:
    """OUR interpretation of the paper's "improved FpLL for better output
    corruption and faster execution time" (the paper gives no details).

    Observed failure of plain FpLL here (see README / AGENT_LOG): its
    probability-based OCS is blind in XOR-dominated logic (c1355, c1908: p
    stays 0.5), and its one-shot ranking cannot see masking between chosen
    key-gates.  FpLL+ therefore

    1. ranks nets ONCE with a simulation-based flip-observability score
       (same 'magnitude x spread' shape as OCS) keeping FpLL's skip-equal-
       score rule (avoids chains of adjacent key-gates) -> candidate pool of
       size max(64, pool_factor*K);
    2. runs the masking-aware lazy-greedy selection of FLL, but only over
       that pool (a small fraction of the N nets).
    """
    sc = observability_scores(comp, rng, n_pat)
    order = sorted(sc, key=lambda i: (-sc[i], i))
    size = max(64, pool_factor * K)
    pool, last, skipped = [], None, []
    for i in order:
        if len(pool) >= size:
            break
        if last is not None and abs(sc[i] - last) < 1e-12:
            skipped.append(i)
            continue
        pool.append(i)
        last = sc[i]
    for i in skipped:                     # pool too small (many tied scores,
        if len(pool) >= size:             # e.g. apex4): relax the skip rule
            break
        pool.append(i)
    return [comp.names[i] for i in _lazy_greedy(comp, K, rng, pool, n_pat)]


ALGORITHMS = {
    "random": select_random,
    "fll": select_fll,
    "fpll": select_fpll,
    "fpll_plus": select_fpll_plus,
}
