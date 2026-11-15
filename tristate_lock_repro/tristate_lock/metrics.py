"""Output-corruption metrics exactly as defined in the paper (Sec. II/V).

* output corruptibility : mean percentage Hamming distance between correct
                          and erroneous outputs (ideal 50 %)
* corruption rate       : percentage of (key, input-vector) pairs whose
                          outputs differ from the correct ones (ideal 100 %)
* output coverage       : percentage of outputs corrupted at least once
                          (ideal 100 %)

Computed by simulation: ``n_vec`` random input vectors, each applied for
``n_keys`` random *incorrect* keys (paper: 1000 x 100 = 100,000 test vectors).
"""
from __future__ import annotations

import random

import numpy as np
from typing import Dict, List, Optional

from .keygates import BUF, INV
from .locking import (LockedDesign, Models, golden_outputs, lock_netlist,
                      simulate_locked)
from .netlist import Netlist
from .sim import Compiled, popcount, random_patterns


def random_wrong_keys(design: LockedDesign, n: int, rng: random.Random) -> List[List[int]]:
    ck = design.correct_key()
    nk = len(ck)
    keys = []
    while len(keys) < n:
        k = [rng.getrandbits(1) for _ in range(nk)]
        if k != ck:
            keys.append(k)
    return keys


def corruption_metrics(design: LockedDesign, comp_orig: Compiled,
                       comp_locked: Compiled, n_vec: int, n_keys: int,
                       rng: random.Random, models: Optional[Models] = None
                       ) -> Dict[str, float]:
    models = models or Models()
    pats = random_patterns(comp_orig.n_in, n_vec, rng)
    gold = golden_outputs(comp_orig, pats, n_vec)
    keys = random_wrong_keys(design, n_keys, rng)
    outs = simulate_locked(design, comp_locked, pats, keys, n_vec, models, rng)
    T = n_vec * n_keys
    R = 0
    for j in range(n_keys):
        R |= 1 << (j * n_vec)
    m = len(outs)
    nbytes = (T + 7) // 8
    # bit-matrix of corruption events: row = output, column = (key, vector)
    rows = []
    for o, g in zip(outs, gold):
        d = o ^ (g * R)
        rows.append(np.unpackbits(np.frombuffer(d.to_bytes(nbytes, "little"), dtype=np.uint8),
                                  bitorder="little")[:T])
    arr = np.stack(rows)                                  # (m, T) uint8
    hd = arr.sum(axis=0, dtype=np.int32)                  # Hamming distance per trial
    per_key_cov = arr.reshape(m, n_keys, n_vec).any(axis=2)  # (m, n_keys)
    return {
        # --- the three metrics of the paper -----------------------------
        "output_corruptibility": 100.0 * float(hd.sum()) / (T * m),
        "corruption_rate": 100.0 * float((hd > 0).mean()),
        # D1 (primary, literal wording of the paper): outputs corrupted at
        #    least once over ALL (key, vector) trials
        "output_coverage": 100.0 * float(arr.any(axis=1).mean()),
        # --- alternative readings of "output coverage" (reported for
        #     transparency, see README "Ambiguities") ---------------------
        # D2: per wrong key, fraction of outputs corrupted at least once over
        #     the vectors, averaged over keys
        "output_coverage_per_key": 100.0 * float(per_key_cov.mean()),
        # D3: SKG-Lock+ definition: max Hamming distance / m
        "output_coverage_maxhd": 100.0 * float(hd.max()) / m,
    }


def correct_key_equivalent(design: LockedDesign, comp_orig: Compiled,
                           comp_locked: Compiled, n_vec: int,
                           rng: random.Random, models: Optional[Models] = None) -> bool:
    """B1: with the correct key the locked design equals the original."""
    models = models or Models()
    pats = random_patterns(comp_orig.n_in, n_vec, rng)
    gold = golden_outputs(comp_orig, pats, n_vec)
    outs = simulate_locked(design, comp_locked, pats, [design.correct_key()],
                           n_vec, models, rng)
    return outs == gold


def draw_behaviours(K: int, rng: random.Random) -> List[str]:
    """Correct behaviour (BUF/INV) of every key-gate, 50/50."""
    return [rng.choice((BUF, INV)) for _ in range(K)]
