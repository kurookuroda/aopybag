# pygbag 移行計画書

**Aozora Reader（Pygame 版）をブラウザ（WebAssembly）環境へ移行する手順**

---

## 前提条件

- Pygame 版がローカルで正常に動作していること（フェーズ1・2完了済み）
- Python 3.10 以上がインストールされていること
- `pip install pygbag` が実行できること

---

## 01. pygbag とは

pygbag は Pygame プログラムを WebAssembly（WASM）に変換し、ブラウザ上で動作させるためのツールです。Python コードをそのままブラウザで実行できるため、プラグイン不要で配布できます。

```
Python + Pygame コード
        ↓
    pygbag ビルド
        ↓
    build/web/  （HTML + WASM + アセット）
        ↓
    静的ホスティング（GitHub Pages など）
```

---

## 02. 移行の3つの柱

pygbag への移行で必須となる変更は以下の3つです。

### 柱1：メインループの async 化

pygbag はブラウザのイベントループ上で動作するため、メインループを `async`/`await` で書き換える必要があります。

```python
import asyncio
import pygame

async def main():
    pygame.init()
    screen = pygame.display.set_mode((256, 256))
    clock = pygame.time.Clock()

    app = App()  # 既存のゲームロジック

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        app.update()
        app.draw()
        pygame.display.flip()
        clock.tick(60)

        # pygbag の鉄則：毎フレーム必ず yield 制御を返す
        await asyncio.sleep(0)

asyncio.run(main())
```

> **重要：** `await asyncio.sleep(0)` をループ内に入れないとブラウザがフリーズします。これは pygbag 実行時の絶対条件です。

### 柱2：アセットの同梱と読み込み

pygbag では通常のファイルシステムアクセスが制限されます。フォント・テキスト・サウンファイルはビルド時に同梱する必要があります。

**ビルドコマンド：**

```bash
pygbag \
  --assets PixelMplus10-Regular.ttf,PixelMplus12-Regular.ttf,aozora_416.txt,beep_talk.wav,beep_space.wav,beep_fast.wav,beep_faster.wav \
  main.py
```

**読み込み方法：**

同梱したアセットは実行時に仮想ファイルシステム上に展開されるため、`open()` や `pygame.font.Font()` で通常通り読み込めます。

```python
# ビルド時に同梱していれば、そのまま読み込める
font = pygame.font.Font("PixelMplus10-Regular.ttf", 12)

with open("aozora_416.txt", encoding="utf-8") as f:
    text = f.read()
```

> **注意：** 同梱していないファイルは `FileNotFoundError` になります。ビルドコマンドの `--assets` リストを必ず確認してください。

### 柱3：サウンドの扱い

pygbag 環境では pygame.mixer の挙動に制限が出ることがあります。

| 状況 | 対応 |
|------|------|
| WAV/OGG ファイルが正常に読み込める | そのまま `pygame.mixer.Sound` で再生 |
| mixer の初期化に失敗する | 無音フォールバックで動作（既存の SoundManager が対応済み） |
| 再生開始に遅延がある | 短い効果音は WAV を使用。MP3 は避ける |

既存の `SoundManager` は「ファイル不在・mixer 初期化失敗時に無音フォールバック」する設計になっているため、pygbag 移行時もそのまま使えます。

---

## 03. 移行手順（ステップバイステップ）

### Step 1：main.py の async 化

エントリーポイントを async 版に書き換えます。

```python
# main.py
import asyncio
import pygame
import sys

# 既存モジュールのインポート
from reader import App

async def main():
    pygame.init()

    # App クラスの初期化（reader.py 内のロジックはそのまま）
    app = App()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            app.input.handle_event(event)

        app.update()
        app.draw()

        # pygbag 必須：毎フレームイベントループに制御を返す
        await asyncio.sleep(0)

    pygame.quit()

# pygbag では asyncio.run(main()) が自動で呼ばれる場合もあるが、
# 明示的に書いておくとローカル実行も可能
if __name__ == "__main__":
    asyncio.run(main())
```

### Step 2：アセットを assets/ ディレクトリに集約

