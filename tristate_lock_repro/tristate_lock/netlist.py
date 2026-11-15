"""Gate-level netlist data structure + parsers for ISCAS .bench and MCNC .blif.

Only combinational circuits are supported (the paper evaluates combinational
ISCAS-85 / MCNC benchmarks).

A netlist is a DAG of gates.  Every gate drives exactly one net whose name is
the gate name.  Primary inputs are nets without a driving gate.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Tuple

MULTI_OPS = {"AND", "NAND", "OR", "NOR", "XOR", "XNOR"}
UNARY_OPS = {"NOT", "BUF"}
CONST_OPS = {"CONST0", "CONST1"}
ALL_OPS = MULTI_OPS | UNARY_OPS | CONST_OPS

# Complementing the *driver* polarity: used so that an inverting key-gate
# (correct behaviour == INV) leaves the circuit function unchanged
# (cf. Fig. 1 of the paper where NAND G4 becomes AND).
COMPLEMENT = {
    "AND": "NAND", "NAND": "AND",
    "OR": "NOR", "NOR": "OR",
    "XOR": "XNOR", "XNOR": "XOR",
    "NOT": "BUF", "BUF": "NOT",
    "CONST0": "CONST1", "CONST1": "CONST0",
}


@dataclass(frozen=True)
class Gate:
    op: str
    fanins: Tuple[str, ...]


class Netlist:
    def __init__(self, name: str = "top"):
        self.name = name
        self.inputs: List[str] = []
        self.outputs: List[str] = []
        self.gates: Dict[str, Gate] = {}
        self._topo = None

    # ------------------------------------------------------------------ build
    def add_input(self, n: str) -> None:
        self.inputs.append(n)
        self._topo = None

    def add_output(self, n: str) -> None:
        self.outputs.append(n)

    def add_gate(self, out: str, op: str, fanins) -> None:
        op = op.upper()
        if op == "BUFF":
            op = "BUF"
        if op not in ALL_OPS:
            raise ValueError(f"unsupported gate op {op!r}")
        if out in self.gates:
            raise ValueError(f"net {out!r} driven twice")
        self.gates[out] = Gate(op, tuple(fanins))
        self._topo = None

    def copy(self) -> "Netlist":
        c = Netlist(self.name)
        c.inputs = list(self.inputs)
        c.outputs = list(self.outputs)
        c.gates = dict(self.gates)  # Gate is immutable
        return c

    # --------------------------------------------------------------- analysis
    def topo_order(self) -> List[str]:
        """Gate nets in topological order (fanins before fanouts)."""
        if self._topo is not None:
            return self._topo
        indeg = {}
        fo = defaultdict(list)
        for g, gate in self.gates.items():
            d = 0
            for f in gate.fanins:
                if f in self.gates:
                    d += 1
                    fo[f].append(g)
            indeg[g] = d
        q = deque(g for g, d in indeg.items() if d == 0)
        order = []
        while q:
            g = q.popleft()
            order.append(g)
            for s in fo[g]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    q.append(s)
        if len(order) != len(self.gates):
            raise ValueError("combinational loop detected")
        self._topo = order
        return order

    def stats(self) -> Dict[str, int]:
        return {"inputs": len(self.inputs), "outputs": len(self.outputs),
                "gates": len(self.gates)}

    def validate(self) -> None:
        known = set(self.inputs) | set(self.gates)
        for g, gate in self.gates.items():
            for f in gate.fanins:
                if f not in known:
                    raise ValueError(f"gate {g}: undefined fanin {f}")
        for o in self.outputs:
            if o not in known:
                raise ValueError(f"undefined output {o}")
        self.topo_order()


# ------------------------------------------------------------------- parsers
_BENCH_ASSIGN = re.compile(r"^\s*(\S+)\s*=\s*(\w+)\s*\((.*)\)\s*$")


def read_bench(path: str) -> Netlist:
    import os
    nl = Netlist(os.path.splitext(os.path.basename(path))[0])
    with open(path) as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            up = line.upper()
            if up.startswith("INPUT"):
                nl.add_input(line[line.index("(") + 1:line.rindex(")")].strip())
            elif up.startswith("OUTPUT"):
                nl.add_output(line[line.index("(") + 1:line.rindex(")")].strip())
            else:
                m = _BENCH_ASSIGN.match(line)
                if not m:
                    raise ValueError(f"cannot parse bench line: {line!r}")
                out, op, args = m.groups()
                nl.add_gate(out, op, [a.strip() for a in args.split(",") if a.strip()])
    nl.validate()
    return nl


def _blif_logical_lines(path: str):
    buf = ""
    with open(path) as fh:
        for raw in fh:
            line = raw.split("#", 1)[0].rstrip("\n")
            if line.rstrip().endswith("\\"):
                buf += line.rstrip()[:-1] + " "
                continue
            buf += line
            if buf.strip():
                yield buf.strip()
            buf = ""
    if buf.strip():
        yield buf.strip()


def read_blif(path: str) -> Netlist:
    """Read a combinational BLIF file and map every .names SOP cover onto
    primitive AND/OR/NOT gates (one AND per cube, one OR per node, shared
    input inverters).  Output-0 covers are complemented."""
    import os
    nl = Netlist(os.path.splitext(os.path.basename(path))[0])
    nodes = []  # (inputs, output, [(pattern, val)])
    cur = None
    for line in _blif_logical_lines(path):
        tok = line.split()
        if tok[0] == ".model":
            nl.name = tok[1]
        elif tok[0] == ".inputs":
            for t in tok[1:]:
                nl.add_input(t)
        elif tok[0] == ".outputs":
            for t in tok[1:]:
                nl.add_output(t)
        elif tok[0] == ".names":
            cur = (tok[1:-1], tok[-1], [])
            nodes.append(cur)
        elif tok[0] == ".end":
            break
        elif tok[0].startswith("."):
            raise ValueError(f"unsupported BLIF construct {tok[0]} (sequential?)")
        else:  # cover line
            if cur is None:
                raise ValueError("cover line outside .names")
            if len(cur[0]) == 0:
                cur[2].append(("", tok[0]))
            else:
                cur[2].append((tok[0], tok[1]))

    inv_cache: Dict[str, str] = {}

    def inv(net: str) -> str:
        if net not in inv_cache:
            nm = f"{net}__n"
            while nm in nl.gates or nm in nl.inputs:
                nm += "_"
            nl.add_gate(nm, "NOT", [net])
            inv_cache[net] = nm
        return inv_cache[net]

    for ins, out, cover in nodes:
        if not cover:                       # empty cover -> constant 0
            nl.add_gate(out, "CONST0", [])
            continue
        vals = {v for _, v in cover}
        if len(vals) != 1:
            raise ValueError(f"mixed on/off cover in node {out}")
        onset = vals.pop() == "1"
        if not ins:                         # constant node
            nl.add_gate(out, "CONST1" if onset else "CONST0", [])
            continue
        terms: List[str] = []
        const_true = False
        for j, (pat, _) in enumerate(cover):
            lits = []
            for ch, net in zip(pat, ins):
                if ch == "1":
                    lits.append(net)
                elif ch == "0":
                    lits.append(inv(net))
            if not lits:
                const_true = True
                break
            if len(lits) == 1:
                terms.append(lits[0])
            else:
                nm = f"{out}__t{j}"
                nl.add_gate(nm, "AND", lits)
                terms.append(nm)
        if const_true:
            nl.add_gate(out, "CONST1" if onset else "CONST0", [])
            continue
        # de-duplicate while keeping order
        seen, uniq = set(), []
        for t in terms:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        terms = uniq
        if len(terms) == 1:
            nl.add_gate(out, "BUF" if onset else "NOT", [terms[0]])
        else:
            nl.add_gate(out, "OR" if onset else "NOR", terms)
    nl.validate()
    return nl


def read_netlist(path: str) -> Netlist:
    if path.endswith(".bench"):
        return read_bench(path)
    if path.endswith(".blif"):
        return read_blif(path)
    raise ValueError("unknown netlist extension: " + path)


def write_bench(nl: Netlist, path: str) -> None:
    with open(path, "w") as fh:
        for i in nl.inputs:
            fh.write(f"INPUT({i})\n")
        for o in nl.outputs:
            fh.write(f"OUTPUT({o})\n")
        for g in nl.topo_order():
            gate = nl.gates[g]
            op = "BUFF" if gate.op == "BUF" else gate.op
            fh.write(f"{g} = {op}({', '.join(gate.fanins)})\n")
