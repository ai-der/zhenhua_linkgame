# -*- coding: utf-8 -*-
import sys
import os
import random
import asyncio
from collections import deque
import pygame

# ==================== 全局配置 ====================
# 难度字典： (行数, 列数, 方块大小, 时间限制)
DIFFICULTIES = {
    "easy": (6, 6, 110, 300),
    "normal": (8, 8, 90, 240),
    "hard": (10, 10, 72, 180)
}

MARGIN = 40
HUD_H = 140  # 增高信息栏，容纳两排按钮
FPS = 60

# 颜色定义
BG = (26, 30, 42)
PANEL = (38, 44, 60)
GRID_LINE = (46, 52, 70)
TEXT = (236, 240, 248)
ACCENT = (255, 209, 102)
HINT_COLOR = (110, 230, 255)
BTN_COLORS = [(230, 150, 70), (70, 170, 200), (70, 180, 140), (200, 100, 200)]

PALETTE = [
    (239, 71, 111), (255, 193, 7), (6, 214, 160), (17, 138, 178),
    (131, 56, 236), (255, 140, 66), (0, 187, 249), (247, 37, 133),
]
LETTERS = "ABCDEFGHIJKLMNOP"
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ==================== 工具函数 ====================
def load_font(size, bold=False):
    try:
        return pygame.font.Font("font.otf", size)
    except Exception:
        return pygame.font.Font(None, size)


