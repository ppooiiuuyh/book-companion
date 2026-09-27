"""파일럿 최종본을 OCR 비교 테스트의 정답(5, 9, 16, 23쪽)과 비교: 글자 오류율 + 띄어쓰기 F1."""
import json, re, sys, unicodedata
from pathlib import Path
from rapidfuzz.distance import Levenshtein as L
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from bookc.common import typo
BOOK = ROOT / "books/하류사회/_work"
GT = ROOT / "experiments/ocr-bakeoff/ground_truth"
OCR = ROOT / "experiments/ocr-bakeoff/outputs/tessdata_fast_psm4"

def page_text_final(p):
    fin = json.load(open(BOOK / f"final/p{p:03d}.json"))
    out = []
    for b in fin["blocks"]:
        if b["type"] in ("heading", "subheading", "title"): out.append(typo(b["text"]))
        elif b["type"] == "figure":
            if b.get("title"): out.append(typo(b["title"], dash=False))
            out += [typo(n) for n in b.get("notes", [])]
        else:
            out += [typo(t) for _, t in b["lines"]]
    return "\n".join(out)

def norm(s):
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[‘’‚‛`´′']", "'", s); s = re.sub(r"[“”„\"]", '"', s)
    s = re.sub(r"[『』「」《》〈〉]", '"', s); s = re.sub(r"[–—−‐~〜]", "-", s)
    s = re.sub(r"\[\^\d+\]", "", s)   # 각주 표시는 정답에 없음
    return s

def cer(gt, hyp):
    g = re.sub(r"\s", "", norm(gt)); h = re.sub(r"\s", "", norm(hyp))
    return L.distance(g, h), len(g)

def spaces(s):
    chars, sp = [], []
    for line in norm(s).splitlines():
        line = line.strip()
        for ch in line:
            if ch == " ":
                if sp: sp[-1] = 1
                continue
            chars.append(ch); sp.append(0)
        if sp: sp[-1] = -1
    return "".join(chars), sp

def space_f1(gt, hyp):
    g, gs = spaces(gt); h, hs = spaces(hyp); tp = fp = fn = 0
    for tag, i1, i2, j1, j2 in L.opcodes(g, h):
        if tag != "equal": continue
        for k in range(i2 - i1):
            a, b = gs[i1 + k], hs[j1 + k]
            if -1 in (a, b): continue
            tp += a == 1 and b == 1; fp += a == 0 and b == 1; fn += a == 1 and b == 0
    return tp, fp, fn

rows = []
for p in (5, 9, 16, 23):
    gt = open(GT / f"p{p:03d}.txt").read()
    fin = page_text_final(p); ocr = open(OCR / f"p{p:03d}.txt").read()
    (d1, n), (d0, _) = cer(gt, fin), cer(gt, ocr)
    tp, fp, fn = space_f1(gt, fin)
    rows.append((p, n, d0, d1, tp, fp, fn))
    print(f"p{p:03d}: 글자 {n}  OCR 초벌 오류 {d0} ({d0/n:.2%})  교정 후 오류 {d1} ({d1/n:.2%})  띄어쓰기 tp{tp} fp{fp} fn{fn}")
N = sum(r[1] for r in rows); D0 = sum(r[2] for r in rows); D1 = sum(r[3] for r in rows)
TP = sum(r[4] for r in rows); FP = sum(r[5] for r in rows); FN = sum(r[6] for r in rows)
P = TP / max(TP + FP, 1); R = TP / max(TP + FN, 1)
print(f"합계: 글자 {N}, 초벌 CER {D0/N:.2%} → 교정 후 CER {D1/N:.2%}, 띄어쓰기 F1 {2*P*R/(P+R):.3f}")
