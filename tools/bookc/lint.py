"""품질 게이트: 쪽 커버리지, 앵커·링크·각주 무결성, OCR 잔재, 용어 혼동 검사."""
from __future__ import annotations
import re
from .common import Book, pid, read_json

# 여러 책에서 흔한 한국어 OCR 혼동(오류형 → 올바른 형). 책별 목록은 _work/confusions.json에 둔다.
DEFAULT_CONFUSIONS = {"사희": "사회", "별어": "벌어"}
ARTIFACT_RE = re.compile(r"[\\|※`ㅁㅠ]|[A-Za-z]{2,}")
PERCENT_RE = re.compile(r"(?<![\d.])\d{1,2}[98](?=\s?(이상|이하|정도|중|가|를|의|로|에|는|이|수준))")


def run(book: Book, chapters: list[str] | None = None) -> dict:
    m = book.manifest
    confusions = {**DEFAULT_CONFUSIONS, **(read_json(book.work / "confusions.json", {}) or {})}
    for rp in sorted((book.work / "review").glob("p*.json")):
        confusions.update((read_json(rp, {}) or {}).get("confusions", {}))
    chs = [c for c in m["chapters"] if not chapters or c["id"] in chapters]
    errors, warnings, stats = [], [], {}
    for ch in chs:
        src = book.root / ch["slug"] / "source.md"
        if not src.exists():
            errors.append(f"{ch['id']}: source.md 없음"); continue
        text = src.read_text()
        p0, p1 = ch["pages"]
        # 허용 영문: review에서 교정자가 직접 쓴 영문 단어
        allowed = set()
        unreviewed = []
        for p in range(p0, p1 + 1):
            if f"<!-- {pid(p)} -->" not in text:
                errors.append(f"{ch['id']}: {pid(p)} 앵커 누락")
            fin = read_json(book.work / "final" / f"{pid(p)}.json")
            if fin is None:
                errors.append(f"{ch['id']}: {pid(p)} 최종본 없음")
            elif not fin.get("reviewed"):
                unreviewed.append(pid(p))
            rev = read_json(book.work / "review" / f"{pid(p)}.json", {}) or {}
            blob = " ".join(str(v) for v in rev.get("fix", {}).values()) + " " + \
                " ".join(str(f.get(k, "")) for f in rev.get("figures", []) for k in ("title", "data_md", "desc")) + \
                " " + " ".join(str(n) for f in rev.get("figures", []) for n in f.get("notes", [])) + \
                " " + " ".join(rev.get("footnotes", {}).values())
            allowed |= set(re.findall(r"[A-Za-z]{2,}", blob))
        # 이미지 링크
        for link in re.findall(r"\]\((img/[^)]+)\)", text):
            if not (src.parent / link).exists():
                errors.append(f"{ch['id']}: 이미지 없음 {link}")
        # 각주
        refs = set(re.findall(r"\[\^(\w+)\](?!:)", text)); defs = set(re.findall(r"^\[\^(\w+)\]:", text, re.M))
        for r in sorted(refs - defs):
            errors.append(f"{ch['id']}: 각주 [^{r}] 정의 없음")
        # 본문만 (주석·앵커 제거) 대상 검사
        body = re.sub(r"<!--.*?-->", "", text)
        body_nolinks = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
        body_nolinks = re.sub(r"^---.*?---", "", body_nolinks, flags=re.S)
        for tok in sorted(set(ARTIFACT_RE.findall(body_nolinks)) - allowed - {"X"}):
            if tok.strip() and not tok.startswith("|"):
                warnings.append(f"{ch['id']}: OCR 잔재 의심 '{tok}'")
        if "|" in re.sub(r"^>?\s*\|.*$", "", body_nolinks, flags=re.M):
            warnings.append(f"{ch['id']}: 표 밖의 '|' 문자")
        for mt in PERCENT_RE.finditer(body_nolinks):
            warnings.append(f"{ch['id']}: % 오인식 의심 '{body_nolinks[max(0, mt.start() - 8):mt.end() + 4]}'")
        for wrong, right in confusions.items():
            n = body_nolinks.count(wrong)
            if n:
                warnings.append(f"{ch['id']}: 혼동형 '{wrong}'(→{right}) {n}회")
        unsure = body_nolinks.count("[?")
        stats[ch["id"]] = {"pages": p1 - p0 + 1, "unreviewed": unreviewed, "unsure_marks": unsure,
                          "chars": len(re.sub(r"\s", "", body_nolinks)), "footnotes": len(defs),
                          "figures": len(re.findall(r"\]\(img/", text))}
        if unreviewed:
            warnings.append(f"{ch['id']}: 미교정 쪽 {len(unreviewed)}개")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}
