# Unbalanced optimal transport framework for rhinoplasty planning: code and data

Code and anonymized data for Kumar AR, Varshney LR. *An Unbalanced Optimal Transport Framework for AI-Based Surgical Planning in Rhinoplasty: Development and Proof-of-Concept Study* (JMIR AI, under review).

## Requirements
Python 3.10+, POT 0.9.7 (`pip install POT==0.9.7`), numpy, scipy, pandas, pingouin, cvxpy (Clarabel), matplotlib, python-docx.

## Run
```
python reanalysis.py   # all analyses -> results.json (about 4 minutes; cost-matrix perturbation dominates)
python extra.py        # septal-supply x threshold sweep, reg_m rank correlations -> results.json
python figures.py      # Figure 1, Figure 2, Figure S1
python ma1.py          # Multimedia Appendix 1 (supplementary tables S1-S13, Figure S1)
```

## Solver settings
`ot.unbalanced.mm_unbalanced(P, Q, C, reg_m=1.0, div="kl", numItermax=100000, stopThr=1e-12)`.
POT's default `numItermax=1000` does not converge for reg_m >= 50 (see Figure S1).

## Inputs
- Base cost matrix and indication layer (septum->rib 0.4, upper lateral->rib 0.8 when septal supply <= 0.20): `reanalysis.py`, top of file.
- Scenario source and target vectors: `reanalysis.py`.
- `ratings_anonymized.csv`: complexity ratings (1-5) from six fellowship-trained facial plastic surgeons. Plans A/B/C = conservative/moderate/aggressive. Rater demographics are withheld to prevent re-identification.

## License
MIT (code); CC BY 4.0 (data).
