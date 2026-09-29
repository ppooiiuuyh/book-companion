"""초벌 OCR: Tesseract(kor, psm4, 1스레드) 쪽 단위 병렬 → 줄 단위 JSON."""
from __future__ import annotations
import csv, io, os, subprocess, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from .common import Book, pid, MODELS_DIR, write_json, read_json, tess_lang_args
from .intake import page_image


def tesseract_txt_tsv(img, psm=4, lang="kor") -> tuple[str, str]:
    """한 번의 실행으로 txt(띄어쓰기 정확)와 tsv(위치·신뢰도)를 함께 받는다."""
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "o")
        subprocess.run(["tesseract", str(img), base, *tess_lang_args(lang),
                        "--psm", str(psm), "txt", "tsv"], capture_output=True, env=env)
        return (open(base + ".txt", encoding="utf-8").read(), open(base + ".tsv", encoding="utf-8").read())


def attach_text(lines: list[dict], txt: str) -> int:
    """TSV 줄(출력 순서)과 txt 줄을 짝지어 txt의 띄어쓰기를 쓴다. 짝이 안 맞는 줄 수를 돌려준다."""
    tl = [l.strip() for l in txt.splitlines() if l.strip()]
    bad = 0
    for i, l in enumerate(lines):
        cand = tl[i] if i < len(tl) else None
        if cand is not None and cand.replace(" ", "") == l["text"].replace(" ", ""):
            l["text"] = cand
        else:
            bad += 1  # 폴백: 단어 간격으로 띄어쓰기 추정
            ws = l["words"]; hs = sorted(w["b"][3] - w["b"][1] for w in ws); h = hs[len(hs) // 2] if hs else 30
            out = ws[0]["t"]
            for a, b in zip(ws, ws[1:]):
                out += (" " if b["b"][0] - a["b"][2] > 0.28 * h else "") + b["t"]
            l["text"] = out
    return bad


def parse_tsv(tsv: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE))
    lines, cur, key = [], None, None
    for r in rows:
        if r["level"] != "5":
            continue
        k = (r["block_num"], r["par_num"], r["line_num"])
        t = (r.get("text") or "").strip()
        if not t:
            continue
        x, y, w, h, c = (int(r["left"]), int(r["top"]), int(r["width"]), int(r["height"]), float(r["conf"]))
        if k != key:
            cur = {"words": [], "block": int(r["block_num"]), "par": int(r["par_num"])}
            lines.append(cur)
            key = k
        cur["words"].append({"t": t, "b": [x, y, x + w, y + h], "c": round(c, 1)})
    out = []
    for i, l in enumerate(lines, 1):
        ws = l["words"]
        x0 = min(w["b"][0] for w in ws); y0 = min(w["b"][1] for w in ws)
        x1 = max(w["b"][2] for w in ws); y1 = max(w["b"][3] for w in ws)
        out.append({"id": f"L{i:02d}", "text": " ".join(w["t"] for w in ws), "bbox": [x0, y0, x1, y1],
                    "conf": round(sum(w["c"] for w in ws) / len(ws), 1),
                    "low_words": [w["t"] for w in ws if w["c"] < 60],
                    "block": l["block"], "par": l["par"], "words": ws})
    return out


def finalize(lines: list[dict]) -> list[dict]:
    # 세로 위치 순서로 재정렬 후 번호 재부여
    lines.sort(key=lambda l: (l["bbox"][1], l["bbox"][0]))
    for i, l in enumerate(lines, 1):
        l["id"] = f"L{i:02d}"
    return lines


def ocr_page(book: Book, page: int, force=False) -> dict:
    dst = book.d("ocr") / f"{pid(page)}.json"
    if dst.exists() and not force:
        return read_json(dst)
    t = time.time()
    txt, tsv = tesseract_txt_tsv(page_image(book, page), book.manifest["settings"]["ocr"]["psm"], book.manifest["settings"]["ocr"].get("lang", "kor"))
    lines = parse_tsv(tsv)
    bad = attach_text(lines, txt)
    lines = finalize(lines)
    res = {"page": page, "lines": lines, "unpaired": bad, "sec": round(time.time() - t, 2)}
    write_json(dst, res)
    return res


def run(book: Book, pages: list[int], workers: int | None = None, force=False):
    workers = workers or os.cpu_count() or 2
    t = time.time()
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(lambda p: ocr_page(book, p, force), pages))
    book.set_status("ocr", done_pages=sorted(set(book.manifest.get("status", {}).get("ocr", {}).get("done_pages", []) + pages)),
                    last_run_sec=round(time.time() - t, 1), workers=workers)
    return res