```
aozora-reader/
├── main.py
├── reader.py              # App クラス（フェーズ1・2で完成済み）
├── input_manager.py       # InputManager クラス
├── palette.py             # Pyxel 色番号 → RGB 変換
├── sound_manager.py       # SoundManager クラス
└── assets/
    ├── PixelMplus10-Regular.ttf
    ├── PixelMplus12-Regular.ttf
    ├── aozora_416.txt
    ├── beep_talk.wav
    ├── beep_space.wav
    ├── beep_fast.wav
    └── beep_faster.wav
```

### Step 3：ファイルパスの確認

`reader.py` 内のファイルパスが `assets/` 配下を指しているか確認します。

```python
# 変更前
FILE_PATH = "aozora_416.txt"
FONT_CONFIG = {
    10: "PixelMplus10-Regular.ttf",
    12: "PixelMplus12-Regular.ttf",
}
SOUND_CONFIG = {
    'talk':        "beep_talk.wav",
    'talk_space':  "beep_space.wav",
    'talk_fast':   "beep_fast.wav",
    'talk_faster': "beep_faster.wav",
}

# 変更後（assets/ ディレクトリ配下に集約した場合）
FILE_PATH = "assets/aozora_416.txt"
FONT_CONFIG = {
    10: "assets/PixelMplus10-Regular.ttf",
    12: "assets/PixelMplus12-Regular.ttf",
}
SOUND_CONFIG = {
    'talk':        "assets/beep_talk.wav",
    'talk_space':  "assets/beep_space.wav",
    'talk_fast':   "assets/beep_fast.wav",
    'talk_faster': "assets/beep_faster.wav",
}
```

> **ポイント：** `--assets` オプションで指定するパスと、コード内のパスを一致させる必要があります。

### Step 4：ビルドの実行

```bash
# プロジェクトルートで実行
pygbag --assets assets/PixelMplus10-Regular.ttf,assets/PixelMplus12-Regular.ttf,assets/aozora_416.txt,assets/beep_talk.wav,assets/beep_space.wav,assets/beep_fast.wav,assets/beep_faster.wav main.py
```

または、シェルスクリプトにまとめておくと便利です。

```bash
#!/bin/bash
# build_web.sh

ASSETS=$(IFS=,; echo "${ASSET_LIST[*]}")
pygbag --assets "$ASSETS" main.py
```

### Step 5：ローカルでブラウザ確認

ビルド後、`build/web/` 以下に出力されます。

```bash
# ローカルサーバを立ち上げて確認
python -m http.server 8000 --directory build/web/
```

ブラウザで `http://localhost:8000` を開き、以下を確認します。

- [ ] 画面が 256×256 で表示される
- [ ] テキストがタイプライター風に表示される
- [ ] Enter / マウスクリック / ↓キーでページ送りできる
- [ ] ↑キーで前のページに戻れる
- [ ] F キーでフォントサイズが切り替わる
- [ ] Space / ↓+Z / ↓+X で表示速度が変わる
- [ ] R キーでリセットされる
- [ ] 読了画面が表示される

### Step 6：デプロイ

`build/web/` 内のファイル群を静的ホスティングービスにアップロードします。

| サービス | 方法 |
|---------|------|
| GitHub Pages | `gh-pages` ブランチまたは GitHub Actions で自動デプロイ |
| Netlify | `build/web/` をドラッグ＆ドロップ、または CLI でデプロイ |
| Vercel | `build/web/` を CLI または Git 連携でデプロイ |
| 自前サーバ | `build/web/` 内のファイルをそのまま配置 |

---

## 04. よくある問題と対処法

### 問題1：アセットが読み込めない

**症状：** `FileNotFoundError: PixelMplus10-Regular.ttf`

**原因：** `--assets` オプションにファイルが含まれていない、またはパスが不一致。

**対処：**
- ビルドコマンドの `--assets` に正しいパスが指定されているか確認
- コード内のパスと `--assets` のパスが一致しているか確認

### 問題2：ブラウザでキー入力が効かない

**症状：** Space / Arrow / Enter などがブラウザのショートカットと競合する。

**原因：** ブラウザ側のデフォルト動作（スクロール・フォーム送信など）と競合。

