import json, numpy as np
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
R = json.load(open("results.json"))
d = Document()
st = d.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(10)
for s in d.sections: s.left_margin = s.right_margin = Inches(0.8)
PL = ["Conservative", "Moderate", "Aggressive"]
f3 = lambda x: f"{x:.3f}"
def shade(cell, hexc="D9D9D9"):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexc); tcPr.append(sh)
def table(title, header, rows, note=None):
    p = d.add_paragraph(); r = p.add_run(title); r.bold = True
    t = d.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; rr = c.paragraphs[0].add_run(h); rr.bold = True; rr.font.size = Pt(8.5); shade(c)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; rr = cells[i].paragraphs[0].add_run(str(v)); rr.font.size = Pt(8.5)
    if note:
        p = d.add_paragraph(); rr = p.add_run(note); rr.italic = True; rr.font.size = Pt(8)
    d.add_paragraph()
def h(text, lvl=1): d.add_heading(text, level=lvl)

h("Multimedia Appendix 1. Supplementary tables and figure", 0)
d.add_paragraph("All values recomputed from the original scripts with POT " + "0.9.7" +
                " (mm_unbalanced, KL divergence, reg_m = 1.0 unless stated), run to convergence (numItermax = 100,000; stopThr = 1e-12).")

h("Supplementary tables")
pr = R["primary"]; ER = R["ratings"]; BL = R["baselines"]; po = ER["pooled"]
LAB0 = ["Septum", "Upper lateral", "Lower lateral", "Ear", "Rib"]
for sc, sl, nm in (("1", slice(0,3), "S1"), ("2", slice(3,6), "S2")):
    p = d.add_paragraph(); r = p.add_run(f"Table {nm}. Scenario {sc}: transport matrices π for the conservative (π1), moderate (π2), and aggressive (π3) plans. Rows are sources; columns are target positions."); r.bold = True
    for k, x in enumerate(R["primary"][sl]):
        p = d.add_paragraph(); rr = p.add_run(f"π{k+1}, {['conservative','moderate','aggressive'][k]} (transport cost {x['transport_cost']:.3f})"); rr.italic = True
        t = d.add_table(rows=1, cols=6); t.style = "Table Grid"
        for ci, hh in enumerate(["Source / target"] + LAB0):
            c = t.rows[0].cells[ci]; c.text = ""; q = c.paragraphs[0].add_run(hh); q.bold = True; q.font.size = Pt(8.5); shade(c)
        for i2 in range(5):
            cells = t.add_row().cells
            for ci, v in enumerate([LAB0[i2]] + [f"{y:.3f}" for y in x["pi"][i2]]):
                cells[ci].text = ""; q = cells[ci].paragraphs[0].add_run(v); q.font.size = Pt(8.5)
    p = d.add_paragraph(); q = p.add_run("Created or removed cartilage is not a cell of π; it appears as the difference between π's row and column sums and P and Q (Table S4)."); q.italic = True; q.font.size = Pt(8)
    d.add_paragraph()

C = np.array([[0, .2, .3, .8, 1], [.2, 0, .2, .9, 1], [.3, .2, 0, .8, 1], [.8, .9, .8, 0, .7], [1, 1, 1, .7, 0]], float)
C2 = C.copy(); C2[0, 4] = .4; C2[1, 4] = .8
LAB = ["Septum", "Upper lateral", "Lower lateral", "Ear", "Rib"]
table("Table S3. Cost matrix after the indication layer (Scenario 2). Changed cells: septum→rib 1.0→0.4; upper lateral→rib 1.0→0.8",
      ["Source / target"] + LAB, [[LAB[i]] + [f"{v:.1f}" for v in C2[i]] for i in range(5)],
      "Ear and rib rows are never used in the primary analysis because P is zero in those regions.")

rows = []
for x in pr:
    rows.append([x["scenario"], x["plan"], " ".join(f"{v:.3f}" for v in x["row_sums"][:3]), " ".join(f"{v:.2f}" for v in x["P"][:3]),
                 " ".join(f"{v:.3f}" for v in x["col_sums"]), " ".join(f"{v:.2f}" for v in x["Q"])])
table("Table S4. Achieved versus requested marginals for every plan",
      ["Scenario", "Plan", "Row sums of π (Sep, UL, LL)", "P (Sep, UL, LL)", "Column sums of π (Sep, UL, LL, Ear, Rib)", "Q (Sep, UL, LL, Ear, Rib)"], rows,
      "In POT's unbalanced solvers, created or destroyed mass is not a cell of π; it appears as the gap between π's marginals and P or Q. In Scenario 2, row sums exceed P, so net mass is created (Σπ > ΣP) and appears on the septal and upper lateral rows.")

rows = []
for x, y in zip(R["normalized"], pr):
    rows.append([x["scenario"], x["plan"], f3(y["transport_cost"]), f3(x["transport_cost"]), f3(x["full_objective"])])
