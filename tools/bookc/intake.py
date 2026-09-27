"""인테이크: 원본 페이지 이미지 추출, 잉크 프로파일, 장 구분 검출, manifest 작성."""
from __future__ import annotations
import re, subprocess, os
from pathlib import Path
import pymupdf
from PIL import Image
from .common import Book, pid, sha1, MODELS_DIR, write_json

CHAPTER_RE = re.compile(r"^\s*(제\s*(\d+)\s*[장부]|서문|서장|들어가며|머리말|프롤로그|마치며|맺음말|나가며|에필로그|종장|후기)")


def extract_pages(book: Book, pdf: Path) -> int:
    """PDF 각 쪽의 원본 이미지를 재압축 없이 꺼낸다. 이미지가 없는 쪽은 144dpi로 렌더링."""
    out = book.d("pages")
    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc, start=1):
        dst_jpg = out / f"{pid(i)}.jpg"
        if dst_jpg.exists():
            continue
        imgs = page.get_images(full=True)
        if len(imgs) == 1:
            x = doc.extract_image(imgs[0][0])
            ext = "jpg" if x["ext"] in ("jpeg", "jpg") else x["ext"]
            (out / f"{pid(i)}.{ext}").write_bytes(x["image"])
        else:
            page.get_pixmap(dpi=144, colorspace=pymupdf.csGRAY).save(out / f"{pid(i)}.png")
    return len(doc)


def page_image(book: Book, page: int) -> Path:
    for ext in ("jpg", "png", "jpeg"):
        p = book.work / "pages" / f"{pid(page)}.{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(page)


def ink_ratio(img_path: Path) -> float:
    im = Image.open(img_path).convert("L")
    im.thumbnail((430, 490))
    px = im.getdata()
    return sum(1 for v in px if v < 128) / len(px) * 100


def quick_ocr(img: Path, psm: int = 6) -> str:
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    r = subprocess.run(["tesseract", str(img), "-", "--tessdata-dir", str(MODELS_DIR), "-l", "kor", "--psm", str(psm)],
                       capture_output=True, text=True, env=env)
    return r.stdout


def detect_structure(book: Book, n_pages: int) -> dict:
    ink = [round(ink_ratio(page_image(book, p)), 2) for p in range(1, n_pages + 1)]
    # 1) 장 표지 후보: 잉크가 비슷한 쪽이 두 번 연속(표지 + 간지)
    cands = [p for p in range(1, n_pages) if 8 < ink[p - 1] < 25 and abs(ink[p - 1] - ink[p]) < 1.5]
    heads = []
    for p in cands:
        txt = quick_ocr(page_image(book, p))
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        if lines and CHAPTER_RE.match(re.sub(r"\s+", "", lines[0])):
            label = re.sub(r"\s+", "", lines[0])
            title = " ".join(lines[1:])
            heads.append({"page": p, "label": label, "title": title.strip()})
    # 2) 앞부분: 첫 장 표지 전까지, 본문이 시작되는 쪽 찾기 (글자가 많은 첫 쪽)
    first_head = heads[0]["page"] if heads else n_pages
    body_start, preface_title = None, None
    for p in range(1, first_head):
        txt = quick_ocr(page_image(book, p))
        first = re.sub(r"\s+", "", next((l for l in txt.splitlines() if l.strip()), ""))
        if CHAPTER_RE.match(first) and len(re.sub(r"\s", "", txt)) > 300:
            body_start, preface_title = p, first
            break
    chapters = []
    if body_start and body_start < first_head:
        chapters.append({"id": "00", "label": preface_title, "title": preface_title, "pages": [body_start, first_head - 1]})
    # 3) 끝: 잉크가 거의 없는 마지막 쪽들 제외
    last = n_pages
    while last > 1 and ink[last - 1] < 0.5:
        last -= 1
    for i, h in enumerate(heads):
        end = heads[i + 1]["page"] - 1 if i + 1 < len(heads) else last
        m = re.match(r"제(\d+)[장부]", h["label"])
        cid = f"{int(m.group(1)):02d}" if m else f"{len(chapters):02d}"
        chapters.append({"id": cid, "label": h["label"], "title": h["title"] or h["label"],
                         "pages": [h["page"], end], "title_pages": [h["page"], h["page"] + 1]})
    for ch in chapters:
        slug = re.sub(r"[^\w가-힣]+", "_", ch["title"]).strip("_")[:40]
        ch["slug"] = f'{ch["id"]}_{slug}'
    return {"ink": ink, "chapters": chapters, "front_matter": [1, (body_start or 1) - 1],
            "review_needed": ["마지막 장의 끝 쪽(후기·역자 후기·판권 포함 여부)을 확인하세요."]}


def run(book: Book, pdf: Path, meta: dict):
    n = extract_pages(book, pdf)
    st = detect_structure(book, n)
    m = book.manifest
    meta = {"title": re.sub(r"\s*\(.*?\)\s*$", "", pdf.stem), **meta}
    m.update({"book": meta, "pdf": {"name": pdf.name, "sha1": sha1(pdf), "pages": n},
              "chapters": st["chapters"], "front_matter": st["front_matter"],
              "review_needed": st["review_needed"],
              "settings": {"ocr": {"engine": "tesseract", "model": "tessdata_fast(kor)", "psm": 4,
                                   "omp_thread_limit": 1}}})
    write_json(book.work / "ink.json", st["ink"])
    book.set_status("intake", done=True, pages=n, chapters=len(st["chapters"]))
    return m
