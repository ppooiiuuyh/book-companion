"""조립: 쪽 최종본 → 장별 source.md (+ img/ 크롭). 줄 결합 시 띄어쓰기는 형태소 분석기로 결정."""
from __future__ import annotations
import datetime, re
from PIL import Image
from .common import Book, pid, read_json, typo
from .intake import page_image

_kiwi = None
OPEN_END = "(‘“「『[<"
CLOSE_START = ")’”」』].,?!:;%"
PUNCT_END = ",.?!)’”」』:;"


def kiwi():
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    return _kiwi


def join_space(a: str, b: str, force: str | None = None) -> str:
    """줄 a 끝과 줄 b 시작 사이에 공백을 넣을지 결정."""
    if force in ("space", "nospace"):
        return " " if force == "space" else ""
    a, b = a.rstrip(), b.lstrip()
    if not a or not b:
        return ""
    if b[0] in CLOSE_START or a[-1] in OPEN_END:
        return ""
    if b[0] in "‘“'\"「『":   # 여는 따옴표·낫표로 시작하면 앞은 띄어 쓴다
        return " "
    if a[-1] in PUNCT_END:
        return " "
    if a[-1] in "–-" or b[0] in "–-":
        return ""
    ta = " ".join(a.split()[-2:]); tb = " ".join(b.split()[:2])
    spaced = kiwi().space(ta + tb, reset_whitespace=False)
    # 경계 위치(공백 아닌 글자 수 기준)에 공백이 들어갔는지 확인
    n = len(ta.replace(" ", "")); cnt = 0
    for i, ch in enumerate(spaced):
        if ch != " ":
            cnt += 1
            if cnt == n:
                return " " if i + 1 < len(spaced) and spaced[i + 1] == " " else ""
    return ""


def para_text(block: dict) -> str:
    out = ""
    for i, (_, t) in enumerate(block["lines"]):
        if i == 0:
            out = t.rstrip() if re.match(r"^\s+[-•*]\s", t) else t.strip()
        else:
            out += join_space(out, t, block["joins"][i - 1] if i - 1 < len(block["joins"]) else None) + t.strip()
    return typo(out)


def crop_figure(book: Book, page: int, blk: dict, img_dir) -> str | None:
    if not blk.get("bbox"):
        return None
    img = Image.open(page_image(book, page)).convert("L")
    x0, y0, x1, y1 = blk["bbox"]
    pad = 12
    box = (max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad))
    c = img.crop(box)
    if c.width > 1200:
        c = c.resize((1200, int(c.height * 1200 / c.width)))
    kind = blk.get("kind", "fig")
    name = f"{blk['id']}_{kind}.png"
    img_dir.mkdir(parents=True, exist_ok=True)
    c.save(img_dir / name, optimize=True)
    return f"img/{name}"


def figure_md(book, page, blk, img_dir) -> str:
    path = crop_figure(book, page, blk, img_dir)
    kind = blk.get("kind", "fig")
    label = {"fig": "도표", "tab": "표", "photo": "사진", "illu": "삽화"}.get(kind, "도표")
    q = []
    title = typo(blk.get("title") or "", dash=False)
    if title and re.match(r"^(도표|표|그림|사진)\s*\d", title):
        head = f"**{title}**"
    else:
        head = f"**[{label}] {title}**" if title else f"**[{label}]**"
    q.append(f"{head} <!-- {blk['id']} -->")
    if path:
        q.append(f"![{title or label}]({path})")
    if blk.get("caption"):
        q.append(f"*{typo(blk['caption'])}*")
    if blk.get("data_md"):
        q.append("")
        q += blk["data_md"].strip().splitlines()
    for n in blk.get("notes", []):
        q.append("")
        q.append(typo(n))
    if blk.get("desc"):
        q.append("")
        q.append(f"*[판독] {blk['desc']}*")
    return "\n".join("> " + l if l else ">" for l in q)


