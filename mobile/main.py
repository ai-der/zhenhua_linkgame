import asyncio
import pygame
from linkgame_web import LinkGame


async def main():
    # 网页端必须在异步入口初始化显示和字体，防止音频死锁
    pygame.display.init()
    pygame.font.init()

    game = LinkGame()
    running = True
    while running:
        # 网页端严禁使用 clock.tick(60)，使用固定 dt 步长
        dt = 1.0 / 60.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # 只监听鼠标事件，Pygbag 会自动将手机触摸转换为鼠标坐标
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                game._handle_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        game.update(dt)
        game.draw()
        pygame.display.flip()

        # ✅ 必须让出控制权，否则浏览器主线程卡死导致黑屏无法点击
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())