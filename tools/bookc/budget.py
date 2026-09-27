"""분량·토큰 추정 리포트. 계수는 실측으로 보정한다(파이썬 len = 글자 수)."""
from __future__ import annotations
import re
from .common import Book, read_json

TOKENS_PER_CHAR = (0.6, 0.9)  # 한국어 1자당 토큰(추정 범위). 실측 시 갱신.


def run(book: Book) -> str:
    rows, tot_ocr, tot_src = [], 0, 0
    for ch in book.manifest["chapters"]:
        p0, p1 = ch["pages"]
        ocr = sum(len(l["text"]) for p in range(p0, p1 + 1)
                  for l in (read_json(book.work / "ocr" / f"p{p:03d}.json", {"lines": []}) or {"lines": []})["lines"])
        src = book.root / ch["slug"] / "source.md"
        s = len(src.read_text()) if src.exists() else 0
        tot_ocr += ocr; tot_src += s
        rows.append(f"| {ch['id']} | {ch['title'][:24]} | {p0}–{p1} | {ocr:,} | {s:,} |")
    lo, hi = TOKENS_PER_CHAR
    out = ["| 장 | 제목 | 쪽 | OCR 글자 수 | source.md 글자 수 |", "|---|---|---|---|---|"] + rows
    out.append(f"| 합계 | | | {tot_ocr:,} | {tot_src:,} |")
    out.append("")
    out.append(f"원문 전체(OCR 기준) 추정 토큰: {int(tot_ocr * lo):,} – {int(tot_ocr * hi):,} (1자당 {lo}–{hi} 가정)")
    return "\n".join(out)
