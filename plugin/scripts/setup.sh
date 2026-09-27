#!/usr/bin/env bash
# book-companion 실행 환경 준비. 마지막 줄에 사용할 python 경로를 PY=... 로 출력한다.
# 한 번 준비되면 ~/.bookc/env 에 기록되어 다음부터는 바로 끝난다.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
STATE="$HOME/.bookc"; mkdir -p "$STATE"
PKGS="pymupdf pillow numpy rapidfuzz kiwipiepy"
check() { "$1" -c "import pymupdf, PIL, numpy, rapidfuzz, kiwipiepy" 2>/dev/null; }

if [ -f "$STATE/env" ]; then . "$STATE/env"; fi
if [ -n "${PY:-}" ] && check "$PY" && command -v tesseract >/dev/null; then echo "PY=$PY"; exit 0; fi

# 1) tesseract (한국어 모델은 플러그인에 포함: scripts/models/tessdata)
if ! command -v tesseract >/dev/null; then
  if command -v apt-get >/dev/null; then
    SUDO=""; [ "$(id -u)" != 0 ] && command -v sudo >/dev/null && SUDO="sudo"
    $SUDO apt-get update -qq >/dev/null 2>&1; $SUDO apt-get install -y -qq tesseract-ocr >/dev/null 2>&1
  elif command -v brew >/dev/null; then brew install tesseract >/dev/null 2>&1
  fi
fi
command -v tesseract >/dev/null || { echo "ERROR: tesseract를 설치하지 못했습니다" >&2; exit 1; }

# 2) python 패키지: 시스템 python → pip, 안 되면 uv venv
PY="$(command -v python3)"
if ! check "$PY"; then
  "$PY" -m pip install -q --break-system-packages $PKGS >/dev/null 2>&1 || "$PY" -m pip install -q --user $PKGS >/dev/null 2>&1 || true
fi
if ! check "$PY"; then
  command -v uv >/dev/null || "$PY" -m pip install -q --break-system-packages uv >/dev/null 2>&1 || "$PY" -m pip install -q --user uv >/dev/null 2>&1
  UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
  "$UV" venv -q -p 3.12 "$STATE/venv" >/dev/null 2>&1 || "$UV" venv -q "$STATE/venv" >/dev/null 2>&1
  "$UV" pip install -q -p "$STATE/venv/bin/python" $PKGS >/dev/null 2>&1
  PY="$STATE/venv/bin/python"
fi
check "$PY" || { echo "ERROR: python 패키지 설치 실패 ($PKGS)" >&2; exit 1; }
echo "PY=$PY" > "$STATE/env"
# 자체 점검: 한국어 모델 로드
tesseract --tessdata-dir "$HERE/models/tessdata" --list-langs 2>/dev/null | grep -q kor || { echo "ERROR: kor 모델 로드 실패" >&2; exit 1; }
echo "PY=$PY"
