import pygame
import sys
import os
import platform

# ===== 設定 =====
# pygbag ビルド時に --assets オプションで指定するパスと一致させる
ASSETS_DIR = "assets"

FONT_CONFIG = {
    10: f"{ASSETS_DIR}/PixelMplus10-Regular.ttf",
    12: f"{ASSETS_DIR}/PixelMplus12-Regular.ttf",
}
FONT_SIZE_DEFAULT = 12

SCREEN_W = 256
SCREEN_H = 256

BOX_X = 8
BOX_Y = 8
BOX_W = 240
BOX_H = 240
PADDING = 8
FOOTER_H = 16
MAX_TEXT_W = BOX_W - PADDING * 2

CHAR_INTERVAL = 2
FAST_INTERVAL = 1
FILE_PATH = f"{ASSETS_DIR}/aozora_416.txt"

# サウンドファイルのパス（wav / ogg 推奨。mp3 は pygame によっては遅延あり）
SOUND_CONFIG = {
    'talk':       f"{ASSETS_DIR}/beep_talk.ogg",
    'talk_space': f"{ASSETS_DIR}/beep_space.ogg",
    'talk_fast':  f"{ASSETS_DIR}/beep_fast.ogg",
    'talk_faster':f"{ASSETS_DIR}/beep_faster.ogg",
}

# Pyxel デフォルト16色パレット (PICO-8)
PYXEL_PALETTE = {
    0: (0, 0, 0),
    1: (29, 43, 83),
    2: (126, 37, 83),
    3: (0, 135, 81),
    4: (171, 82, 54),
    5: (96, 88, 79),
    6: (194, 195, 199),
    7: (255, 241, 232),
    8: (255, 0, 77),
    9: (255, 163, 0),
    10: (255, 240, 36),
    11: (0, 228, 54),
    12: (41, 173, 255),
    13: (131, 118, 156),
    14: (255, 119, 168),
    15: (255, 204, 170),
}

# キー対応表（Pyxel の定数名 → Pygame のキーコード）
KEY_MAP = {
    'Z': pygame.K_z,
    'X': pygame.K_x,
    'RETURN': pygame.K_RETURN,
    'SPACE': pygame.K_SPACE,
    'UP': pygame.K_UP,
    'DOWN': pygame.K_DOWN,
    'R': pygame.K_r,
    'F': pygame.K_f,
    'Q': pygame.K_q,
    'ESCAPE': pygame.K_ESCAPE,
}


