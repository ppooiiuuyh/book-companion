"""
eBookToPdf (개선판)
- 저장 경로 설정
- 동작 로그 (UI + 로그 파일)
- 현재 처리 중 페이지 / 진행률 표시
- 중단 / 이어하기 (시작 페이지 입력)
- 이미 캡처된 이미지로 PDF만 만들기

필요 패키지: pip install PySide6 pynput mss pillow natsort
macOS 권한: 손쉬운 사용, 입력 모니터링, 화면 기록 (실행하는 터미널/IDE에 부여)
"""
import os
import sys
import glob
import threading
import traceback
import faulthandler
from datetime import datetime

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

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSlider, QSpinBox, QCheckBox,
    QPlainTextEdit, QProgressBar, QFileDialog, QGroupBox, QComboBox,
)

APP_VERSION = "v3 (macOS main-thread fix)"
DEFAULT_POS1 = (3, 130)      # 기본 좌측상단 좌표
DEFAULT_POS2 = (860, 1108)   # 기본 우측하단 좌표
IMG_PATTERN = "img_*.png"


def img_filename(page: int) -> str:
    return f"img_{page:04d}.png"


def list_images(img_dir: str) -> list:
    return natsort.natsorted(glob.glob(os.path.join(img_dir, IMG_PATTERN)))


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

    def _prepare(self, im):
        im = im.convert("L" if self.grayscale else "RGB")
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
                   f"JPEG 품질 {self.quality}, {'흑백' if self.grayscale else '컬러'}, {self.dpi} DPI")
            self.log.emit(f"PDF 변환 시작: 이미지 {len(files)}장 ({opt})")
            images = []
            for i, f in enumerate(files, 1):
                with Image.open(f) as im:
                    images.append(self._prepare(im))
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

        self.coord_picked.connect(self._on_coord_picked)
        self._build_ui()
        self._set_running(False)
        self.setMinimumSize(560, 860)
        self.log(f"eBookToPdf {APP_VERSION} 시작")

    # ---------------- UI ----------------
    def _build_ui(self):
        title = QLabel("E-Book PDF 생성기")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = title.font(); f.setPointSize(20); title.setFont(f)

        # 캡처 영역
        area_box = QGroupBox("캡처 영역")
        g = QGridLayout(area_box)
        self.label_pos1 = QLabel(str(DEFAULT_POS1))
        self.label_pos2 = QLabel(str(DEFAULT_POS2))
        self.btn_pos1 = QPushButton("좌표 위치 클릭")
        self.btn_pos2 = QPushButton("좌표 위치 클릭")
        self.btn_pos1.clicked.connect(lambda: self._pick_coord(1))
        self.btn_pos2.clicked.connect(lambda: self._pick_coord(2))
        g.addWidget(QLabel("이미지 좌측상단"), 0, 0); g.addWidget(self.label_pos1, 0, 1); g.addWidget(self.btn_pos1, 0, 2)
        g.addWidget(QLabel("이미지 우측하단"), 1, 0); g.addWidget(self.label_pos2, 1, 1); g.addWidget(self.btn_pos2, 1, 2)

        # 저장 설정
        save_box = QGroupBox("저장 설정")
        g2 = QGridLayout(save_box)
        default_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.isdir(default_dir):
            default_dir = os.path.expanduser("~")
        self.input_dir = QLineEdit(default_dir)
        self.btn_browse = QPushButton("찾아보기")
        self.btn_browse.clicked.connect(self._browse_dir)
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("생성할 PDF 이름")
        self.chk_delete = QCheckBox("PDF 생성 후 캡처 이미지 삭제")
        self.chk_delete.setChecked(True)
        g2.addWidget(QLabel("저장 경로"), 0, 0); g2.addWidget(self.input_dir, 0, 1); g2.addWidget(self.btn_browse, 0, 2)
        g2.addWidget(QLabel("PDF 이름"), 1, 0); g2.addWidget(self.input_name, 1, 1, 1, 2)
        g2.addWidget(self.chk_delete, 2, 0, 1, 3)

        # 페이지 설정
        page_box = QGroupBox("페이지 설정")
        g3 = QGridLayout(page_box)
        self.spin_total = QSpinBox(); self.spin_total.setRange(1, 99999); self.spin_total.setValue(1)
        self.spin_start = QSpinBox(); self.spin_start.setRange(1, 99999); self.spin_start.setValue(1)
        self.spin_start.setToolTip("이어하기: 뷰어를 이 페이지에 맞춰두고 시작하세요.")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 30); self.speed_slider.setValue(5)
        self.speed_label = QLabel()
        self.speed_slider.valueChanged.connect(self._update_speed_label)
        self._update_speed_label()
        g3.addWidget(QLabel("총 페이지 수"), 0, 0); g3.addWidget(self.spin_total, 0, 1)
        g3.addWidget(QLabel("시작(현재) 페이지"), 1, 0); g3.addWidget(self.spin_start, 1, 1)
        g3.addWidget(self.speed_label, 2, 0); g3.addWidget(self.speed_slider, 2, 1)

        # 출력 품질
        quality_box = QGroupBox("PDF 출력 품질")
        g4 = QGridLayout(quality_box)
        self.combo_size = QComboBox()
        for label, val in [("리사이즈 안 함 (원본, 기본)", 0), ("긴 변 3000px", 3000), ("긴 변 2400px", 2400),
                           ("긴 변 2000px", 2000), ("긴 변 1600px", 1600), ("긴 변 1200px", 1200)]:
            self.combo_size.addItem(label, val)
        self.combo_size.setCurrentIndex(0)
        self.spin_quality = QSpinBox(); self.spin_quality.setRange(30, 100); self.spin_quality.setValue(90)
        self.spin_quality.setToolTip("PDF 안의 이미지는 JPEG로 저장됩니다. 85~92면 글자가 깨끗하고 용량도 적당합니다.")
        self.spin_dpi = QSpinBox(); self.spin_dpi.setRange(72, 600); self.spin_dpi.setValue(144)
        self.spin_dpi.setToolTip("화질에는 영향 없음. PDF 뷰어에서 100% 배율일 때의 페이지 크기만 바뀝니다.")
        self.chk_gray = QCheckBox("흑백 변환 (컬러 삽화가 많은 책에서 용량 절감)")
        g4.addWidget(QLabel("이미지 크기"), 0, 0); g4.addWidget(self.combo_size, 0, 1)
        g4.addWidget(QLabel("JPEG 품질"), 1, 0); g4.addWidget(self.spin_quality, 1, 1)
        g4.addWidget(QLabel("PDF DPI"), 2, 0); g4.addWidget(self.spin_dpi, 2, 1)
        g4.addWidget(self.chk_gray, 3, 0, 1, 2)

        # 진행 상태
        self.label_current = QLabel("대기 중")
        fc = self.label_current.font(); fc.setPointSize(15); fc.setBold(True); self.label_current.setFont(fc)
        self.label_current.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress = QProgressBar(); self.progress.setValue(0)

        # 버튼
        self.btn_start = QPushButton("캡처 시작 / 이어하기")
        self.btn_start.setMinimumHeight(44)
        self.btn_stop = QPushButton("중단")
        self.btn_stop.setMinimumHeight(44)
        self.btn_pdf = QPushButton("PDF만 만들기")
        self.btn_reset = QPushButton("초기화")
        self.btn_start.clicked.connect(self._start_capture)
        self.btn_stop.clicked.connect(self._stop_capture)
        self.btn_pdf.clicked.connect(self._make_pdf_only)
        self.btn_reset.clicked.connect(self._reset)
        btn_row1 = QHBoxLayout(); btn_row1.addWidget(self.btn_start, 3); btn_row1.addWidget(self.btn_stop, 1)
        btn_row2 = QHBoxLayout(); btn_row2.addWidget(self.btn_pdf); btn_row2.addWidget(self.btn_reset)

        # 로그
        self.log_view = QPlainTextEdit(); self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        btn_clear_log = QPushButton("로그 지우기")
        btn_clear_log.clicked.connect(self.log_view.clear)

        sign = QLabel("Made By EastShine")
        sign.setAlignment(Qt.AlignmentFlag.AlignRight)
        fs = sign.font(); fs.setItalic(True); fs.setPointSize(10); sign.setFont(fs)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(area_box)
        layout.addWidget(save_box)
        layout.addWidget(page_box)
        layout.addWidget(quality_box)
        layout.addWidget(self.label_current)
        layout.addWidget(self.progress)
        layout.addLayout(btn_row1)
        layout.addLayout(btn_row2)
        log_header = QHBoxLayout(); log_header.addWidget(QLabel("동작 로그")); log_header.addStretch(); log_header.addWidget(btn_clear_log)
        layout.addLayout(log_header)
        layout.addWidget(self.log_view, 1)
        layout.addWidget(sign)

        container = QWidget(); container.setLayout(layout)
        self.setCentralWidget(container)

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
        for w in (self.btn_start, self.btn_pdf, self.btn_reset, self.btn_pos1, self.btn_pos2,
                  self.btn_browse, self.input_dir, self.input_name, self.spin_total,
                  self.spin_start, self.speed_slider, self.combo_size, self.spin_quality,
                  self.spin_dpi, self.chk_gray):
            w.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def _paths(self):
        save_dir = self.input_dir.text().strip()
        name = self.input_name.text().strip() or "default"
        img_dir = os.path.join(save_dir, f"{name}_images")
        pdf_path = os.path.join(save_dir, f"{name}.pdf")
        log_path = os.path.join(save_dir, f"{name}_log.txt")
        return save_dir, name, img_dir, pdf_path, log_path

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

        def on_click(x, y, button, pressed):
            if pressed:
                # pynput 스레드 → 시그널로 메인 스레드에 전달
                self.coord_picked.emit(which, int(x), int(y))
                return False

        # join() 하지 않으므로 UI가 멈추지 않음
        self._listener = mouse.Listener(on_click=on_click)
        self._listener.start()

    def _on_coord_picked(self, which, x, y):
        if which == 1:
            self.pos1 = (x, y); self.label_pos1.setText(f"({x}, {y})")
        else:
            self.pos2 = (x, y); self.label_pos2.setText(f"({x}, {y})")
        self.log(f"{'좌측상단' if which == 1 else '우측하단'} 좌표: ({x}, {y})")
        self._listener = None

    # ---------------- 캡처 ----------------
    def _start_capture(self):
        save_dir, name, img_dir, pdf_path, log_path = self._paths()

        if not save_dir or not os.path.isdir(save_dir):
            self.log("저장 경로가 올바르지 않습니다.")
            return
        if not self.input_name.text().strip():
            self.log("PDF 이름을 입력하세요.")
            self.input_name.setFocus()
            return

        left, right = sorted((self.pos1[0], self.pos2[0]))
        top, bottom = sorted((self.pos1[1], self.pos2[1]))
        if right - left < 10 or bottom - top < 10:
            self.log("캡처 영역이 너무 작습니다. 좌표를 다시 지정하세요.")
            return
        region = {"left": left, "top": top, "width": right - left, "height": bottom - top}

        total = self.spin_total.value()
        start = self.spin_start.value()
        if start > total:
            self.log(f"시작 페이지({start})가 총 페이지 수({total})보다 큽니다.")
            return

        os.makedirs(img_dir, exist_ok=True)
        self._log_file = log_path

        existing = list_images(img_dir)
        if start == 1 and existing:
            # 새로 시작: 이전 이미지가 섞이지 않게 정리
            for f in existing:
                os.remove(f)
            self.log(f"새로 시작: 기존 이미지 {len(existing)}장 삭제")
        elif start > 1:
            have = {os.path.basename(f) for f in existing}
            missing = [p for p in range(1, start) if img_filename(p) not in have]
            self.log(f"이어하기: {start}페이지부터 캡처 (기존 이미지 {len(existing)}장)")
            if missing:
                preview = ", ".join(map(str, missing[:10])) + (" ..." if len(missing) > 10 else "")
                self.log(f"⚠ 1~{start - 1} 중 누락된 페이지: {preview}")
            self.log("뷰어가 지금 시작 페이지를 보여주고 있는지 확인하세요.")

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
        self.capture_worker = None

        if status == "completed":
            self.log(f"캡처 완료! ({last_saved}/{total})")
            self.spin_start.setValue(1)
            self._run_pdf()
            return

        self._set_running(False)
        next_page = min(last_saved + 1, total)
        self.spin_start.setValue(max(next_page, 1))
        if status == "stopped":
            self.label_current.setText(f"중단됨: {last_saved} / {total} 페이지까지 저장")
            self.log(f"중단됨. 마지막 저장 페이지: {last_saved}")
        else:
            self.label_current.setText("오류 발생 - 로그를 확인하세요")
        self.log(f"이어하기: 뷰어를 {next_page}페이지로 맞춘 뒤 '캡처 시작 / 이어하기'를 누르세요. "
                 f"(시작 페이지 {next_page}로 자동 설정됨)")

    # ---------------- PDF ----------------
    def _make_pdf_only(self):
        save_dir, name, img_dir, pdf_path, log_path = self._paths()
        if not os.path.isdir(img_dir):
            self.log(f"이미지 폴더가 없습니다: {img_dir}")
            return
        self._log_file = log_path
        self._set_running(True)
        self.btn_stop.setEnabled(False)
        self._run_pdf()

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
        self.spin_total.setValue(1); self.spin_start.setValue(1)
        self.speed_slider.setValue(5)
        self.combo_size.setCurrentIndex(0)
        self.progress.setValue(0)
        self.label_current.setText("대기 중")
        self.log("초기화 완료")

    def closeEvent(self, event):
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