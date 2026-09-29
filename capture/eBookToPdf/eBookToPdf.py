# /// script
# requires-python = ">=3.10,<3.15"
# dependencies = [
#     "mss>=10.2.0,<11",
#     "pynput>=1.8.2,<2",
#     "pillow>=12.3.0,<13",
#     "natsort>=8.4.0,<9",
#     "pyside6>=6.11.2,<7",
# ]
# ///
"""
eBookToPdf (개선판)
- 저장 경로 설정
- 동작 로그 (UI + 로그 파일)
- 현재 처리 중 페이지 / 진행률 표시
- 중단 (다시 시작하면 1쪽부터, 남은 데이터는 확인 후 삭제)
- 캡처 데이터는 저장 위치/_captures/<이름>/ 에 모음

실행: uv run eBookToPdf.py (필요 패키지는 이 파일 머리의 script 블록에 있어 uv가 알아서 설치)
필요 패키지: PySide6 pynput mss pillow natsort
macOS 권한: 손쉬운 사용, 입력 모니터링, 화면 기록 (실행하는 터미널/IDE에 부여). 시작할 때 확인하고, 화면 기록·손쉬운 사용이 없으면 캡처를 시작하지 않는다.
"""
import os
import sys
import glob
import threading
import traceback
import faulthandler
from datetime import datetime

# book-companion 연결: 이 파일이 book-companion/capture/eBookToPdf/에 있을 때의 경로
_HERE = os.path.dirname(os.path.abspath(__file__))
BC_PDF_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "books-pdf"))

faulthandler.enable()  # 강제 종료 시 어느 줄에서 죽었는지 터미널에 출력

import mss
import mss.tools

if sys.platform == "darwin":
    # mss는 macOS에서 기본적으로 '논리 해상도(1x)'로 캡처한다(kCGWindowImageNominalResolution).
    # Retina 화면이면 절반 해상도로 찍혀 글자가 흐려지므로, 0으로 바꿔 실제 픽셀(2x)로 캡처한다.
    import mss.darwin
    mss.darwin.IMAGE_OPTIONS = 0
import natsort
from PIL import Image
from PIL import JpegImagePlugin  # noqa: F401  일부 Pillow 버전에서 PDF 저장 시 KeyError: 'JPEG' 방지
from pynput import mouse
from pynput.keyboard import Key, Controller as KeyboardController

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QRect, QUrl
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSlider, QSpinBox, QCheckBox,
    QPlainTextEdit, QProgressBar, QFileDialog, QGroupBox, QComboBox, QScrollArea, QSizePolicy, QFrame,
    QToolButton, QMessageBox,
)

APP_VERSION = "v3 (macOS main-thread fix)"
DEFAULT_POS1 = (3, 130)      # 기본 좌측상단 좌표
DEFAULT_POS2 = (860, 1108)   # 기본 우측하단 좌표
IMG_PATTERN = "img_*.png"


def img_filename(page: int) -> str:
    return f"img_{page:04d}.png"


def list_images(img_dir: str) -> list:
    return natsort.natsorted(glob.glob(os.path.join(img_dir, IMG_PATTERN)))


# ---------------------------------------------------------------------------
# macOS 권한 확인 (화면 기록 · 손쉬운 사용 · 입력 모니터링)
# 권한은 이 파이썬이 아니라 '실행한 앱'(터미널, iTerm, VS Code 등)에 붙는다.
# ---------------------------------------------------------------------------
import ctypes
import subprocess

_HOST_APPS = {
    "com.apple.Terminal": "터미널",
    "com.googlecode.iterm2": "iTerm",
    "com.microsoft.VSCode": "Visual Studio Code",
    "com.microsoft.VSCodeInsiders": "Visual Studio Code Insiders",
    "com.todesktop.230313mzl4w4u92": "Cursor",
    "dev.warp.Warp-Stable": "Warp",
    "com.jetbrains.pycharm": "PyCharm",
    "com.jetbrains.pycharm.ce": "PyCharm CE",
    "net.kovidgoyal.kitty": "kitty",
    "io.alacritty": "Alacritty",
    "com.mitchellh.ghostty": "Ghostty",
}
_TERM_PROGRAMS = {"Apple_Terminal": "터미널", "iTerm.app": "iTerm", "vscode": "Visual Studio Code",
                  "WarpTerminal": "Warp", "ghostty": "Ghostty"}


def host_app() -> str:
    """권한을 줘야 하는 앱 이름. 번들 id → TERM_PROGRAM → 부모 프로세스의 .app 순으로 찾는다."""
    bid = os.environ.get("__CFBundleIdentifier", "")
    if bid in _HOST_APPS:
        return _HOST_APPS[bid]
    tp = os.environ.get("TERM_PROGRAM", "")
    if tp in _TERM_PROGRAMS:
        return _TERM_PROGRAMS[tp]
    try:
        pid = os.getppid()
        for _ in range(12):
            out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                                 capture_output=True, text=True).stdout.strip()
            if not out:
                break
            ppid, comm = out.split(None, 1)
            if ".app/" in comm:
                return os.path.basename(comm.split(".app/")[0])
            pid = int(ppid)
            if pid <= 1:
                break
    except Exception:
        pass
    return bid or tp or "실행한 터미널(또는 편집기) 앱"


def _fw(name):
    try:
        return ctypes.cdll.LoadLibrary(f"/System/Library/Frameworks/{name}.framework/{name}")
    except OSError:
        return None


def check_permissions() -> dict:
    """{'screen': bool|None, 'accessibility': bool|None, 'input': bool|None} — None은 확인 불가."""
    res = {"screen": None, "accessibility": None, "input": None}
    if sys.platform != "darwin":
        return res
    cg = _fw("CoreGraphics")
    if cg is not None and hasattr(cg, "CGPreflightScreenCaptureAccess"):
        cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
        res["screen"] = bool(cg.CGPreflightScreenCaptureAccess())
    ax = _fw("ApplicationServices")
    if ax is not None:
        ax.AXIsProcessTrusted.restype = ctypes.c_bool
        res["accessibility"] = bool(ax.AXIsProcessTrusted())
    io = _fw("IOKit")
    if io is not None and hasattr(io, "IOHIDCheckAccess"):
        io.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]; io.IOHIDCheckAccess.restype = ctypes.c_uint32
        v = io.IOHIDCheckAccess(1)          # kIOHIDRequestTypeListenEvent
        res["input"] = {0: True, 1: False}.get(v)   # 0 허용, 1 거부, 2 아직 묻지 않음
    return res


