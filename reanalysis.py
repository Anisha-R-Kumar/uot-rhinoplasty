"""
UOT rhinoplasty framework: full re-analysis for JMIR AI revision (ms #107274).
Addresses Reviewer EH major comments 1-9 and Reviewer DQ comments.
Solver: POT mm_unbalanced, KL divergence, converged (numItermax=100000, stopThr=1e-12).
"""
import json, itertools, warnings
import numpy as np, ot, cvxpy as cp, pandas as pd, pingouin as pg
from scipy import stats
warnings.filterwarnings("ignore")
rng = np.random.default_rng(20261112)
R = {"pot_version": ot.__version__, "cvxpy_version": cp.__version__}
LAB = ["Septum", "Upper lateral", "Lower lateral", "Ear", "Rib"]
ITER = dict(numItermax=100000, stopThr=1e-12)

# ---------------- inputs (as submitted) ----------------
C_BASE = np.array([[0, .2, .3, .8, 1], [.2, 0, .2, .9, 1], [.3, .2, 0, .8, 1],
                   [.8, .9, .8, 0, .7], [1, 1, 1, .7, 0]], float)
P1 = np.array([.50, .25, .20, 0, 0])
Q1 = [np.array(q) for q in ([.45, .25, .25, 0, 0], [.30, .20, .45, 0, 0], [.20, .20, .35, .25, 0])]
P2 = np.array([.10, .20, .20, 0, 0])
Q2 = [np.array(q) for q in ([.30, .20, .20, 0, .20], [.40, .20, .30, 0, .30], [.40, .20, .35, 0, .35])]
PLANS = ["Conservative", "Moderate", "Aggressive"]

def layer(C, sept, thr=0.20, s_rib=0.4, ul_rib=0.8):
    C = C.copy()
    if sept <= thr + 1e-12:
        C[0, 4] = s_rib; C[1, 4] = ul_rib
    return C

def kl(a, b):
    m = a > 1e-15
    return float(np.sum(a[m] * np.log(a[m] / b[m])) - a.sum() + b.sum())

def solve(P, Q, C, reg_m=1.0):
    pi = ot.unbalanced.mm_unbalanced(P, Q, C, reg_m=reg_m, div="kl", **ITER)
    r, c = pi.sum(1), pi.sum(0)
    tc = float((pi * C).sum())
    return dict(pi=pi, tc=tc, kl_src=kl(r, P), kl_tgt=kl(c, Q),
                full=tc + reg_m * kl(r, P) + reg_m * kl(c, Q),
                rows=r, cols=c, mass_pi=float(pi.sum()))

def scen(P, Qs, C_fn, reg_m=1.0):
    return [solve(P, Q, C_fn(P), reg_m) for Q in Qs]

C1 = lambda P: C_BASE
C2 = lambda P: layer(C_BASE, P[0])
norm = lambda v: v / v.sum()

# ---------------- 1. primary results + margins + full objective ----------------
S1 = scen(P1, Q1, C1); S2 = scen(P2, Q2, C2)
R["input_sums"] = {"P1": P1.sum(), "Q1": [q.sum() for q in Q1], "P2": P2.sum(), "Q2": [q.sum() for q in Q2]}
def pack(S, P, Qs, tag):
    out = []
    for k, (s, Q) in enumerate(zip(S, Qs)):
        out.append(dict(scenario=tag, plan=PLANS[k], transport_cost=s["tc"], kl_source=s["kl_src"],
                        kl_target=s["kl_tgt"], full_objective=s["full"], total_mass_pi=s["mass_pi"],
                        total_P=P.sum(), total_Q=Q.sum(),
                        row_sums=s["rows"].round(4).tolist(), P=P.tolist(),
                        col_sums=s["cols"].round(4).tolist(), Q=Q.tolist(),
                        pi=s["pi"].round(4).tolist()))
    return out
R["primary"] = pack(S1, P1, Q1, "S1") + pack(S2, P2, Q2, "S2")

# ---------------- 2. normalized inputs ----------------
S1n = scen(norm(P1), [norm(q) for q in Q1], C1)
S2n = scen(norm(P2), [norm(q) for q in Q2], C2)   # normalized septum = 0.20 -> layer still triggers (<=)
R["normalized"] = pack(S1n, norm(P1), [norm(q) for q in Q1], "S1") + pack(S2n, norm(P2), [norm(q) for q in Q2], "S2")
R["normalized_P2_septum"] = float(norm(P2)[0])

