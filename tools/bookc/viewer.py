"""진행 현황 페이지(progress.html)의 '책' 탭들에 넣을 데이터 모으기.

한눈에 보기: 책 정보, 한 줄 요약, 리뷰(7단계), 장별 흐름, 핵심 주장, 장 지도, 질문
인사이트: insights.md I 항목
반박·비평: insights.md R 항목, research/critiques.md, 도표 신뢰도
원문 보기: source.md 블록 텍스트(앵커 → 원문)
"""
from __future__ import annotations
import json, re
from .common import Book, pid, read_json

ANC = re.compile(r"<!-- (p\d{3}-b\d+) -->")
TAG = re.compile(r"\[(주장|근거|해석)\]\s*")


def _chapters(book: Book, body_only=False):
    for c in book.manifest.get("chapters", []):
        if body_only and c.get("back"):
            continue
        yield c


def _label(c):
    return f"{c['label']} {c['title']}" if c["title"] != c["label"] else c["label"]


def book_info(book: Book) -> dict:
    b = dict(book.manifest.get("book", {}))
    b.setdefault("pdf_pages", book.manifest.get("pdf", {}).get("pages"))
    return b


def source_blocks(book: Book) -> dict:
    """{block_id: [chapter_idx, text]} 와 장 목록. 도표 블록은 제목만."""
    blocks, order, chs = {}, [], []
    for i, c in enumerate(_chapters(book)):
        chs.append({"id": c["id"], "label": _label(c), "slug": c["slug"]})
        p = book.root / c["slug"] / "source.md"
        if not p.exists():
            continue
        text = re.sub(r"^---.*?---\s*", "", p.read_text(), flags=re.S)
        parts = ANC.split(text)
        # parts: [앞부분, id1, 본문1, id2, 본문2, ...]
        for k in range(1, len(parts), 2):
            bid, body = parts[k], parts[k + 1]
            body = re.sub(r"<!--.*?-->", "", body)
            body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
            lines = [l.strip().lstrip(">").strip() for l in body.strip().splitlines()]
            lines = [l for l in lines if l and not l.startswith("|")]
            t = " ".join(lines)
            t = re.sub(r"\*\[판독\].*", "", t).strip()
            t = re.sub(r"^#+\s*", "", t)
            if len(t) > 1400:
                t = t[:1400] + " …"
            blocks[bid] = [i, t]
            order.append(bid)
    return {"blocks": blocks, "order": order, "chapters": chs}


def chapter_flow(book: Book) -> list[dict]:
    """본문 장마다 study.md L1 요약의 앞 두 문장."""
    out = []
    for c in _chapters(book, body_only=True):
        p = book.root / c["slug"] / "study.md"
        if not p.exists():
            continue
        s = p.read_text()
        m = re.search(r"##\s*L1[^\n]*\n(.*?)(?=\n##\s|\Z)", s, re.S)
        if not m:
            continue
        body = TAG.sub("", " ".join(l.strip() for l in m.group(1).splitlines() if l.strip()))
        sents = re.split(r"(?<=[.다])\s+(?=\S)", body)
        out.append({"id": c["id"], "label": _label(c), "text": " ".join(sents[:2]).strip(),
                    "pages": c["pages"], "chars": len(re.sub(r"<!--.*?-->|\s", "", (book.root / c["slug"] / "source.md").read_text()))
                    if (book.root / c["slug"] / "source.md").exists() else 0})
    return out


def figures(book: Book) -> list[dict]:
    """source.md의 도표 + reading/NN.md '도표 읽기'의 판정(맞음/부분적/어긋남)."""
    out = []
    for c in _chapters(book, body_only=True):
        src = book.root / c["slug"] / "source.md"
        if not src.exists():
            continue
        verdict = {}
        rd = book.root / "reading" / f"{c['id']}.md"
        if rd.exists():
            sec = re.search(r"## 도표 읽기\n(.*?)(?=\n## |\Z)", rd.read_text(), re.S)
            for ln in (sec.group(1).splitlines() if sec else []):
                m = re.search(r"\((p\d{3}-b\d+)\)\s*:\s*(.*)", ln)
                if m:
                    v = next((w for w in ("어긋남", "부분적", "맞음") if w in m.group(2)[:200]), None)
                    note = re.sub(r"\*\*", "", m.group(2)).strip()
                    verdict[m.group(1)] = (v, note[:260])
        for m in re.finditer(r"^> \*\*(.+?)\*\* <!-- (p\d{3}-b\d+) -->\n> !\[[^\]]*\]\((img/[^)]+)\)", src.read_text(), re.M):
            title, bid, img = m.groups()
            v, note = verdict.get(bid, (None, ""))
            if "_photo" in img and not v:
                continue
            out.append({"id": bid, "ch": c["id"], "title": re.sub(r"\[\^\w+\]", "", title), "img": f"{c['slug']}/{img}",
                        "verdict": v or "판정 없음", "note": note})
    return out


def questions(book: Book) -> dict:
    q = {"discuss": [], "open": []}
    sy = book.root / "synthesis.md"
    if sy.exists():
        m = re.search(r"## 함께 이야기해 볼 질문\n(.*?)(?=\n## |\Z)", sy.read_text(), re.S)
        if m:
            q["discuss"] = [re.sub(r"^\s*(\d+\.|[-*])\s*", "", l).strip() for l in m.group(1).splitlines()
                            if re.match(r"^\s*(\d+\.|[-*])\s", l)]
    wl = book.root / "research" / "watchlist.md"
    if wl.exists():
        q["open"] = [re.sub(r"^\s*-\s*\[ \]\s*", "", l).strip() for l in wl.read_text().splitlines() if re.match(r"^\s*-\s*\[ \]", l)]
    ca = book.root / "reading" / "_carry.md"
    if ca.exists():
        for l in ca.read_text().splitlines():
            if "미해결" in l and re.match(r"^\s*[-*]", l):
                q["open"].append(re.sub(r"^\s*[-*]\s*", "", l).strip())
    return q


