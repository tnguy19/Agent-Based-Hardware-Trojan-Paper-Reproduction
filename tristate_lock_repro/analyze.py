#!/usr/bin/env python3
"""Aggregate results/raw_results.csv into the paper's Table II / Table III /
Fig. 5 analogues and a claim-by-claim comparison (results/report_tables.md)."""
import json, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")
d = pd.read_csv(os.path.join(R, "raw_results.csv"))
ref = pd.read_csv(os.path.join(HERE, "reference", "paper_fig5_digitised.csv"), comment="#")
paper = json.load(open(os.path.join(HERE, "reference", "paper_tables.json")))
M = ["output_corruptibility", "corruption_rate", "output_coverage",
     "output_coverage_per_key", "output_coverage_maxhd"]
CIRC = ["c432", "c1355", "c1908", "c3540", "c5315", "c7552", "i8", "apex4"]
LARGEST4 = ["c7552", "c5315", "i8", "apex4"]
ALGO_NAME = {"fll": "FLL", "fpll": "FpLL (as published)", "fpll_plus": "FpLL+ (our 'improved')",
             "random": "random (baseline)"}
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e"

def circuit_mean(df, circuits=CIRC):
    """mean over seeds per circuit, then over circuits (paper: mean over 8 circuits).
    Also returns the std over seeds of the circuit-mean."""
    df = df[df.circuit.isin(circuits)]
    per_seed = df.groupby(["seed"])[M].mean()
    return df.groupby("circuit")[M].mean()[M].mean(), per_seed.std(ddof=1)

md = []
def sec(t): md.append(f"\n### {t}\n")
def table(df, floatfmt="{:.1f}"):
    md.append(df.to_markdown(floatfmt=".1f") + "\n")

main = d[d.tag == "main"]
half = d[d.tag == "half"]

# ------------------------------------------------------------- Table II
sec("Table II analogue - mean over the 8 circuits (5 % key-gates; mean over 5 seeds, ± = std over seeds)")
rows = []
for algo in ["fll", "fpll", "fpll_plus", "random"]:
    for m in M:
        r = {"algorithm": ALGO_NAME[algo], "metric": m}
        for scheme, nm in (("xor", "XOR/XNOR"), ("tri", "tristate")):
            mean, sd = circuit_mean(main[(main.algo == algo) & (main.scheme == scheme)])
            r[nm] = f"{mean[m]:.1f} ± {sd[m]:.1f}"
            r[nm + "_v"] = mean[m]
        r["tri - xor"] = r["tristate_v"] - r["XOR/XNOR_v"]
        pk = paper["table_II"].get(algo if algo in ("fll", "fpll") else "", {}).get(m)
        r["paper XOR | tri"] = f"{pk[0]} | {pk[1]}" if pk else "-"
        rows.append(r)
t2 = pd.DataFrame(rows).drop(columns=["tristate_v", "XOR/XNOR_v"])
t2.to_csv(os.path.join(R, "table_II_reproduced.csv"), index=False)
md.append(t2.to_markdown(index=False, floatfmt=".2f") + "\n")

# ------------------------------------------------------------- Fig. 5 data
sec("Fig. 5 analogue - per circuit, FLL, 5 % key-gates (ours vs paper's digitised bars)")
f = main[main.algo == "fll"].groupby(["circuit", "scheme"])[M].mean().unstack("scheme").reindex(CIRC)
tab = pd.DataFrame(index=CIRC)
for m, pk in (("output_corruptibility", "corruptibility"), ("corruption_rate", "corruption_rate"),
              ("output_coverage", "coverage")):
    tab[f"{m} XOR"] = f[(m, "xor")]; tab[f"{m} tri"] = f[(m, "tri")]
    tab[f"paper {pk} XOR"] = ref.set_index("circuit")[f"xor_{pk}"]
    tab[f"paper {pk} tri"] = ref.set_index("circuit")[f"tri_{pk}"]
tab["coverage_per_key XOR"] = f[("output_coverage_per_key", "xor")]
tab["coverage_per_key tri"] = f[("output_coverage_per_key", "tri")]
tab.round(1).to_csv(os.path.join(R, "fig5_reproduced.csv"))
md.append(tab.round(1).T.to_markdown(floatfmt=".1f") + "\n")