def find_path(grid, rows, cols, a, b):
    H, W = rows + 2, cols + 2
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
    def __init__(self, text, action, base_color):
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.text = text
        self.action = action
        self.base_color = base_color
        self.enabled = True

    def update_rect(self, x, y, w, h):
        self.rect.update(x, y, w, h)

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
        pygame.init()
        self.clock = pygame.time.Clock()

        self.current_diff = "normal"
        self.tile_surfs = []
        self.load_images()

        self.buttons = [
            Button("简单", "easy", BTN_COLORS[0]),
            Button("普通", "normal", BTN_COLORS[1]),
            Button("困难", "hard", BTN_COLORS[2]),
            Button("重排", "reshuffle", BTN_COLORS[0]),
            Button("提示", "hint", BTN_COLORS[1]),
            Button("新游戏", "new_game", BTN_COLORS[2]),
        ]

        self.set_difficulty("normal")

    def load_images(self):
        self.tile_surfs = []
        assets_dir = "assets"
        try:
            files = sorted(
                [f for f in os.listdir(assets_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])
        except Exception:
            files = []

        for name in files:
            path = os.path.join(assets_dir, name)
            try:
                img = pygame.image.load(path).convert_alpha()
                s = 200  # 保持高分辨率，在画的时候再缩放
                surf = pygame.Surface((s, s), pygame.SRCALPHA)
                color_idx = sum(ord(c) for c in name) % len(PALETTE)
                pygame.draw.rect(surf, PALETTE[color_idx], (0, 0, s, s), border_radius=40)

                img_scaled = pygame.transform.smoothscale(img, (s - 16, s - 16))
                layer = pygame.Surface((s, s), pygame.SRCALPHA)
                layer.blit(img_scaled, (8, 8))

                mask = pygame.Surface((s, s), pygame.SRCALPHA)
                pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, s, s), border_radius=40)
                layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

                surf.blit(layer, (0, 0))
                self.tile_surfs.append(surf)
            except Exception as e:
                print(f"❌ 图片加载失败 {path}: {e}")

        if len(self.tile_surfs) < 2:
            for i in range(8):
                surf = pygame.Surface((200, 200))
                surf.fill(PALETTE[i % len(PALETTE)])
                self.tile_surfs.append(surf)

    def set_difficulty(self, diff):
        self.current_diff = diff
        self.rows, self.cols, self.tile_size, self.time_limit = DIFFICULTIES[diff]

        self.board_w = self.cols * self.tile_size
        self.board_h = self.rows * self.tile_size
        self.width = self.board_w + MARGIN * 2
        self.height = self.board_h + MARGIN * 2 + HUD_H
        self.board_x = MARGIN
        self.board_y = HUD_H + MARGIN

        # 网页端必须使用基础模式，这里由于尺寸大，手机端能够自适应缩放
        self.screen = pygame.display.set_mode((self.width, self.height))

        # 根据窗口大小动态调整字体和按钮
        self.f_mid = load_font(int(self.tile_size * 0.35), bold=True)
        self.f_small = load_font(int(self.tile_size * 0.25))
        self.f_btn = load_font(int(self.tile_size * 0.22), bold=True)

        # 布局按钮
        bw = self.board_w // 3 - 10
        bh = 36
        start_x = self.board_x

        # 第一排：难度选择
        self.buttons[0].update_rect(start_x, 15, bw, bh)
        self.buttons[1].update_rect(start_x + bw + 15, 15, bw, bh)
        self.buttons[2].update_rect(start_x + (bw + 15) * 2, 15, bw, bh)

        # 第二排：操作
        self.buttons[3].update_rect(start_x, 60, bw, bh)
        self.buttons[4].update_rect(start_x + bw + 15, 60, bw, bh)
        self.buttons[5].update_rect(start_x + (bw + 15) * 2, 60, bw, bh)

        self.new_game()

    def cell_center(self, r, c):
        if r == 0: return (self.board_x + (c - 1) * self.tile_size + self.tile_size // 2, self.board_y - 15)
        if r == self.rows + 1: return (
        self.board_x + (c - 1) * self.tile_size + self.tile_size // 2, self.board_y + self.board_h + 15)
        if c == 0: return (self.board_x - 15, self.board_y + (r - 1) * self.tile_size + self.tile_size // 2)
        if c == self.cols + 1: return (
        self.board_x + self.board_w + 15, self.board_y + (r - 1) * self.tile_size + self.tile_size // 2)
        return (self.board_x + (c - 1) * self.tile_size + self.tile_size // 2,
                self.board_y + (r - 1) * self.tile_size + self.tile_size // 2)

    def new_game(self):
        self.grid = [[-1] * (self.cols + 2) for _ in range(self.rows + 2)]
        pool = []
        kinds = len(self.tile_surfs)
        for i in range((self.rows * self.cols) // 2):
            k = i % kinds
            pool.extend((k, k))
        random.shuffle(pool)

        idx = 0
        for r in range(1, self.rows + 1):
            for c in range(1, self.cols + 1):
                self.grid[r][c] = pool[idx]
                idx += 1

        self.selected = None
        self.effects = []
        self.hint = None
        self.hint_path = None
        self.hint_timer = 0.0
        self.score = 0
        self.time_left = self.time_limit
        self.state = "playing"
        self.message = ""
        self.message_timer = 0.0
        self.ensure_solvable()

    def remaining(self):
        return sum(1 for r in range(1, self.rows + 1) for c in range(1, self.cols + 1) if self.grid[r][c] != -1)

    def find_any_pair(self):
        groups = {}
        for r in range(1, self.rows + 1):
            for c in range(1, self.cols + 1):
                k = self.grid[r][c]
                if k != -1: groups.setdefault(k, []).append((r, c))
        for pts in groups.values():
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    p = find_path(self.grid, self.rows, self.cols, pts[i], pts[j])
                    if p: return (pts[i], pts[j], p)
        return None

    def do_reshuffle(self):
        if self.remaining() < 2: return
        cells = [(r, c) for r in range(1, self.rows + 1) for c in range(1, self.cols + 1) if self.grid[r][c] != -1]
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

    def _handle_click(self, pos):
        import time
        curr_t = time.time()
        if hasattr(self, '_last_click') and curr_t - self._last_click < 0.2:
            return
        self._last_click = curr_t

        if self.state != "playing":
            self.new_game()
            return

        for btn in self.buttons:
            if btn.enabled and btn.rect.collidepoint(pos):
                if btn.action == "new_game":
                    self.new_game()
                elif btn.action == "reshuffle":
                    self.do_reshuffle()
                elif btn.action == "hint":
                    self.show_hint()
                elif btn.action in DIFFICULTIES:
                    self.set_difficulty(btn.action)
                return

        if not (self.board_x <= pos[0] < self.board_x + self.board_w and self.board_y <= pos[
            1] < self.board_y + self.board_h):
            return
        c = int((pos[0] - self.board_x) // self.tile_size) + 1
        r = int((pos[1] - self.board_y) // self.tile_size) + 1

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
                path = find_path(self.grid, self.rows, self.cols, a, (r, c))
                if path:
                    self.clear_pair(a, (r, c), path)
                    self.selected = None
                    return
            self.selected = (r, c)

    def update(self, dt):
        playing = (self.state == "playing")
        for btn in self.buttons:
            btn.enabled = True if btn.action in ["new_game", "easy", "normal", "hard"] else playing

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

    def draw(self):
        self.screen.fill(BG)
        pygame.draw.rect(self.screen, PANEL,
                         (self.board_x - 10, self.board_y - 10, self.board_w + 20, self.board_h + 20), border_radius=20)

        for r in range(1, self.rows + 1):
            for c in range(1, self.cols + 1):
                if (r + c) % 2 == 0:
                    pygame.draw.rect(self.screen, GRID_LINE, (
                    self.board_x + (c - 1) * self.tile_size, self.board_y + (r - 1) * self.tile_size, self.tile_size,
                    self.tile_size))

        for r in range(1, self.rows + 1):
            for c in range(1, self.cols + 1):
                k = self.grid[r][c]
                if k != -1:
                    # 动态缩放渲染
                    scaled = pygame.transform.smoothscale(self.tile_surfs[k], (self.tile_size - 6, self.tile_size - 6))
                    self.screen.blit(scaled, (
                    self.board_x + (c - 1) * self.tile_size + 3, self.board_y + (r - 1) * self.tile_size + 3))

        if self.selected:
            r, c = self.selected
            x, y = self.board_x + (c - 1) * self.tile_size + 3, self.board_y + (r - 1) * self.tile_size + 3
            pygame.draw.rect(self.screen, ACCENT, (x - 2, y - 2, self.tile_size - 2, self.tile_size - 2), 3,
                             border_radius=12)

        if self.hint:
            for (r, c) in self.hint:
                x, y = self.board_x + (c - 1) * self.tile_size + 3, self.board_y + (r - 1) * self.tile_size + 3
                pygame.draw.rect(self.screen, HINT_COLOR, (x - 2, y - 2, self.tile_size - 2, self.tile_size - 2), 3,
                                 border_radius=12)
            if self.hint_path:
                pts = [self.cell_center(r, c) for r, c in self.hint_path]
                if len(pts) >= 2:
                    pygame.draw.lines(self.screen, HINT_COLOR, False, pts, 3)

        for e in self.effects:
            p = min(1.0, e["t"] / e["life"])
            if e["type"] == "pop":
                r, c = e["cell"]
                cx, cy = self.cell_center(r, c)
                surf = pygame.transform.smoothscale(self.tile_surfs[e["kind"]],
                                                    (self.tile_size - 6, self.tile_size - 6)).copy()
                surf.set_alpha(int(255 * (1 - p)))
                self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
            elif e["type"] == "path":
                pts = [self.cell_center(r, c) for r, c in e["path"]]
                if len(pts) >= 2:
                    pygame.draw.lines(self.screen, (*ACCENT, int(255 * (1 - p))), False, pts, 4)

        # HUD 绘制
        pygame.draw.rect(self.screen, (34, 39, 54), (0, 0, self.width, HUD_H))
        self.screen.blit(self.f_mid.render(f"分数  {self.score}", True, TEXT), (self.board_x, 15))
        tcol = (255, 110, 110) if self.time_left < 30 else TEXT
        tm = self.f_mid.render(f"时间  {int(self.time_left):03d}s", True, tcol)
        self.screen.blit(tm, tm.get_rect(topright=(self.width - self.board_x, 15)))

        mouse_pos = pygame.mouse.get_pos()
        for btn in self.buttons: btn.draw(self.screen, self.f_btn, mouse_pos)

        if self.message_timer > 0:
            surf = self.f_mid.render(self.message, True, (25, 25, 35))
            box = pygame.Surface((surf.get_width() + 30, surf.get_height() + 20), pygame.SRCALPHA)
            pygame.draw.rect(box, (*ACCENT, 235), box.get_rect(), border_radius=12)
            box.blit(surf, surf.get_rect(center=box.get_rect().center))
            self.screen.blit(box, box.get_rect(center=(self.width // 2, self.board_y + self.board_h // 2)))

        if self.state != "playing":
            veil = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            veil.fill((10, 12, 20, 180))
            self.screen.blit(veil, (0, 0))
            title = "恭喜通关！" if self.state == "won" else "时间到，游戏结束"
            t = load_font(40, True).render(title, True, (110, 240, 180) if self.state == "won" else (255, 130, 130))
            self.screen.blit(t, t.get_rect(center=(self.width // 2, self.height // 2 - 40)))
            s = self.f_mid.render(f"最终得分：{self.score}", True, TEXT)
            self.screen.blit(s, s.get_rect(center=(self.width // 2, self.height // 2 + 10)))
            r = self.f_small.render("点击任意位置重新开始", True, (180, 186, 205))
            self.screen.blit(r, r.get_rect(center=(self.width // 2, self.height // 2 + 50)))

    async def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            self.update(dt)
            self.draw()
            pygame.display.flip()
            await asyncio.sleep(0)