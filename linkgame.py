# -*- coding: utf-8 -*-
import sys
import os
import random
import asyncio
from collections import deque

# 强行把 pygame 暴露到全局，防止在网页端被吞
try:
    import pygame
except ImportError:
    print("❌ 找不到 pygame")
# ==================== 全局配置 ====================
ROWS, COLS = 6, 8     # 棋盘行数、列数
TILE = 96            # ★ 方块基准尺寸:改这一个数就能整体放大/缩小、推荐:64（紧凑）/ 80（舒适）/ 96（大屏）/ 120（超大）
MARGIN = 40
HUD_H = 120

# 重新计算画布大小
BOARD_W = COLS * TILE
BOARD_H = ROWS * TILE
WIDTH = BOARD_W + MARGIN * 2
HEIGHT = BOARD_H + MARGIN * 2 + HUD_H
BOARD_X = MARGIN
BOARD_Y = HUD_H + MARGIN
FPS = 60
TOTAL_TIME = 240.0

# 颜色定义
BG = (26, 30, 42)
PANEL = (38, 44, 60)
GRID_LINE = (46, 52, 70)
TEXT = (236, 240, 248)
ACCENT = (255, 209, 102)
HINT_COLOR = (110, 230, 255)

PALETTE = [
    (239, 71, 111), (255, 193, 7), (6, 214, 160), (17, 138, 178),
    (131, 56, 236), (255, 140, 66), (0, 187, 249), (247, 37, 133),
]
LETTERS = "ABCDEFGH"
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ==================== 工具函数 ====================
def load_font(size, bold=False):
    """针对网页端优化:直接尝试加载本地 font.otf，防崩溃兜底"""
    try:
        return pygame.font.Font("font.otf", size)
    except Exception:
        return pygame.font.Font(None, size)


def cell_topleft(r, c):
    return (BOARD_X + (c - 1) * TILE + 3, BOARD_Y + (r - 1) * TILE + 3)


