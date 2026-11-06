import asyncio
import pygame
import sys
import os

# 确保能找到 pc 文件夹里的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from linkgame_pc import LinkGame


async def main():
    pygame.display.init()
    pygame.font.init()

    game = LinkGame()
    running = True
    while running:
        dt = 1.0 / 60.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                game._handle_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        game.update(dt)
        game.draw()
        pygame.display.flip()


        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())