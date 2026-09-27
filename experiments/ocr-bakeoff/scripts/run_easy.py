import easyocr, time, json
r=easyocr.Reader(['ko','en'], gpu=False, model_storage_directory='easy_models', download_enabled=False)
for p in ["p005","p009","p016","p023","p041"]:
    t=time.time(); res=r.readtext(f"pages/{p}.jpeg", paragraph=False); dt=time.time()-t
    items=sorted(res, key=lambda b:(sum(pt[1] for pt in b[0])/4))
    lines=[]; cur=[]; cy=None
    for b,txt,conf in items:
        y=sum(pt[1] for pt in b)/4; h=b[2][1]-b[0][1]
        if cy is not None and abs(y-cy)>h*0.5:
            lines.append(" ".join(x[1] for x in sorted(cur))); cur=[]
        cur.append((b[0][0],txt)); cy=y
    if cur: lines.append(" ".join(x[1] for x in sorted(cur)))
    open(f"outputs/easyocr_ko+en/{p}.txt","w").write("\n".join(lines))
    json.dump([{"box":[[float(v) for v in pt] for pt in b],"text":t_,"conf":float(c)} for b,t_,c in items],open(f"outputs/easyocr_ko+en/{p}.json","w"),ensure_ascii=False)
    print(p, round(dt,1), len(res), flush=True)