def run_chapter(book: Book, cid: str) -> str:
    ch = next(c for c in book.manifest["chapters"] if c["id"] == cid)
    out_dir = book.root / ch["slug"]
    img_dir = out_dir / "img"
    p0, p1 = ch["pages"]
    body, sec = [], 0
    reviewed = 0
    heading = f"# {ch['label']} {ch['title']}" if ch["label"] != ch["title"] else f"# {ch['title']}"
    pending_para = None  # 쪽·도표를 건너 이어지는 문단

    def flush():
        nonlocal pending_para
        if pending_para is not None:
            body.append(pending_para); body.append("")
            pending_para = None

    deferred_figs = []
    footnotes = {}
    for page in range(p0, p1 + 1):
        fin = read_json(book.work / "final" / f"{pid(page)}.json")
        if fin is None:
            flush(); body.append(f"<!-- {pid(page)} --> <!-- 미처리 쪽 -->"); body.append("")
            continue
        reviewed += 1 if fin.get("reviewed") else 0
        footnotes.update(fin.get("footnotes", {}))
        if fin.get("title_page"):
            body.append(f"<!-- {pid(page)} --> <!-- 장 표지 -->"); body.append("")
            continue
        page_mark_done = False
        if not fin["blocks"]:
            flush(); body.append(f"<!-- {pid(page)} --> <!-- 빈 쪽 -->"); body.append(""); continue
        for blk in fin["blocks"]:
            t = blk["type"]
            if t == "para" and blk.get("cont") and pending_para is not None:
                txt = para_text(blk)
                sep = join_space(pending_para, txt)
                if not page_mark_done:
                    # 쪽 표시는 이어지는 문단 안, 경계 다음 첫 공백 뒤에 넣는다
                    m = re.search(r"\s", txt)
                    cut = m.start() + 1 if m else len(txt)
                    txt = txt[:cut] + f"<!-- {pid(page)} -->" + ("" if cut == len(txt) else "") + txt[cut:]
                    page_mark_done = True
                pending_para += sep + txt
                continue
            flush()
            if deferred_figs and t != "figure":
                body += deferred_figs; deferred_figs = []
            if not page_mark_done:
                body.append(f"<!-- {pid(page)} -->"); page_mark_done = True
            if t == "title":
                continue
            if t == "subheading":
                body.append(f"### {typo(blk['text'])} <!-- {blk['id']} -->"); body.append("")
            elif t == "heading":
                sec += 1
                body.append(f"## {typo(blk['text'])} <!-- §{int(cid)}.{sec} {blk['id']} -->"); body.append("")
            elif t == "figure":
                md = figure_md(book, page, blk, img_dir)
                body.append(md); body.append("")
            elif t in ("para", "note"):
                txt = para_text(blk)
                if re.match(r"^\s*(\d+\.|[-•*])\s", txt):   # 목록 항목: 앵커를 뒤에 둬야 목록으로 렌더링됨
                    pending_para = re.sub(r"^(\s*)[•*]\s", r"\1- ", txt) + f" <!-- {blk['id']} -->"
                else:
                    pending_para = f"<!-- {blk['id']} -->" + txt
                if t == "note":
                    flush()
    flush()
    # 본문에 [^n]만 있고 정의가 없으면 주석 장에서 만든 notes.json으로 채운다
    notes = read_json(book.work / "notes.json", {}) or {}
    for r in re.findall(r"\[\^(\w+)\](?!:)", "\n".join(body)):
        if r not in footnotes and r in notes:
            footnotes[r] = notes[r]
    if footnotes:
        body.append("")
        for k, v in sorted(footnotes.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0)):
            body.append(f"[^{k}]: {typo(v)}")
    fm = ["---", f"book: {book.manifest['book'].get('title')}", f"chapter: \"{cid}\"", f"title: {ch['title']}",
          f"pages: {pid(p0)}-{pid(p1)}", "layer: source",
          f"reviewed_pages: {reviewed}/{p1 - p0 + 1}",
          f"generated: {datetime.date.today().isoformat()}", "---", ""]
    text = "\n".join(fm + [heading, ""] + body).rstrip() + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "source.md").write_text(text)
    # 더 이상 참조되지 않는 도표 이미지 정리
    if img_dir.exists():
        used = set(re.findall(r"\]\(img/([^)]+)\)", text))
        for f in img_dir.iterdir():
            if f.name not in used:
                f.unlink()
    book.set_status("assemble", **{cid: {"pages": [p0, p1], "reviewed": reviewed,
                                        "chars": len(re.sub(r"<!--.*?-->", "", text))}})
    return f"{ch['slug']}/source.md  ({len(text)} chars, reviewed {reviewed}/{p1 - p0 + 1})"