table("Table S5. Results with inputs normalized to sum to 1",
      ["Scenario", "Plan", "Transport cost, submitted inputs", "Transport cost, normalized", "Full objective, normalized"], rows,
      f"Within-scenario ordering is preserved. After normalization the Scenario 2 moderate and aggressive plans are nearly identical (difference {R['checks']['S2_marginal_normalized'][1]:.4f}). "
      f"Normalized Scenario 2 septal supply is {R['normalized_P2_septum']:.2f}, which still triggers the layer at threshold 0.20.")

rows = []
for k in range(3):
    a = pr[3 + k]; b = R["no_layer"][k]; sa = R["rib_sources_layer"][k]; sb = R["rib_sources_nolayer"][k]
    rows.append([PL[k], f3(a["transport_cost"]), f3(b["transport_cost"]),
                 f"Sep {sa['Septum']:.3f}, UL {sa['Upper lateral']:.3f}, LL {sa['Lower lateral']:.3f}",
                 f"Sep {sb['Septum']:.3f}, UL {sb['Upper lateral']:.3f}, LL {sb['Lower lateral']:.3f}"])
table("Table S6. Scenario 2 with and without the indication layer",
      ["Plan", "Transport cost, with layer", "Transport cost, base matrix", "Rib column sources, with layer", "Rib column sources, base matrix"], rows,
      "Without the layer, rib demand is drawn from the lower and upper lateral rows and the septal row contributes nothing.")

rows = []
for s in R["septum_threshold_sweep"]:
    rows.append([f"{s['septum']:.2f}"] + [f"{'on' if x['trig'] else 'off'}: {x['dominant']}" for x in s["res"]])
table("Table S7. Indication-layer threshold sweep: dominant source of rib-column mass (aggressive revision target)",
      ["Septal supply in P", "Threshold 0.10", "0.15", "0.20", "0.25", "0.30"], rows,
      "Upper lateral cartilage = 0.20 and lower lateral = 0.20 held fixed. With septal supply 0.10 (Scenario 2), the layer is triggered at every threshold tested, so Scenario 2 results do not depend on the 0.20 choice. "
      "For intermediate septal supply (0.15–0.30), whether septum is routed to rib depends on the threshold.")

rows = []
for s in R["layer_sweep"]:
    if abs(s["threshold"] - 0.20) > 1e-9: continue
    rows.append([f"{s['sept_rib']:.1f}", f"{s['ul_rib']:.1f}", " / ".join(f3(c) for c in s["costs"]), "Yes" if s["ordered"] else "No", ", ".join(sorted(set(s["dominant_rib_source"])))])
table("Table S8. Sensitivity to the modified indication-layer costs (Scenario 2, threshold 0.20)",
      ["Septum→rib cost", "Upper lateral→rib cost", "Transport cost (cons / mod / aggr)", "Ordering preserved", "Dominant rib source"], rows,
      "Cost ordering was preserved in all 75 threshold × cost combinations tested. Septal routing held when septum→rib was ≤ 0.6 and upper lateral→rib exceeded it by at least 0.2; otherwise rib-column mass shifted to the upper or lower lateral rows.")

pe = R["perturbation"]
rows = [[k.replace("pct", "%"), v["N"], f"{100*v['S1_order']:.1f}%", f"{100*v['S2_order']:.1f}%", f"{100*v['S1_ear_only_aggressive']:.1f}%", f"{100*v['S2_septum_dominant_rib']:.1f}%"] for k, v in pe.items()]
table("Table S9. Random perturbation of the cost matrix",
      ["Perturbation (± uniform, multiplicative)", "Draws", "Scenario 1 ordering preserved", "Scenario 2 ordering preserved", "Scenario 1 ear only in aggressive plan", "Scenario 2 septum dominant rib source, all plans"], rows,
      "Each off-diagonal entry (kept symmetric, clipped to [0.01, 1]) and each indication-layer cost was independently perturbed. Seed 20261112.")

rows = []
for s, rr in zip(R["regm_sensitivity"], R["regm_rho"]):
    rows.append([s["reg_m"], " / ".join(f3(v) for v in s["S1"]), " / ".join(f3(v) for v in s["S2"]),
                 " / ".join(f3(v) for v in s["S1_ear"]), " / ".join(f3(v) for v in s["S2_rib"]),
                 "—" if rr["rho"] is None else f"{rr['rho'][0]:.3f}"])
table("Table S10. Mass-penalty sensitivity on the two clinical scenarios (converged)",
      ["reg_m", "Scenario 1 cost (C/M/A)", "Scenario 2 cost (C/M/A)", "Scenario 1 ear column", "Scenario 2 rib column", "Pooled ρ with mean rating"], rows,
      "In both scenarios, plans become distinguishable (all pairwise differences > 0.001) from reg_m = 0.5, and within-scenario ordering is preserved from 0.5 through 100. "
      "Pooled ρ at reg_m 0.05–0.1 is based on costs below 0.002 and is not interpretable.")

