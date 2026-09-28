"""단계 상태·선행 조건·재개 지점 판단, 그리고 기기 동기화용 상태 묶음(pack/unpack)."""
from __future__ import annotations
import re, tarfile
from pathlib import Path
from .common import Book, pid, read_json

STAGES = {
    "intake":     {"no": 1, "name": "인테이크(추출·구조 검출·초벌 OCR)", "requires": []},
    "parse":      {"no": 2, "name": "파싱(원본 대조 교정·조립)", "requires": ["intake"]},
    "research":   {"no": 3, "name": "조사(리뷰·비평)", "requires": ["intake"]},
    "read":       {"no": 4, "name": "통독(메모·장/절 요약)", "requires": ["parse", "research"]},
    "synthesize": {"no": 5, "name": "종합(대조·index)", "requires": ["read"]},
    "insight":    {"no": 6, "name": "인사이트(핵심·반박 정리)", "requires": ["synthesize"]},
    "review":     {"no": 7, "name": "리뷰(서점·비평·기록)", "requires": ["insight"]},
}
# 동기화에서 제외할 것(다시 만들 수 있는 것)
REGEN = {"pages", "layout", "draft", "final"}


def body_chapters(book: Book) -> list[dict]:
    return [c for c in book.manifest.get("chapters", []) if not c.get("back")]


def content_pages(book: Book, ch: dict) -> list[int]:
    tp = set(ch.get("title_pages", []))
    return [p for p in range(ch["pages"][0], ch["pages"][1] + 1) if p not in tp]


def progress(book: Book) -> dict:
    m = book.manifest
    st = m.get("status", {})
    out = {}
    n = m.get("pdf", {}).get("pages", 0)
    ocr_done = len(st.get("ocr", {}).get("done_pages", []))
    out["intake"] = {"done": bool(st.get("intake", {}).get("done")) and n > 0 and ocr_done >= n
                     and bool(st.get("intake", {}).get("structure_confirmed")),
                     "detail": f"OCR {ocr_done}/{n}쪽, 구조 확인 {'완료' if st.get('intake', {}).get('structure_confirmed') else '미완료'}"}
    chs = m.get("chapters", [])
    per = {}
    for ch in chs:
        pages = content_pages(book, ch)
        rev = sum(1 for p in pages if (book.work / "review" / f"{pid(p)}.json").exists())
        per[ch["id"]] = {"reviewed": rev, "pages": len(pages),
                         "assembled": st.get("parse", {}).get("chapters", {}).get(ch["id"]) == "done"}
    tot = sum(v["pages"] for v in per.values()); rv = sum(v["reviewed"] for v in per.values())
    out["parse"] = {"done": bool(chs) and all(v["assembled"] and v["reviewed"] == v["pages"] for v in per.values()),
                    "detail": f"교정 {rv}/{tot}쪽, 조립 완료 {sum(v['assembled'] for v in per.values())}/{len(per)}장",
                    "chapters": per}
    r = st.get("research", {})
    out["research"] = {"done": bool(r.get("done")), "detail": ", ".join(r.get("files", [])) or "없음"}
    rd = st.get("read", {}).get("chapters_done", [])
    sd = st.get("read", {}).get("study_done", [])
    bc = [c["id"] for c in body_chapters(book)]
    out["read"] = {"done": bool(bc) and all(c in rd and c in sd for c in bc),
                   "detail": f"요약(1차) {len([c for c in bc if c in sd])}/{len(bc)}장, 통독(2차) {len([c for c in bc if c in rd])}/{len(bc)}장",
                   "next": next((c for c in bc if c not in rd), None)}
    out["synthesize"] = {"done": bool(st.get("synthesize", {}).get("done")),
                         "detail": "완료" if st.get("synthesize", {}).get("done") else "미완료"}
    ins = st.get("insight", {})
    out["insight"] = {"done": bool(ins.get("done")),
                      "detail": "완료" if ins.get("done") else ("insights.md 있음(미확정)" if (book.root / "insights.md").exists() else "미완료")}
    rv = st.get("review", {})
    rvd = book.root / "reviews"
    have = [k for k in ("store", "critical", "log") if (rvd / f"{k}.md").exists()]
    out["review"] = {"done": bool(rv.get("done")), "detail": ("완료 · " if rv.get("done") else "") + (f"{len(have)}/3편" if have else "미완료")}
    return out