# agreement with the paper (per circuit, FLL)
sec("Agreement with the paper's Fig. 5 (FLL)")
ag = []
for m, pk in (("output_corruptibility", "corruptibility"), ("corruption_rate", "corruption_rate"),
              ("output_coverage", "coverage"), ("output_coverage_per_key", "coverage")):
    for sch in ("xor", "tri"):
        a = f[(m, sch)].values; b = ref.set_index("circuit").loc[CIRC, f"{sch}_{pk}"].values
        ag.append({"metric": m, "scheme": sch, "mean abs. error (pts)": np.abs(a - b).mean(),
                   "Pearson r (8 circuits)": np.corrcoef(a, b)[0, 1] if a.std() > 1e-9 and b.std() > 1e-9 else np.nan})
ag = pd.DataFrame(ag)
md.append(ag.to_markdown(index=False, floatfmt=".2f") + "\n")
ag.to_csv(os.path.join(R, "agreement_with_paper.csv"), index=False)

# ------------------------------------------------------------- Table III
sec("Table III analogue - tristate with half the key-gates (2.5 %) vs XOR/XNOR (5 %)")
rows = []
for algo in ["fll", "fpll", "fpll_plus"]:
    for m in M[:3] + M[3:4]:
        x, _ = circuit_mean(main[(main.algo == algo) & (main.scheme == "xor")])
        h8, _ = circuit_mean(half[(half.algo == algo)])
        h4, _ = circuit_mean(half[(half.algo == algo)], LARGEST4)
        x4, _ = circuit_mean(main[(main.algo == algo) & (main.scheme == "xor")], LARGEST4)
        pk = paper["table_III"].get(algo, {}).get(m)
        rows.append({"algorithm": ALGO_NAME[algo], "metric": m, "XOR 5% (ours)": x[m], "XOR 5% 4 largest (ours)": x4[m],
                     "tri 2.5% 8 circ (ours)": h8[m], "tri 2.5% 4 largest (ours)": h4[m],
                     "paper (XOR | 8 | 4 largest)": " | ".join(map(str, pk)) if pk else "-"})
t3 = pd.DataFrame(rows)
t3.to_csv(os.path.join(R, "table_III_reproduced.csv"), index=False)
md.append(t3.to_markdown(index=False, floatfmt=".1f") + "\n")

# ------------------------------------------------------- model sensitivity
sec("Sensitivity to how Hi-Z / UNK are simulated (FLL, tristate 5 %, mean of 8 circuits)")
mod = d[(d.tag == "model")].groupby(["hiz", "unk"])[M[:3] + ["output_coverage_per_key"]].mean().round(1)
xor_ref, _ = circuit_mean(main[(main.algo == "fll") & (main.scheme == "xor")])
md.append(mod.to_markdown(floatfmt=".1f") + "\n")
md.append(f"\nFor reference, XOR/XNOR with the same locations: corruptibility {xor_ref['output_corruptibility']:.1f}, "
          f"rate {xor_ref['corruption_rate']:.1f}, coverage {xor_ref['output_coverage']:.1f}, "
          f"coverage per key {xor_ref['output_coverage_per_key']:.1f}.\n")
mod.to_csv(os.path.join(R, "model_sensitivity.csv"))

# ------------------------------------------------------------ claim checks
sec("Claim-by-claim check")
cl = []
for algo in ("fll", "fpll", "fpll_plus"):
    x, _ = circuit_mean(main[(main.algo == algo) & (main.scheme == "xor")])
    t, _ = circuit_mean(main[(main.algo == algo) & (main.scheme == "tri")])
    cl.append({"algorithm": ALGO_NAME[algo],
               "|Δ corruptibility| (paper <0.3)": abs(t["output_corruptibility"] - x["output_corruptibility"]),
               "|Δ corruption rate| (paper <0.3)": abs(t["corruption_rate"] - x["corruption_rate"]),
               "Δ coverage D1 (paper +2.5..3.5)": t["output_coverage"] - x["output_coverage"],
               "Δ coverage D2 per-key": t["output_coverage_per_key"] - x["output_coverage_per_key"],
               "Δ coverage D3 max-HD": t["output_coverage_maxhd"] - x["output_coverage_maxhd"]})
cl = pd.DataFrame(cl)
md.append(cl.to_markdown(index=False, floatfmt=".2f") + "\n")
cl.to_csv(os.path.join(R, "claim_check.csv"), index=False)

