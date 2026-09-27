"""실행 로그(_work/runlog.jsonl)와 진행 현황 대시보드(progress.html).

bc.py log <book> <event> k=v ...  로 이벤트를 남기면 progress.html을 다시 그린다.
event: run-start | run-end | stage-start | stage-end | wave-start | wave-end | task-start | task-end | note
"""
from __future__ import annotations
import datetime, html, json, os, shutil
from pathlib import Path
from .common import Book, pid

# 전체 진행률 가중치(작업량 비례 추정)
WEIGHTS = {"intake": 5, "parse": 50, "research": 10, "study": 15, "read": 15, "synthesize": 5}
STAGE_LABEL = {"intake": "1 인테이크", "parse": "2 파싱", "research": "3 조사",
               "study": "4a 통독 1차(요약)", "read": "4b 통독 2차(메모)", "synthesize": "5 종합"}


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def read_log(book: Book) -> list[dict]:
    p = book.work / "runlog.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def metrics(book: Book) -> dict:
    """현재 상태 수치(진행률 계산·누적 그래프용)."""
    from .state import progress, body_chapters, RESEARCH_PARTS
    if not book.manifest_path.exists():
        return {"overall": 0, "stages": {}}
    pr = progress(book)
    st = book.manifest.get("status", {})
    per = pr["parse"]["chapters"]
    pages_tot = sum(v["pages"] for v in per.values()) or 1
    pages_rev = sum(v["reviewed"] for v in per.values())
    ch_tot = len(per) or 1
    ch_asm = sum(1 for v in per.values() if v["assembled"])
    body = [c["id"] for c in body_chapters(book)]
    rd = st.get("read", {})
    parts_dir = book.root / "research" / "_parts"
    parts = sum(1 for k in RESEARCH_PARTS if (parts_dir / f"{k}.md").exists())
    n = book.manifest.get("pdf", {}).get("pages", 0) or 1
    ocr = len(st.get("ocr", {}).get("done_pages", []))
    s = {
        "intake": {"done": pr["intake"]["done"], "value": min(ocr, n) / n * 0.9 + (0.1 if st.get("intake", {}).get("structure_confirmed") else 0),
                   "text": pr["intake"]["detail"]},
        "parse": {"done": pr["parse"]["done"], "value": 0.8 * pages_rev / pages_tot + 0.2 * ch_asm / ch_tot,
                  "text": f"교정 {pages_rev}/{pages_tot}쪽 · 조립 {ch_asm}/{ch_tot}장", "pages_rev": pages_rev, "pages_tot": pages_tot},
        "research": {"done": pr["research"]["done"], "value": 1.0 if pr["research"]["done"] else parts / len(RESEARCH_PARTS) * 0.8,
                     "text": "완료" if pr["research"]["done"] else f"영역 {parts}/{len(RESEARCH_PARTS)}"},
        "study": {"done": bool(body) and all(c in rd.get("study_done", []) for c in body),
                  "value": len([c for c in body if c in rd.get("study_done", [])]) / (len(body) or 1),
                  "text": f"{len([c for c in body if c in rd.get('study_done', [])])}/{len(body)}장"},
        "read": {"done": bool(body) and all(c in rd.get("chapters_done", []) for c in body),
                 "value": len([c for c in body if c in rd.get("chapters_done", [])]) / (len(body) or 1),
                 "text": f"{len([c for c in body if c in rd.get('chapters_done', [])])}/{len(body)}장"},
        "synthesize": {"done": pr["synthesize"]["done"], "value": 1.0 if pr["synthesize"]["done"] else 0.0,
                       "text": pr["synthesize"]["detail"]},
    }
    for v in s.values():
        if v["done"]:
            v["value"] = 1.0
        v["value"] = round(min(1.0, v["value"]), 4)
    overall = sum(WEIGHTS[k] * s[k]["value"] for k in WEIGHTS) / sum(WEIGHTS.values())
    return {"overall": round(overall, 4), "stages": s, "pages_rev": pages_rev, "pages_tot": pages_tot}


def chapter_grid(book: Book) -> list[dict]:
    from .state import progress
    if not book.manifest_path.exists():
        return []
    pr = progress(book)
    rd = book.manifest.get("status", {}).get("read", {})
    rows = []
    for c in book.manifest.get("chapters", []):
        v = pr["parse"]["chapters"][c["id"]]
        rows.append({"id": c["id"], "title": f"{c['label']} {c['title']}" if c["title"] != c["label"] else c["label"],
                     "back": bool(c.get("back")), "reviewed": v["reviewed"], "pages": v["pages"],
                     "assembled": v["assembled"], "study": c["id"] in rd.get("study_done", []),
                     "read": c["id"] in rd.get("chapters_done", [])})
    return rows


def log(book: Book, event: str, **kw) -> dict:
    ev = {"ts": now_iso(), "event": event, **{k: v for k, v in kw.items() if v not in (None, "")}}
    if event == "run-start":
        ev.setdefault("run", "bookc")
        ev["run_id"] = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        book.manifest.setdefault("status", {})["current_run"] = ev["run_id"]
        book.save()
    else:
        cur = book.manifest.get("status", {}).get("current_run")
        if cur:
            ev.setdefault("run_id", cur)
    if event in ("run-start", "run-end", "wave-end", "task-end", "stage-end"):
        m = metrics(book)
        ev["overall"] = m["overall"]
        ev["pages_rev"] = m.get("pages_rev")
    if event == "run-end":
        book.manifest.get("status", {}).pop("current_run", None)
        book.save()
    book.work.mkdir(parents=True, exist_ok=True)
    with open(book.work / "runlog.jsonl", "a") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    return ev


def render(book: Book) -> Path:
    data = {
        "title": book.manifest.get("book", {}).get("title", book.root.name) if book.manifest_path.exists() else book.root.name,
        "generated": now_iso(),
        "events": read_log(book),
        "metrics": metrics(book),
        "grid": chapter_grid(book),
        "stageLabel": STAGE_LABEL,
        "weights": WEIGHTS,
        "active": bool(book.manifest.get("status", {}).get("current_run")) if book.manifest_path.exists() else False,
    }
    tpl = (Path(__file__).parent / "progress_template.html").read_text()
    out = tpl.replace("__TITLE__", html.escape(data["title"])) \
             .replace("__REFRESH__", '<meta http-equiv="refresh" content="20">' if data["active"] else "") \
             .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    dst = book.root / "progress.html"
    dst.write_text(out)
    copy_dir = os.environ.get("BOOKC_PROGRESS_COPY_DIR")
    if copy_dir:
        Path(copy_dir).mkdir(parents=True, exist_ok=True)
        c = Path(copy_dir) / f"progress_{book.root.name}_{datetime.datetime.now().strftime('%H%M%S%f')}.html"
        shutil.copy(dst, c)
        return c
    return dst
