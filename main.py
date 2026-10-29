import asyncio
import traceback
from linkgame import LinkGame
import pygame
async def main():
    try:
        print("🚀 [Debug] 开始执行 main() ...")
        game = LinkGame()
        print("✅ [Debug] LinkGame 初始化完成，准备进入 run() ...")
        await game.run()
    except Exception as e:
        print(f"❌ [Debug] 发生致命错误: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())