"""책 개요: 장 목록(쪽 범위·상태)과 각 source.md의 절 제목, 주석 장에서 notes.json 추출."""
from __future__ import annotations
import re
from .common import Book, pid, read_json, write_json


def outline(book: Book, with_sections: bool = True) -> str:
    m = book.manifest
    off = m.get("printed_page_offset")
    out = [f"# {m['book'].get('title')} 개요", "", "| id | 장 | 쪽(PDF) | 폴더 | 뒷부분 |", "|---|---|---|---|---|"]
    for c in m["chapters"]:
        rng = f"{c['pages'][0]}–{c['pages'][1]}"
        out.append(f"| {c['id']} | {c['label']} {c['title'] if c['title'] != c['label'] else ''} | {rng} | {c['slug']} | {'✓' if c.get('back') else ''} |")
    if off is not None:
        out += ["", f"인쇄 쪽 번호 = PDF 쪽 번호 + {off}"]
    if with_sections:
        for c in m["chapters"]:
            src = book.root / c["slug"] / "source.md"
            if not src.exists():
                continue
            hs = re.findall(r"^(##+) (.*?) <!-- (§[\d.]+ )?(p\d+-b\d+) -->", src.read_text(), re.M)
            if hs:
                out += ["", f"## {c['id']} {c['title']}"]
                for lv, t, sec, bid in hs:
                    out.append(f"{'  ' * (len(lv) - 2)}- {sec or ''}{t}  ({bid})")
    return "\n".join(out)


def build_notes(book: Book, cid: str) -> dict:
    """주석 장 source.md의 'N. 내용' 항목을 _work/notes.json {N: 내용}으로 만든다."""
    ch = next(c for c in book.manifest["chapters"] if c["id"] == cid)
    text = (book.root / ch["slug"] / "source.md").read_text()
    text = re.sub(r"<!-- p\d+ -->", "", text)
    notes = {}
    for mt in re.finditer(r"^(\d+)\.\s+(.*?)\s*(<!-- p\d+-b\d+ -->)?\s*$", text, re.M):
        notes[mt.group(1)] = re.sub(r" {2,}", " ", re.sub(r"\s*<!--.*?-->\s*", " ", mt.group(2))).strip()  # 쪽을 넘는 항목에 끼어든 앵커 제거
    write_json(book.work / "notes.json", notes)
    book.manifest.setdefault("roles", {})["notes"] = cid
    book.save()
    return notes
