"""Key-gate models: conventional XOR/XNOR and the paper's tristate key-gate.

Tristate key-gate (paper Sec. III, Fig. 3 / Table I)
----------------------------------------------------
A tristate *inverter* (enable driven by key-bit k1) and a tristate *buffer*
(enable driven by k0) are wired in parallel to the same output ``o``.

    buffer enabled  & inverter disabled -> o = i          (BUF)
    inverter enabled & buffer disabled  -> o = not i      (INV)
    both disabled                       -> o = Hi-Z       (floating, retains
                                                           its previous value)
    both enabled                        -> o = UNK        (contention, an
                                                           intermediate voltage)

Types 1..4 differ by whether each enable is active-high or active-low
(read off Fig. 3; verified against the type-1 truth table of Table I and the
BUF key combinations listed in Sec. III: type1=(0,1), type2=(1,1),
type3=(0,0), type4=(1,0) as (k1,k0)):

    type  buffer enable (k0)   inverter enable (k1)
      1       active high          active high
      2       active high          active low
      3       active low           active high
      4       active low           active low
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

BUF, INV, HIZ, UNK = "BUF", "INV", "HIZ", "UNK"

# type -> (buffer_enable_active_high, inverter_enable_active_high)
TRI_TYPES = {1: (True, True), 2: (True, False), 3: (False, True), 4: (False, False)}


def tri_mode(tri_type: int, k1: int, k0: int) -> str:
    """Operating mode of a tristate key-gate for the 2-bit key (k1,k0)."""
    buf_hi, inv_hi = TRI_TYPES[tri_type]
    buf_en = bool(k0) if buf_hi else not k0
    inv_en = bool(k1) if inv_hi else not k1
    if buf_en and not inv_en:
        return BUF
    if inv_en and not buf_en:
        return INV
    if not buf_en and not inv_en:
        return HIZ
    return UNK


def tri_correct_key(tri_type: int, behaviour: str) -> Tuple[int, int]:
    """(k1,k0) that makes a type-`tri_type` gate behave as BUF or INV."""
    for k1 in (0, 1):
        for k0 in (0, 1):
            if tri_mode(tri_type, k1, k0) == behaviour:
                return k1, k0
    raise AssertionError


def xor_behaviour(xor_kind: str, key_bit: int) -> str:
    """XOR: key 0 -> BUF, 1 -> INV.  XNOR: key 1 -> BUF, 0 -> INV."""
    inverted = bool(key_bit) if xor_kind == "XOR" else not key_bit
    return INV if inverted else BUF


@dataclass
class KeyGate:
    net: str                       # net on which the key-gate sits (after its driver)
    scheme: str                    # "xor" | "tri"
    behaviour: str                 # *correct* behaviour: BUF or INV
    key_idx: Tuple[int, ...]       # positions in the key vector: (k,) or (k1,k0)
    xor_kind: Optional[str] = None  # "XOR"/"XNOR" for scheme == "xor"
    tri_type: Optional[int] = None  # 1..4 for scheme == "tri"

    def correct_bits(self) -> Tuple[int, ...]:
        if self.scheme == "xor":
            want_inv = self.behaviour == INV
            if self.xor_kind == "XOR":
                return (1 if want_inv else 0,)
            return (0 if want_inv else 1,)
        return tri_correct_key(self.tri_type, self.behaviour)