# ---------------- 3. no indication layer ----------------
S2_nolayer = scen(P2, Q2, C1)
R["no_layer"] = pack(S2_nolayer, P2, Q2, "S2")
def rib_sources(pi): return {LAB[i]: float(pi[i, 4]) for i in range(3)}
R["rib_sources_layer"] = [rib_sources(s["pi"]) for s in S2]
R["rib_sources_nolayer"] = [rib_sources(s["pi"]) for s in S2_nolayer]

# ---------------- 4. threshold + modified-cost sweep ----------------
sweep = []
for thr in [0.10, 0.15, 0.20, 0.25, 0.30]:
    for sr in [0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
        for ur in [0.6, 0.8, 1.0]:
            if ur < sr: continue
            S = [solve(P2, Q, layer(C_BASE, P2[0], thr, sr, ur)) for Q in Q2]
            tcs = [s["tc"] for s in S]
            dom = [LAB[int(np.argmax(s["pi"][:3, 4]))] for s in S]
            sweep.append(dict(threshold=thr, sept_rib=sr, ul_rib=ur, triggered=P2[0] <= thr,
                              costs=tcs, ordered=bool(tcs[0] < tcs[1] < tcs[2]),
                              dominant_rib_source=dom))
R["layer_sweep"] = sweep

# ---------------- 5. cost-matrix perturbation ----------------
def perturb(C, amp):
    M = C.copy(); n = len(C)
    for i in range(n):
        for j in range(i + 1, n):
            v = np.clip(C[i, j] * (1 + rng.uniform(-amp, amp)), 0.01, 1.0)
            M[i, j] = M[j, i] = v
    return M
pert = {}
for amp in [0.10, 0.20]:
    ok1 = ok2 = ear_only3 = sept_dom = 0; N = 1000
    for _ in range(N):
        Cp = perturb(C_BASE, amp)
        a = [solve(P1, Q, Cp) for Q in Q1]
        Cl = Cp.copy(); Cl[0, 4] = np.clip(0.4 * (1 + rng.uniform(-amp, amp)), .01, 1); Cl[1, 4] = np.clip(0.8 * (1 + rng.uniform(-amp, amp)), .01, 1)
        b = [solve(P2, Q, Cl) for Q in Q2]
        ta = [s["tc"] for s in a]; tb = [s["tc"] for s in b]
        ok1 += ta[0] < ta[1] < ta[2]; ok2 += tb[0] < tb[1] < tb[2]
        ear_only3 += (a[2]["cols"][3] > .01) and (a[0]["cols"][3] < .01) and (a[1]["cols"][3] < .01)
        sept_dom += all(np.argmax(s["pi"][:3, 4]) == 0 for s in b)
    pert[f"{int(amp*100)}pct"] = dict(N=N, S1_order=ok1 / N, S2_order=ok2 / N,
                                     S1_ear_only_aggressive=ear_only3 / N, S2_septum_dominant_rib=sept_dom / N)
R["perturbation"] = pert

# ---------------- 6. reg_m sensitivity on the actual scenarios (converged) ----------------
grid = [0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 50, 100]
sens = []
for rm in grid:
    a = scen(P1, Q1, C1, rm); b = scen(P2, Q2, C2, rm)
    sens.append(dict(reg_m=rm, S1=[s["tc"] for s in a], S2=[s["tc"] for s in b],
                     S1_full=[s["full"] for s in a], S2_full=[s["full"] for s in b],
                     S1_ear=[float(s["cols"][3]) for s in a], S2_rib=[float(s["cols"][4]) for s in b],
                     S1_order=bool(a[0]["tc"] < a[1]["tc"] < a[2]["tc"]),
                     S2_order=bool(b[0]["tc"] < b[1]["tc"] < b[2]["tc"]),
                     S1_order_weak=bool(a[0]["tc"] <= a[1]["tc"] <= a[2]["tc"] and a[0]["tc"] < a[2]["tc"])))
R["regm_sensitivity"] = sens
# old abstract-distribution sensitivity: default vs converged iterations
Ps = np.array([.4, .3, .3, 0, 0]); Qs = [Ps, np.array([.3, .25, .4, 0, 0]), np.array([.25, .2, .35, .2, 0])]
old = []
for rm in [0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100]:
    d = [float((ot.unbalanced.mm_unbalanced(Ps, q, C_BASE, reg_m=rm, div="kl") * C_BASE).sum()) for q in Qs]
    h = [float((ot.unbalanced.mm_unbalanced(Ps, q, C_BASE, reg_m=rm, div="kl", **ITER) * C_BASE).sum()) for q in Qs]
    old.append(dict(reg_m=rm, default_iter=d, converged=h))
R["old_fig1_check"] = old

# ---------------- 7. baselines ----------------
W_DEF = np.array([0.2, 0.2, 0.2, 0.8, 1.0])
def baselines(P, Q, C):
    l1 = float(np.abs(P - Q).sum())
    deficit = float(np.sum(np.maximum(Q - P, 0) * W_DEF))
    bot = float(ot.emd2(norm(P), norm(Q), C))  # balanced OT on normalized inputs
    return dict(L1=l1, weighted_deficit=deficit, balanced_OT=bot)
BL = [baselines(P1, q, C_BASE) for q in Q1] + [baselines(P2, q, layer(C_BASE, P2[0])) for q in Q2]
R["baselines"] = BL

# illustrative case where L1 is blind to route difficulty but UOT is not
Pi = np.array([.5, .25, .25, 0, 0])
Qa = np.array([.4, .25, .35, 0, 0])   # 0.10 septum -> lower lateral (tip graft)
Qb = np.array([.4, .25, .25, .10, 0]) # 0.10 demand placed in ear column
R["illustrative"] = dict(L1=[float(np.abs(Pi - Qa).sum()), float(np.abs(Pi - Qb).sum())],
                         UOT=[solve(Pi, Qa, C_BASE)["tc"], solve(Pi, Qb, C_BASE)["tc"]],
                         UOT_full=[solve(Pi, Qa, C_BASE)["full"], solve(Pi, Qb, C_BASE)["full"]])

# ---------------- 8. supply-capped variant with donor reserves (empty donor targets) -------------
# Rows: nasal supply + harvestable donor reserve (hard caps, no creation of nasal cartilage).
# Targets: nasal positions only (donor columns empty); solver decides whether to harvest.
# Donor graft demand from submitted Q is reassigned to the nasal position the graft serves:
#   S1 aggressive ear 0.25 -> lower lateral (tip/alar grafts); S2 rib -> septum (dorsal/L-strut).
EAR_CAP, RIB_CAP = 0.15, 0.50
def capped(P_nasal, Q_nasal, C, lam=1.0, caps=(EAR_CAP, RIB_CAP)):
    supply = np.concatenate([P_nasal, caps])
    Cn = C[:, :3]                     # 5 sources -> 3 nasal targets
    X = cp.Variable((5, 3), nonneg=True)
    col = cp.sum(X, axis=0)
    obj = cp.sum(cp.multiply(Cn, X)) + lam * cp.sum(cp.kl_div(col, Q_nasal))
    prob = cp.Problem(cp.Minimize(obj), [cp.sum(X, axis=1) <= supply])
    prob.solve(solver="CLARABEL")
    x = np.maximum(X.value, 0)
    return dict(tc=float((x * Cn).sum()), full=float(prob.value), ear=float(x[3].sum()),
                rib=float(x[4].sum()), cols=x.sum(0).round(4).tolist(), pi=x.round(4).tolist())
Q1n = [np.array([.45, .25, .25]), np.array([.30, .20, .45]), np.array([.20, .20, .60])]
Q2n = [np.array([.50, .20, .20]), np.array([.70, .20, .30]), np.array([.75, .20, .35])]
R["capped"] = dict(caps=[EAR_CAP, RIB_CAP],
                   S1=[capped(P1[:3], q, C_BASE) for q in Q1n],
                   S2_layer=[capped(P2[:3], q, layer(C_BASE, P2[0])) for q in Q2n],
                   S2_nolayer=[capped(P2[:3], q, C_BASE) for q in Q2n])
# cap sensitivity
R["capped_cap_sweep"] = [dict(ear=e, rib=r, S1_ear=[capped(P1[:3], q, C_BASE, caps=(e, r))["ear"] for q in Q1n],
                              S2_rib=[capped(P2[:3], q, layer(C_BASE, P2[0]), caps=(e, r))["rib"] for q in Q2n])
                         for e, r in [(0.10, 0.3), (0.15, 0.5), (0.25, 0.8)]]

# ---------------- 9. expert ratings ----------------
s1 = np.array([[1, 3, 4], [1, 2, 3], [1, 2, 3], [2, 3, 4], [1, 3, 5], [1, 1, 2]])
s2 = np.array([[3, 4, 5], [3, 4, 5], [3, 4, 4], [4, 5, 5], [4, 4, 5], [2, 3, 3]])
ER = {}
for tag, s in [("S1", s1), ("S2", s2)]:
    pt = stats.page_trend_test(s); fr = stats.friedmanchisquare(*s.T)
    jt_note = "submitted JT P values were one-sided and assumed independent groups"
    df = pd.DataFrame([(r, p, s[r, p]) for r in range(6) for p in range(3)], columns=["rater", "plan", "y"])
    icc = pg.intraclass_corr(df, targets="plan", raters="rater", ratings="y").set_index("Type")
    ER[tag] = dict(mean=s.mean(0).round(2).tolist(), sd=s.std(0, ddof=1).round(2).tolist(),
                   page_L=float(pt.statistic), page_p=float(pt.pvalue),
                   friedman_chi2=float(fr.statistic), friedman_p=float(fr.pvalue),
                   kendall_W=float(fr.statistic / (6 * 2)),
                   ICC_A1=float(icc.loc["ICC(A,1)", "ICC"]), ICC_A1_CI=list(icc.loc["ICC(A,1)", "CI95"]), ICC_A1_p=float(icc.loc["ICC(A,1)", "pval"]),
                   ICC_Ak=float(icc.loc["ICC(A,k)", "ICC"]), ICC_Ak_CI=list(icc.loc["ICC(A,k)", "CI95"]),
                   raters_monotone=int(sum(all(np.diff(r) >= 0) for r in s)),
                   raters_strict=int(sum(all(np.diff(r) > 0) for r in s)))
ratings_mean = np.concatenate([s1.mean(0), s2.mean(0)])
costs = np.array([x["transport_cost"] for x in R["primary"]])
def exact_spearman(x, y):
    r0 = stats.spearmanr(x, y)[0]; perms = list(itertools.permutations(y))
    return float(r0), float(np.mean([abs(stats.spearmanr(x, p)[0]) >= abs(r0) - 1e-12 for p in perms]))
# cluster bootstrap CI over raters for pooled rho
boot = []
for _ in range(5000):
    idx = rng.integers(0, 6, 6)
    m = np.concatenate([s1[idx].mean(0), s2[idx].mean(0)])
    boot.append(stats.spearmanr(m, costs)[0])
ER["pooled"] = dict(
    submitted_costs=[0, .038, .127, .088, .119, .130],
    submitted=exact_spearman(ratings_mean, np.array([0, .038, .127, .088, .119, .130])),
    corrected=exact_spearman(ratings_mean, costs),
    corrected_asymptotic_p=float(stats.spearmanr(ratings_mean, costs)[1]),
    corrected_boot_CI=[float(np.nanpercentile(boot, 2.5)), float(np.nanpercentile(boot, 97.5))],
    L1=exact_spearman(ratings_mean, np.array([b["L1"] for b in BL])),
    weighted_deficit=exact_spearman(ratings_mean, np.array([b["weighted_deficit"] for b in BL])),
    balanced_OT=exact_spearman(ratings_mean, np.array([b["balanced_OT"] for b in BL])),
    UOT_full_objective=exact_spearman(ratings_mean, np.array([x["full_objective"] for x in R["primary"]])),
    normalized_UOT=exact_spearman(ratings_mean, np.array([x["transport_cost"] for x in R["normalized"]])))
# within-scenario Kendall tau-b, individual ratings vs plan cost (18 pairs/scenario), rater-cluster bootstrap
for tag, s, c in [("S1", s1, costs[:3]), ("S2", s2, costs[3:])]:
    x = np.tile(c, 6); y = s.ravel()
    tau = stats.kendalltau(x, y)[0]; bt = []
    for _ in range(5000):
        idx = rng.integers(0, 6, 6); bt.append(stats.kendalltau(np.tile(c, 6), s[idx].ravel())[0])
    ER[tag]["tau_b_individual"] = float(tau); ER[tag]["tau_b_CI"] = [float(np.nanpercentile(bt, 2.5)), float(np.nanpercentile(bt, 97.5))]
R["ratings"] = ER

# ---------------- reported-number checks ----------------
R["checks"] = dict(S1_ratio=S1[2]["tc"] / S1[1]["tc"],
                   S2_rib_increase=S2[2]["cols"][4] / S2[0]["cols"][4],
                   S2_marginal=[S2[1]["tc"] - S2[0]["tc"], S2[2]["tc"] - S2[1]["tc"]],
                   S2_marginal_ratio=(S2[1]["tc"] - S2[0]["tc"]) / (S2[2]["tc"] - S2[1]["tc"]),
                   S2_marginal_normalized=[S2n[1]["tc"] - S2n[0]["tc"], S2n[2]["tc"] - S2n[1]["tc"]],
                   rating_increments_S2=[float(s2.mean(0)[1] - s2.mean(0)[0]), float(s2.mean(0)[2] - s2.mean(0)[1])])

def conv(o):
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    if isinstance(o, np.ndarray): return o.tolist()
    raise TypeError(type(o))
json.dump(R, open("results.json", "w"), indent=1, default=conv)
print("done")
