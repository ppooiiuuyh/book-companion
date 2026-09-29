"""교정 적용: layout + review(JSON) → 쪽 최종본(_work/final/pNNN.json, 블록 단위)."""
from __future__ import annotations
import re
from .common import Book, pid, read_json, write_json

LIST_RE = re.compile(r"^\s*(\d{1,2}\.|[-•*])\s")   # 1909. 같은 연도는 목록 아님


def run_page(book: Book, page: int) -> dict:
    lay = read_json(book.work / "layout" / f"{pid(page)}.json")
    rev = read_json(book.work / "review" / f"{pid(page)}.json", {})
    ch = book.chapter_of(page)
    if ch and page in ch.get("title_pages", []):
        res = {"page": page, "title_page": True, "blocks": [], "reviewed": True}
        write_json(book.d("final") / f"{pid(page)}.json", res)
        return {"title_page": True}
    lines = {l["id"]: dict(l) for l in lay["lines"]}
    order = [l["id"] for l in lay["lines"]]
    # 1) 삽입·삭제·수정
    for after, new in rev.get("insert_after", {}).items():
        idx = order.index(after) + 1 if after in order else 0
        for k, t in enumerate(new):
            nid = f"{after}{chr(97 + k)}"
            ref = lines.get(after, {})
            lines[nid] = {"id": nid, "text": t, "kind": "body", "para_start": False,
                          "bbox": ref.get("bbox", [0, 0, 0, 0]), "conf": 100}
            order.insert(idx + k, nid)
    for lid in rev.get("delete", []):
        if lid in lines:
            lines[lid]["kind"] = "drop"
    for lid, t in rev.get("fix", {}).items():
        if lid in lines:
            lines[lid]["text"] = t
            lines[lid]["fixed"] = True
    for lid, k in rev.get("kind", {}).items():
        if lid in lines and lines[lid]["kind"] != "drop":   # delete가 kind보다 우선
            lines[lid]["kind"] = k
    for lid in rev.get("para_start", []):
        if lid in lines: lines[lid]["para_start"] = True
    for lid in rev.get("no_para_start", []):
        if lid in lines: lines[lid]["para_start"] = False
    joins = rev.get("join", {})
    # 2) 도표: review가 있으면 그것을, 없으면 layout 후보를 쓴다
    figs = []
    if "figures" in rev:
        for i, f in enumerate(rev["figures"]):
            ids = f.get("lines", [])
            bbox = f.get("bbox")
            if not bbox:
                cand = [lf for lf in lay["figures"] if set(ids) & set(lf["lines"] + lf.get("attached", []))]
                boxes = [c["bbox"] for c in cand] + [lines[l]["bbox"] for l in ids if l in lines]
                bbox = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                        max(b[2] for b in boxes), max(b[3] for b in boxes)] if boxes else None
            for lid in ids:
                if lid in lines: lines[lid]["kind"] = "infig"
            y = min([lines[l]["bbox"][1] for l in ids if l in lines] + ([bbox[1]] if bbox else [10 ** 6]))
            figs.append({**f, "bbox": bbox, "y": y})
    else:
        for lf in lay["figures"]:
            att = lf.get("attached", [])
            title = " ".join(lines[l]["text"] for l in att if lines[l]["kind"] == "figtitle")
            notes = [lines[l]["text"] for l in att if lines[l]["kind"] == "fignote"]
            cap = " ".join(lines[l]["text"] for l in att if lines[l]["kind"] == "caption")
            for l in lf["lines"] + att:
                lines[l]["kind"] = "infig"
            kind = "fig" if title else "photo"
            figs.append({"kind": kind, "bbox": lf["bbox"], "title": title, "notes": notes, "caption": cap,
                         "y": min([lf["bbox"][1]] + [lines[l]["bbox"][1] for l in att])})
    # 3) 블록 구성 (세로 순서)
    items = [("line", lines[i]["bbox"][1], lines[i]) for i in order if lines[i]["kind"] not in ("drop", "infig", "fig")]
    items += [("fig", f["y"], f) for f in figs]
    items.sort(key=lambda t: t[1])
    blocks, cur, bno = [], None, 0
    for typ, _, obj in items:
        if typ == "fig":
            bno += 1
            blocks.append({"id": f"{pid(page)}-b{bno}", "type": "figure", **{k: v for k, v in obj.items() if k != "y"}})
            cur = None
            continue
        k = obj["kind"]
        if k in ("title", "heading", "heading?", "subheading"):
            bno += 1
            blocks.append({"id": f"{pid(page)}-b{bno}",
                           "type": {"title": "title", "subheading": "subheading"}.get(k, "heading"),
                           "text": obj["text"]})
            cur = None
            continue
        start = obj.get("para_start") or cur is None or LIST_RE.match(obj["text"]) or k in ("note", "list")
        if start:
            bno += 1
            cur = {"id": f"{pid(page)}-b{bno}", "type": "note" if k == "note" else "para", "lines": [],
                   "joins": [], "cont": not obj.get("para_start") and not LIST_RE.match(obj["text"])
                   and not blocks and k not in ("note",)}
            blocks.append(cur)
        elif cur["lines"]:
            cur["joins"].append(joins.get(cur["lines"][-1][0], None))
        cur["lines"].append((obj["id"], obj["text"]))
    # 쪽 끝 줄의 join(다음 쪽으로 이어지는 결합)을 문단에 남긴다
    for b in blocks:
        if b.get("lines") and joins.get(b["lines"][-1][0]):
            b["tail_join"] = joins[b["lines"][-1][0]]
    # 문단 첫 줄이 들여쓰기 없이 시작하면(=앞 쪽/앞 블록에서 이어짐) cont 표시
    for b in blocks:
        if b["type"] == "para" and b["lines"]:
            first = lines[b["lines"][0][0]]
            b["cont"] = (not first.get("para_start")) and not LIST_RE.match(first["text"])
    res = {"page": page, "blocks": blocks, "reviewed": bool(rev), "unsure": rev.get("unsure", []),
           "glossary": rev.get("glossary", []), "footnotes": rev.get("footnotes", {}), "fixed_lines": sum(1 for l in lines.values() if l.get("fixed")),
           "deleted_lines": len(rev.get("delete", []))}
    write_json(book.d("final") / f"{pid(page)}.json", res)
    return {"blocks": len(blocks), "reviewed": bool(rev), "fixed": res["fixed_lines"]}