def request_permissions(res: dict):
    """없는 권한에 대해 macOS 요청 창을 띄운다(한 번만 뜨는 창도 있다)."""
    if res.get("screen") is False:
        cg = _fw("CoreGraphics")
        if cg is not None and hasattr(cg, "CGRequestScreenCaptureAccess"):
            cg.CGRequestScreenCaptureAccess()
    if res.get("input") is not True:
        io = _fw("IOKit")
        if io is not None and hasattr(io, "IOHIDRequestAccess"):
            io.IOHIDRequestAccess.argtypes = [ctypes.c_uint32]
            io.IOHIDRequestAccess(1)


PERM_LABELS = {"screen": ("화면 기록", "Privacy_ScreenCapture"),
               "accessibility": ("손쉬운 사용", "Privacy_Accessibility"),
               "input": ("입력 모니터링", "Privacy_ListenEvent")}
REQUIRED_PERMS = ("screen", "accessibility")   # 없으면 캡처를 시작하지 않는다
# 입력 모니터링: 좌표 클릭 감지에 쓰인다. 확인 결과가 모호할 수 있어 경고만 한다.


def make_right_key_presser():
    """→ 키를 누르는 함수를 반환. 반드시 메인 스레드에서 호출할 것.

    macOS에서 pynput 키보드 Controller는 생성 시 TIS(입력 소스) API를 호출하는데,
    이를 메인 스레드 밖에서 부르면 'trace trap'으로 강제 종료된다.
    그래서 맥에서는 Quartz로 키 이벤트를 직접 보낸다(스레드에서 호출해도 안전).
    """
    if sys.platform == "darwin":
        import Quartz  # pynput 설치 시 pyobjc-framework-Quartz가 함께 설치됨
        KEYCODE_RIGHT = 124

        def press():
            for down in (True, False):
                ev = Quartz.CGEventCreateKeyboardEvent(None, KEYCODE_RIGHT, down)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        return press

    kb = KeyboardController()  # 메인 스레드에서 생성

    def press():
        kb.press(Key.right)
        kb.release(Key.right)
    return press


# ---------------------------------------------------------------------------
# 캡처 작업 (별도 스레드)
# ---------------------------------------------------------------------------
class CaptureWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)        # (현재 페이지, 총 페이지)
    finished_capture = Signal(str, int)  # (상태: completed/stopped/error, 마지막 저장 페이지)

    def __init__(self, region, start_page, total_page, speed, img_dir,
                 focus_pos, return_pos, press_next, mouse_ctrl, countdown=3):
        super().__init__()
        # 키보드/마우스 컨트롤러는 모두 메인 스레드에서 만들어서 전달받는다
        self.press_next = press_next
        self.mouse_ctrl = mouse_ctrl
        self.region = region
        self.start_page = start_page
        self.total_page = total_page
        self.speed = speed
        self.img_dir = img_dir
        self.focus_pos = focus_pos
        self.return_pos = return_pos
        self.countdown = countdown
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        last_saved = self.start_page - 1
        try:
            m = self.mouse_ctrl

            for sec in range(self.countdown, 0, -1):
                self.log.emit(f"{sec}초 후 캡처를 시작합니다...")
                if self._stop.wait(1):
                    self.finished_capture.emit("stopped", last_saved)
                    return

            # 뷰어를 맨 앞으로 가져오기 위해 캡처 영역 가운데를 한 번 클릭
            self.log.emit(f"뷰어 활성화 클릭 {self.focus_pos}")
            m.position = self.focus_pos
            self._stop.wait(0.3)
            m.click(mouse.Button.left)
            self._stop.wait(0.5)
            m.position = self.return_pos
            if self._stop.wait(1):
                self.finished_capture.emit("stopped", last_saved)
                return

            prev_rgb = None
            with mss.mss() as sct:
                for page in range(self.start_page, self.total_page + 1):
                    # 페이지 넘김 후 로딩 대기 (중단 시 즉시 빠져나옴)
                    if self._stop.wait(self.speed):
                        break

                    self.progress.emit(page, self.total_page)
                    img = sct.grab(self.region)
                    path = os.path.join(self.img_dir, img_filename(page))
                    mss.tools.to_png(img.rgb, img.size, output=path)
                    last_saved = page
                    if page == self.start_page:
                        self.log.emit(
                            f"캡처 이미지 크기: {img.size[0]} x {img.size[1]} px "
                            f"(영역 {self.region['width']} x {self.region['height']} pt)"
                        )
                    self.log.emit(f"[{page}/{self.total_page}] 저장: {img_filename(page)}")

                    if prev_rgb is not None and img.rgb == prev_rgb:
                        self.log.emit(
                            f"⚠ {page}페이지가 이전 페이지와 동일합니다. "
                            f"페이지가 안 넘어갔거나 캡처 대기 시간이 짧을 수 있습니다."
                        )
                    prev_rgb = img.rgb

                    if self._stop.is_set():
                        break

                    # 다음 페이지로 (마지막 페이지에서는 넘기지 않음)
                    if page < self.total_page:
                        self.press_next()

            status = "completed" if last_saved >= self.total_page else "stopped"
            self.finished_capture.emit(status, last_saved)

        except Exception:
            self.log.emit("캡처 중 오류 발생:\n" + traceback.format_exc())
            self.finished_capture.emit("error", last_saved)