def can_run(book: Book, stage: str) -> tuple[bool, str]:
    if stage not in STAGES:
        return False, f"알 수 없는 단계: {stage}"
    if stage == "intake":
        return True, "실행 가능"
    if not book.manifest_path.exists():
        return False, "이 책은 아직 1단계(인테이크)를 시작하지 않았습니다. 먼저 /bookc-1-intake 를 실행하세요."
    pr = progress(book)
    missing = [s for s in STAGES[stage]["requires"] if not pr[s]["done"]]
    if missing:
        lines = [f"현재 {STAGES[stage]['no']}단계({STAGES[stage]['name']})는 실행할 수 없습니다. 선행 단계가 끝나지 않았습니다:"]
        for s in missing:
            lines.append(f"- {STAGES[s]['no']}단계 {STAGES[s]['name']}: {pr[s]['detail']} → /bookc-{STAGES[s]['no']}-{s}")
        return False, "\n".join(lines)
    return True, "실행 가능"


def next_action(book: Book) -> str:
    if not book.manifest_path.exists():
        return "intake"
    pr = progress(book)
    for s in STAGES:
        if not pr[s]["done"]:
            ok, _ = can_run(book, s)
            if ok:
                return s
    return "done"


def report(book: Book) -> str:
    title = book.manifest.get("book", {}).get("title", book.root.name)
    pr = progress(book) if book.manifest_path.exists() else None
    lines = [f"# {title} — 진행 상태", "", "| 단계 | 상태 | 내용 |", "|---|---|---|"]
    for s, info in STAGES.items():
        if pr is None:
            lines.append(f"| {info['no']} {info['name']} | 미시작 | |")
            continue
        ok, _ = can_run(book, s)
        state = "완료" if pr[s]["done"] else ("진행 가능" if ok else "대기(선행 단계 필요)")
        lines.append(f"| {info['no']} {info['name']} | {state} | {pr[s]['detail']} |")
    na = next_action(book)
    if na == "done":
        lines += ["", "다음 할 일: 모든 단계 완료 → /bookc-open 으로 책을 열어 대화"]
    else:
        lines += ["", f"다음 할 일: {STAGES[na]['no']}단계 {STAGES[na]['name']} → /bookc-{STAGES[na]['no']}-{na}"]
    if pr:
        lines += ["", "| 장 | 교정 | 조립 |", "|---|---|---|"]
        for cid, v in pr["parse"]["chapters"].items():
            lines.append(f"| {cid} | {v['reviewed']}/{v['pages']} | {'✓' if v['assembled'] else ''} |")
    return "\n".join(lines)


