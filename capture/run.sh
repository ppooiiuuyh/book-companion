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

macOS 권한(화면 기록 · 손쉬운 사용 · 입력 모니터링)은 이 명령을 실행한 앱
(터미널, iTerm, VS Code 등)에 붙습니다. 도구가 뜨면 맨 위 'macOS 권한' 칸에서 상태를 보여 주고,
화면 기록·손쉬운 사용이 없으면 캡처를 시작하지 않습니다. 허용한 뒤에는 그 앱을 완전히 종료했다가
다시 실행하세요.

→ 캡처 도구를 띄웁니다 (처음엔 패키지 설치로 1–2분 걸릴 수 있음)
MSG

cd "$HERE/eBookToPdf"
exec uv run --quiet "$APP"