# ---------------------------------------------------------------------------
# PDF 변환 작업 (별도 스레드)
# ---------------------------------------------------------------------------
class PdfWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)
    finished_pdf = Signal(bool, str)  # (성공 여부, PDF 경로)

    def __init__(self, img_dir, pdf_path, delete_images,
                 max_side=0, quality=90, grayscale=False, dpi=144):
        super().__init__()
        self.img_dir = img_dir
        self.pdf_path = pdf_path
        self.delete_images = delete_images
        self.max_side = max_side      # 긴 변 최대 픽셀 (0 = 원본 유지)
        self.quality = quality        # PDF 내부 JPEG 품질
        self.grayscale = grayscale    # 흑백 변환
        self.dpi = dpi                # PDF 페이지 크기 계산용 (픽셀 / dpi = 인치)

    def _prepare(self, im, keep_color=False):
        # 첫 페이지(표지)는 흑백 변환 설정과 상관없이 항상 컬러로 둔다
        im = im.convert("L" if (self.grayscale and not keep_color) else "RGB")
        if self.max_side and max(im.size) > self.max_side:
            ratio = self.max_side / max(im.size)
            new_size = (max(1, round(im.width * ratio)), max(1, round(im.height * ratio)))
            im = im.resize(new_size, Image.LANCZOS)
        return im

    def run(self):
        try:
            files = list_images(self.img_dir)
            if not files:
                self.log.emit(f"이미지가 없습니다: {self.img_dir}")
                self.finished_pdf.emit(False, "")
                return

            opt = (f"{'리사이즈 안 함' if not self.max_side else '긴 변 ' + str(self.max_side) + 'px'}, "
                   f"JPEG 품질 {self.quality}, {'흑백(첫 페이지는 컬러)' if self.grayscale else '컬러'}, {self.dpi} DPI")
            self.log.emit(f"PDF 변환 시작: 이미지 {len(files)}장 ({opt})")
            images = []
            for i, f in enumerate(files, 1):
                with Image.open(f) as im:
                    images.append(self._prepare(im, keep_color=(i == 1)))
                self.progress.emit(i, len(files))
                if i == 1:
                    w, h = images[0].size
                    self.log.emit(f"PDF 페이지 크기: {w} x {h} px "
                                  f"(약 {w / self.dpi * 2.54:.1f} x {h / self.dpi * 2.54:.1f} cm)")
                if i % 20 == 0 or i == len(files):
                    self.log.emit(f"PDF 변환 중... {i}/{len(files)}")

            first, rest = images[0], images[1:]
            first.save(self.pdf_path, save_all=True, append_images=rest,
                       resolution=float(self.dpi), quality=self.quality, optimize=True)
            size_mb = os.path.getsize(self.pdf_path) / 1024 / 1024
            self.log.emit(f"PDF 저장 완료: {self.pdf_path} ({size_mb:.1f} MB, "
                          f"페이지당 약 {size_mb * 1024 / len(files):.0f} KB)")

            if self.delete_images:
                for f in files:
                    os.remove(f)
                try:
                    os.rmdir(self.img_dir)
                except OSError:
                    pass  # 다른 파일이 남아 있으면 폴더는 유지
                self.log.emit("캡처 이미지 삭제 완료")

            self.finished_pdf.emit(True, self.pdf_path)
        except Exception:
            self.log.emit("PDF 변환 중 오류 발생:\n" + traceback.format_exc())
            self.finished_pdf.emit(False, "")


# ---------------------------------------------------------------------------
# 캡처 영역 표시 (파란 사각형 오버레이)
# ---------------------------------------------------------------------------
class RegionOverlay(QWidget):
    """캡처 영역 둘레에 파란 테두리를 그리는 투명 창.
    - 테두리는 영역 '바깥'에 그려서 캡처 이미지에 들어가지 않는다.
    - 마우스 클릭이 뒤의 창으로 그대로 지나가고, 포커스를 가져가지 않는다(방향키가 뷰어로 간다).
    """
    BORDER = 4
    LABEL_H = 22

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._w = self._h = 0

    def show_region(self, left, top, width, height):
        b, lh = self.BORDER, self.LABEL_H
        self._w, self._h = width, height
        # 라벨은 영역 위쪽 바깥에 둔다(화면 맨 위라 자리가 없으면 영역 아래 바깥)
        self._label_top = top - b - lh >= 0
        y0 = top - b - (lh if self._label_top else 0)
        h = height + 2 * b + lh
        self.setGeometry(QRect(left - b, y0, width + 2 * b, h))
        self.show(); self.raise_(); self.update()

    def paintEvent(self, _):
        b, lh = self.BORDER, self.LABEL_H
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        blue = QColor(30, 120, 255)
        ry = lh if self._label_top else 0
        pen = QPen(blue, b); pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(b // 2, ry + b // 2, self._w + b, self._h + b)   # 영역 바로 바깥 테두리
        # 크기 라벨
        text = f"캡처 영역 {self._w} × {self._h}"
        f = QFont(); f.setPointSize(11); f.setBold(True); p.setFont(f)
        tw = p.fontMetrics().horizontalAdvance(text) + 14
        ly = 0 if self._label_top else self._h + 2 * b
        p.fillRect(0, ly, tw, lh, blue)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(0, ly, tw, lh), Qt.AlignmentFlag.AlignCenter, text)
        p.end()


# ---------------------------------------------------------------------------
# 화면 스타일 (QSS) · 카드 도우미
# ---------------------------------------------------------------------------
ACCENT = "#2563eb"


