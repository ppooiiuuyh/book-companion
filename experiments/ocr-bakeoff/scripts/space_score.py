import sys, unicodedata, re
from rapidfuzz.distance import Levenshtein as L

def prep(s):
    s=unicodedata.normalize("NFC",s)
    s=re.sub(r"[‘’‚‛`´′']", "'", s); s=re.sub(r"[“”„\"]", '"', s); s=re.sub(r"[『』「」《》〈〉]", '"', s); s=re.sub(r"[–—−‐~〜]", "-", s)
    # 줄바꿈은 공백 판단에서 제외: 줄 경계는 'unknown'
    chars=[]; spaces=[]
    for line in s.splitlines():
        line=line.strip()
        if not line: continue
        for i,ch in enumerate(line):
            if ch==' ': 
                if spaces: spaces[-1]=1
                continue
            chars.append(ch); spaces.append(0)
        if spaces: spaces[-1]=-1  # line end: unknown
    return "".join(chars), spaces
def spacef1(gt,hyp):
    g,gs=prep(gt); h,hs=prep(hyp)
    tp=fp=fn=0
    for tag,i1,i2,j1,j2 in L.opcodes(g,h):
        if tag!='equal': continue
        for k in range(i2-i1):
            a=gs[i1+k]; b=hs[j1+k]
            if a==-1 or b==-1: continue
            if a==1 and b==1: tp+=1
            elif a==0 and b==1: fp+=1
            elif a==1 and b==0: fn+=1
    return tp,fp,fn
for eng in sys.argv[1:]:
    T=F=N=0
    for p in ["p005","p009","p016","p023","p041"]:
        tp,fp,fn=spacef1(open(f"ground_truth/{p}.txt").read(), open(f"outputs/{eng}/{p}.txt").read()); T+=tp;F+=fp;N+=fn
    P=T/max(T+F,1); R=T/max(T+N,1)
    print(f"{eng}: space precision {P:.3f} recall {R:.3f} F1 {2*P*R/max(P+R,1e-9):.3f}  (tp {T} fp {F} fn {N})")