def cell_center(r, c):
    return (BOARD_X + (c - 1) * TILE + TILE // 2, BOARD_Y + (r - 1) * TILE + TILE // 2)


def find_path(grid, a, b):
    """BFS 寻路，限制拐弯 <= 2 次"""
    H, W = ROWS + 2, COLS + 2
    INF = 99
    best = [[[INF] * 4 for _ in range(W)] for _ in range(H)]
    parent = {}

    start = (a[0], a[1], -1)
    parent[start] = None
    dq = deque([(a[0], a[1], -1, 0)])

    while dq:
        r, c, d, turns = dq.popleft()
        for nd, (dr, dc) in enumerate(DIRS):
            nr, nc = r + dr, c + dc
            if not (0 <= nr < H and 0 <= nc < W):
                continue

            nt = turns if (d == -1 or d == nd) else turns + 1
            if nt > 2:
                continue

            if (nr, nc) == b:
                path = []
                cur = (r, c, d)
                while cur is not None:
                    path.append((cur[0], cur[1]))
                    cur = parent[cur]
                path.reverse()
                path.append(b)
                return path

            if grid[nr][nc] != -1:
                continue

            if nt < best[nr][nc][nd]:
                best[nr][nc][nd] = nt
                parent[(nr, nc, nd)] = (r, c, d)
                dq.append((nr, nc, nd, nt))
    return None


# ==================== UI 按钮 ====================
class Button:
    def __init__(self, x, y, w, h, text, action, base_color):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.base_color = base_color
        self.enabled = True

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        bg = self.base_color if (self.enabled and hovered) else (56, 62, 78) if not self.enabled else tuple(
            max(0, c - 30) for c in self.base_color)
        if hovered and self.enabled:
            pygame.draw.rect(screen, (255, 255, 255), self.rect, 2, border_radius=8)

        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        txt = font.render(self.text, True, (240, 244, 252) if self.enabled else (108, 114, 132))
        screen.blit(txt, txt.get_rect(center=self.rect.center))


# ==================== 游戏主体 ====================
class LinkGame:
    def __init__(self):
        print("▶️ [Debug] 进入 LinkGame.__init__ ...")

        # ✅ 打印一下 pygame 到底是什么
        print("▶️ [Debug] 当前 pygame 的路径:", getattr(pygame, "__file__", "未知"))

        try:
            pygame.display.init()
            pygame.font.init()
            print("▶️ [Debug] 显示与字体模块初始化成功")
        except Exception as e:
            print(f"❌ [Debug] pygame 模块初始化失败: {e}")

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        print("▶️ [Debug] set_mode() 完成")

        self.clock = pygame.time.Clock()

        print("▶️ [Debug] 开始加载字体...")
        self.f_mid = load_font(28, bold=True)
        self.f_small = load_font(17)
        self.f_tile = load_font(36, bold=True)
        self.f_btn = load_font(16, bold=True)
        print("▶️ [Debug] 字体加载完成")

        # ================= 加载图片 =================
        print("▶️ [Debug] 开始加载 assets 图片...")
        self.tile_surfs = []
        assets_dir = "assets"

        try:
            # 动态扫描所有支持的图片格式，不管里面有几张图
            files = sorted([
                f for f in os.listdir(assets_dir)
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            ])
            print(f"✅ [Debug] 成功识别到 {len(files)} 张图片")
        except Exception as e:
            print(f"❌ [Debug] 读取 assets 失败: {e}")
            files = []

        # 在循环开始前定义参数（你可以在这里随意修改数字）定义图片大小
        # 按 TILE 尺寸动态计算留白和圆角
        pad = int(TILE * 0.05)  # 留白占方块总宽度的 5%
        rad = int(TILE * 0.2)  # 圆角占方块总宽度的 20%

        for name in files:
            path = os.path.join(assets_dir, name)
            try:
                # 1. 加载原图
                img = pygame.image.load(path).convert_alpha()
                s = TILE - 4  # 尽量占满，留2px缝隙

                # 2. 将原图直接缩放铺满整个方块
                img_scaled = pygame.transform.smoothscale(img, (s, s))

                # 3. 创建一个透明的圆角遮罩
                surf = pygame.Surface((s, s), pygame.SRCALPHA)
                surf.blit(img_scaled, (0, 0))

                # 4. 画一个圆角矩形作为遮罩，把多出去的四角全部透明化
                mask = pygame.Surface((s, s), pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, s, s), border_radius=12)

                # 5. 将遮罩应用到图片上（这会完美裁掉四角）
                surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

                self.tile_surfs.append(surf)
            except Exception as e:
                print(f"❌ 图片加载失败 {path}: {e}")

        # 兜底:如果图太少，用颜色方块补齐
        if len(self.tile_surfs) < 2:
            print("⚠️ 警告:有效图片少于 2 种，使用默认彩色方块兜底！")
            for i in range(8):
                surf = pygame.Surface((TILE - 6, TILE - 6))
                surf.fill(PALETTE[i % len(PALETTE)])
                self.tile_surfs.append(surf)

        # 自动计算种类数量
        self.num_kinds = len(self.tile_surfs)
        print(f"✅ [Debug] 最终加载图案种类: {self.num_kinds}")
        # ================= 图片加载结束 =================


        # 按钮初始化
        bw, bh, gap = 90, 36, 15
        start_x = (WIDTH - (bw * 3 + gap * 2)) // 2
        self.buttons = [
            Button(start_x, 50, bw, bh, "重排", "reshuffle", (230, 150, 70)),
            Button(start_x + bw + gap, 50, bw, bh, "提示", "hint", (70, 170, 200)),
            Button(start_x + (bw + gap) * 2, 50, bw, bh, "新游戏", "new_game", (70, 180, 140)),
        ]
        print("▶️ [Debug] 按钮初始化完成")
        self.new_game()
        print("✅ [Debug] LinkGame 初始化彻底完成！")
    def new_game(self):
        self.grid = [[-1] * (COLS + 2) for _ in range(ROWS + 2)]
        pool = []
        for i in range((ROWS * COLS) // 2):
            k = i % 8
            pool.extend((k, k))
        random.shuffle(pool)

        idx = 0
        for r in range(1, ROWS + 1):
            for c in range(1, COLS + 1):
                self.grid[r][c] = pool[idx]
                idx += 1

        self.selected = None
        self.effects = []
        self.hint = None
        self.hint_path = None
        self.hint_timer = 0.0
        self.score = 0
        self.time_left = TOTAL_TIME
        self.state = "playing"
        self.message = ""
        self.message_timer = 0.0

        self.ensure_solvable()

    def remaining(self):
        return sum(1 for r in range(1, ROWS + 1) for c in range(1, COLS + 1) if self.grid[r][c] != -1)

    def find_any_pair(self):
        groups = {}
        for r in range(1, ROWS + 1):
            for c in range(1, COLS + 1):
                k = self.grid[r][c]
                if k != -1:
                    groups.setdefault(k, []).append((r, c))
        for pts in groups.values():
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    p = find_path(self.grid, pts[i], pts[j])
                    if p: return (pts[i], pts[j], p)
        return None

    def do_reshuffle(self):
        if self.remaining() < 2: return
        cells = [(r, c) for r in range(1, ROWS + 1) for c in range(1, COLS + 1) if self.grid[r][c] != -1]
        vals = [self.grid[r][c] for r, c in cells]
        for _ in range(60):
            random.shuffle(vals)
            for (r, c), v in zip(cells, vals): self.grid[r][c] = v
            if self.find_any_pair(): break
        self.selected = None
        self.hint = None
        self.hint_path = None
        self.set_message("已重排")

    def ensure_solvable(self):
        for _ in range(40):
            if self.find_any_pair(): return
            self.do_reshuffle()

    def show_hint(self):
        pair = self.find_any_pair()
        if pair:
            self.hint = (pair[0], pair[1])
            self.hint_path = pair[2]
            self.hint_timer = 2.0

    def set_message(self, text, duration=1.5):
        self.message = text
        self.message_timer = duration

    def clear_pair(self, a, b, path):
        kind = self.grid[a[0]][a[1]]
        self.grid[a[0]][a[1]] = -1
        self.grid[b[0]][b[1]] = -1
        self.effects.append({"type": "path", "path": path, "t": 0.0, "life": 0.3})
        for cell in (a, b):
            self.effects.append({"type": "pop", "cell": cell, "kind": kind, "t": 0.0, "life": 0.3})
        self.score += 10

        if self.remaining() == 0:
            self.score += int(self.time_left) * 5
            self.state = "won"
        elif self.find_any_pair() is None:
            self.do_reshuffle()
            self.set_message("自动重排！")

    # ==================== 核心交互逻辑 ====================
    def _handle_click(self, pos):
        import time
        current_time = time.time()
        # ✅ 防抖:如果距离上一次点击不到 0.2 秒，直接忽略
        if hasattr(self, '_last_click_time') and current_time - self._last_click_time < 0.2:
            return
        self._last_click_time = current_time

        """统一处理鼠标/触摸点击"""
        if self.state != "playing":
            self.new_game()
            return

        # 1. 检测按钮
        for btn in self.buttons:
            if btn.enabled and btn.rect.collidepoint(pos):
                if btn.action == "new_game":
                    self.new_game()
                elif btn.action == "reshuffle":
                    self.do_reshuffle()
                elif btn.action == "hint":
                    self.show_hint()
                return

        # 2. 检测棋盘
        if not (BOARD_X <= pos[0] < BOARD_X + BOARD_W and BOARD_Y <= pos[1] < BOARD_Y + BOARD_H):
            return
        c = int((pos[0] - BOARD_X) // TILE) + 1
        r = int((pos[1] - BOARD_Y) // TILE) + 1

        if self.grid[r][c] == -1:
            self.selected = None
            return

        if self.selected is None:
            self.selected = (r, c)
        elif self.selected == (r, c):
            self.selected = None
        else:
            a = self.selected
            if self.grid[a[0]][a[1]] == self.grid[r][c]:
                path = find_path(self.grid, a, (r, c))
                if path:
                    self.clear_pair(a, (r, c), path)
                    self.selected = None
                    return
            self.selected = (r, c)

    def update(self, dt):
        playing = (self.state == "playing")
        for btn in self.buttons:
            btn.enabled = True if btn.action == "new_game" else playing

        for e in self.effects: e["t"] += dt
        self.effects = [e for e in self.effects if e["t"] < e["life"]]

        if self.hint_timer > 0:
            self.hint_timer -= dt
            if self.hint_timer <= 0:
                self.hint = None
                self.hint_path = None
        if self.message_timer > 0:
            self.message_timer -= dt

        if self.state == "playing":
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self.state = "lost"

    # ==================== 渲染 ====================
    def draw(self):
        self.screen.fill(BG)
        pygame.draw.rect(self.screen, PANEL, (BOARD_X - 10, BOARD_Y - 10, BOARD_W + 20, BOARD_H + 20), border_radius=20)

        for r in range(1, ROWS + 1):
            for c in range(1, COLS + 1):
                if (r + c) % 2 == 0:
                    pygame.draw.rect(self.screen, GRID_LINE,
                                     (BOARD_X + (c - 1) * TILE, BOARD_Y + (r - 1) * TILE, TILE, TILE))

        for r in range(1, ROWS + 1):
            for c in range(1, COLS + 1):
                k = self.grid[r][c]
                if k != -1:
                    self.screen.blit(self.tile_surfs[k], cell_topleft(r, c))

        if self.selected:
            x, y = cell_topleft(*self.selected)
            pygame.draw.rect(self.screen, ACCENT, (x - 2, y - 2, TILE - 2, TILE - 2), 3, border_radius=12)

        if self.hint:
            for (r, c) in self.hint:
                x, y = cell_topleft(r, c)
                pygame.draw.rect(self.screen, HINT_COLOR, (x - 2, y - 2, TILE - 2, TILE - 2), 3, border_radius=12)
            if self.hint_path:
                pts = [cell_center(r, c) for r, c in self.hint_path]
                pygame.draw.lines(self.screen, HINT_COLOR, False, pts, 3)

        # 绘制特效
        for e in self.effects:
            p = min(1.0, e["t"] / e["life"])
            if e["type"] == "pop":
                r, c = e["cell"]
                cx, cy = cell_center(r, c)
                surf = self.tile_surfs[e["kind"]].copy()
                surf.set_alpha(int(255 * (1 - p)))
                w = int(surf.get_width() * (1.0 + 0.5 * p))
                surf = pygame.transform.smoothscale(surf, (w, w))
                self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
            elif e["type"] == "path":
                pts = [cell_center(r, c) for r, c in e["path"]]
                # 创建一个和整个窗口一样大的透明图层来画线，防止超出屏幕被截断
                layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.lines(layer, (*ACCENT, int(255 * (1 - p))), False, pts, 4)

                # 把图层盖到主屏幕上
                self.screen.blit(layer, (0, 0))

        # 绘制 HUD
        pygame.draw.rect(self.screen, (34, 39, 54), (0, 0, WIDTH, HUD_H))
        row1_y = 12
        self.screen.blit(self.f_mid.render(f"分数  {self.score}", True, TEXT), (MARGIN, row1_y))
        tcol = (255, 110, 110) if self.time_left < 30 else TEXT
        tm = self.f_mid.render(f"时间  {int(self.time_left):03d}s", True, tcol)
        self.screen.blit(tm, tm.get_rect(midtop=(WIDTH // 2, row1_y)))
        self.screen.blit(self.f_mid.render(f"剩余  {self.remaining()}", True, TEXT), (WIDTH - MARGIN - 80, row1_y))

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons: btn.draw(self.screen, self.f_btn, mouse_pos)

        if self.message_timer > 0:
            surf = self.f_mid.render(self.message, True, (25, 25, 35))
            box = pygame.Surface((surf.get_width() + 30, surf.get_height() + 20), pygame.SRCALPHA)
            pygame.draw.rect(box, (*ACCENT, 235), box.get_rect(), border_radius=12)
            box.blit(surf, surf.get_rect(center=box.get_rect().center))
            self.screen.blit(box, box.get_rect(center=(WIDTH // 2, BOARD_Y + BOARD_H // 2)))

        if self.state != "playing":
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((10, 12, 20, 180))
            self.screen.blit(veil, (0, 0))
            title = "恭喜通关！" if self.state == "won" else "时间到，游戏结束"
            t = load_font(40, True).render(title, True, (110, 240, 180) if self.state == "won" else (255, 130, 130))
            self.screen.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))
            s = self.f_mid.render(f"最终得分:{self.score}", True, TEXT)
            self.screen.blit(s, s.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10)))
            r = self.f_small.render("点击任意位置重新开始", True, (180, 186, 205))
            self.screen.blit(r, r.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50)))

    # ==================== 异步主循环 ====================
    async def run(self):

        # 确保在进入游戏主循环前，先让浏览器喘口气，让文件系统完全加载完
        await asyncio.sleep(0.1)

        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    # ✅ 只需要这一个，Pygbag 会自动把手机触摸转成鼠标点击
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            self.update(dt)
            self.draw()
            pygame.display.flip()

            # 必须的异步让步
            await asyncio.sleep(0)