def qss(dark: bool) -> str:
    bg, card, text, sub, line, field = (
        ("#0f1115", "#171a21", "#e7e9ee", "#9aa3b2", "#2a2f3a", "#1f232c") if dark else
        ("#f4f5f7", "#ffffff", "#111827", "#6b7280", "#e5e7eb", "#f9fafb"))
    return f"""
    QWidget {{ background: {bg}; color: {text}; font-size: 12px; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: {bg}; border: none; }}
    #card {{ background: {card}; border: 1px solid {line}; border-radius: 14px; }}
    QLabel, QCheckBox, #plain {{ background: transparent; }}
    #h1 {{ font-size: 17px; font-weight: 700; }}
    #sub, #hint {{ color: {sub}; }}
    #hint {{ font-size: 11px; }}
    #step {{ background: {ACCENT}; color: white; border-radius: 9px; font-weight: 700; font-size: 11px; }}
    #stepTitle {{ font-size: 13px; font-weight: 650; }}
    #coord {{ font-family: Menlo, monospace; font-size: 12px; padding: 4px 8px;
              background: {field}; border: 1px solid {line}; border-radius: 8px; }}
    #chip {{ border-radius: 8px; padding: 2px 8px; font-size: 11px; font-weight: 600; }}
    #chip[state="ok"] {{ background: #dcfce7; color: #166534; }}
    #chip[state="no"] {{ background: #fee2e2; color: #991b1b; }}
    #chip[state="unk"] {{ background: #fef3c7; color: #92400e; }}
    QLineEdit, QSpinBox, QComboBox, QPlainTextEdit {{
        background: {field}; border: 1px solid {line}; border-radius: 7px; padding: 4px 7px; }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {ACCENT}; }}
    QPlainTextEdit {{ font-family: Menlo, monospace; font-size: 11px; }}
    QPushButton {{ background: {card}; border: 1px solid {line}; border-radius: 7px; padding: 4px 10px; }}
    QPushButton:hover {{ border-color: {ACCENT}; }}
    QPushButton:disabled {{ color: {sub}; }}
    #primary {{ background: {ACCENT}; color: white; border: none; font-size: 13px; font-weight: 700;
                padding: 8px; border-radius: 8px; }}
    #primary:hover {{ background: #1d4ed8; }}
    #primary:disabled {{ background: {line}; color: {sub}; }}
    #danger {{ color: #dc2626; border-color: #fca5a5; font-weight: 600; }}
    #ghost {{ background: transparent; border: none; color: {ACCENT}; padding: 4px 6px; }}
    QToolButton {{ background: transparent; border: none; color: {sub}; font-weight: 600; padding: 4px 0; }}
    QProgressBar {{ background: {line}; border: none; border-radius: 4px; height: 8px; max-height: 8px; }}
    QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
    QSlider::groove:horizontal {{ height: 6px; background: {line}; border-radius: 3px; }}
    QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: white; border: 2px solid {ACCENT}; width: 14px; margin: -6px 0; border-radius: 9px; }}
    #status {{ font-size: 13px; font-weight: 700; }}
    #err {{ color: #dc2626; font-size: 12px; }}
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{ width: 14px; height: 14px; border-radius: 5px; border: 1.5px solid {line}; background: {field}; }}
    QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
    QSpinBox {{ padding-right: 8px; }}
    """


def card():
    f = QFrame(); f.setObjectName("card")
    lay = QVBoxLayout(f); lay.setContentsMargins(14, 11, 14, 12); lay.setSpacing(7)
    return f, lay


def step_header(n, title, hint=None):
    row = QHBoxLayout(); row.setSpacing(10)
    num = QLabel(str(n)); num.setObjectName("step"); num.setFixedSize(18, 18)
    num.setAlignment(Qt.AlignmentFlag.AlignCenter)
    t = QLabel(title); t.setObjectName("stepTitle")
    row.addWidget(num); row.addWidget(t); row.addStretch()
    if hint:
        h = QLabel(hint); h.setObjectName("hint"); row.addWidget(h)
    return row


def field_row(label, *widgets, stretch_first=True):
    row = QHBoxLayout(); row.setSpacing(8)
    lab = QLabel(label); lab.setObjectName("sub"); lab.setMinimumWidth(78)
    row.addWidget(lab)
    for i, w in enumerate(widgets):
        row.addWidget(w, 1 if (i == 0 and stretch_first) else 0)
    return row