def critiques(book: Book) -> list[dict]:
    from .progress import _md_block
    p = book.root / "research" / "critiques.md"
    if not p.exists():
        return []
    text = re.sub(r"^---.*?---\s*", "", p.read_text(), flags=re.S)
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"^##\s+(.+)", ln)
        if m:
            cur = {"title": m.group(1).strip(), "lines": []}; out.append(cur); continue
        if cur is not None and not ln.startswith("# "):
            cur["lines"].append(ln)
    for c in out:
        c["html"] = _md_block([re.sub(r"^#{3,}\s*", "**", l) + ("**" if l.startswith("###") else "") for l in c.pop("lines")])
    return out


def sources_list(book: Book) -> dict:
    """research/sources.md의 [n] → 제목·URL (반박·비평 탭의 출처 배지용)."""
    p = book.root / "research" / "sources.md"
    out = {}
    if not p.exists():
        return out
    for ln in p.read_text().splitlines():
        m = re.match(r"^\s*(?:[-*]\s*)?\[?(\d+)\]?[.)]?\s+(.*)$", ln) or re.match(r"^\|\s*(\d+)\s*\|(.*)$", ln)
        if m:
            url = re.search(r"https?://[^\s)|>]+", m.group(2))
            out[m.group(1)] = {"t": re.sub(r"\s*\|\s*", " · ", re.sub(r"https?://\S+", "", m.group(2))).strip(" ·|")[:140],
                               "u": url.group(0) if url else ""}
    return out


def reviews(book: Book) -> dict | None:
    from .progress import _md_block
    d = book.root / "reviews"
    if not d.exists():
        return None
    meta = read_json(d / "meta.json", {}) or {}
    out = {"variants": [], "meta": meta}
    for key, name in (("store", "서점 리뷰"), ("critical", "비평형 서평"), ("log", "독서 기록")):
        p = d / f"{key}.md"
        if not p.exists():
            continue
        text = re.sub(r"^---.*?---\s*", "", p.read_text(), flags=re.S)
        title = ""
        m = re.match(r"^#\s+(.+)\n", text)
        if m:
            title, text = m.group(1).strip(), text[m.end():]
        paras, buf = [], []
        for ln in text.splitlines():
            if ln.startswith("## "):
                if buf: paras.append(_md_block(buf)); buf = []
                paras.append(f"<h4>{_md_block([ln[3:]])[3:-4]}</h4>")
            else:
                buf.append(ln)
        if buf: paras.append(_md_block(buf))
        body = re.sub(r"<!--.*?-->|[#*>\[\]()`]", "", text)
        out["variants"].append({"key": key, "name": name, "title": title, "html": "".join(paras),
                                "chars": len(re.sub(r"\s", "", body)), "meta": meta.get(key, {})})
    return out if out["variants"] else None


def chapter_map(book: Book, ins: dict | None, figs: list[dict], flow: list[dict]) -> list[dict]:
    """장 × (핵심 주장 수, 반박 강도 합, 도표 어긋남/부분적 수, 외부 비평 언급 수, 읽기 시간)."""
    page_ch = {}
    for c in _chapters(book, body_only=True):
        for p in range(c["pages"][0], c["pages"][1] + 1):
            page_ch[pid(p)] = c["id"]
    rows = {f["id"]: {"id": f["id"], "label": f["label"], "claims": 0, "rebut": 0.0, "figbad": 0, "figs": 0,
                      "ext": 0, "minutes": round(f["chars"] / 500)} for f in flow}
    def chs_of(html):
        return {page_ch.get(a[:4]) for a in re.findall(r'data-anc="(p\d{3}(?:-b\d+)?)"', html)} - {None}
    w = {"강": 3, "중": 2, "약": 1}
    if ins:
        claim_ch = {}
        for k in ins.get("claims", []):
            cs = chs_of(k["html"]); claim_ch[k["id"]] = cs
            for c in cs:
                if c in rows: rows[c]["claims"] += 1
        for r in ins.get("rebuttals", []):
            cs = chs_of(r["html"]) or set().union(*[claim_ch.get(t, set()) for t in r["target"]])
            for c in cs:
                if c in rows: rows[c]["rebut"] += w.get(r["strength"], 1) / max(1, len(cs))
    for f in figs:
        if f["ch"] in rows:
            rows[f["ch"]]["figs"] += 1
            if f["verdict"] in ("부분적", "어긋남"):
                rows[f["ch"]]["figbad"] += 1
    if ins:  # 외부 출처([n])를 근거로 든 반박이 걸린 장
        for r in ins.get("rebuttals", []):
            if re.search(r"\[\d+\]", r["html"]):
                for c in chs_of(r["html"]):
                    if c in rows: rows[c]["ext"] += 1
    for r in rows.values():
        r["rebut"] = round(r["rebut"], 1)
    return list(rows.values())


def collect(book: Book, ins: dict | None) -> dict:
    flow = chapter_flow(book)
    figs = figures(book)
    return {"info": book_info(book), "flow": flow, "figures": figs, "questions": questions(book),
            "critiques": critiques(book), "sources": sources_list(book), "reviews": reviews(book),
            "map": chapter_map(book, ins, figs, flow), "src": source_blocks(book), "slug": book.root.name}