def pack(book: Book, dst: Path) -> Path:
    """기기로 보낼(또는 기기에서 받아 올) 보존 상태를 tar.gz 하나로 묶는다."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dst, "w:gz") as tf:
        for p in sorted(book.root.rglob("*")):
            rel = p.relative_to(book.root)
            parts = rel.parts
            if p.is_dir():
                continue
            if parts[0] == "_work" and (len(parts) > 1 and parts[1] in REGEN):
                continue
            if p.suffix == ".tgz":
                continue
            tf.add(p, arcname=str(rel))
    return dst


def unpack(book: Book, src: Path) -> int:
    book.root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(src, "r:gz") as tf:
        members = [m for m in tf.getmembers() if not m.name.startswith(("/", ".."))]
        tf.extractall(book.root, members=members)
    if hasattr(book, "_m"):
        del book._m
    return len(members)


def find_book(books_dir: Path, pdf_name: str, pdf_sha1: str | None = None) -> str | None:
    """이미 만든 책 폴더 중 같은 PDF(sha1 또는 파일명)로 만든 것을 찾아 폴더 이름을 돌려준다."""
    for mf in sorted(books_dir.glob("*/_work/manifest.json")):
        m = read_json(mf, {})
        if pdf_sha1 and m.get("pdf", {}).get("sha1") == pdf_sha1:
            return mf.parent.parent.name
        if m.get("pdf", {}).get("name") == pdf_name:
            return mf.parent.parent.name
    return None


RESEARCH_PARTS = {
    "bookstore": "국내 서점(교보문고·예스24·알라딘) 책 소개·출판사 서평·독자 리뷰",
    "blog": "블로그·후기(네이버 블로그·브런치·티스토리 등) 서로 다른 관점 5–10개",
    "press": "신문 서평·칼럼·인터뷰·논문·인용, 저자 경력과 이 책의 위치",
    "origin": "원서 반응(원어 검색: 출간 당시 반향, 이후 평가, 후속작·반론)",
}


def notes_chapter(book: Book) -> str | None:
    r = book.manifest.get("roles", {}).get("notes")
    if r:
        return str(r)
    for c in book.manifest.get("chapters", []):
        if c.get("back") and re.sub(r"\s", "", c.get("label", "")) in ("주석", "미주", "옮긴이주", "역주"):
            return c["id"]
    return None


def ready(book: Book) -> list[dict]:
    """지금 바로 시작할 수 있는 작업 목록(우선순위 순). /bookc 전체 실행의 파동(wave) 스케줄링용.
    kind: parse | research | research-merge | study | read"""
    if not book.manifest_path.exists() or not progress(book)["intake"]["done"]:
        return []
    pr = progress(book)
    st = book.manifest.get("status", {})
    rd = st.get("read", {}).get("chapters_done", [])
    sd = st.get("read", {}).get("study_done", [])
    per = pr["parse"]["chapters"]
    parsed = lambda cid: per[cid]["assembled"] and per[cid]["reviewed"] == per[cid]["pages"]
    tasks = []
    nc = notes_chapter(book)
    notes_ready = nc is None or parsed(nc)
    # 1) 통독 2차: 순차 경로(가장 오래 걸리는 사슬)이므로 최우선. 한 번에 한 장만.
    body = [c["id"] for c in body_chapters(book)]
    nxt = next((c for c in body if c not in rd), None)
    if nxt and parsed(nxt) and nxt in sd and pr["research"]["done"]:
        tasks.append({"kind": "read", "chapter": nxt})
    # 2) 주석 장 파싱 (다른 장 조립의 전제)
    if nc and not parsed(nc):
        tasks.append({"kind": "parse", "chapter": nc, "note": "주석 장: 조립 후 bc.py notes"})
    # 3) 조사 부분들
    if not pr["research"]["done"]:
        parts = book.root / "research" / "_parts"
        left = [k for k in RESEARCH_PARTS if not (parts / f"{k}.md").exists()]
        for k in left:
            tasks.append({"kind": "research", "part": k, "scope": RESEARCH_PARTS[k]})
        if not left:
            tasks.append({"kind": "research-merge"})
    # 4) 나머지 장 파싱 (장 순서대로)
    for c in book.manifest["chapters"]:
        if c["id"] != nc and not parsed(c["id"]):
            left = [p for p in content_pages(book, c) if not (book.work / "review" / f"{pid(p)}.json").exists()]
            t = {"kind": "parse", "chapter": c["id"], "pages_left": len(left)}
            if not left:
                t["note"] = "교정 완료, 조립·lint만" + ("" if notes_ready else " (주석 장 조립 뒤)")
            tasks.append(t)
    # 5) 통독 1차(장별 요약·도표 읽기): 원문만 근거라 파싱이 끝난 장이면 병렬 가능
    for cid in body:
        if parsed(cid) and cid not in sd:
            tasks.append({"kind": "study", "chapter": cid})
    return tasks
