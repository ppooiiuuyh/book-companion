#!/usr/bin/env bash
# eBookToPdf 실행기 (macOS). 붙여 넣어 실행하면 필요한 것만 설치하고 캡처 도구를 띄운다.
#   bash "<프로젝트 폴더>/capture/run.sh"   (/bookc-capture가 실제 경로를 채워 준다)
# 이미 준비된 것은 건너뛴다: uv가 있으면 설치 생략, 파이썬·패키지는 uv가 캐시에서 재사용.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$HERE/eBookToPdf/eBookToPdf.py"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "이 실행기는 macOS용입니다."; exit 1
fi
[[ -f "$APP" ]] || { echo "캡처 도구가 없습니다: $APP"; exit 1; }

# 1) uv (파이썬 실행·패키지 관리자)
if ! command -v uv >/dev/null 2>&1 && [[ -x "$HOME/.local/bin/uv" ]]; then
  export PATH="$HOME/.local/bin:$PATH"
fi
if command -v uv >/dev/null 2>&1; then
  echo "✓ uv 있음 ($(uv --version)) — 설치 건너뜀"
else
  echo "→ uv 설치 (처음 한 번, 약 10초)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# 2) 저장 폴더
mkdir -p "$HERE/../books-pdf"

# 3) 권한 안내 (한 번만 필요)
cat <<'MSG'

처음 실행이면 macOS 권한 세 가지를 '터미널'(또는 iTerm)에 허용해야 합니다.
  시스템 설정 → 개인정보 보호 및 보안 → 화면 기록 / 손쉬운 사용 / 입력 모니터링
허용 후에는 터미널을 한 번 껐다 켜고 이 명령을 다시 실행하세요.

→ 캡처 도구를 띄웁니다 (처음엔 패키지 설치로 1–2분 걸릴 수 있음)
MSG

cd "$HERE/eBookToPdf"
exec uv run --quiet "$APP"
