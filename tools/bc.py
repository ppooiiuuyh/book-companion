#!/usr/bin/env python3
"""Book Companion CLI

기계 처리
  bc.py intake    <book> --pdf X.pdf [--title --author ...] [--force]   쪽 이미지 추출 + 구조 검출
  bc.py ocr       <book> [--pages 5-25]                                 초벌 OCR (이미 된 쪽은 건너뜀)
  bc.py prepare   <book> --pages ch:02 [--pdf X.pdf]                    쪽 이미지·OCR·draft 준비(재개용)
  bc.py layout    <book> --pages ch:00,01
  bc.py apply     <book> --pages ch:00,01
  bc.py assemble  <book> --chapters 00,01
  bc.py lint      <book> --chapters 00,01
  bc.py glossary  <book>
  bc.py notes     <book> --chapters 92                                  주석 장 → _work/notes.json
  bc.py budget    <book>
  bc.py outline   <book>
상태
  bc.py status    <book>                 진행표 + 다음 할 일
  bc.py can       <book> <stage>         선행 조건 검사 (불가 시 exit 1)
  bc.py next      <book>                 다음 단계 이름
  bc.py todo      <book> parse|read      남은 장·쪽
  bc.py ready     <book>                 지금 시작할 수 있는 작업(우선순위 순, JSON 줄)
  bc.py mark      <book> <stage> [--chapters ..] [--files ..] [--undo]   stage: intake|parse|research|study|read|synthesize
  bc.py set       <book> key.path=JSON값 ...
  bc.py chapter   <book> add|edit|del <id> [label=.. title=.. pages=216-218 title_pages=216,217 back=1]
동기화
  bc.py pack      <book> <out.tgz>
  bc.py unpack    <book> <in.tgz>
  bc.py find-book <books_dir> --pdf X.pdf
"""
import argparse, json, signal, sys
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bookc.common import Book, sha1, pid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("book")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--pdf")
    ap.add_argument("--title"); ap.add_argument("--author"); ap.add_argument("--translator")
    ap.add_argument("--publisher"); ap.add_argument("--year"); ap.add_argument("--original")
    ap.add_argument("--pages")
    ap.add_argument("--chapters")
    ap.add_argument("--files")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--undo", action="store_true")
    a = ap.parse_args()
    chs = a.chapters.split(",") if a.chapters else None

    if a.cmd == "find-book":
        from bookc.state import find_book
        pdf = Path(a.pdf)
        print(find_book(Path(a.book), pdf.name, sha1(pdf) if pdf.exists() else None) or "")
        return
    book = Book(a.book)

    if a.cmd == "intake":
        from bookc import intake
        if book.manifest_path.exists() and not a.force:
            print("이미 인테이크한 책입니다(구조를 다시 검출하려면 --force).")
            n = intake.extract_pages(book, Path(a.pdf)) if a.pdf else 0
            return
        meta = {k: v for k, v in dict(title=a.title, author=a.author, translator=a.translator,
                                        publisher=a.publisher, year=a.year, original_title=a.original).items() if v}
        m = intake.run(book, Path(a.pdf), meta)
        for ch in m["chapters"]:
            print(ch["id"], ch["pages"], ch["label"], "|", ch["title"], "| 표지", ch.get("title_pages"))
    elif a.cmd == "ocr":
        from bookc import ocr
        pages = book.pages(a.pages) if a.pages else list(range(1, book.manifest["pdf"]["pages"] + 1))
        res = ocr.run(book, pages, force=a.force)
        print(f"{len(res)} pages, {book.manifest['status']['ocr']['last_run_sec']} s")
    elif a.cmd == "prepare":
        from bookc import intake, ocr, layout
        if a.pdf:
            intake.extract_pages(book, Path(a.pdf))
        pages = book.pages(a.pages)
        miss = [p for p in pages if not any((book.work / "pages" / f"{pid(p)}.{e}").exists() for e in ("jpg", "png"))]
        if miss:
            sys.exit(f"쪽 이미지 없음 {miss[:5]}… --pdf 로 PDF를 지정하세요.")
        ocr.run(book, pages)
        for p in pages:
            layout.run_page(book, p)
        print(f"준비 완료: {len(pages)}쪽 (draft: _work/draft/)")
    elif a.cmd == "layout":
        from bookc import layout
        for p in book.pages(a.pages):
            print(p, layout.run_page(book, p))
    elif a.cmd == "apply":
        from bookc import apply
        for p in book.pages(a.pages):
            print(p, apply.run_page(book, p))
    elif a.cmd == "assemble":
        from bookc import assemble
        for cid in chs:
            print(assemble.run_chapter(book, cid))
    elif a.cmd == "lint":
        from bookc import lint
        rep = lint.run(book, chs)
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        sys.exit(0 if rep["ok"] else 1)
    elif a.cmd == "glossary":
        from bookc import glossary
        print(glossary.run(book))
    elif a.cmd == "notes":
        from bookc.outline import build_notes
        n = build_notes(book, chs[0])
        print(f"notes.json: {len(n)}개 ({', '.join(list(n)[:5])} …)")
    elif a.cmd == "budget":
        from bookc import budget
        print(budget.run(book))
    elif a.cmd == "outline":
        from bookc.outline import outline
        print(outline(book))
    elif a.cmd == "status":
        from bookc.state import report
        print(report(book))
    elif a.cmd == "can":
        from bookc.state import can_run
        ok, msg = can_run(book, a.rest[0])
        print(msg)
        sys.exit(0 if ok else 1)
    elif a.cmd == "next":
        from bookc.state import next_action
        print(next_action(book))
    elif a.cmd == "todo":
        from bookc.state import progress, content_pages
        pr = progress(book)
        what = a.rest[0] if a.rest else "parse"
        if what == "parse":
            for ch in book.manifest["chapters"]:
                v = pr["parse"]["chapters"][ch["id"]]
                if v["assembled"] and v["reviewed"] == v["pages"]:
                    continue
                left = [p for p in content_pages(book, ch) if not (book.work / "review" / f"{pid(p)}.json").exists()]
                print(f"{ch['id']}\t{ch['slug']}\t남은 교정 {len(left)}쪽\t{','.join(map(str, left)) or '-'}\t"
                      f"{'조립 필요' if not v['assembled'] else ''}")
        else:
            rs = book.manifest.get("status", {}).get("read", {})
            for ch in book.manifest["chapters"]:
                if ch.get("back"):
                    continue
                need = [n for n, k in (("1차", "study_done"), ("2차", "chapters_done")) if ch["id"] not in rs.get(k, [])]
                if need:
                    print(f"{ch['id']}\t{ch['slug']}\t남은 통독 {'+'.join(need)}")
    elif a.cmd == "ready":
        from bookc.state import ready
        for t in ready(book):
            print(json.dumps(t, ensure_ascii=False))
    elif a.cmd == "mark":
        stage = a.rest[0]
        st = book.manifest.setdefault("status", {}).setdefault(stage, {})
        if stage == "intake":
            st["structure_confirmed"] = not a.undo
        elif stage == "parse":
            d = st.setdefault("chapters", {})
            for c in chs:
                if a.undo: d.pop(c, None)
                else: d[c] = "done"
        elif stage in ("read", "study"):
            st = book.manifest["status"].setdefault("read", {})
            book.manifest["status"].pop("study", None)
            d = st.setdefault("chapters_done" if stage == "read" else "study_done", [])
            for c in chs:
                if a.undo and c in d: d.remove(c)
                elif not a.undo and c not in d: d.append(c)
        elif stage in ("research", "synthesize"):
            st["done"] = not a.undo
            if a.files: st["files"] = a.files.split(",")
        book.save()
        print(json.dumps(st, ensure_ascii=False))
    elif a.cmd == "set":
        for kv in a.rest:
            k, v = kv.split("=", 1)
            try: v = json.loads(v)
            except json.JSONDecodeError: pass
            node = book.manifest
            *path, last = k.split(".")
            for key in path:
                node = node[int(key)] if isinstance(node, list) else node.setdefault(key, {})
            if isinstance(node, list): node[int(last)] = v
            else: node[last] = v
        book.save()
        print("ok")
    elif a.cmd == "chapter":
        import re
        op, cid, *kvs = a.rest
        chl = book.manifest["chapters"]
        ch = next((c for c in chl if c["id"] == cid), None)
        if op == "del":
            chl.remove(ch)
        else:
            if op == "add":
                if ch: sys.exit(f"이미 있는 장 id: {cid}")
                ch = {"id": cid, "title_pages": []}; chl.append(ch)
            for kv in kvs:
                k, v = kv.split("=", 1)
                if k == "pages": v = [int(x) for x in v.split("-")] if "-" in v else [int(v), int(v)]
                elif k == "title_pages": v = [int(x) for x in v.split(",") if x]
                elif k == "back": v = v not in ("0", "false", "")
                ch[k] = v
            ch.setdefault("label", ch.get("title", cid)); ch.setdefault("title", ch["label"])
            ch["slug"] = f'{cid}_' + re.sub(r"[^\w가-힣]+", "_", ch["title"]).strip("_")[:40]
            chl.sort(key=lambda c: c["pages"][0])
        book.save()
        for c in chl:
            print(c["id"], c["pages"], c["label"], "|", c["title"], "| 표지", c.get("title_pages"), "| back" if c.get("back") else "")
    elif a.cmd == "pack":
        from bookc.state import pack
        print(pack(book, Path(a.rest[0])))
    elif a.cmd == "unpack":
        from bookc.state import unpack
        print(unpack(book, Path(a.rest[0])), "files")
    else:
        ap.error("unknown cmd")


if __name__ == "__main__":
    main()