cp_ = R["capped"]; rows = []
for tag, key in [("Scenario 1", "S1"), ("Scenario 2 (base matrix)", "S2_nolayer")]:
    for k, x in enumerate(cp_[key]):
        rows.append([tag, PL[k], f3(x["tc"]), f3(x["full"]), f3(x["ear"]), f3(x["rib"])])
table(f"Table S11. Supply-capped variant with empty donor targets (solver decides whether to harvest; ear reserve {cp_['caps'][0]}, rib reserve {cp_['caps'][1]})",
      ["Scenario", "Plan", "Transport cost", "Full objective", "Ear harvested", "Rib harvested"], rows,
      "Nasal supply is a hard upper bound (no creation of nasal cartilage); donor rows carry a harvestable reserve; targets include nasal positions only, with the donor graft demand in the submitted Q reassigned to the position it serves "
      "(Scenario 1 ear → lower lateral; Scenario 2 rib → septum/dorsum). Solved with CVXPY (Clarabel). The submitted indication layer acts on septum→rib cells, which do not exist in this variant, so Scenario 2 results are identical with or without it. "
      "Scenario 1 harvested no ear cartilage and Scenario 2 harvested no rib cartilage at any reserve setting tested ((0.10, 0.30), (0.15, 0.50), (0.25, 0.80)).")

rows = []
for k, tag in [("S1", "Scenario 1"), ("S2", "Scenario 2")]:
    e = ER[k]
    rows.append([tag, f"L = {e['page_L']:.1f}; P = {e['page_p']:.4f}", f"χ² = {e['friedman_chi2']:.2f}; P = {e['friedman_p']:.4f}", f"{e['kendall_W']:.2f}",
                 f"{e['ICC_A1']:.2f} ({e['ICC_A1_CI'][0]:.2f}–{e['ICC_A1_CI'][1]:.2f})", f"{e['ICC_Ak']:.2f} ({e['ICC_Ak_CI'][0]:.2f}–{e['ICC_Ak_CI'][1]:.2f})",
                 f"{e['tau_b_individual']:.2f} ({e['tau_b_CI'][0]:.2f}–{e['tau_b_CI'][1]:.2f})", f"{e['raters_monotone']}/6 ({e['raters_strict']}/6 strictly)"])
table("Table S12. Expert rating statistics (repeated-measures methods)",
      ["Scenario", "Page trend test (exact)", "Friedman test", "Kendall W", "ICC(A,1) (95% CI)", "ICC(A,k) (95% CI)", "Kendall τb, individual ratings vs cost (95% CI)", "Raters with non-decreasing ratings"], rows,
      "ICC: two-way random effects, absolute agreement (Shrout–Fleiss ICC2 / ICC2k), computed with pingouin. τb confidence intervals by rater-cluster bootstrap (5,000 resamples). "
      f"Pooled Spearman ρ between mean ratings and transport cost across six plans: {po['corrected'][0]:.3f}, exact P = {po['corrected'][1]:.3f} (bootstrap 95% CI {po['corrected_boot_CI'][0]:.2f}–{po['corrected_boot_CI'][1]:.2f}).")

raw1 = [[1, 3, 4], [1, 2, 3], [1, 2, 3], [2, 3, 4], [1, 3, 5], [1, 1, 2]]; raw2 = [[3, 4, 5], [3, 4, 5], [3, 4, 4], [4, 5, 5], [4, 4, 5], [2, 3, 3]]
table("Table S13. Anonymized individual ratings", ["Rater", "S1 Plan A", "S1 Plan B", "S1 Plan C", "S2 Plan A", "S2 Plan B", "S2 Plan C"],
      [[f"R{i+1}"] + raw1[i] + raw2[i] for i in range(6)],
      "Years in practice and annual case volume are omitted to prevent re-identification and are reported only in aggregate in the manuscript.")
p = d.add_paragraph(); r = p.add_run("Figure S1. Convergence check of the solver. Transport cost for illustrative inputs (P = Q1 = [0.40, 0.30, 0.30, 0, 0]; Q2 = [0.30, 0.25, 0.40, 0, 0]; Q3 = [0.25, 0.20, 0.35, 0.20, 0]) with POT's default iteration limit of 1000 (dotted) and run to convergence (solid). With the default limit, solutions at reg_m of 50 and above had not converged; for Q1 = P the converged cost is zero at every reg_m."); r.bold = False
d.add_picture("FigureS1_convergence_check.png", width=Inches(4.8))
d.save("Multimedia_Appendix_1.docx"); print("saved")
