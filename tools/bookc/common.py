"""공용 유틸: 경로, manifest, 정규화."""
from __future__ import annotations
import json, os, re, unicodedata, hashlib, datetime
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = TOOLS_DIR.parent
MODELS_DIR = Path(os.environ.get("BOOKC_TESSDATA", PROJECT_DIR / "models" / "tessdata"))


def pid(page: int) -> str:
    return f"p{page:03d}"


class Book:
    """책 하나의 작업 폴더. books/<slug>/ 아래에 _work/와 장 폴더가 생긴다."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.work = self.root / "_work"
        self.manifest_path = self.work / "manifest.json"

    # 하위 경로
    def d(self, name: str) -> Path:
        p = self.work / name
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def manifest(self) -> dict:
        if not hasattr(self, "_m"):
            self._m = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}
        return self._m

    def save(self):
        self.work.mkdir(parents=True, exist_ok=True)
        self.manifest["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=1))

    def set_status(self, step: str, **kw):
        st = self.manifest.setdefault("status", {}).setdefault(step, {})
        st.update(kw)
        self.save()

    def chapter_of(self, page: int) -> dict | None:
        for ch in self.manifest.get("chapters", []):
            if ch["pages"][0] <= page <= ch["pages"][1]:
                return ch
        return None

    def pages(self, spec: str | None = None) -> list[int]:
        """'5-25,30' 또는 'ch:00,01' 또는 None(본문 전체)"""
        m = self.manifest
        if not spec:
            return [p for ch in m["chapters"] for p in range(ch["pages"][0], ch["pages"][1] + 1)]
        if spec.startswith("ch:"):
            ids = spec[3:].split(",")
            return [p for ch in m["chapters"] if ch["id"] in ids for p in range(ch["pages"][0], ch["pages"][1] + 1)]
        out = []
        for part in spec.split(","):
            if "-" in part:
                a, b = part.split("-")
                out += list(range(int(a), int(b) + 1))
            else:
                out.append(int(part))
        return out


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_compare(s: str) -> str:
    """채점·비교용 정규화: 공백 제거, 기호 통일."""
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[‘’‚‛`´′']", "'", s)
    s = re.sub(r"[“”„\"]", '"', s)
    s = re.sub(r"[『』「」《》〈〉]", '"', s)
    s = re.sub(r"[–—−‐~〜]", "-", s)
    return re.sub(r"\s+", "", s)


def read_json(p: Path, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def typo(s: str, dash: bool = True) -> str:
    """책의 조판 기호로 통일: 작은따옴표(위치로 여닫음 판단), 가운뎃점, 숫자 범위 대시."""
    s = s.replace("ㆍ", "·")
    if dash:
        s = re.sub(r"(?<![\d\-–])(\d{1,4})\s?-\s?(\d{1,4})(?![\d\-–])", r"\1–\2", s)  # 범위만(ISBN·등록번호 같은 연쇄·긴 번호는 제외)
    out = []
    for i, ch in enumerate(s):
        if ch in "'\"‘’":
            prev = s[i - 1] if i > 0 else " "
            out.append("‘" if (prev.isspace() or prev in "(「『[<‘“—–·/") else "’")
        else:
            out.append(ch)
    return "".join(out)