class InputManager:
    """Pyxel の btn / btnp に相当する入力管理クラス。

    btn : キーが現在押下中かどうか
    btnp: キーが前フレームでは押されておらず、今フレームで初めて押されたか

    マウスの左クリック（MOUSE_LEFT）は MOUSEBUTTONDOWN イベントを捕捉して
    btnp 相当の動作を実現する。
    """

    def __init__(self):
        self.prev_keys = {}
        self.curr_keys = {}
        self.mouse_click = False  # MOUSEBUTTONDOWN 検出用
        self.joysticks = []
        self._init_joysticks()

    def _init_joysticks(self):
        for i in range(pygame.joystick.get_count()):
            try:
                js = pygame.joystick.Joystick(i)
                js.init()
                self.joysticks.append(js)
            except pygame.error:
                pass

    def handle_event(self, event):
        """pygame.event.get() で取得したイベントを渡す。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse_click = True

    def update(self):
        self.prev_keys = self.curr_keys.copy()
        keys = pygame.key.get_pressed()
        self.curr_keys = {}

        # キーボード
        for name, keycode in KEY_MAP.items():
            self.curr_keys[name] = keys[keycode]

        # マウス（押下中状態）
        mouse = pygame.mouse.get_pressed()
        self.curr_keys['MOUSE_LEFT'] = mouse[0]

        # ゲームパッド
        self._update_gamepad()

    def _update_gamepad(self):
        if not self.joysticks:
            for name in ['PAD_A', 'PAD_B', 'PAD_X', 'PAD_SELECT',
                         'PAD_START', 'PAD_UP', 'PAD_DOWN']:
                self.curr_keys[name] = False
            return

        js = self.joysticks[0]
        self.curr_keys['PAD_A'] = js.get_button(0)
        self.curr_keys['PAD_B'] = js.get_button(1)
        self.curr_keys['PAD_X'] = js.get_button(2)
        self.curr_keys['PAD_SELECT'] = js.get_button(6) if js.get_numbuttons() > 6 else False
        self.curr_keys['PAD_START'] = js.get_button(7) if js.get_numbuttons() > 7 else False

        # Hat (D-Pad)  ※値は整数 (-1, 0, 1)
        if js.get_numhats() > 0:
            hat = js.get_hat(0)
            self.curr_keys['PAD_UP'] = hat[1] == 1
            self.curr_keys['PAD_DOWN'] = hat[1] == -1
        else:
            self.curr_keys['PAD_UP'] = False
            self.curr_keys['PAD_DOWN'] = False

    def btn(self, key):
        """Pyxel の btn と同等。"""
        return self.curr_keys.get(key, False)

    def btnp(self, key):
        """Pyxel の btnp と同等。"""
        if key == 'MOUSE_LEFT':
            # マウスはクリックイベントを使って「瞬間」判定を行う
            result = self.mouse_click
            self.mouse_click = False
            return result
        return self.curr_keys.get(key, False) and not self.prev_keys.get(key, False)


class SoundManager:
    """タイピング音を wav / ogg / mp3 ファイルから読み込んで再生。

    ファイルが存在しない場合は無音で動作する。
    pygame.mixer が初期化できない場合も無音で動作する。
    """

    def __init__(self, config):
        """
        Args:
            config: {名前: ファイルパス} の辞書。
                    例: {'talk': 'beep_talk.wav', ...}
        """
        self.enabled = False
        self.sounds = {}
        self.config = config
        self._init()

    def _init(self):
        # mixer の初期化確認
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=256)
            except Exception:
                return  # 無音で動作

        self._load_sounds()
        self.enabled = bool(self.sounds)

    def _load_sounds(self):
        """設定されたファイルパスからサウンドを読み込む。"""
        for name, path in self.config.items():
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except pygame.error:
                    pass  # 読み込み失敗は無視

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()


def load_paragraphs(path):
    """テキストファイルを読み込み、段落（行）のリストを返す。"""
    if not os.path.exists(path):
        return ["（ファイルが見つかりません）"]
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    # splitlines() で \r\n も \n も統一的に扱える
    return raw.splitlines()


def wrap_paragraphs(paragraphs, font, max_w):
    """段落リストを折り返して行リストにする。

    元の Pyxel 版と同様、font が等幅フォントを前提としている。
    フォールバックフォントが等幅でない場合も font.size() で正確に計測する。

    注: 文字ごとに font.size() を呼ぶため、数万文字級の長文では
    若干のオーバーヘッドが出る可能性がある。体感速度に問題が出た場合は
    等幅フォント前提で累積幅を使った最適化を検討する。
    """
    wrapped = []
    for para in paragraphs:
        if para == "":
            wrapped.append("")
            continue
        line = ""
        for ch in para:
            test = line + ch
            if font:
                test_w = font.size(test)[0]
            else:
                test_w = len(test) * 8
            if test_w > max_w:
                if line:
                    wrapped.append(line)
                    line = ch
                else:
                    wrapped.append(ch)
                    line = ""
            else:
                line = test
        if line:
            wrapped.append(line)
    return wrapped


def paginate(lines, rows_per_page):
    """行リストをページ（行リストのリスト）に分割する。"""
    return [lines[i:i + rows_per_page] for i in range(0, len(lines), rows_per_page)]


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Aozora Reader (Pygame)")
        self.clock = pygame.time.Clock()
        self.input = InputManager()
        self.sound = SoundManager(SOUND_CONFIG)
        self.frame_count = 0
        # pygbag（ブラウザ）環境では sys.exit() が使えないため、
        # 終了は running フラグで管理する。デスクトップ実行時は
        # run() 側でこのフラグを見てループを抜け、そこで初めて
        # pygame.quit() / sys.exit() を呼ぶ。
        self.running = True

        # フォント読み込み（見つからなければシステムフォントで代替）
        self.fonts = {}
        for size, path in FONT_CONFIG.items():
            self.fonts[size] = self._load_font(path, size)

        self.paragraphs = load_paragraphs(FILE_PATH)

        self.current_size = int(FONT_SIZE_DEFAULT)
        self.font = self._get_font(self.current_size)
        self.line_height = self.current_size + 6

        self._rebuild_pages()

        self.page_index = 0
        self.revealed = 0
        self.timer = 0
        self.page_done = False
        self.skip_cooldown = 0

    def _load_font(self, path, size):
        """フォントファイルを読み込む。無い場合はOS別にシステムフォントを探して代替。"""
        if os.path.exists(path):
            return pygame.font.Font(path, size)

        system = platform.system()
        if system == "Windows":
            candidates = [
                "msgothic",      # MS Gothic（等幅・日本語）
                "msmincho",      # MS Mincho
                "meiryo",        # Meiryo
                "yugothic",      # Yu Gothic
                "monospace",
            ]
        elif system == "Darwin":  # macOS
            candidates = [
                "hiragino sans gb",     # ヒラギノ角ゴ
                "hiragino mincho pron", # ヒラギノ明朝
                "yu gothic medium",     # YuGothic
                "monospace",
            ]
        else:  # Linux その他
            candidates = [
                "noto sans cjk jp",     # Noto Sans CJK JP
                "noto sans mono cjk jp",
                "ipagothic",             # IPAゴシック
                "ipamincho",             # IPA明朝
                "takao gothic",          # Takaoゴシック
                "monospace",
            ]

        for name in candidates:
            try:
                font = pygame.font.SysFont(name, size)
                # SysFont は見つからなくてもデフォルトフォントを返すので、
                # 名前に "monospace" が含まれるかで最低限の判定を行う
                if font and name != "monospace":
                    return font
            except Exception:
                pass

        # 最終フォールバック: Pygame 組み込みフォント（日本語非対応だがクラッシュはしない）
        return pygame.font.Font(None, size)

    def _get_font(self, size):
        return self.fonts.get(int(size))

    def _rebuild_pages(self):
        self.font = self._get_font(self.current_size)
        self.line_height = int(self.current_size) + 6
        rows_per_page = max(1, (BOX_H - PADDING * 2 - FOOTER_H) // self.line_height)

        wrapped = wrap_paragraphs(self.paragraphs, self.font, MAX_TEXT_W)
        self.pages = paginate(wrapped, rows_per_page)

    def reset(self):
        self.page_index = 0
        self.revealed = 0
        self.timer = 0
        self.page_done = False
        self.skip_cooldown = 0

    def toggle_font_size(self):
        sizes = sorted(FONT_CONFIG.keys())
        idx = sizes.index(int(self.current_size))
        new_size = sizes[(idx + 1) % len(sizes)]

        self.current_size = int(new_size)
        self._rebuild_pages()

        if self.page_index >= len(self.pages):
            self.page_index = max(0, len(self.pages) - 1)

        self.revealed = 0
        self.timer = 0
        self.page_done = False
        self.skip_cooldown = 5

    @property
    def current_page_text(self):
        if 0 <= self.page_index < len(self.pages):
            return "\n".join(self.pages[self.page_index])
        return ""

    def _down_alone_pressed(self):
        down = self.input.btnp('DOWN') or self.input.btnp('PAD_DOWN')
        a_held = self.input.btn('Z') or self.input.btn('PAD_A')
        b_held = self.input.btn('X') or self.input.btn('PAD_B')
        return down and not (a_held or b_held)

    def _skip_pressed(self):
        return (
            self.input.btnp('RETURN')
            or self.input.btnp('MOUSE_LEFT')
            or self._down_alone_pressed()
        )

    def _back_pressed(self):
        return self.input.btnp('UP') or self.input.btnp('PAD_UP')

    def _next_pressed(self):
        return (
            self._down_alone_pressed()
            or self.input.btnp('RETURN')
            or self.input.btnp('MOUSE_LEFT')
        )

    def _super_speed_combo(self):
        down = self.input.btn('DOWN') or self.input.btn('PAD_DOWN')
        b_btn = self.input.btn('X') or self.input.btn('PAD_B')
        return down and b_btn

    def _speed_combo(self):
        down = self.input.btn('DOWN') or self.input.btn('PAD_DOWN')
        a_btn = self.input.btn('Z') or self.input.btn('PAD_A')
        return down and a_btn

    def _space_held(self):
        return self.input.btn('SPACE')

    def _reset_pressed(self):
        return self.input.btnp('R') or self.input.btnp('PAD_SELECT') or self.input.btnp('PAD_START')

    def _font_toggle_pressed(self):
        return self.input.btnp('F') or self.input.btnp('PAD_X')

    def _get_typing_speed(self):
        if self._super_speed_combo():
            return 0, 3
        if self._speed_combo():
            return 0, 1
        if self._space_held():
            return FAST_INTERVAL, 1
        return CHAR_INTERVAL, 1

    def _play_talk_sound(self, interval, chars_per_tick):
        if not self.sound.enabled:
            return
        if interval == 0 and chars_per_tick >= 3:
            self.sound.play('talk_faster')
        elif interval == 0 and chars_per_tick == 1:
            self.sound.play('talk_fast')
        elif interval == FAST_INTERVAL:
            self.sound.play('talk_space')
        else:
            self.sound.play('talk')

    def update(self):
        self.frame_count += 1

        # イベント処理（QUIT + InputManager へマウスイベントを渡す）
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            self.input.handle_event(event)

        self.input.update()

        if self.input.btnp('Q') or self.input.btnp('ESCAPE'):
            self.running = False
            return

        if self._reset_pressed():
            self.reset()
            return

        if self._font_toggle_pressed():
            self.toggle_font_size()
            return

        if self._back_pressed():
            if self.page_index >= len(self.pages):
                if self.pages:
                    self.page_index = len(self.pages) - 1
                    self.revealed = len(self.current_page_text)
                    self.page_done = True
                    self.skip_cooldown = 5
                return
            if self.page_index > 0:
                self.page_index -= 1
                self.revealed = len(self.current_page_text)
                self.page_done = True
                self.skip_cooldown = 5
            return

        if self.skip_cooldown > 0:
            self.skip_cooldown -= 1
            return

        if self.page_index >= len(self.pages):
            return

        text = self.current_page_text

        if not self.page_done:
            if self._skip_pressed():
                self.revealed = len(text)
                self.page_done = True
                self.skip_cooldown = 8
                return

            interval, chars_per_tick = self._get_typing_speed()

            self.timer += 1
            if self.timer >= interval:
                self.timer = 0
                advanced = False

                for _ in range(chars_per_tick):
                    while self.revealed < len(text) and text[self.revealed] == "\n":
                        self.revealed += 1
                    if self.revealed < len(text):
                        self.revealed += 1
                        advanced = True

                if advanced:
                    self._play_talk_sound(interval, chars_per_tick)

                if self.revealed >= len(text):
                    self.revealed = len(text)
                    self.page_done = True
                    self.skip_cooldown = 5
        else:
            if self._next_pressed():
                self.page_index += 1
                self.revealed = 0
                self.timer = 0
                self.page_done = False

    def draw(self):
        # cls(0)
        self.screen.fill(PYXEL_PALETTE[0])

        # rect (塗りつぶし)
        pygame.draw.rect(
            self.screen, PYXEL_PALETTE[1],
            (BOX_X + 1, BOX_Y + 1, BOX_W - 2, BOX_H - 2)
        )
        # rectb (枠線)
        pygame.draw.rect(
            self.screen, PYXEL_PALETTE[7],
            (BOX_X, BOX_Y, BOX_W, BOX_H), width=1
        )

        if self.page_index >= len(self.pages):
            self._draw_text(BOX_X + PADDING, BOX_Y + PADDING, "-- 読了 --", 7)
            self._draw_ui()
            pygame.display.flip()
            return

        text = self.current_page_text
        shown = text[:self.revealed]
        for i, line in enumerate(shown.split("\n")):
            y = BOX_Y + PADDING + i * self.line_height
            self._draw_text(BOX_X + PADDING, y, line, 7)

        if self.page_done and self.frame_count % 30 < 15:
            self._draw_text(BOX_X + BOX_W - 14, BOX_Y + BOX_H - 12, "▼", 7)

        self._draw_ui()
        pygame.display.flip()

    def _draw_text(self, x, y, text, color_index):
        """Pyxel の text() と同等。font.render + blit で描画する。"""
        color = PYXEL_PALETTE[color_index]
        surf = self.font.render(text, True, color)
        self.screen.blit(surf, (x, y))

    def _draw_ui(self):
        if not self.pages:
            return

        total = len(self.pages)
        current = min(self.page_index + 1, total)
        page_label = f"{current}/{total}"
        font_label = f"{int(self.current_size)}px"

        footer_y = BOX_Y + BOX_H - PADDING - self.current_size

        label_w = self.font.size(page_label)[0]
        x = BOX_X + BOX_W - PADDING - label_w
        self._draw_text(x, footer_y, page_label, 5)
        self._draw_text(BOX_X + PADDING, footer_y, font_label, 5)

    def run(self):
        """デスクトップ実行用の同期ループ。ブラウザ(pygbag)版は main.py の
        非同期ループを使うため、ここでは使用しない。"""
        while self.running:
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    app = App()
    app.run()
