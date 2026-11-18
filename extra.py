import json, numpy as np, ot, warnings, itertools
from scipy import stats
warnings.filterwarnings("ignore")
R=json.load(open("results.json"))
C=np.array([[0,.2,.3,.8,1],[.2,0,.2,.9,1],[.3,.2,0,.8,1],[.8,.9,.8,0,.7],[1,1,1,.7,0]],float)
IT=dict(numItermax=100000,stopThr=1e-12)
P1=np.array([.5,.25,.2,0,0]);Q1=[np.array(q) for q in ([.45,.25,.25,0,0],[.3,.2,.45,0,0],[.2,.2,.35,.25,0])]
P2=np.array([.1,.2,.2,0,0]);Q2=[np.array(q) for q in ([.3,.2,.2,0,.2],[.4,.2,.3,0,.3],[.4,.2,.35,0,.35])]
def lay(sept,thr):
    M=C.copy()
    if sept<=thr+1e-12: M[0,4]=.4;M[1,4]=.8
    return M
# septal-supply x threshold sweep (aggressive revision target)
rows=[]
for sept in [0.05,0.10,0.15,0.20,0.25,0.30,0.40]:
    P=np.array([sept,.2,.2,0,0]); r=[]
    for thr in [0.10,0.15,0.20,0.25,0.30]:
        M=lay(sept,thr); pi=ot.unbalanced.mm_unbalanced(P,Q2[2],M,reg_m=1,div='kl',**IT)
        src=["Septum","Upper lateral","Lower lateral"][int(np.argmax(pi[:3,4]))]
        r.append(dict(thr=thr,trig=bool(sept<=thr),dominant=src,rib=float(pi[:,4].sum()),tc=float((pi*M).sum())))
    rows.append(dict(septum=sept,res=r))
R["septum_threshold_sweep"]=rows
# pooled rho across reg_m (exact)
mr=np.array([1.17,2.33,3.5,3.17,4.0,4.5])
def ex(x,y):
    r0=stats.spearmanr(x,y)[0]; ps=list(itertools.permutations(y)); return float(r0), float(np.mean([abs(stats.spearmanr(x,p)[0])>=abs(r0)-1e-12 for p in ps]))
R["regm_rho"]=[dict(reg_m=s["reg_m"],rho=ex(mr,np.array(s["S1"]+s["S2"])) if max(s["S1"]+s["S2"])>1e-6 else None) for s in R["regm_sensitivity"]]
json.dump(R,open("results.json","w"),indent=1)
for r in rows: print(r["septum"],[(x["thr"],x["trig"],x["dominant"][:4]) for x in r["res"]])
for r in R["regm_rho"]: print(r)
