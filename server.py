#!/usr/bin/env python3
"""
COOP/COEP ヘッダー付き HTTP サーバー
pygbag の WASM (SharedArrayBuffer) に必要なヘッダーを付与する。

使い方:
    python3 server.py
    # またはポート指定
    python3 server.py 8000
"""

import sys
import http.server
import socketserver
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
DIRECTORY = "build/web"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # SharedArrayBuffer に必要なヘッダー
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        # wasm の MIME タイプを明示
        if self.path.endswith(".wasm"):
            self.send_header("Content-Type", "application/wasm")
        super().end_headers()

    def log_message(self, format, *args):
        # アクセスログを見やすく
        print(f"  {self.address_string()} - {format % args}")

if __name__ == "__main__":
    if not Path(DIRECTORY).exists():
        print(f"[ERROR] ディレクトリ '{DIRECTORY}' が見つかりません。")
        print(f"        先に pygbag でビルドしてください:")
        print(f"        python3 -m pygbag .")
        sys.exit(1)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"=== COOP/COEP ヘッダー付きサーバー起動 ===")
        print(f"  ディレクトリ: {DIRECTORY}")
        print(f"  URL: http://localhost:{PORT}")
        print(f"")
        print(f"【GitHub Codespaces の場合】")
        print(f"  1. PORTS タブで {PORT} を Public に変更")
        print(f"  2. ブラウザで表示された URL を開く")
        print(f"")
        print(f"  Ctrl+C で停止")
        httpd.serve_forever()
