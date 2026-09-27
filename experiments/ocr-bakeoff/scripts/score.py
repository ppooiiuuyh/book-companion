import json, re, unicodedata, sys, os
from rapidfuzz.distance import Levenshtein as L
PAGES=["p005","p009","p016","p023","p041"]
TERMS=["하류","중류","중산층","하층","상층","계층","격차","신인류","쇼와","신중간층","미혼","자산가","갸루","블루칼라","비정규직","유니클로","디플레이션","크라운","렉서스","지니계수","중상","중하","희망격차","샐러리맨","고도경제성장","사토도시키"]
def norm(s):
    s=unicodedata.normalize("NFC",s)
    s=re.sub(r"[‘’‚‛`´′']", "'", s); s=re.sub(r"[“”„\"]", '"', s)
    s=re.sub(r"[『』「」《》〈〉]", '"', s)
    s=re.sub(r"[–—−‐~〜]", "-", s)
    s=s.replace("×","x").replace("X","X")
    s=s.replace("，",",").replace("。",".").replace("：",":").replace("（","(").replace("）",")")
    return re.sub(r"\s+","",s)
def score(gt, hyp):
    g,h=norm(gt),norm(hyp)
    ops=L.opcodes(g,h)
    eq=sum(i2-i1 for tag,i1,i2,j1,j2 in ops if tag=="equal")
    d=L.distance(g,h)
    return {"n_gt":len(g),"n_hyp":len(h),"cer":d/len(g),"recall":eq/len(g),"precision":eq/max(len(h),1)}
def terms(gt,hyp):
    g,h=norm(gt),norm(hyp); tot=hit=0; miss=[]
    for t in TERMS:
        c=g.count(t)
        if c: 
            k=min(c,h.count(t)); tot+=c; hit+=k
            if k<c: miss.append(f"{t}({k}/{c})")
    return tot,hit,miss
res={}
for eng in sys.argv[1:]:
    rows=[]; T=H=0; G=D=EQ=HN=0
    for p in PAGES:
        f=f"outputs/{eng}/{p}.txt"
        if not os.path.exists(f): continue
        gt=open(f"ground_truth/{p}.txt").read(); hyp=open(f).read()
        s=score(gt,hyp); t,hh,miss=terms(gt,hyp)
        if p=="p016":
            ch=json.load(open("ground_truth/p016_chart.json")); hn=norm(hyp)
            s["chart_values"]=f'{sum(1 for v in ch["values"] if v in hn)}/{len(ch["values"])}'
            s["chart_labels"]=f'{sum(1 for v in set(ch["labels"]) if v in hn)}/{len(set(ch["labels"]))}'
        s.update({"terms":f"{hh}/{t}","term_miss":miss}); rows.append((p,s))
        T+=t;H+=hh; g=norm(gt); h=norm(hyp); G+=len(g); D+=L.distance(g,h); HN+=len(h)
        EQ+=sum(i2-i1 for tag,i1,i2,j1,j2 in L.opcodes(g,h) if tag=="equal")
    res[eng]={"pages":dict(rows),"total":{"cer":D/G,"recall":EQ/G,"precision":EQ/HN,"terms":f"{H}/{T}","term_acc":H/T}}
    print(f"== {eng}: CER {D/G:.3f}  recall {EQ/G:.3f}  precision {EQ/HN:.3f}  terms {H}/{T}")
    for p,s in rows: print(f"  {p}: CER {s['cer']:.3f} rec {s['recall']:.3f} prec {s['precision']:.3f} terms {s['terms']} {s.get('chart_values','')} {s.get('chart_labels','')} miss={s['term_miss']}")
json.dump(res,open("scores.json","w"),ensure_ascii=False,indent=1)
