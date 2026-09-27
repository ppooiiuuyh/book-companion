import time, json, sys
from rapidocr import RapidOCR
try:
    from rapidocr import LangRec, OCRVersion, ModelType
    eng = RapidOCR(params={"Rec.lang_type": LangRec.KOREAN, "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE})
    cfg="PP-OCRv5 korean rec"
except Exception as ex:
    print("fallback", ex); eng=RapidOCR(); cfg="default"
print(cfg)
for p in ["p005","p009","p016","p023","p041"]:
    t=time.time(); r=eng(f"pages/{p}.jpeg"); dt=time.time()-t
    boxes=r.boxes.tolist() if r.boxes is not None else []; txts=list(r.txts or []); scores=list(r.scores or [])
    # order: sort by y then x, group into lines
    items=sorted(zip(boxes,txts,scores), key=lambda b:(min(pt[1] for pt in b[0]), min(pt[0] for pt in b[0])))
    lines=[]; cur=[]; cy=None
    for b,t_,s in items:
        y=sum(pt[1] for pt in b)/4; h=max(pt[1] for pt in b)-min(pt[1] for pt in b)
        if cy is None or abs(y-cy)<h*0.5: cur.append((min(pt[0] for pt in b),t_)); cy=y if cy is None else cy
        else: lines.append(" ".join(x[1] for x in sorted(cur))); cur=[(min(pt[0] for pt in b),t_)]; cy=y
    if cur: lines.append(" ".join(x[1] for x in sorted(cur)))
    open(f"outputs/rapidocr_fallback_ch/{p}.txt","w").write("\n".join(lines))
    json.dump([{"box":b,"text":t_,"score":s} for b,t_,s in items],open(f"outputs/rapidocr_fallback_ch/{p}.json","w"),ensure_ascii=False)
    print(p, round(dt,2), len(txts))