# ---------------------------------------------------------------------------
# 메인 윈도우
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    coord_picked = Signal(int, int, int)  # (1=좌측상단/2=우측하단, x, y)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("eBookToPdf")
        self.setMinimumSize(560, 720)

        self.pos1 = DEFAULT_POS1
        self.pos2 = DEFAULT_POS2
        self.capture_worker = None
        self.pdf_worker = None
        self._listener = None
        self._log_file = None

        self.overlay = RegionOverlay()
        self.coord_picked.connect(self._on_coord_picked)
        self._build_ui()
        self._set_running(False)
        self.setMinimumSize(460, 420)
        scr = QApplication.primaryScreen()
        avail = scr.availableGeometry().height() if scr else 900
        self.resize(max(520, self.centralWidget().widget().minimumSizeHint().width() + 20), min(940, avail - 60))   # 화면 높이에 맞춰 시작 크기를 정한다
        self.log(f"eBookToPdf {APP_VERSION} 시작")
        QTimer.singleShot(400, self._update_overlay)   # 시작할 때 현재 영역을 한 번 보여 준다
        QTimer.singleShot(200, self._check_perms)
        QTimer.singleShot(700, self._warmup_capture)

    # ---------------- UI ----------------
    def _build_ui(self):
        dark = self.palette().window().color().lightness() < 128
        self.setStyleSheet(qss(dark))

        # ── 머리
        head = QVBoxLayout(); head.setSpacing(2)
        h1 = QLabel("eBook → PDF"); h1.setObjectName("h1")
        sub = QLabel("전자책 화면을 쪽마다 캡처해 PDF로 만듭니다 · 개인 소장용"); sub.setObjectName("sub")
        head.addWidget(h1); head.addWidget(sub)

        # ── 1 권한
        c1, l1 = card()
        l1.addLayout(step_header(1, "macOS 권한"))
        chips = QHBoxLayout(); chips.setSpacing(6)
        self._chips = {}
        for k in ("screen", "accessibility", "input"):
            ch = QLabel(PERM_LABELS[k][0]); ch.setObjectName("chip"); ch.setProperty("state", "unk")
            self._chips[k] = ch; chips.addWidget(ch)
        chips.addStretch()
        self.btn_perm_check = QPushButton("다시 확인"); self.btn_perm_check.setObjectName("ghost")
        self.btn_perm_check.clicked.connect(self._check_perms)
        self.btn_perm_open = QPushButton("설정 열기"); self.btn_perm_open.setToolTip("권한 설정 화면을 엽니다")
        self.btn_perm_open.clicked.connect(self._open_perm_settings)
        chips.addWidget(self.btn_perm_check); chips.addWidget(self.btn_perm_open)
        l1.addLayout(chips)
        self.label_perm = QLabel("확인 중..."); self.label_perm.setObjectName("hint")
        self.label_perm.setWordWrap(True); self.label_perm.setTextFormat(Qt.TextFormat.RichText)
        l1.addWidget(self.label_perm)

        # ── 2 캡처 영역
        c2, l2 = card()
        self._area_hint = QLabel(""); self._area_hint.setObjectName("hint")
        hdr = step_header(2, "캡처 영역"); hdr.addWidget(self._area_hint); l2.addLayout(hdr)
        self.label_pos1 = QLabel(str(DEFAULT_POS1)); self.label_pos1.setObjectName("coord")
        self.label_pos2 = QLabel(str(DEFAULT_POS2)); self.label_pos2.setObjectName("coord")
        self.btn_pos1 = QPushButton("화면에서 찍기"); self.btn_pos2 = QPushButton("화면에서 찍기")
        self.btn_pos1.clicked.connect(lambda: self._pick_coord(1))
        self.btn_pos2.clicked.connect(lambda: self._pick_coord(2))
        grid = QGridLayout(); grid.setHorizontalSpacing(8); grid.setVerticalSpacing(8)
        for r, (name, lab, btn) in enumerate([("좌측 상단", self.label_pos1, self.btn_pos1),
                                              ("우측 하단", self.label_pos2, self.btn_pos2)]):
            t = QLabel(name); t.setObjectName("sub"); t.setMinimumWidth(78)
            grid.addWidget(t, r, 0); grid.addWidget(lab, r, 1); grid.addWidget(btn, r, 2)
        grid.setColumnStretch(1, 1)
        l2.addLayout(grid)
        self.chk_overlay = QCheckBox("영역을 파란 테두리로 표시 (캡처에는 안 찍힘)")
        self.chk_overlay.setChecked(True)
        self.chk_overlay.toggled.connect(lambda on: self._update_overlay())
        l2.addWidget(self.chk_overlay)

        # ── 3 책 정보
        c3, l3 = card()
        l3.addLayout(step_header(3, "책 정보"))
        default_dir = BC_PDF_DIR if os.path.isdir(BC_PDF_DIR) else os.path.expanduser("~/Desktop")
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")
        self.input_name = QLineEdit(); self.input_name.setPlaceholderText("필수 · 책 제목 권장 (파일 이름이 됩니다)")
        self.input_name.setObjectName("required")
        self.input_name.textChanged.connect(self._validate_form)
        l3.addLayout(field_row("PDF 이름 *", self.input_name))
        self.label_name_err = QLabel(""); self.label_name_err.setObjectName("err"); self.label_name_err.setVisible(False)
        l3.addWidget(self.label_name_err)
        self.spin_total = QSpinBox(); self.spin_total.setRange(1, 99999); self.spin_total.setValue(1)
        self.spin_total.setToolTip("뷰어를 첫 쪽(표지)에 두고 시작하면 여기까지 캡처합니다.")
        l3.addLayout(field_row("총 페이지 *", self.spin_total))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal); self.speed_slider.setRange(1, 30); self.speed_slider.setValue(5)
        self.speed_label = QLabel(); self.speed_label.setObjectName("sub"); self.speed_label.setMinimumWidth(78)
        self.speed_slider.valueChanged.connect(self._update_speed_label); self._update_speed_label()
        sr = QHBoxLayout(); sr.addWidget(self.speed_label); sr.addWidget(self.speed_slider, 1)
        l3.addLayout(sr)
        self.input_dir = QLineEdit(default_dir)
        self.btn_browse = QPushButton("변경"); self.btn_browse.clicked.connect(self._browse_dir)
        self.btn_open_dir = QPushButton("열기"); self.btn_open_dir.clicked.connect(self._open_dir)
        l3.addLayout(field_row("저장 위치", self.input_dir, self.btn_browse, self.btn_open_dir))

        # 고급 설정 (접힘)
        adv_btn = QToolButton(); adv_btn.setText("▸ 고급 설정 (화질·흑백·이미지 정리)"); adv_btn.setCheckable(True)
        adv = QWidget(); adv.setObjectName("plain"); al = QVBoxLayout(adv); al.setContentsMargins(0, 4, 0, 0); al.setSpacing(8)
        self.combo_size = QComboBox()
        for label, val in [("원본 크기 (기본)", 0), ("긴 변 3000px", 3000), ("긴 변 2400px", 2400),
                           ("긴 변 2000px", 2000), ("긴 변 1600px", 1600), ("긴 변 1200px", 1200)]:
            self.combo_size.addItem(label, val)
        self.spin_quality = QSpinBox(); self.spin_quality.setRange(30, 100); self.spin_quality.setValue(90)
        self.spin_dpi = QSpinBox(); self.spin_dpi.setRange(72, 600); self.spin_dpi.setValue(144)
        al.addLayout(field_row("이미지 크기", self.combo_size))
        qr = QHBoxLayout(); q1 = QLabel("JPEG 품질"); q1.setObjectName("sub"); q1.setMinimumWidth(78)
        q2 = QLabel("DPI"); q2.setObjectName("sub")
        qr.addWidget(q1); qr.addWidget(self.spin_quality, 1); qr.addSpacing(10); qr.addWidget(q2); qr.addWidget(self.spin_dpi, 1)
        al.addLayout(qr)
        self.chk_gray = QCheckBox("흑백으로 저장 (표지는 컬러 유지)")
        self.chk_delete = QCheckBox("PDF를 만든 뒤 캡처 이미지 지우기 (저장 위치의 _captures/ 안)"); self.chk_delete.setChecked(True)
        al.addWidget(self.chk_gray); al.addWidget(self.chk_delete)
        adv.setVisible(False)
        adv_btn.toggled.connect(lambda on: (adv.setVisible(on),
                                            adv_btn.setText(("▾" if on else "▸") + " 고급 설정 (화질·흑백·이미지 정리)")))
        l3.addWidget(adv_btn); l3.addWidget(adv)

        # ── 4 실행
        c4, l4 = card()
        l4.addLayout(step_header(4, "실행"))
        self.label_current = QLabel("대기 중"); self.label_current.setObjectName("status")
        self.progress = QProgressBar(); self.progress.setTextVisible(False); self.progress.setValue(0)
        l4.addWidget(self.label_current); l4.addWidget(self.progress)
        self.btn_start = QPushButton("캡처 시작"); self.btn_start.setObjectName("primary")
        self.btn_stop = QPushButton("중단"); self.btn_stop.setObjectName("danger")
        self.btn_reset = QPushButton("초기화")
        self.btn_start.clicked.connect(self._start_capture); self.btn_stop.clicked.connect(self._stop_capture)
        self.btn_reset.clicked.connect(self._reset)
        br = QHBoxLayout(); br.addWidget(self.btn_start, 3); br.addWidget(self.btn_stop, 1)
        l4.addLayout(br)
        br2 = QHBoxLayout(); br2.addWidget(self.btn_reset); br2.addStretch()
        l4.addLayout(br2)

        # 로그 (접힘)
        log_btn = QToolButton(); log_btn.setText("▾ 동작 로그"); log_btn.setCheckable(True); log_btn.setChecked(True)
        self.log_view = QPlainTextEdit(); self.log_view.setReadOnly(True); self.log_view.setMaximumBlockCount(5000)
        self.log_view.setMinimumHeight(120)
        log_btn.toggled.connect(lambda on: (self.log_view.setVisible(on), log_btn.setText(("▾" if on else "▸") + " 동작 로그")))
        l4.addWidget(log_btn); l4.addWidget(self.log_view)

        foot = QLabel("원작 eBookToPdf © DongHyun Kim (MIT)"); foot.setObjectName("hint")
        foot.setAlignment(Qt.AlignmentFlag.AlignRight)

        root = QVBoxLayout(); root.setContentsMargins(16, 14, 16, 10); root.setSpacing(10)
        root.addLayout(head)
        for c in (c1, c2, c3, c4):
            root.addWidget(c)
        root.addStretch(); root.addWidget(foot)
        container = QWidget(); container.setLayout(root)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(container)
        self.setCentralWidget(scroll)
        self.setWindowTitle("eBookToPdf")
        for sp in (self.spin_total, self.spin_quality, self.spin_dpi):
            sp.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)   # 화살표 대신 입력·스크롤

    # ---------------- 공통 ----------------
    @property
    def speed(self) -> float:
        return self.speed_slider.value() / 10.0

    def _update_speed_label(self):
        self.speed_label.setText(f"캡처 대기: {self.speed:.1f}초")

    def log(self, msg: str):
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        self.log_view.appendPlainText(line)
        print(line)
        if self._log_file:
            try:
                with open(self._log_file, "a", encoding="utf-8") as fp:
                    fp.write(line + "\n")
            except OSError:
                pass

    def _set_running(self, running: bool):
        self._running = running
        for w in (self.btn_reset, self.btn_pos1, self.btn_pos2,
                  self.btn_browse, self.input_dir, self.input_name, self.spin_total,
                  self.speed_slider, self.combo_size, self.spin_quality,
                  self.spin_dpi, self.chk_gray, self.chk_delete, self.chk_overlay):
            w.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self._validate_form()

    INVALID_NAME = set('/\\:*?"<>|')

    def _name_error(self) -> str:
        name = self.input_name.text().strip()
        if not name:
            return "PDF 이름을 입력하세요."
        if set(name) & self.INVALID_NAME or name.startswith("."):
            return "이름에 / \\ : * ? \" < > | 문자를 쓸 수 없고, 점(.)으로 시작할 수 없습니다."
        return ""

    def _validate_form(self, *_):
        err = self._name_error()
        typed = bool(self.input_name.text())
        self.label_name_err.setText(err if typed else "")
        self.label_name_err.setVisible(bool(err) and typed)
        self.btn_start.setEnabled(not getattr(self, "_running", False) and not err)
        self.btn_start.setToolTip(err or "")

    def _paths(self):
        """저장 위치/PDF 이름.pdf, 캡처 데이터는 저장 위치/_captures/<이름>/ 에 모은다."""
        save_dir = self.input_dir.text().strip()
        name = self.input_name.text().strip()
        work_dir = os.path.join(save_dir, "_captures", name)
        img_dir = os.path.join(work_dir, "images")
        pdf_path = os.path.join(save_dir, f"{name}.pdf")
        log_path = os.path.join(work_dir, "log.txt")
        return save_dir, name, img_dir, pdf_path, log_path

    def _check_perms(self, log=True) -> bool:
        """필수 권한이 모두 있으면 True. 상태를 화면과 로그에 적는다."""
        self._perm = check_permissions()
        app = host_app()
        if sys.platform != "darwin":
            self.label_perm.setText("macOS가 아니라 권한 확인을 건너뜁니다.")
            return True
        mark = {True: "✓", False: "✗", None: "?"}
        parts = [f"{PERM_LABELS[k][0]} {mark[self._perm[k]]}" for k in ("screen", "accessibility", "input")]
        missing = [k for k in REQUIRED_PERMS if self._perm[k] is not True]
        ok = not missing
        text = f"권한을 줄 앱: <b>{app}</b><br>" + " · ".join(parts)
        if ok:
            text += "<br><span style='color:#1a7f37'>캡처할 준비가 됐습니다.</span>"
            if self._perm["input"] is not True:
                text += "<br><span style='color:#9a6700'>입력 모니터링이 확인되지 않았습니다. 좌표 클릭이 안 잡히면 허용하세요.</span>"
        else:
            names = ", ".join(PERM_LABELS[k][0] for k in missing)
            text += (f"<br><span style='color:#cf222e'><b>{names}</b> 권한이 없어 캡처를 시작할 수 없습니다.</span>"
                     f"<br>'권한 설정 열기' → '{app}' 켜기 → {app} 완전히 종료 후 다시 실행")
        # 칩과 짧은 안내
        mk = {True: ("ok", "✓"), False: ("no", "✕"), None: ("unk", "?")}
        for k, ch in getattr(self, "_chips", {}).items():
            state, m_ = mk[self._perm.get(k)]
            ch.setText(f"{m_}  {PERM_LABELS[k][0]}")
            ch.setProperty("state", state); ch.style().unpolish(ch); ch.style().polish(ch)
        if ok:
            text = f"권한은 <b>{app}</b>에 붙습니다. 캡처할 준비가 됐습니다."
        else:
            names = ", ".join(PERM_LABELS[k][0] for k in missing)
            text = (f"<span style='color:#dc2626'><b>{names}</b> 권한이 없어 캡처를 시작할 수 없습니다.</span> "
                    f"'권한 설정 열기' → <b>{app}</b> 켜기 → {app}을(를) 완전히 종료 후 다시 실행")
        self.label_perm.setText(text)
        if log:
            self.log(f"권한 확인 ({app}): " + ", ".join(parts))
        return ok

    def _warmup_capture(self):
        """macOS 15(Sequoia)+는 화면 기록 권한이 있어도, 예전 방식 캡처 API를 쓰는 앱에
        '시스템 개인정보 보호 윈도우 선택기를 우회하여…' 확인 창을 주기적으로 띄운다.
        캡처 도중에 뜨면 첫 쪽이 망가질 수 있으므로, 시작할 때 1픽셀을 미리 찍어 창을 먼저 띄운다."""
        if sys.platform != "darwin" or not getattr(self, "_perm", {}).get("screen"):
            return
        try:
            with mss.mss() as sct:
                sct.grab({"left": 0, "top": 0, "width": 1, "height": 1})
            self.log("화면 캡처 확인 완료. macOS가 '화면에 직접 접근' 확인 창을 띄우면 '허용'을 누르세요"
                     " (macOS 15 이상에서 주기적으로 다시 묻습니다).")
        except Exception as e:
            self.log(f"화면 캡처 확인 실패: {e}")

    def _open_perm_settings(self):
        res = getattr(self, "_perm", None) or check_permissions()
        request_permissions(res)
        targets = [k for k in ("screen", "accessibility", "input") if res.get(k) is not True] or ["screen"]
        for k in targets:
            QDesktopServices.openUrl(QUrl(
                f"x-apple.systempreferences:com.apple.preference.security?{PERM_LABELS[k][1]}"))
        self.log("권한 설정 화면을 열었습니다: " + ", ".join(PERM_LABELS[k][0] for k in targets)
                 + ". 켠 뒤에는 실행한 앱을 다시 시작해야 적용됩니다.")

    def _open_dir(self):
        d = self.input_dir.text().strip()
        if not d or not os.path.isdir(d):
            self.log(f"폴더가 없습니다: {d}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        self.log(f"폴더 열기: {d}")

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "저장 경로 선택", self.input_dir.text())
        if d:
            self.input_dir.setText(d)
            self.log(f"저장 경로 설정: {d}")

    # ---------------- 좌표 선택 ----------------
    def _pick_coord(self, which: int):
        if self._listener is not None:
            self._listener.stop()
        name = "좌측상단" if which == 1 else "우측하단"
        self.log(f"{name} 좌표 선택: 화면에서 원하는 위치를 클릭하세요.")
        if getattr(self, "_perm", {}).get("accessibility") is False:
            self.log("⚠ 손쉬운 사용 권한이 없어 클릭이 감지되지 않을 수 있습니다.")

        def on_click(x, y, button, pressed):
            if pressed:
                # pynput 스레드 → 시그널로 메인 스레드에 전달
                self.coord_picked.emit(which, int(x), int(y))
                return False

        # join() 하지 않으므로 UI가 멈추지 않음
        self._listener = mouse.Listener(on_click=on_click)
        self._listener.start()

    def _region(self):
        left, right = sorted((self.pos1[0], self.pos2[0]))
        top, bottom = sorted((self.pos1[1], self.pos2[1]))
        return {"left": left, "top": top, "width": right - left, "height": bottom - top}

    def _update_overlay(self):
        r = self._region()
        if self.chk_overlay.isChecked() and r["width"] >= 10 and r["height"] >= 10:
            self.overlay.show_region(r["left"], r["top"], r["width"], r["height"])
        else:
            self.overlay.hide()
        if hasattr(self, "_area_hint"):
            self._area_hint.setText(f"{r['width']} × {r['height']}")

    def _on_coord_picked(self, which, x, y):
        if which == 1:
            self.pos1 = (x, y); self.label_pos1.setText(f"({x}, {y})")
        else:
            self.pos2 = (x, y); self.label_pos2.setText(f"({x}, {y})")
        self.log(f"{'좌측상단' if which == 1 else '우측하단'} 좌표: ({x}, {y})")
        self._listener = None
        self._update_overlay()

    # ---------------- 캡처 ----------------
    def _start_capture(self):
        if not self._check_perms(log=False):
            missing = ", ".join(PERM_LABELS[k][0] for k in REQUIRED_PERMS if self._perm[k] is not True)
            self.log(f"⚠ 캡처를 시작하지 않습니다: {missing} 권한이 없습니다 ({host_app()}). "
                     "'권한 설정 열기'로 허용한 뒤 앱을 다시 실행하세요.")
            return
        save_dir, name, img_dir, pdf_path, log_path = self._paths()

        if not save_dir or not os.path.isdir(save_dir):
            self.log("저장 경로가 올바르지 않습니다.")
            return
        err = self._name_error()
        if err:
            self.log(err); self.input_name.setFocus(); self._validate_form()
            return

        left, right = sorted((self.pos1[0], self.pos2[0]))
        top, bottom = sorted((self.pos1[1], self.pos2[1]))
        if right - left < 10 or bottom - top < 10:
            self.log("캡처 영역이 너무 작습니다. 좌표를 다시 지정하세요.")
            return
        region = {"left": left, "top": top, "width": right - left, "height": bottom - top}

        total = self.spin_total.value()
        start = 1

        # 같은 이름으로 남은 캡처 데이터가 있으면 지워도 되는지 묻고, 처음부터 한다
        existing = list_images(img_dir) if os.path.isdir(img_dir) else []
        if existing or os.path.exists(pdf_path):
            what = []
            if existing:
                what.append(f"캡처 이미지 {len(existing)}장 ({img_dir})")
            if os.path.exists(pdf_path):
                what.append(f"같은 이름의 PDF ({pdf_path}) — 새로 만들면 덮어씁니다")
            ans = QMessageBox.question(
                self, "이전 캡처 데이터가 있습니다",
                "아래 데이터가 남아 있습니다.\n\n- " + "\n- ".join(what)
                + "\n\n지우고 1쪽부터 새로 캡처할까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if ans != QMessageBox.StandardButton.Yes:
                self.log("캡처를 취소했습니다(이전 데이터 유지).")
                return
            for f in existing:
                os.remove(f)
            self.log(f"이전 캡처 이미지 {len(existing)}장을 지웠습니다.")

        os.makedirs(img_dir, exist_ok=True)
        self._log_file = log_path
        self.log("뷰어가 첫 쪽(표지)을 보여 주고 있는지 확인하세요.")

        self.log(f"영역 {region}, 페이지 {start}~{total}, 대기 {self.speed:.1f}초")
        self.log(f"이미지 폴더: {img_dir}")

        focus_pos = ((left + right) // 2, (top + bottom) // 2)

        try:
            # macOS: pynput/TIS 관련 객체는 반드시 메인 스레드에서 생성
            mouse_ctrl = mouse.Controller()
            press_next = make_right_key_presser()
        except Exception:
            self.log("입력 장치 준비 실패:\n" + traceback.format_exc())
            return
        return_pos = tuple(int(v) for v in mouse_ctrl.position)

        self.progress.setRange(0, total)
        self.progress.setValue(start - 1)
        self.label_current.setText(f"준비 중... ({start}/{total})")

        self.capture_worker = CaptureWorker(region, start, total, self.speed, img_dir,
                                            focus_pos, return_pos, press_next, mouse_ctrl)
        self.capture_worker.log.connect(self.log)
        self.capture_worker.progress.connect(self._on_capture_progress)
        self.capture_worker.finished_capture.connect(self._on_capture_finished)
        self._set_running(True)
        if self.chk_overlay.isChecked():
            # 카운트다운 동안 영역을 보여 주고, 첫 캡처 직전에 숨긴다
            self._update_overlay()
            QTimer.singleShot(max(0, self.capture_worker.countdown * 1000 - 300), self.overlay.hide)
        self.capture_worker.start()

    def _on_capture_progress(self, page, total):
        self.label_current.setText(f"캡처 중: {page} / {total} 페이지")
        self.progress.setValue(page)

    def _stop_capture(self):
        if self.capture_worker and self.capture_worker.isRunning():
            self.log("중단 요청됨... 현재 페이지 저장 후 멈춥니다.")
            self.capture_worker.stop()
            self.btn_stop.setEnabled(False)

    def _on_capture_finished(self, status, last_saved):
        total = self.spin_total.value()
        self._update_overlay()
        self.capture_worker = None

        if status == "completed":
            self.log(f"캡처 완료! ({last_saved}/{total})")
            self._run_pdf()
            return

        self._set_running(False)
        if status == "stopped":
            self.label_current.setText(f"중단됨: {last_saved} / {total} 페이지")
            self.log(f"중단됨. {last_saved}쪽까지 캡처했습니다. 다시 시작하면 1쪽부터 새로 합니다.")
        else:
            self.label_current.setText("오류 발생 - 로그를 확인하세요")

    # ---------------- PDF ----------------
    def _run_pdf(self):
        save_dir, name, img_dir, pdf_path, log_path = self._paths()
        self.label_current.setText("PDF 변환 중...")
        self.pdf_worker = PdfWorker(
            img_dir, pdf_path, self.chk_delete.isChecked(),
            max_side=self.combo_size.currentData(),
            quality=self.spin_quality.value(),
            grayscale=self.chk_gray.isChecked(),
            dpi=self.spin_dpi.value(),
        )
        self.pdf_worker.log.connect(self.log)
        self.pdf_worker.progress.connect(lambda i, n: (self.progress.setRange(0, n), self.progress.setValue(i)))
        self.pdf_worker.finished_pdf.connect(self._on_pdf_finished)
        self.btn_stop.setEnabled(False)
        self.pdf_worker.start()

    def _on_pdf_finished(self, ok, path):
        self.pdf_worker = None
        self._set_running(False)
        self.label_current.setText("PDF 변환 완료!" if ok else "PDF 변환 실패 - 로그 확인")

    # ---------------- 초기화 / 종료 ----------------
    def _reset(self):
        self.pos1 = DEFAULT_POS1; self.pos2 = DEFAULT_POS2
        self.label_pos1.setText(str(DEFAULT_POS1)); self.label_pos2.setText(str(DEFAULT_POS2))
        self.input_name.clear()
        self.spin_total.setValue(1)
        self.speed_slider.setValue(5)
        self.combo_size.setCurrentIndex(0)
        self.progress.setValue(0)
        self.label_current.setText("대기 중")
        self.log("초기화 완료")
        self._update_overlay()

    def closeEvent(self, event):
        self.overlay.close()
        if self.capture_worker and self.capture_worker.isRunning():
            self.capture_worker.stop()
            self.capture_worker.wait(3000)
        if self.pdf_worker and self.pdf_worker.isRunning():
            self.pdf_worker.wait()
        if self._listener is not None:
            self._listener.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())