**対処：**
- Canvas 要素にフォーカスが当たっているか確認
- `preventDefault()` を必要に応じて呼ぶ（ただしゲーム外の操作を奪わないよう注意）
- pygbag 側で対処されている場合もあるので、最新版を使用

### 問題3：サウンドが再生されない

**症状：** タイピング音が鳴らない。

**原因：** ブラウザの自動再生ポリシー（ユーザー操作なしでの音声再生禁止）。

**対処：**
- 既存の `SoundManager` は無音フォールバック設計なので、ゲーム自体は動作する
- 初回クリック・キー入力後に mixer が有効になる場合がある
- サウンドは必須ではない設計のまま維持する

### 問題4：ビルドが失敗する

**症状：** `pygbag` コマンドでエラーが出る。

**対処：**
- Python 3.10 以上を使用しているか確認
- `pip install --upgrade pygbag` で最新版に更新
- 依存ライブラリ（`pygame`, `asyncio`）が正しくインストールされているか確認

### 問題5：日本語フォントが表示されない（豆腐になる）

**症状：** テキストが □ や ? で表示される。

**原因：** フォントファイルが同梱されていない、またはフォールバック先のフォントが日本語非対応。

**対処：**
- `--assets` に `.ttf` ファイルが含まれているか確認
- フォールバックフォントが日本語対応か確認（`SoundManager` と同様に無音ではなく、デフォルト日本語テキストを表示する設計にする）

---

## 05. 推奨ディレクトリ構成（pygbag 版）

```
aozora-reader/
├── main.py                  # エントリーポイント（async 版）
├── reader.py                # App クラス（Pygame ロジック）
├── input_manager.py         # InputManager（btn/btnp 互換）
├── palette.py               # Pyxel 色番号 → RGB 変換
├── sound_manager.py         # SoundManager（WAV/OGG 再生）
├── assets/
│   ├── PixelMplus10-Regular.ttf
│   ├── PixelMplus12-Regular.ttf
│   ├── aozora_416.txt
│   ├── beep_talk.wav
│   ├── beep_space.wav
│   ├── beep_fast.wav
│   └── beep_faster.wav
├── build_web.sh             # pygbag ビルド用スクリプト
└── requirements.txt         # 依存パッケージ一覧
```

### requirements.txt の例

```
pygame>=2.5.0
pygbag>=0.7.0
```

---

## 06. ビルドスクリプト例

```bash
#!/bin/bash
# build_web.sh

set -e

ASSETS="assets/PixelMplus10-Regular.ttf,assets/PixelMplus12-Regular.ttf,assets/aozora_416.txt,assets/beep_talk.wav,assets/beep_space.wav,assets/beep_fast.wav,assets/beep_faster.wav"

echo "=== pygbag ビルド開始 ==="
pygbag --assets "$ASSETS" main.py

echo "=== ビルド完了 ==="
echo "出力先: build/web/"
echo "ローカル確認: python -m http.server 8000 --directory build/web/"
```

---

## 07. チェックリスト

### 移行作業

- [ ] `main.py` を async 化（`asyncio.sleep(0)` をループに追加）
- [ ] アセットを `assets/` ディレクトリに集
- [ ] コード内のファイルパスを `assets/` 配下に修正
- [ ] `pygbag` をインストール（`pip install pygbag`）
- [ ] ビルドコマンドを実行
- [ ] ローカルサーバでブラウザ確認

### 動作確認

- [ ] 画面が 256×256 で表示される
- [ ] テキストがタイプライター風に表示される
- [ ] Enter / マウスクリック / ↓キーでページ送り
- [ ] ↑キーで前のページに戻る
- [ ] F キーでフォントサイズ切り替え
- [ ] Space / ↓+Z / ↓+X で表示速度変更
- [ ] R キーでリセット
- [ ] 読了画面が表示される
- [ ] サウンドが再生される（または無音で動作）

### デプロイ

- [ ] GitHub Pages / Netlify / Vercel などにデプロイ
- [ ] デプロイ先 URL で動作確認
- [ ] スマートフォン・タブレットでの動作確認（任意）

---

*計画書作成日: 2026-09-17*
