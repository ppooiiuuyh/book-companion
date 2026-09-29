#!/usr/bin/env bash
# 플러그인 패키지 만들기: plugin/ + tools/ + models/ + references/ → plugin/dist/book-companion.plugin
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/plugin/dist"; STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$ROOT/plugin/.claude-plugin" "$ROOT/plugin/skills" "$ROOT/plugin/README.md" "$STAGE/"
mkdir -p "$STAGE/scripts" "$STAGE/references"
cp "$ROOT/plugin/scripts/setup.sh" "$STAGE/scripts/"
cp -R "$ROOT/tools" "$ROOT/models" "$STAGE/scripts/"
cp "$ROOT/references/"*.md "$STAGE/references/"
mkdir -p "$STAGE/scripts/capture/eBookToPdf"
cp "$ROOT/capture/run.sh" "$STAGE/scripts/capture/"
cp "$ROOT/capture/eBookToPdf/eBookToPdf.py" "$ROOT/capture/eBookToPdf/LICENSE" "$STAGE/scripts/capture/eBookToPdf/"
find "$STAGE" -name __pycache__ -prune -exec rm -rf {} + ; find "$STAGE" -name .DS_Store -delete
mkdir -p "$OUT"; rm -f "$OUT/book-companion.plugin"
(cd "$STAGE" && zip -qr "$OUT/book-companion.plugin" .)
echo "$OUT/book-companion.plugin"
