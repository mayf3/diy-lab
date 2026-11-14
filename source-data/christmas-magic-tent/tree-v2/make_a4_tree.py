#!/usr/bin/env python3
"""生成 A4 分页拼接的圣诞树图案模板（SVG，浏览器 100% 打印即为 1:1）。

待实测参数集中在 CFG，全部为显式占位：帐篷到货量尺后修改重跑。
用法: python3 make_a4_tree.py [--out generated]
"""
from __future__ import annotations
import json, sys
from pathlib import Path

CFG = {
    "A4_W": 210.0, "A4_H": 297.0, "MARGIN": 10.0,   # A4 纵向；打印时选「实际大小/100%」，禁用「适应页面」
    "OVERLAP": 10.0,                                  # 相邻页搭接宽度，对齐用十字标
    "TREE_H": 800.0,                                  # 树冠目标高度 mm（可改）
    "TREE_W": 560.0,                                  # 树冠底宽 mm（可改）
    "TRUNK_W": 90.0,                                  # 树干带高度 mm
    "SNOW_H": 90.0,                                   # 雪顶带高度 mm
    "TENT_SIDE_W": None,                              # 【待实测】帐篷侧墙可用宽
    "TENT_SIDE_H": None,                              # 【待实测】帐篷侧墙可用高
    "LAYERS": 5,                                      # 树冠分层
}

GREEN, DARK, WHITE, INK = "#3e7d4f", "#2c5e46", "#f2f6f3", "#22333a"


def tree_svg_fragment(x0, y0, w, h, layers, snow_h):
    """在 (x0,y0) 左上角画一棵分层树冠（SVG y 向下）。返回图案元素字符串。"""
    s = []
    lh = h / layers
    for i in range(layers):
        lw = w * (1 - i * (0.82 / layers))          # 越往上越窄
        lx = x0 + (w - lw) / 2
        ly = y0 + i * lh
        s.append(f'<path d="M {lx:.1f} {ly+lh:.1f} L {lx+lw/2:.1f} {ly:.1f} L {lx+lw:.1f} {ly+lh:.1f} Z" fill="{GREEN}"/>')
        s.append(f'<path d="M {lx:.1f} {ly+lh:.1f} L {lx+lw/2:.1f} {ly+lh*0.55:.1f} L {lx+lw:.1f} {ly+lh:.1f} Z" fill="{DARK}"/>')
    s.append(f'<rect x="{x0+w*0.14:.1f}" y="{y0+h-snow_h*0:.1f}" width="0" height="0"/>')
    # 雪顶带（顶层上方白色弧带）
    s.append(f'<rect x="{x0+w*0.30:.1f}" y="{y0-14:.1f}" width="{w*0.40:.1f}" height="{snow_h:.1f}" rx="8" fill="{WHITE}" stroke="{INK}" stroke-width="1"/>')
    return "\n".join(s)


def crosshair(x, y):
    return (f'<line x1="{x-8:.1f}" y1="{y:.1f}" x2="{x+8:.1f}" y2="{y:.1f}" stroke="{INK}" stroke-width="0.8"/>'
            f'<line x1="{x:.1f}" y1="{y-8:.1f}" x2="{x:.1f}" y2="{y+8:.1f}" stroke="{INK}" stroke-width="0.8"/>')


def page(idx, total, tile_x, tile_y, tile_w, tile_h, tree_box):
    w, h = CFG["A4_W"], CFG["A4_H"]
    m = CFG["MARGIN"]
    pw, ph = w - 2*m, h - 2*m
    inner = (f'<g clip-path="url(#tile{idx})">'
             + tree_svg_fragment(0, 0, CFG["TREE_W"], CFG["TREE_H"], CFG["LAYERS"], CFG["SNOW_H"])
             + '</g>')
    translate = f'translate({-(tile_x):.1f},{-(tile_y):.1f})'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">
  <defs><clipPath id="tile{idx}"><rect x="{tile_x:.1f}" y="{tile_y:.1f}" width="{tile_w:.1f}" height="{tile_h:.1f}"/></clipPath>
  <g id="tree{idx}">{tree_svg_fragment(0, 0, CFG["TREE_W"], CFG["TREE_H"], CFG["LAYERS"], CFG["SNOW_H"])}</g></defs>
  <rect x="0" y="0" width="{w}" height="{h}" fill="white"/>
  <rect x="{m}" y="{m}" width="{pw}" height="{ph}" fill="none" stroke="#bbbbbb" stroke-width="0.5" stroke-dasharray="4 3"/>
  <g transform="{translate}" clip-path="url(#tile{idx})">
    <use href="#tree{idx}"/>
  </g>
  <g>
    {crosshair(m, m)}{crosshair(m+pw, m)}{crosshair(m, m+ph)}{crosshair(m+pw, m+ph)}
    {crosshair(m+pw/2, m)}{crosshair(m+pw/2, m+ph)}
  </g>
  <text x="{m}" y="{h-4}" font-size="7" fill="{INK}" font-family="monospace">PAGE {idx+1}/{total} · 打印 100%（禁用适应页面）· 搭接 {CFG["OVERLAP"]:.0f}mm · 树冠 {CFG["TREE_W"]:.0f}×{CFG["TREE_H"]:.0f}mm</text>
  <text x="{m+pw-90:.1f}" y="{m+12:.1f}" font-size="7" fill="#999999" font-family="monospace">PLACEHOLDER · 待实测回填</text>
</svg>'''


def main():
    out = Path(sys.argv[sys.argv.index("--out")+1]) if "--out" in sys.argv else Path(__file__).resolve().parent / "generated" / "a4"
    out.mkdir(parents=True, exist_ok=True)
    pw = CFG["A4_W"] - 2*CFG["MARGIN"]
    ph = CFG["A4_H"] - 2*CFG["MARGIN"]
    cols = max(1, math.ceil(CFG["TREE_W"] / pw))
    rows = math.ceil((CFG["TREE_H"] + CFG["SNOW_H"]) / ph)
    tiles = [(c*pw - c*CFG["OVERLAP"], r*ph - r*CFG["OVERLAP"]) for r in range(rows) for c in range(cols)]
    pages = []
    for i, (tx, ty) in enumerate(tiles):
        pages.append(page(i, len(tiles), tx, ty, pw, ph, (0, 0, CFG["TREE_W"], CFG["TREE_H"])))
        (out / f"a4_tree_p{i+1}.svg").write_text(pages[-1], encoding="utf-8")
    meta = {"config": CFG, "pages": len(tiles), "tile_size_mm": [pw, ph], "overlap_mm": CFG["OVERLAP"],
            "pending_measurement": ["TENT_SIDE_W", "TENT_SIDE_H"],
            "print": ["A4 纵向", "缩放 100%（禁用「适应页面」/「适合纸张」）", "彩色输出", "四角十字标用于对齐",
                       "相邻页搭接 OVERLAP mm：先对齐十字标再粘贴"],
            "output_dir": str(out)}
    (out / "print_settings.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import math
    main()
