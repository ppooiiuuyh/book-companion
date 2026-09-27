"""교정(review)에서 모은 용어를 glossary.md로 정리. 첫 등장 쪽과 등장 장을 붙인다."""
from __future__ import annotations
import re
from .common import Book, pid, read_json


def run(book: Book) -> str:
    terms: dict[str, dict] = {}
    for ch in book.manifest["chapters"]:
        for p in range(ch["pages"][0], ch["pages"][1] + 1):
            rev = read_json(book.work / "review" / f"{pid(p)}.json", {}) or {}
            for g in rev.get("glossary", []):
                t = terms.setdefault(g["term"], {"note": g.get("note", ""), "first": p, "chapters": []})
                if not t["note"] and g.get("note"):
                    t["note"] = g["note"]
    # 등장 장: source.md 본문에서 검색
    for ch in book.manifest["chapters"]:
        src = book.root / ch["slug"] / "source.md"
        if not src.exists():
            continue
        body = re.sub(r"<!--.*?-->", "", src.read_text())
        for term, t in terms.items():
            if term in body:
                t["chapters"].append(ch["id"])
    lines = ["---", f"book: {book.manifest['book'].get('title')}", "layer: study",
             "note: 교정 중 Claude가 정리한 용어. 뜻풀이는 요약이므로 원문은 첫 등장 쪽을 확인할 것", "---", "",
             "# 용어집", "", "| 용어 | 뜻 (요약) | 첫 등장 | 등장 장 |", "|---|---|---|---|"]
    for term in sorted(terms, key=lambda s: s):
        t = terms[term]
        lines.append(f"| {term} | {t['note']} | {pid(t['first'])} | {', '.join(t['chapters'])} |")
    (book.root / "glossary.md").write_text("\n".join(lines) + "\n")
    return f"glossary.md: {len(terms)} terms"