sec("Selection time (s, mean over circuits) - paper claims improved FpLL is faster")
st = d[d.tag == "main"].drop_duplicates(["circuit", "algo"]).groupby("algo")["sel_time_s"].mean().round(2)
md.append(st.to_frame().to_markdown() + "\n")

open(os.path.join(R, "report_tables.md"), "w").write("\n".join(md))

# ------------------------------------------------------------------ figures
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c8c7c2", "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK})
def fig5(algo, fname, title):
    sub = main[main.algo == algo].groupby(["circuit", "scheme"])[M].mean().unstack("scheme").reindex(CIRC)
    panels = [("output_corruptibility", "Output corruptibility (%)", "corruptibility", 50),
              ("corruption_rate", "Corruption rate (%)", "corruption_rate", 100),
              ("output_coverage", "Output coverage (%) - D1: corrupted at least once", "coverage", 100),
              ("output_coverage_per_key", "Output coverage (%) - D2: per-key average", "coverage", 100)]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7), dpi=150)
    x = np.arange(len(CIRC)); w = 0.36
    for ax, (m, lab, pk, ymax) in zip(axs.ravel(), panels):
        ax.bar(x - w / 2 - 0.01, sub[(m, "xor")], w, color=BLUE, label="XOR/XNOR (ours)", zorder=3)
        ax.bar(x + w / 2 + 0.01, sub[(m, "tri")], w, color=ORANGE, label="Tristate (ours)", zorder=3)
        if algo == "fll":
            pr = ref.set_index("circuit").loc[CIRC]
            ax.scatter(x - w / 2 - 0.01, pr[f"xor_{pk}"], marker="D", s=22, color=INK, zorder=5, label="Paper, digitised (Fig. 5)")
            ax.scatter(x + w / 2 + 0.01, pr[f"tri_{pk}"], marker="D", s=22, color=INK, zorder=5)
        ax.set_xticks(x); ax.set_xticklabels(CIRC); ax.set_ylim(0, ymax * 1.08)
        ax.set_ylabel(lab, fontsize=8); ax.grid(axis="y", color="#e6e5e1", zorder=0)
        for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
        ax.tick_params(length=0)
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper left", ncol=3, fontsize=8, frameon=False, bbox_to_anchor=(0.005, 0.955))
    fig.suptitle(title, fontsize=11, x=0.01, y=0.995, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(os.path.join(R, fname)); plt.close(fig)

fig5("fll", "fig5_fll_reproduced.png", "Fig. 5 reproduction - FLL insertion, 5 % key-gates, 1000 vectors x 100 wrong keys, mean of 5 seeds")
fig5("fpll_plus", "fig5_fpllplus.png", "Same experiment with the FpLL+ insertion (our interpretation of the paper's 'improved FpLL')")

# Table III bar chart
fig, ax = plt.subplots(figsize=(7, 3.6), dpi=150)
lab = ["XOR/XNOR 5%", "tristate 5%", "tristate 2.5%\n(8 circuits)", "tristate 2.5%\n(4 largest)"]
vals = []
x_, _ = circuit_mean(main[(main.algo == "fll") & (main.scheme == "xor")])
t_, _ = circuit_mean(main[(main.algo == "fll") & (main.scheme == "tri")])
h8, _ = circuit_mean(half[half.algo == "fll"]); h4, _ = circuit_mean(half[half.algo == "fll"], LARGEST4)
vals = [x_["output_corruptibility"], t_["output_corruptibility"], h8["output_corruptibility"], h4["output_corruptibility"]]
cols = [BLUE, ORANGE, ORANGE, ORANGE]
b = ax.bar(range(4), vals, 0.55, color=cols, zorder=3)
for i, v in enumerate(vals): ax.text(i, v + 2.2, f"{v:.1f}", ha="center", fontsize=8, color=INK)
ax.scatter([0, 2, 3], paper["table_III"]["fll"]["output_corruptibility"], marker="D", s=26, color=INK, zorder=5, label="Paper, Table III")
ax.set_xticks(range(4)); ax.set_xticklabels(lab, fontsize=8); ax.set_ylim(0, 55)
ax.set_ylabel("Output corruptibility (%)"); ax.grid(axis="y", color="#e6e5e1", zorder=0)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
ax.tick_params(length=0); ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.set_title("Halving the number of tristate key-gates (FLL): same key size as XOR/XNOR", fontsize=9, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(R, "table3_halved_keygates.png")); plt.close(fig)
print("wrote tables and figures to", R)
