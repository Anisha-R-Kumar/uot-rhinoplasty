import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
R = json.load(open("results.json"))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
PL = ["Conservative", "Moderate", "Aggressive"]
COL = ["#9DB4C0", "#3E7CB1", "#0B3C5D"]

# ---------------- Figure 1: reg_m sensitivity on the actual scenarios ----------------
S = R["regm_sensitivity"]; x = [s["reg_m"] for s in S]
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=False)
for k, (key, title) in enumerate([("S1", "Scenario 1: primary"), ("S2", "Scenario 2: revision")]):
    for p in range(3):
        ax[k].plot(x, [s[key][p] for s in S], marker="o", ms=3.5, lw=1.6, color=COL[p], label=PL[p])
    ax[k].axvline(1.0, ls="--", lw=0.8, color="0.4")
    ax[k].set_xscale("log"); ax[k].set_title(title, fontsize=9.5, loc="left")
    ax[k].set_xlabel("Mass penalty, reg$_m$ (log scale)")
    ax[k].grid(axis="y", lw=0.4, color="0.88")
ax[0].set_ylabel("Transport cost ⟨C, π⟩")
ax[0].legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig("Figure1_regm_sensitivity.png", dpi=300); plt.close(fig)

# ---------------- Figure 2: transport plans drawn from pi ----------------
LAB = ["Septum", "Upper lateral", "Lower lateral", "Ear", "Rib"]
def flow_panel(ax, rec, title):
    pi = np.array(rec["pi"]); P = np.array(rec["P"]); Q = np.array(rec["Q"]); cols = np.array(rec["col_sums"])
    ys = np.arange(5)[::-1] * 1.0; xl, xr, w = 0.0, 3.0, 0.9
    scale = 1.6
    for i in range(5):
        # source bar (P) left
        ax.add_patch(FancyBboxPatch((xl - P[i] * scale, ys[i] - .16), max(P[i] * scale, 1e-4), .32, boxstyle="square,pad=0", fc="#3E7CB1", ec="none"))
        ax.text(xl - P[i] * scale - .08, ys[i], f"{LAB[i]}  {P[i]:.2f}", ha="right", va="center", fontsize=7.5)
        # target: requested Q outline, achieved column sum filled
        ax.add_patch(FancyBboxPatch((xr, ys[i] - .16), max(cols[i] * scale, 1e-4), .32, boxstyle="square,pad=0", fc="#E07A5F" if i >= 3 else "#3E7CB1", ec="none", alpha=.85))
        ax.add_patch(FancyBboxPatch((xr, ys[i] - .16), max(Q[i] * scale, 1e-4), .32, boxstyle="square,pad=0", fc="none", ec="0.2", lw=.8, ls="--"))
        ax.text(xr + max(Q[i], cols[i]) * scale + .08, ys[i], f"{cols[i]:.3f} / {Q[i]:.2f}", ha="left", va="center", fontsize=7.5)
    for i in range(5):
        for j in range(5):
            f = pi[i][j]
            if f < 0.005: continue
            lw = 1 + f * 40
            colr = "#E07A5F" if j >= 3 else ("0.55" if i == j else "#3E7CB1")
            ax.annotate("", xy=(xr - .05, ys[j]), xytext=(xl + .05, ys[i]),
                        arrowprops=dict(arrowstyle="-|>", lw=lw * .35, color=colr, alpha=.8, mutation_scale=7, shrinkA=0, shrinkB=0))
            if i != j:
                t = [.30, .55, .80][len([1 for a in ax.texts if a.get_gid() == "flow"]) % 3]
                tx = xl + (xr - xl) * t; ty = ys[i] + (ys[j] - ys[i]) * t
                ax.text(tx, ty + .12, f"{f:.3f}", fontsize=7, ha="center", color=colr, gid="flow", bbox=dict(fc="white", ec="none", pad=.4, alpha=.9))
                continue
                ax.text(tx, ty + .12, f"{f:.3f}", fontsize=7, ha="center", color=colr, bbox=dict(fc="white", ec="none", pad=.4, alpha=.9))
    ax.text(xl - .1, ys[0] + .6, "Source P", ha="right", fontsize=8, weight="bold")
    ax.text(xr, ys[0] + .6, "Achieved / requested target", ha="left", fontsize=8, weight="bold")
    ax.set_xlim(-3.2, 5.6); ax.set_ylim(-.7, 4.9); ax.axis("off")
    ax.set_title(title, loc="left", fontsize=9.5)
p = R["primary"]
fig, ax = plt.subplots(2, 1, figsize=(7.2, 6.4))
flow_panel(ax[0], p[2], f"A. Scenario 1, aggressive plan: transport cost {p[2]['transport_cost']:.3f}, full objective {p[2]['full_objective']:.3f}")
flow_panel(ax[1], p[5], f"B. Scenario 2, aggressive plan: transport cost {p[5]['transport_cost']:.3f}, full objective {p[5]['full_objective']:.3f}")
fig.text(0.01, 0.005, "Arrow width is proportional to π[i][j]; labeled values are off-diagonal flows. Filled bars on the right are achieved column sums of π; dashed outlines are\nrequested targets Q. Coral marks flows into donor-site columns. Grey arrows are cartilage retained in place (diagonal).", fontsize=6.8, color="0.3")
fig.tight_layout(rect=(0, .04, 1, 1)); fig.savefig("Figure2_transport_plans.png", dpi=300); plt.close(fig)

# ---------------- Supplementary Figure S1: old Figure 1 convergence artifact ----------------
O = R["old_fig1_check"]; x = [o["reg_m"] for o in O]
fig, ax = plt.subplots(figsize=(4.6, 3.0))
for p in range(3):
    ax.plot(x, [o["default_iter"][p] for o in O], ls=":", marker="x", ms=3.5, color=COL[p])
    ax.plot(x, [o["converged"][p] for o in O], ls="-", marker="o", ms=3, color=COL[p], label=PL[p])
ax.set_xscale("log"); ax.set_xlabel("reg$_m$ (log scale)"); ax.set_ylabel("Transport cost")
ax.set_title("Original sensitivity inputs: default 1,000 iterations (dotted)\nvs converged (solid)", fontsize=8.5, loc="left")
ax.legend(frameon=False, fontsize=7.5); ax.grid(axis="y", lw=.4, color="0.88")
fig.tight_layout(); fig.savefig("FigureS1_convergence_check.png", dpi=300); plt.close(fig)
print("figs ok")
