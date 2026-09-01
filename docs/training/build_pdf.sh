#!/usr/bin/env bash
# ClaudeCode研修スライド（HTML）を 1280x720 の PDF に書き出す
#
#   使い方: bash docs/training/build_pdf.sh docs/training/claudecode-kenshu-05.html
#
# 日本語フォント（Noto Sans JP）はスライドと同じ階層の fonts/ から読む。
# 無い場合はここで Google Fonts から取得する（リポジトリには含めない）。
set -euo pipefail

SRC="${1:-docs/training/claudecode-kenshu-05.html}"
SRC_DIR="$(cd "$(dirname "$SRC")" && pwd)"
BASE="$(basename "$SRC" .html)"
OUT="${2:-$SRC_DIR/$BASE.pdf}"

# Chromium（Playwright 同梱版があればそれを使う）
CHROME="${CHROME:-}"
if [ -z "$CHROME" ]; then
  for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome \
           /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
           "$(command -v chromium || true)" "$(command -v google-chrome || true)"; do
    [ -x "$c" ] && CHROME="$c" && break
  done
fi
[ -n "$CHROME" ] || { echo "Chromium/Chrome が見つかりません。CHROME=... で指定してください" >&2; exit 1; }

# フォントの用意
if [ ! -d "$SRC_DIR/fonts" ]; then
  echo "Noto Sans JP を取得します..."
  mkdir -p "$SRC_DIR/fonts"
  UA="Mozilla/5.0 (Windows NT 6.1; rv:20.0) Gecko/20100101 Firefox/20.0"
  for w in 400 700 900; do
    url=$(curl -sS -A "$UA" "https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@$w" \
          | grep -o 'https://[^)]*\.woff')
    curl -sS "$url" -o "$SRC_DIR/fonts/NotoSansJP-$w.woff"
  done
fi

"$CHROME" --headless --no-sandbox --disable-gpu \
  --virtual-time-budget=20000 --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$SRC_DIR/$(basename "$SRC")" 2>/dev/null

echo "→ $OUT"
