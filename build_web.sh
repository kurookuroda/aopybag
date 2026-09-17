#!/bin/bash
# build_web.sh
# pygbag で main.py をブラウザ(WebAssembly)向けにビルドする。
# 実行前に assets/ 配下に下記7ファイルを配置しておくこと。

set -e

#ASSETS="assets/PixelMplus10-Regular.ttf,assets/PixelMplus12-Regular.ttf,assets/aozora_416.txt,assets/beep_talk.wav,assets/beep_space.wav,assets/beep_fast.wav,assets/beep_faster.wav"

echo "=== pygbag ビルド開始 ==="
#pygbag --assets "$ASSETS" main.py

python3 -m pygbag .
python3 -m http.server 8000 --directory build/web/

echo "=== ビルド完了 ==="
echo "出力先: build/web/"
echo "ローカル確認: python -m http.server 8000 --directory build/web/"
