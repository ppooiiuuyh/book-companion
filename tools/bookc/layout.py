"""레이아웃: 줄 유형 추정(소제목·본문·도표 내부·도표 제목·주/출처·캡션), 문단 시작, 도표 영역 검출,
그리고 교정자(Claude)가 볼 검수 초안(_work/draft/pNNN.md) 생성."""
from __future__ import annotations
import re
from collections import deque
import numpy as np
from PIL import Image
from .common import Book, pid, read_json, write_json
from .intake import page_image

FIGTITLE_RE = re.compile(r"^\s*(도표|그림|표|사진)\s*\d")
FIGNOTE_RE = re.compile(r"^\s*(주|출처|자료|※)\s*[:：]?")
SENT_END_RE = re.compile(r"[.?!)」』’”]$")
CELL = 8  # 도표 검출 격자 크기(px)


def _median(v, default=0):
    v = sorted(v)
    return v[len(v) // 2] if v else default


def ink_density(gray: np.ndarray, b) -> float:
    x0, y0, x1, y1 = b
    crop = gray[y0:y1, x0:x1]
    return float((crop < 128).mean()) if crop.size else 0.0


def find_figures(gray: np.ndarray, text_boxes: list, H: float) -> list[list[int]]:
    """본문 줄을 지운 뒤 남은 큰 잉크 덩어리를 도표·사진 영역으로 본다."""
    h, w = gray.shape
    gh, gw = h // CELL, w // CELL
    g = gray[: gh * CELL, : gw * CELL].reshape(gh, CELL, gw, CELL).min(axis=(1, 3)) < 150
    for (x0, y0, x1, y1) in text_boxes:
        g[max(0, y0 // CELL - 1): y1 // CELL + 2, max(0, x0 // CELL - 1): x1 // CELL + 2] = False
    seen = np.zeros_like(g)
    comps = []
    for y in range(gh):
        for x in range(gw):
            if g[y, x] and not seen[y, x]:
                q = deque([(y, x)]); seen[y, x] = True
                ys, xs, n = [y, y], [x, x], 0
                while q:
                    cy, cx = q.popleft(); n += 1
                    ys[0], ys[1] = min(ys[0], cy), max(ys[1], cy)
                    xs[0], xs[1] = min(xs[0], cx), max(xs[1], cx)
                    for dy in (-2, -1, 0, 1, 2):
                        for dx in (-2, -1, 0, 1, 2):
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < gh and 0 <= nx < gw and g[ny, nx] and not seen[ny, nx]:
                                seen[ny, nx] = True; q.append((ny, nx))
                comps.append([xs[0] * CELL, ys[0] * CELL, (xs[1] + 1) * CELL, (ys[1] + 1) * CELL, n])
    # 큰 덩어리만, 서로 가까우면 병합
    big = [c for c in comps if (c[2] - c[0]) > 3 * H and (c[3] - c[1]) > 3 * H and c[4] > 60]
    merged = True
    while merged:
        merged = False
        for i in range(len(big)):
            for j in range(i + 1, len(big)):
                a, b = big[i], big[j]
                if a[0] - 2 * H < b[2] and b[0] - 2 * H < a[2] and a[1] - 2 * H < b[3] and b[1] - 2 * H < a[3]:
                    big[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]), a[4] + b[4]]
                    big.pop(j); merged = True; break
            if merged:
                break
    return [c[:4] for c in big if (c[2] - c[0]) * (c[3] - c[1]) > 0.02 * w * h]


def hangul_ratio(t: str) -> float:
    t = re.sub(r"\s", "", t)
    return sum(1 for c in t if "가" <= c <= "힣") / max(len(t), 1)


def run_page(book: Book, page: int) -> dict:
    ocr = read_json(book.work / "ocr" / f"{pid(page)}.json")
    lines = ocr["lines"]
    gray = np.asarray(Image.open(page_image(book, page)).convert("L"))
    ph, pw = gray.shape
    if not lines:
        res = {"page": page, "lines": [], "figures": [], "empty": True}
        write_json(book.d("layout") / f"{pid(page)}.json", res)
        _draft(book, page, res)
        return {"lines": 0, "figures": 0}
    hs = [l["bbox"][3] - l["bbox"][1] for l in lines]
    H = _median(hs, 40)
    em = _median([w["b"][3] - w["b"][1] for l in lines for w in l.get("words", []) if len(w["t"]) >= 1], 30)
    # 본문 줄: 폭이 넓고 신뢰도 높은 줄 → 좌측 여백 기준
    wide = [l for l in lines if (l["bbox"][2] - l["bbox"][0]) > 0.6 * pw and l["conf"] > 70
            and hangul_ratio(l["text"]) > 0.5]
    prose = [l["bbox"][0] for l in lines if l["conf"] > 70 and hangul_ratio(l["text"]) > 0.5
             and (l["bbox"][2] - l["bbox"][0]) > 0.15 * pw]
    xs = sorted(prose)
    left = xs[0] if xs else 18
    left = min(left, book.manifest.get("layout", {}).get("left", left))
    dens_body = _median([ink_density(gray, l["bbox"]) for l in wide], 0.12) or 0.12

    # 도표 영역: 본문처럼 보이는 줄(넓고 신뢰도 높은)만 지우고 남은 잉크
    textlike = [l["bbox"] for l in lines if l["conf"] > 80 and (l["bbox"][2] - l["bbox"][0]) > 0.35 * pw
                and hangul_ratio(l["text"]) > 0.6 and not FIGTITLE_RE.match(l["text"])]
    figs = find_figures(gray, textlike, H)
    figures = [{"id": None, "bbox": f, "lines": []} for f in figs]

    prev_bottom = None
    for l in lines:
        x0, y0, x1, y1 = l["bbox"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        l["kind"] = "body"
        for f in figures:
            fx0, fy0, fx1, fy1 = f["bbox"]
            if fx0 - 10 <= cx <= fx1 + 10 and fy0 - 10 <= cy <= fy1 + 10:
                l["kind"] = "fig"; f["lines"].append(l["id"])
        gap = (y0 - prev_bottom) if prev_bottom is not None else y0
        l["gap_above"] = int(gap)
        l["indent"] = x0 - left > 0.6 * em
        l["bold"] = round(ink_density(gray, l["bbox"]) / dens_body, 2)
        width = (x1 - x0) / pw
        if l["kind"] == "body":
            if FIGTITLE_RE.match(l["text"]):
                l["kind"] = "figtitle"
            elif FIGNOTE_RE.match(l["text"]) and any(abs(y0 - f["bbox"][3]) < 6 * H for f in figures):
                l["kind"] = "fignote"
            elif figures and any(0 <= y0 - f["bbox"][3] < 2.5 * H for f in figures) and width < 0.8:
                l["kind"] = "caption"
            elif (gap > 1.6 * H or prev_bottom is None) and width < 0.6 and l["bold"] > 1.15 \
                    and not re.match(r"^\d+\.", l["text"]):
                l["kind"] = "heading?"
        l["para_start"] = l["kind"] == "body" and (l["indent"] or (prev_bottom is not None and gap > 1.6 * H))
        prev_bottom = y1
    ch = book.chapter_of(page)
    if ch and page == ch["pages"][0] and lines and re.sub(r"\s", "", lines[0]["text"]) == re.sub(r"\s", "", ch["label"]):
        lines[0]["kind"] = "title"; lines[0]["para_start"] = False
    # 도표 제목·주를 가장 가까운 도표에 연결
    for l in lines:
        if l["kind"] in ("figtitle", "fignote", "caption") and figures:
            f = min(figures, key=lambda f: min(abs(l["bbox"][1] - f["bbox"][3]), abs(l["bbox"][3] - f["bbox"][1])))
            f.setdefault("attached", []).append(l["id"])
    order = sorted([("line", l["bbox"][1], l) for l in lines] + [("fig", f["bbox"][1], f) for f in figures],
                   key=lambda t: t[1])
    bno = 0
    for kind, _, obj in order:
        if kind == "fig":
            bno += 1; obj["id"] = f"{pid(page)}-b{bno}"
        elif obj["kind"] in ("heading?", "figtitle") or obj.get("para_start"):
            bno += 1
    res = {"page": page, "H": H, "em": em, "left": left, "lines": [{k: v for k, v in l.items() if k != "words"} for l in lines],
           "figures": figures}
    write_json(book.d("layout") / f"{pid(page)}.json", res)
    _draft(book, page, res)
    return {"lines": len(lines), "figures": len(figures), "headings?": sum(l["kind"] == "heading?" for l in lines)}


def _draft(book: Book, page: int, res: dict):
    ch = book.chapter_of(page)
    out = [f"# {pid(page)} 검수 초안  (장: {ch['id'] + ' ' + ch['title'] if ch else '-'})", ""]
    if res.get("empty"):
        out.append("(OCR 결과 없음 — 빈 쪽 또는 그림만 있는 쪽)")
    for f in res.get("figures", []):
        out.append(f"[도표 후보 {f['id']}] bbox={f['bbox']} 내부 줄={','.join(f['lines']) or '-'} "
                   f"연결={','.join(f.get('attached', [])) or '-'}")
    if res.get("figures"):
        out.append("")
    out.append("표시: ¶=문단 시작  H?=소제목 후보  F=도표 내부  FT=도표 제목  FN=주·출처  C=캡션  !=저신뢰 단어")
    out.append("")
    from .assemble import join_space
    ls = res.get("lines", [])
    jm = {}
    for a, b in zip(ls, ls[1:]):
        if a["kind"] == "body" and b["kind"] == "body" and not b.get("para_start"):
            jm[a["id"]] = " ⌴" if join_space(a["text"], b["text"]) else " ⌇"
    out.insert(-1, "줄 끝 표시: ⌴=다음 줄과 띄어 씀, ⌇=붙여 씀 (자동 판단, 틀리면 review의 join으로 고침)")
    tag = {"body": "  ", "title": "T ", "heading?": "H?", "fig": "F ", "figtitle": "FT", "fignote": "FN", "caption": "C "}
    for l in res.get("lines", []):
        mark = "¶" if l.get("para_start") else " "
        low = f"  ! {' '.join(l['low_words'])}" if l.get("low_words") else ""
        out.append(f"{l['id']} {tag.get(l['kind'], '  ')}{mark} | {l['text']}{jm.get(l['id'], '')}{low}")
    (book.d("draft") / f"{pid(page)}.md").write_text("\n".join(out) + "\n")
