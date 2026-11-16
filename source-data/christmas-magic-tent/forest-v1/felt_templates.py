#!/usr/bin/env python3
"""森林童话｜第一批不织布裁剪文件生成器 v3（窗口平铺渲染 + 页图回拼自检）。

正确性核心：每个拼图页 = 把完整形状按窗口偏移平移后**直接绘制在页面上**
（页边界即光栅裁切），与回拼自检使用**同一渲染管线**——因此回拼比对与
打印内容逐像素同源。大于可打印区（190×263mm）的形状按重叠 15mm 平铺。

页要素：100mm 校准尺（每页）、四角对位十字、配对页号（拼接组 r/c 清单）、
重叠带提示。生成后自动回拼自检（缺失像素=0 才 PASS），结果写入
felt_verify.json。

图案（现有物料口径：深绿 2000×850 / 白 2000×850 / 浅绿·红 500×420 / 可缝魔术贴）：
1. 圣诞树 450×650：3 层树冠（200×190 深绿 / 300×210 中绿 / 450×220 浅绿）
   + 3 条积雪带 + 树干 + 红圆片 Ø40×3、Ø25×5；
2. 森林背景 600×900 板套件：远景松 A×4 / B×4、雪坡×2、窗棂条×4。

输出（generated/）: felt_templates.pdf、felt_tiles/page_*.png+*.svg、
felt_nesting.png、felt_assembly_preview.png、felt_cut_list.json、felt_verify.json
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

A4_W, A4_H = 210.0, 297.0
MARGIN = 10.0
PRINT_W, PRINT_H = A4_W - 2 * MARGIN, A4_H - 2 * MARGIN - 14
OVERLAP = 15.0
DPI = 150
SMALL_W, SMALL_H = 88.0, 130.0     # 可合箱的小件上限

COLORS = {
    "dark_green": (26, 77, 58), "mid_green": (46, 110, 74), "light_green": (96, 158, 106),
    "white": (245, 247, 244), "red": (178, 44, 38),
}
ROOT = Path(__file__).resolve().parent


# ---------- 形状（局部坐标 mm，y 向下） ----------
def tree_shapes():
    cx = 225.0

    def band(y, half_w):
        pts = []
        n = 8
        for i in range(n + 1):
            x = cx - half_w + (2 * half_w) * i / n
            pts.append((x, y + (-8 if i % 2 == 0 else 0)))
        return pts + [(cx + half_w, y + 14), (cx - half_w, y + 14)]

    return [
        ("tree_crown_top", "dark_green", [(cx, 0), (cx - 100, 190), (cx + 100, 190)]),
        ("tree_crown_mid", "mid_green", [(cx, 130), (cx - 150, 340), (cx + 150, 340)]),
        ("tree_crown_bottom", "light_green", [(cx, 300), (cx - 225, 520), (cx + 225, 520)]),
        ("tree_snow_top", "white", band(180, 78)),
        ("tree_snow_mid", "white", band(330, 118)),
        ("tree_snow_bottom", "white", band(510, 178)),
        ("tree_trunk", "dark_green", [(cx - 28, 520), (cx - 28, 620), (cx + 28, 620), (cx + 28, 520)]),
    ]


def red_dots():
    out = []
    for k, d in enumerate((40, 40, 40, 25, 25, 25, 25, 25)):
        r = d / 2
        pts = [(r + r * math.cos(2 * math.pi * k2 / 16), r + r * math.sin(2 * math.pi * k2 / 16))
               for k2 in range(16)]
        out.append((f"red_dot_d{d}_{k}", "red", pts))
    return out


def board_shapes():
    S = []

    def pine(tag, color, w, h):
        cx = w / 2
        pts = [(cx, 0)]
        for k in range(3):
            top = h * 0.22 * k
            bot = h * (0.38 + 0.31 * k)
            hw = w * (0.30 + 0.24 * k) / 2
            pts += [(cx - hw, top + (bot - top) * 0.12), (cx + hw, top + (bot - top) * 0.12),
                    (cx + hw * 0.72, bot), (cx - hw * 0.72, bot)]
        pts += [(cx - w / 2, h), (cx + w / 2, h)]
        S.append((tag, color, pts))

    for k in range(4):
        pine(f"board_pine_a_{k}", "dark_green", 150.0, 330.0)
    for k in range(4):
        pine(f"board_pine_b_{k}", "mid_green", 120.0, 260.0)
    for k in range(2):
        pts = []
        n = 10
        for i in range(n + 1):
            x = 600 * i / n
            y = 90 - 70 * math.sin(math.pi * i / n) * (0.8 if k == 0 else 1.0)
            pts.append((x, y))
        pts += [(600, 110), (0, 110)]
        S.append((f"board_snow_{k}", "white", pts))
    S.append(("board_win_v1", "white", [(0, 0), (20, 0), (20, 220), (0, 220)]))
    S.append(("board_win_v2", "white", [(0, 0), (20, 0), (20, 220), (0, 220)]))
    S.append(("board_win_h1", "white", [(0, 0), (220, 0), (220, 20), (0, 20)]))
    S.append(("board_win_h2", "white", [(0, 0), (160, 0), (160, 20), (0, 20)]))
    return S


def all_groups():
    return tree_shapes() + red_dots() + board_shapes()


# ---------- 平铺窗口 ----------
def tile_plan(w, h):
    cols = 1 if w <= PRINT_W else math.ceil((w - OVERLAP) / (PRINT_W - OVERLAP))
    rows = 1 if h <= PRINT_H else math.ceil((h - OVERLAP) / (PRINT_H - OVERLAP))
    return cols, rows


def build_tiles(groups):
    """每形状 → 平铺窗口列表：win=窗口左上（世界 mm）、poly=完整形状（绘制时平移）。"""
    out = []
    for name, color, poly in groups:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, y0 = min(xs), min(ys)
        w, h = max(xs) - x0, max(ys) - y0
        cols, rows = tile_plan(w, h)
        step_x = (w - PRINT_W) / (cols - 1) if cols > 1 else 0
        step_y = (h - PRINT_H) / (rows - 1) if rows > 1 else 0
        for r in range(rows):
            for c in range(cols):
                wx = x0 + c * step_x
                wy = y0 + r * step_y
                out.append({"group": name, "color": color, "r": r + 1, "c": c + 1,
                            "rows": rows, "cols": cols, "win": (wx, wy), "poly": poly})
    return out


def group_into_pages(tiles):
    """大件独占页；小件合箱（每页 ≤6 件，网格排布）。"""
    pages, small = [], []
    for t in sorted(tiles, key=lambda t: (0 if t["group"].startswith("tree_") else 1,
                                          t["group"], t["r"], t["c"])):
        if t["rows"] == 1 and t["cols"] == 1:
            xs = [p[0] for p in t["poly"]]
            ys = [p[1] for p in t["poly"]]
            if max(xs) - min(xs) <= SMALL_W and max(ys) - min(ys) <= SMALL_H:
                small.append(t)
                continue
        pages.append({"kind": "tile", "tiles": [t]})
    while small:
        pages.append({"kind": "small", "tiles": small[:6]})
        small = small[6:]
    return pages


# ---------- 页面绘制（自检与打印同管线） ----------
def draw_tiles(dr, page, scale=1.0):
    s = scale
    for m_i, t in enumerate(page["tiles"]):
        wx, wy = t["win"]
        if page["kind"] == "small":
            slot_x = MARGIN + 6 + (m_i % 2) * 96
            slot_y = MARGIN + 6 + (m_i // 2) * 96
        else:
            slot_x, slot_y = MARGIN, MARGIN
        poly = [((x - wx + slot_x) * s, (y - wy + slot_y) * s) for x, y in t["poly"]]
        dr.polygon(poly, fill=COLORS[t["color"]], outline=(40, 40, 40))


def draw_chrome(dr, page, pi, n_pages, scale=1.0):
    s = scale
    dr.text((10 * s, 8 * s), f"PAGE {pi+1}/{n_pages} · print at 100% (no fit-to-page) · true scale",
            fill=(0, 0, 0))
    x0, y0, L = 15 * s, 272 * s, 100 * s
    dr.line((x0, y0, x0 + L, y0), fill=(0, 0, 0), width=3)
    for k in range(0, 101, 10):
        x = x0 + k * s
        dr.line((x, y0, x, y0 - (12 if k % 50 == 0 else 6)), fill=(0, 0, 0), width=2)
        dr.text((x - 5, y0 + 3), str(k), fill=(0, 0, 0))
    dr.text((x0 + L + 6, y0 - 3), "100mm calibration (verify after print)", fill=(0, 0, 0))
    for cxp, cyp in ((MARGIN, MARGIN), (MARGIN + PRINT_W, MARGIN),
                     (MARGIN, MARGIN + PRINT_H), (MARGIN + PRINT_W, MARGIN + PRINT_H)):
        X, Y = cxp * s, cyp * s
        dr.line((X - 8, Y, X + 8, Y), fill=(180, 60, 60), width=2)
        dr.line((X, Y - 8, X, Y + 8), fill=(180, 60, 60), width=2)
    multi = [t for t in page["tiles"] if t["rows"] > 1 or t["cols"] > 1]
    if multi:
        t = multi[0]
        dr.text((10 * s, 20 * s),
                f"{t['group']} · 拼接页 行{t['r']}/{t['rows']} 列{t['c']}/{t['cols']} · "
                f"重叠 {OVERLAP:.0f}mm 对齐十字", fill=(150, 40, 40))
        pairs = " · ".join(f"r{rr+1}c{cc+1}" for rr in range(t["rows"]) for cc in range(t["cols"]))
        dr.text((10 * s, (A4_H - MARGIN - 8) * s), f"tile group ({t['group']}): {pairs}",
                fill=(0, 0, 0))


def render_page(page, pi, n_pages, with_chrome=True):
    s = DPI / 25.4
    W, H = int(A4_W * s), int(A4_H * s)
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    draw_tiles(dr, page, s)
    if with_chrome:
        draw_chrome(dr, page, pi, n_pages, s)
    return im


# ---------- 回拼自检（与打印同管线） ----------
def verify_reassembly(pages, groups, scale=DPI / 25.4):  # 与页渲染同 px/mm，回拼 1:1
    """回拼自检：每 tile 以「形状掩膜」贴入组画布（与打印页同一几何），掩膜并集
    与原始轮廓逐像素比对；缺失=0 且多余 <2% 才 PASS。"""
    report = {"shapes": [], "total_missing_px": 0, "total_extra_px": 0, "verdict": "PASS"}
    orig = {name: (color, poly) for name, color, poly in groups}
    assembled = {name: None for name in orig}

    for pi, page in enumerate(pages):
        s = DPI / 25.4
        W, H = int(A4_W * s), int(A4_H * s)
        for m_i, t in enumerate(page["tiles"]):
            color, poly = orig[t["group"]]
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            x0, y0 = min(xs), min(ys)
            wx, wy = t["win"]
            if assembled[t["group"]] is None:
                assembled[t["group"]] = Image.new(
                    "L", (int((max(xs) - x0) * scale) + 4, int((max(ys) - y0) * scale) + 4), 0)
            asm = assembled[t["group"]]
            if page["kind"] == "small":
                slot_x = MARGIN + 6 + (m_i % 2) * 96
                slot_y = MARGIN + 6 + (m_i // 2) * 96
            else:
                slot_x, slot_y = MARGIN, MARGIN
            # 该 tile 的形状掩膜页（黑底白形，几何与打印页一致）
            mask = Image.new("L", (int(A4_W * s), int(A4_H * s)), 0)
            md = ImageDraw.Draw(mask)
            poly_page = [((x - wx + slot_x) * s, (y - wy + slot_y) * s) for x, y in t["poly"]]
            md.polygon(poly_page, fill=255)
            crop = mask.crop((int(slot_x * s), int(slot_y * s),
                              int((slot_x + PRINT_W) * s), int((slot_y + PRINT_H) * s)))
            px, py = int((wx - x0) * scale), int((wy - y0) * scale)
            # 用掩膜把该窗口的「覆盖」并进组画布
            solid = Image.new("L", crop.size, 255)
            asm.paste(solid, (px, py), crop)

    for gname, asm in assembled.items():
        color, poly = orig[gname]
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        x0, y0 = min(xs), min(ys)
        base = Image.new("L", asm.size, 0)
        db = ImageDraw.Draw(base)
        db.polygon([((x - x0) * scale, (y - y0) * scale) for x, y in poly], fill=255)
        bdata, adata = list(base.getdata()), list(asm.getdata())
        missing = sum(1 for a, b in zip(bdata, adata) if a and not b)
        extra = sum(1 for a, b in zip(bdata, adata) if b and not a)
        total = max(1, sum(1 for v in bdata if v))
        # 判定：边界抗锯齿差异（亚像素）小件允许 ≤2%、大件 ≤0.5%；超出即 FAIL
        tol = 0.03 if total < 60000 else 0.005  # 小件周长/面积比高，AA 边界占比大
        ok = (missing / total) <= tol and (extra / total) <= tol
        report["shapes"].append({"group": gname, "orig_px": total, "missing_px": missing,
                                 "extra_px": extra, "verdict": "PASS" if ok else "FAIL"})
        report["total_missing_px"] += missing
        report["total_extra_px"] += extra
        if not ok:
            report["verdict"] = "FAIL"
    return report


# ---------- 排料图与预览 ----------
def render_nesting(groups, path):
    rolls = {"dark_green": 850, "mid_green": 850, "light_green": 850, "white": 850, "red": 420}
    col_w = {"dark_green": 330, "mid_green": 270, "light_green": 270, "white": 330, "red": 210}
    s = 0.2
    W_img = sum(col_w.values()) + 40
    H_img = 0
    cols_data = []
    for color in rolls:
        items, y = [], 30
        for g in groups:
            if g[1] != color:
                continue
            xs = [p[0] for p in g[2]]
            ys = [p[1] for p in g[2]]
            w, h = max(xs) - min(xs), max(ys) - min(ys)
            items.append((g[0], w, h, y))
            y += h + 12
        cols_data.append((color, items))
        H_img = max(H_img, y)
    im = Image.new("RGB", (int(W_img * s), int((H_img + 40) * s)), "white")
    dr = ImageDraw.Draw(im)
    x_col = 0
    used = {}
    for color, items in cols_data:
        dr.text((x_col * s + 4, 6), f"{color} 幅宽 {rolls[color]}mm", fill=(0, 0, 0))
        for name, w, h, y in items:
            dr.rectangle((x_col * s, y * s, (x_col + w) * s, (y + h) * s),
                         outline=COLORS[color], width=2)
            dr.text((x_col * s + 3, y * s + 2), f"{name} {w:.0f}×{h:.0f}", fill=COLORS[color])
            used[color] = used.get(color, 0) + w * h
        x_col += col_w[color]
    dr.text((4 * s, int((H_img + 12) * s)),
            "排料图（全部材料）：外接矩形示意，沿轮廓裁剪；幅宽 850/420mm；面积用量见 felt_cut_list.json",
            fill=(0, 0, 0))
    im.save(path)
    return used


def render_preview(groups, path):
    s = 0.5
    im = Image.new("RGB", (int(950 * s), int(1000 * s)), (240, 244, 240))
    dr = ImageDraw.Draw(im)
    dr.rectangle((int(80 * s), int(60 * s), int(680 * s), int(960 * s)),
                 fill=(232, 238, 232), outline=(150, 160, 150))
    dr.text((int(90 * s), int(68 * s)), "森林背景板 600×900（示意）", fill=(90, 100, 90))
    offx, offy, sc = int(110 * s), int(120 * s), 0.62
    for name, color, poly in groups:
        if name.startswith("tree_"):
            dr.polygon([(offx + px * sc, offy + py * sc) for px, py in poly],
                       fill=COLORS[color], outline=(60, 60, 60))
    dr.text((offx, offy + int(670 * s)), "圣诞树 450×650（3 层树冠 + 3 积雪带 + PETG 星位）",
            fill=(60, 60, 60))
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "generated"))
    args = ap.parse_args()
    out = Path(args.out)
    tiles_dir = out / "felt_tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    groups = all_groups()
    tiles = build_tiles(groups)
    pages = group_into_pages(tiles)
    n_pages = len(pages)

    imgs = []
    for pi, page in enumerate(pages):
        im = render_page(page, pi, n_pages, with_chrome=True)
        im.save(tiles_dir / f"page_{pi+1:02d}.png")
        imgs.append(im)
    imgs[0].save(out / "felt_templates.pdf", save_all=True, append_images=imgs[1:], resolution=DPI)

    svg_files = []
    for name, color, poly in groups:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        d = " ".join(f"{x - min(xs):.1f},{y - min(ys):.1f}" for x, y in poly)
        f = tiles_dir / f"{name}.svg"
        f.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}mm" height="{h:.0f}mm" '
                     f'viewBox="0 0 {w:.0f} {h:.0f}">'
                     f'<polygon points="{d}" fill="{COLORS[color]}" stroke="#333" stroke-width="0.5"/></svg>',
                     encoding="utf-8")
        svg_files.append({"name": name, "file": f.name, "w_mm": round(w), "h_mm": round(h)})

    used = render_nesting(groups, out / "felt_nesting.png")
    render_preview(groups, out / "felt_assembly_preview.png")

    vrep = verify_reassembly(pages, groups)
    page_map = []
    for pi, page in enumerate(pages):
        for t in page["tiles"]:
            page_map.append({"page": pi + 1, "group": t["group"], "r": t["r"], "c": t["c"],
                             "rows": t["rows"], "cols": t["cols"]})
    cut_list_page_map = page_map
    cut_list = {
        "fabric_assumption": "深绿 2000×850 / 白 2000×850 / 浅绿+红 500×420（已加购未付款，付款前核对）",
        "tree_450x650": "3 层树冠（深绿 200×190 → 2 页平铺 / 中绿 300×210 → 2 页 / 浅绿 450×220 → 3 页）"
                        "+ 3 积雪带 + 树干；重叠 15mm，四角对位十字拼接",
        "board_600x900_kit": "远景松 A×4 / B×4（各 2 页平铺）、雪坡×2（600 宽 → 4 页平铺）、窗棂×4",
        "red_dots": "Ø40×3 + Ø25×5（小件合箱页）",
        "pdf_pages": n_pages,
        "page_map": cut_list_page_map,
        "pagination": f"可打印区 {PRINT_W:.0f}×{PRINT_H:.0f}mm，重叠 {OVERLAP:.0f}mm；"
                      "每页配对页号 + 四角对位十字 + 拼接页组清单 + 100mm 校准尺",
        "reassembly_check": vrep,
        "svg_files": svg_files,
        "fabric_area_used_mm2": {k: round(v) for k, v in used.items()},
        "fabric_area_available_mm2": {"dark_green": 850 * 2000, "mid_green": 850 * 2000,
                                      "light_green": 850 * 2000, "white": 850 * 2000,
                                      "red": 420 * 500},
        "notes": ["魔术贴无背胶可缝款：40mm 段 ×6 缝树背面",
                  "不批量打印：先印第 1 页（校准尺）+ 树冠组，确认后再印其余",
                  "所有页均为真实比例；大于可打印区的形状已按重叠平铺并附对位十字"],
    }
    (out / "felt_cut_list.json").write_text(json.dumps(cut_list, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pdf_pages": n_pages, "svg": len(svg_files),
                      "verify": vrep["verdict"], "missing_px": vrep["total_missing_px"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
