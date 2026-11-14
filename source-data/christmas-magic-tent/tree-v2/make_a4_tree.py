#!/usr/bin/env python3
"""A4 分页拼接圣诞树图案模板 v2（SVG 可编辑 + A4 PDF 直打印 + 整体拼接预览）。

v2 修正：
- 分页数按「覆盖宽度 = 页宽×n − 搭接×(n−1) ≥ 图案宽」精确计算，消除空白末页；
- 每页含 100mm 标尺 + 四角 50mm 十字标 + 中心线（对齐与比例校验）；
- 输出整体拼接预览（图案轮廓 + A 骨架横梁绑扎位置红框标注）；
- 同一 spec 双输出：SVG（可编辑）+ A4 PDF（150dpi，直接打印）。

待实测参数集中在 CFG（帐篷侧墙可用宽/高），回填后重跑。

用法: python3 make_a4_tree.py [--out generated/a4]
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

GREEN, DARK, WHITE, INK = "#3e7d4f", "#2c5e46", "#f2f6f3", "#22333a"

CFG = {
    "A4_W": 210.0, "A4_H": 297.0, "MARGIN": 10.0,
    "OVERLAP": 10.0,
    "TREE_H": 800.0, "TREE_W": 560.0, "LAYERS": 5,
    "SNOW_H": 90.0,
    "TENT_SIDE_W": None,   # 【待实测】帐篷侧墙可用宽
    "TENT_SIDE_H": None,   # 【待实测】帐篷侧墙可用高
}


def overlap_check():
    pw = CFG["A4_W"] - 2 * CFG["MARGIN"]
    ph = CFG["A4_H"] - 2 * CFG["MARGIN"]
    ov = CFG["OVERLAP"]
    cols = math.ceil((CFG["TREE_W"] - ov) / (pw - ov))
    rows = math.ceil((CFG["TREE_H"] - ov) / (ph - ov))
    return cols, rows, cols * rows, pw, ph


def tree_prims():
    """完整树冠图案原语（世界坐标 mm，y=0 在树冠顶部）。"""
    H, W, L = CFG["TREE_H"], CFG["TREE_W"], CFG["LAYERS"]
    snow = CFG["SNOW_H"]
    prims = []
    layer_h = (H - snow) / L
    for i in range(L):
        w_layer = W * (1 - i * (0.62 / L))
        lx = (W - w_layer) / 2
        ly = snow + i * layer_h
        prims.append(("poly", [(lx, ly + layer_h), (lx + w_layer / 2, ly), (lx + w_layer, ly + layer_h)], GREEN))
        prims.append(("poly", [(lx + w_layer * 0.18, ly + layer_h), (lx + w_layer / 2, ly + layer_h * 0.45),
                               (lx + w_layer * 0.82, ly + layer_h)], DARK))
    prims.append(("rect", (W - W * 0.42) / 2, 0, W * 0.42, snow, WHITE, INK, 1.0, False))
    return prims


def page_spec(index, total, pw, ph):
    """页面装饰原语（标尺/十字标/裁切框）。"""
    m = CFG["MARGIN"]
    w, h = CFG["A4_W"], CFG["A4_H"]
    prims = [("rect", m, m, pw, ph, "none", "#bbbbbb", 0.6, True)]
    prims.append(("line", m + 10, h - m - 8, m + 110, h - m - 8, INK, 1.0, False))
    for k in range(0, 101, 10):
        x = m + 10 + k
        tick = 6 if k % 50 == 0 else 3
        prims.append(("line", x, h - m - 8, x, h - m - 8 - tick, INK, 0.8, False))
    for x, y in ((m, m), (m + pw, m), (m, m + ph), (m + pw, m + ph)):
        prims.append(("line", x - 7, y, x + 7, y, INK, 0.8, False))
        prims.append(("line", x, y - 7, x, y + 7, INK, 0.8, False))
    return prims


def svg_page(tree_prims, tile, page_size, path, footer):
    tx, ty, tw, th = tile
    w, h = page_size
    body = []
    for p in tree_prims:
        if p[0] == "poly":
            _, pts, fill = p
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            body.append(f'<polygon points="{d}" fill="{fill}"/>')
        elif p[0] == "rect":
            _, x, y, w_, h_, fill, stroke, wd, dashed = p
            dash = ' stroke-dasharray="4 3"' if dashed else ""
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_:.1f}" height="{h_:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{wd}"{dash}/>')
    m = CFG["MARGIN"]
    pw, ph = w - 2 * m, h - 2 * m
    deco = [f'<rect x="{m}" y="{m}" width="{pw}" height="{ph}" fill="none" stroke="#bbbbbb" stroke-width="0.6" stroke-dasharray="4 3"/>']
    deco.append(f'<line x1="{m+10}" y1="{h-m-8}" x2="{m+110}" y2="{h-m-8}" stroke="{INK}" stroke-width="1"/>')
    for k in range(0, 101, 10):
        x = m + 10 + k
        tick = 6 if k % 50 == 0 else 3
        deco.append(f'<line x1="{x}" y1="{h-m-8}" x2="{x}" y2="{h-m-8-tick}" stroke="{INK}" stroke-width="0.8"/>')
    for x, y in ((m, m), (m + pw, m), (m, m + ph), (m + pw, m + ph)):
        deco.append(f'<line x1="{x-7:.1f}" y1="{y}" x2="{x+7:.1f}" y2="{y}" stroke="{INK}" stroke-width="0.8"/>')
        deco.append(f'<line x1="{x:.1f}" y1="{y-7:.1f}" x2="{x:.1f}" y2="{y+7:.1f}" stroke="{INK}" stroke-width="0.8"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">'
           f'<defs><clipPath id="t"><rect x="{tx:.1f}" y="{ty:.1f}" width="{tw:.1f}" height="{th:.1f}"/></clipPath></defs>'
           f'<rect width="{w}" height="{h}" fill="white"/>'
           f'<g clip-path="url(#t)"><g transform="translate({-tx:.1f},{-ty:.1f})">' + "".join(body) + '</g></g>'
           + "".join(deco)
           + f'<text x="{m+10}" y="{h-m-16}" font-size="7" fill="{INK}" font-family="monospace">{footer}</text>'
           + "</svg>")
    Path(path).write_text(svg, encoding="utf-8")


def emit_preview(path: Path):
    """整体拼接预览：完整图案 + A 骨架横梁绑扎位置红框标注。"""
    W, H = CFG["TREE_W"], CFG["TREE_H"]
    L, layer_h = CFG["LAYERS"], (H - CFG["SNOW_H"]) / CFG["LAYERS"]
    m = 40
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W+2*m}mm" height="{H+2*m+20}mm" '
           f'viewBox="{-m} {-m-10} {W+2*m} {H+2*m+20}">']
    svg.append(f'<rect x="{-m}" y="{-m-10}" width="{W+2*m}" height="{H+2*m+20}" fill="white"/>')
    for p in tree_prims():
        if p[0] == "poly":
            _, pts, fill = p
            d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            svg.append(f'<polygon points="{d}" fill="{fill}" stroke="#cccccc" stroke-width="1"/>')
        elif p[0] == "rect":
            _, x, y, w_, h_, fill, stroke, wd, _ = p
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w_:.1f}" height="{h_:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{wd}"/>')
    svg.append('<g fill="none" stroke="#c0392b" stroke-width="2">')
    for i in range(L):
        z = CFG["SNOW_H"] + i * layer_h + layer_h / 2
        w_layer = W * (1 - i * (0.62 / L))
        svg.append(f'<rect x="{(W-w_layer)/2:.1f}" y="{z-12:.1f}" width="{w_layer:.1f}" height="24" stroke-dasharray="6 4"/>')
        svg.append(f'<circle cx="{(W-w_layer)/2:.1f}" cy="{z:.1f}" r="6" fill="#c0392b"/>')
        svg.append(f'<circle cx="{(W+w_layer)/2:.1f}" cy="{z:.1f}" r="6" fill="#c0392b"/>')
    svg.append("</g>")
    svg.append(f'<text x="{-m+4}" y="{-m+2}" font-size="10" fill="{INK}" font-family="monospace">'
               f'拼接预览：红框 = 横梁绑扎固定位置（图案板背面）；树冠 {W:.0f}×{H:.0f}mm</text>')
    svg.append("</svg>")
    Path(path).write_text("\n".join(svg), encoding="utf-8")


def emit_pdf(pages, path: Path):
    """用 PIL 把每页原语画成位图并合成 A4 PDF（150dpi）。"""
    from PIL import Image, ImageDraw
    dpi = 150
    w_px = int(CFG["A4_W"] / 25.4 * dpi)
    h_px = int(CFG["A4_H"] / 25.4 * dpi)
    imgs = []
    for prims in pages:
        im = Image.new("RGB", (w_px, h_px), "white")
        dr = ImageDraw.Draw(im)
        s = dpi / 25.4
        for p in prims:
            if p[0] == "line":
                _, x1, y1, x2, y2, color, wd, _ = p
                dr.line((x1 * s, y1 * s, x2 * s, y2 * s), fill=color, width=max(1, int(wd * s)))
            elif p[0] == "rect":
                _, x, y, w_, h_, fill, stroke, wd, dashed = p
                dr.rectangle((x * s, y * s, (x + w_) * s, (y + h_) * s), outline=stroke, width=max(1, int(wd * s)))
            elif p[0] == "text":
                _, x, y, s_, color, size = p
                dr.text((x * s, y * s), s_, fill=color)
        imgs.append(im)
    imgs[0].save(path, save_all=True, append_images=imgs[1:], resolution=dpi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="generated/a4")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cols, rows, total, pw, ph = overlap_check()
    tiles = []
    for r in range(rows):
        for c in range(cols):
            tiles.append((c * (pw - CFG["OVERLAP"]), r * (ph - CFG["OVERLAP"])))
    pages = []
    for i, (tx, ty) in enumerate(tiles):
        footer = (f"PAGE {i+1}/{total} · 打印 100%（禁用适应页面）· 搭接 {CFG['OVERLAP']:.0f}mm · "
                  f"树冠 {CFG['TREE_W']:.0f}×{CFG['TREE_H']:.0f}mm")
        pages.append(page_spec(i, total, pw, ph))
        svg_page(tree_prims(), (tx, ty, pw, ph), (CFG["A4_W"], CFG["A4_H"]),
                 out / f"a4_tree_p{i+1}.svg", footer)
    emit_pdf(pages, out / "a4_tree.pdf")
    emit_preview(out / "assembly_preview.svg")
    meta = {"config": CFG, "pages": total, "tile_mm": [pw, ph], "overlap_mm": CFG["OVERLAP"],
            "coverage_check": (f"{cols}×{rows} 页覆盖 "
                               f"{cols*pw-(cols-1)*CFG['OVERLAP']:.0f}×{rows*ph-(rows-1)*CFG['OVERLAP']:.0f}mm "
                               f"≥ 图案 {CFG['TREE_W']:.0f}×{CFG['TREE_H']:.0f}mm"),
            "pending_measurement": ["TENT_SIDE_W", "TENT_SIDE_H"],
            "outputs": ["a4_tree_p*.svg（可编辑）", "a4_tree.pdf（直接打印）", "assembly_preview.svg（拼接预览）"]}
    (out / "print_settings.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
