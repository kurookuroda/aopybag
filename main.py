"""pygbag（ブラウザ / WebAssembly）向けの非同期エントリーポイント。

ローカルで直接実行する場合は reader.py を実行してください
(`python reader.py`)。こちらの main.py は pygbag でビルドする際の
起点になります。

    pygbag --assets assets/PixelMplus10-Regular.ttf,assets/PixelMplus12-Regular.ttf,assets/aozora_416.txt,assets/beep_talk.wav,assets/beep_space.wav,assets/beep_fast.wav,assets/beep_faster.wav main.py
"""

import asyncio

import pygame

from reader import App


async def main():
    app = App()

    while app.running:
        app.update()
        app.draw()

        # pygbag の鉄則：毎フレーム必ずイベントループへ制御を返す。
        # これを入れないとブラウザタブがフリーズする。
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
