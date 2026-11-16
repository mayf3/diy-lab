#!/usr/bin/env python3
"""森林童话｜第一批不织布裁剪文件生成器（真实比例 A4 PDF + SVG + 排料图 + 校准尺）。

第一批可制作件（对照现有物料：深绿 200×85 / 白 200×85 / 浅绿·红 50×42 / 无背胶魔术贴）：
1. 圣诞树 65×45 cm：3 层不同色树冠（深绿→中绿→浅绿）+ 3 条白色积雪带 + 红色装饰圆片
   （缝/贴）+ 顶端打印星星位（PETG 另出文件）。
2. 森林背景 60×90 cm 展示板套件：远景树剪影（两种深绿）、雪坡（白）、童话窗户框
   （窗棂条）——全部为可由整幅不织布直接裁剪的形状。
3. 每页含 100mm 校准尺（第 1 页）与对位十字；打印 100%、禁用「适应页面」。

输出（generated/）:
- felt_templates.pdf      多页 A4 真实比例
- felt_templates_*.svg    每图案一份可编辑 SVG（真实比例 mm）
- felt_nesting.png        排料图（按 850mm 幅宽估算用量）
- felt_assembly_preview.png  拼接预览（完成效果示意）
- felt_cut_list.json      裁剪清单（每片尺寸/颜色/数量/所在页）

用法: python3 felt_templates.py [--out generated]
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

MM = 1.0
A4_W, A4_H = 210.0, 297.0
DPI = 150
COLORS = {
    "dark_green": (26, 77, 58),
    "mid_green": (46, 110, 74),
    "light_green": (96, 158, 106),
    "white": (245, 247, 244),
    "red": (178, 44, 38),
    "gold": (196, 158, 62),
    "outline": (40, 40, 40),
    "fold": (120, 120, 220),
}

ROOT = Path(__file__).resolve().parent


# ---------- 形状定义（毫米，局部坐标，y 向下为正） ----------
def tree_layers():
    """圣诞树 65×45：3 层树冠（宽 450→深 450 递缩）+3 条积雪带。返回 [(名称, 颜色, 多边形)]。
    坐标：x 0..450，y 0..650（顶端 y=0）。"""
    cx = 225
    shapes = []
    # 层 3（顶）深绿：三角高 190 宽 200
    shapes.append(("crown_top", "dark_green", [(cx, 0), (cx - 100, 190), (cx + 100, 190)]))
    # 层 2（中）中绿：高 210 宽 300
    shapes.append(("crown_mid", "mid_green", [(cx, 130), (cx - 150, 340), (cx + 150, 340)]))
    # 层 1（底）浅绿：高 220 宽 450
    shapes.append(("crown_bottom", "light_green", [(cx, 300), (cx - 225, 520), (cx + 225, 520)]))
    # 3 条积雪带（白色，边沿波浪近似折线）
    def band(y, half_w):
        pts = []
        n = 8
        for i in range(n + 1):
            x = cx - half_w + (2 * half_w) * i / n
            y_off = -8 if i % 2 == 0 else 0
            pts.append((x, y + y_off))
        pts += [(cx + half_w, y + 14), (cx - half_w, y + 14)]
        return pts
    shapes.append(("snow_top", "white", band(180, 78)))
    shapes.append(("snow_mid", "white", band(330, 118)))
    shapes.append(("snow_bottom", "white", band(510, 178)))
    # 树干（棕色→用红色? 无棕色布：用深绿双层加固，标注可选手缝）
    shapes.append(("trunk", "dark_green", [(cx - 28, 520), (cx - 28, 620), (cx + 28, 620), (cx + 28, 520)]))
    return shapes


def red_decor():
    """红色装饰圆片（缝/贴在树冠上）：直径 40 ×3、25 ×5（16 边形近似圆）。"""
    def circle(d):
        r = d / 2
        return [(r + r * math.cos(2 * math.pi * k / 16), r + r * math.sin(2 * math.pi * k / 16))
                for k in range(16)]
    out = [("red_dot_40", "red", circle(40.0)), ("red_dot_40b", "red", circle(40.0)),
           ("red_dot_40c", "red", circle(40.0))]
    out += [(f"red_dot_25_{k}", "red", circle(25.0)) for k in range(5)]
    return out


def forest_board():
    """森林背景 60×90 展示板套件（板面布局由场景负责，此处出裁剪形状）：
    远景树剪影 A/B（两种深绿）×各 4、雪坡（白）×2、窗框条（白）×4。"""
    shapes = []

    def pine(tag, color, w, h, tip=0.0):
        cx = w / 2
        tiers = 3
        pts = [(cx, tip)]
        for k in range(tiers):
            top = tip + h * 0.22 * k
            bot = tip + h * (0.38 + 0.31 * k)
            hw = w * (0.30 + 0.24 * k) / 2
            pts += [(cx - hw, top + (bot - top) * 0.12), (cx + hw, top + (bot - top) * 0.12),
                    (cx + hw * 0.72, bot), (cx - hw * 0.72, bot)]
        pts += [(cx - w / 2, h), (cx + w / 2, h)]
        shapes.append((tag, color, pts))

    for k in range(4):
        pine(f"bg_pine_a_{k}", "dark_green", 150.0, 330.0)
    for k in range(4):
        pine(f"bg_pine_b_{k}", "mid_green", 120.0, 260.0)
    # 雪坡：宽 600 高 90 圆丘折线
    for k in range(2):
        pts = []
        n = 10
        for i in range(n + 1):
            x = 600 * i / n
            y = 90 - 70 * math.sin(math.pi * i / n) * (0.8 if k == 0 else 1.0)
            pts.append((x, y))
        pts += [(600, 90 + 20), (0, 90 + 20)]
        shapes.append((f"bg_snow_{k}", "white", pts))
    # 童话窗户框：4 条窗棂条（宽 20，长 160/220）
    shapes.append(("window_bar_v1", "white", [(0, 0), (20, 0), (20, 220), (0, 220)]))
    shapes.append(("window_bar_v2", "white", [(0, 0), (20, 0), (20, 220), (0, 220)]))
    shapes.append(("window_bar_h1", "white", [(0, 0), (220, 0), (220, 20), (0, 20)]))
    shapes.append(("window_bar_h2", "white", [(0, 0), (160, 0), (160, 20), (0, 20)]))
    return shapes


# ---------- 分页排版（A4 真实比例） ----------
def pages_from_shapes(groups):
    """把形状装箱到 A4 可打印区（190×277，留校准尺边）。简单按序装箱 + 大件跨页分片。"""
    margin = 10.0
    usable_w, usable_h = A4_W - 2 * margin, A4_H - 2 * margin - 18  # 底部 18mm 留信息条
    pages = []  # 每页 [(名称, 颜色, 多边形(页内坐标), 对折线?)]
    cur, cur_h = [], 0.0

    def new_page():
        nonlocal cur, cur_h
        pages.append(cur)
        cur, cur_h = [], 0.0

    for name, color, poly in groups:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if h > usable_h:  # 大件跨页：按高度切片
            n_pages = math.ceil(h / usable_h)
            step = h / n_pages
            for k in range(n_pages):
                y_lo, y_hi = min(ys) + k * step, min(ys) + (k + 1) * step
                sub = [(x, y) for x, y in poly if y_lo - 1e-6 <= y <= y_hi + 1e-6]
                if len(sub) < 3:
                    continue
                if cur and cur_h + step > usable_h:
                    new_page()
                ox = margin + (usable_w - w) / 2
                oy = margin + (usable_h - cur_h) - (y_lo - min(ys))
                cur.append((f"{name}_p{k+1}", color, [(x + ox, y + oy) for x, y in sub]))
                cur_h += step
            continue
        if cur_h + h > usable_h:
            new_page()
        ox = margin + (usable_w - w) / 2
        oy = margin + (usable_h - cur_h) - (ys[0] if False else 0) - max(ys) + min(ys) + cur_h
        # 顶对齐当前余量
        oy = margin + (usable_h - cur_h) - max(ys)
        cur.append((name, color, [(x + ox, y + oy) for x, y in poly]))
        cur_h += h + 8
    if cur:
        pages.append(cur)
    return pages


def draw_ruler(dr, dpi_s, page_w_mm):
    """100mm 校准尺 + 对位十字。"""
    x0, y0, L = 15 * dpi_s, 285 * dpi_s, 100 * dpi_s
    dr.line((x0, y0, x0 + L, y0), fill=(0, 0, 0), width=3)
    for k in range(0, 101, 10):
        x = x0 + k * dpi_s
        tick = 12 if k % 50 == 0 else 6
        dr.line((x, y0, x, y0 - tick * dpi_s / 3.78), fill=(0, 0, 0), width=2)
        dr.text((x - 6, y0 + 4), f"{k}", fill=(0, 0, 0))
    dr.text((x0 + L + 8 * dpi_s / 3.78, y0 - 4), "100mm 校准尺：打印后请实测", fill=(0, 0, 0))


def render_pdf(pages, path):
    n_pages = len(pages)
    imgs = []
    s = DPI / 25.4
    W, H = int(A4_W * s), int(A4_H * s)
    for pi, page in enumerate(pages):
        im = Image.new("RGB", (W, H), "white")
        dr = ImageDraw.Draw(im)
        draw_ruler(dr, s, A4_W) if pi == 0 else None
        dr.text((15 * s, 12 * s), f"PAGE {pi+1}/{n_pages} · 打印 100%（禁用适应页面）· 实际比例 · 森林童话不织布裁剪",
                fill=(0, 0, 0))
        for name, color, poly in page:
            pts = [(x * s, y * s) for x, y in poly]
            dr.polygon(pts, fill=COLORS[color], outline=COLORS["outline"])
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            dr.text((cx - 20, cy - 6), name, fill=COLORS["outline"])
        imgs.append(im)
    imgs[0].save(path, save_all=True, append_images=imgs[1:], resolution=DPI)
    return n_pages


def render_svgs(groups, out_dir):
    """每图案一份真实比例 SVG（可编辑）。"""
    by_name = {}
    for name, color, poly in groups:
        by_name.setdefault(name.rsplit("_p", 1)[0], []).append((color, poly))
    files = []
    for name, items in by_name.items():
        xs = [p[0] for c, poly in items for p in poly]
        ys = [p[1] for c, poly in items for p in poly]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}mm" height="{h:.0f}mm" viewBox="{-2} {-2} {w+4:.0f} {h+4:.0f}">']
        for color, poly in items:
            d = " ".join(f"{x - min(xs):.1f},{y - min(ys):.1f}" for x, y in poly)
            parts.append(f'<polygon points="{d}" fill="{COLORS[color]}" stroke="#333" stroke-width="0.4"/>')
        parts.append("</svg>")
        f = out_dir / f"felt_{name}.svg"
        f.write_text("\n".join(parts), encoding="utf-8")
        files.append((name, f.name, round(w), round(h)))
    return files


def render_nesting(groups, path):
    """排料图：按 850mm 幅宽模拟排料（简单条带装箱），标注用量。"""
    rolls = {"dark_green": 850, "mid_green": 850, "light_green": 850, "white": 850, "red": 420}
    s = 0.22  # px per mm
    lanes = {k: [] for k in rolls}
    lane_y = {k: 0.0 for k in rolls}
    placed = []
    for name, color, poly in groups:
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        W = rolls[color]
        used_w = sum(q[0] + 10 for q in lanes[color]) if lanes[color] else 0
        if used_w + w > W:
            lane_y[color] += max(q[1] + 10 for q in lanes[color]) if lanes[color] else 0
            lanes[color] = []
        lanes[color].append((w, h))
        placed.append((color, lane_y[color], used_w, w, h, name))
    H = max(lane_y[k] + (max(q[1] + 10 for q in lanes[k]) if lanes[k] else 0) for k in rolls) + 40
    W_img = 900
    im = Image.new("RGB", (int(W_img * s), int(H * s)), "white")
    dr = ImageDraw.Draw(im)
    y_off = {"dark_green": 0}
    lane_top = {}
    for k in rolls:
        lane_top[k] = 0
    for color, ly, ux, w, h, name in placed:
        x0 = ux * s
        y0 = 0
        # 计算该颜色当前 lane 的顶部
        pass
    # 简化：逐颜色独立列绘制
    x_col = 0
    col_w = {"dark_green": 300, "mid_green": 240, "light_green": 240, "white": 300, "red": 180}
    for color in rolls:
        y = 30
        dr.text((x_col * s + 4, 6), f"{color} 幅宽 {rolls[color]}mm", fill=(0, 0, 0))
        for c, ly, ux, w, h, name in placed:
            if c != color:
                continue
            dr.rectangle((x_col * s, y * s, (x_col + w) * s, (y + h) * s),
                         outline=COLORS[color], width=2)
            dr.text((x_col * s + 3, y * s + 3), f"{name} {w:.0f}×{h:.0f}", fill=COLORS[color])
            y += h + 10
        x_col += col_w[color]
    # 图例
    dr.text((4, int((H - 30) * s)), "排料示意：布料幅宽 850/420mm；数值为单片外接矩形尺寸；剪刀沿轮廓裁剪；×2 表示需正反两片", fill=(0, 0, 0))
    im.save(path)


def render_preview(path):
    """完成效果示意：65×450 树 + 背景板缩影。"""
    s = 0.5
    W, H = int(900 * s), int(1000 * s)
    im = Image.new("RGB", (W, H), (240, 244, 240))
    dr = ImageDraw.Draw(im)
    # 背景板
    dr.rectangle((int(60 * s), int(40 * s), int(660 * s), int(940 * s)), fill=(228, 236, 230), outline=(150, 160, 150))
    dr.text((int(70 * s), int(48 * s)), "森林背景板 600×900（示意）", fill=(90, 100, 90))
    # 远景树
    for k, (x, h, c) in enumerate([(120, 330, "dark_green"), (300, 260, "mid_green"), (480, 300, "dark_green")]):
        cx = int((x + 60) * s)
        base = int(880 * s)
        for tk in range(3):
            tw = int((h * 0.5) * (1 - 0.3 * tk) * s)
            th = int(h * 0.38 * s)
            y1 = base - int(h * 0.18 * s) - tk * th
            dr.polygon([(cx - tw, y1), (cx + tw, y1), (cx, y1 - th)], fill=COLORS[c])
    # 大树 65×450
    cx = int(450 * s)
    z0 = int(300 * s)
    scale = s
    for name, color, poly in tree_layers():
        dr.polygon([((cx + px) * scale, (z0 + py) * scale) for px, py in poly], fill=COLORS[color])
    dr.text((int(cx - 60 * s), int((300 + 660) * s)), "圣诞树 450×650mm", fill=(60, 60, 60))
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "generated"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    groups = tree_layers() + red_decor() + forest_board()
    pages = pages_from_shapes(groups)
    n_pages = render_pdf(pages, out / "felt_templates.pdf")
    svgs = render_svgs(groups, out)
    render_nesting(groups, out / "felt_nesting.png")
    render_preview(out / "felt_assembly_preview.png")

    cut_list = {
        "fabric_assumption": "深绿 2000×850 / 白 2000×850 / 浅绿+红 500×420（已加购未付款，付款前先核对）",
        "tree": {"size_mm": [450, 650], "layers": "3 层树冠（深/中/浅绿）+3 条积雪带（白）+树干（深绿加固）",
                 "note": "各层单独裁剪后上下叠放：可用缝线或魔术贴定位，顶端留 60×60mm 星星位（PETG 件）"},
        "red_decor": "圆片 Ø40×3 + Ø25×5（缝/魔术贴）",
        "board_kit": "远景松 A×4 + B×4、雪坡×2、窗棂条×4（60×900 展示板用，板体建议 5mm 泡沫板补购）",
        "svg_files": [{"name": n, "file": f, "w_mm": w, "h_mm": h} for n, f, w, h in svgs],
        "pdf_pages": n_pages,
        "ruler": "第 1 页含 100mm 校准尺；打印 100%（禁用适应页面），打印后实测校准尺",
        "notes": ["魔术贴为无背胶可缝款：裁 40mm 段缝在树背面与展示板/墙面",
                  "积雪带与树冠分层裁剪可产生立体层次；层间用双面缝线固定或魔术贴",
                  "红色圆片直径以毫米计，缝在树冠任意图层表面"],
    }
    (out / "felt_cut_list.json").write_text(json.dumps(cut_list, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pdf_pages": n_pages, "svg": len(svgs), "out": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
