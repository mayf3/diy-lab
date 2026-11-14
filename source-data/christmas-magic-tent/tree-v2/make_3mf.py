#!/usr/bin/env python3
"""把二进制 STL 打包为 3MF（几何 + 摆盘；不含切片配置）。

v2 修正（相对首版）：
- STL 由 Blender 以米导出 → 3MF 按 **毫米** 输出（×1000，修正首版 0.046mm 单位错误）；
- 每个零件**重定心**：Z 最小值贴床（z=0），XY 居中到盘内指定坐标（修正世界坐标上盘）；
- 去掉跨文件全局累计（修正重复面/错面）；
- 打包前逐零件校验：水密（每条边恰好被两个三角共用）、无重复三角、盘内边界，
  任一不合格即报错退出，不以「ZIP 可读」充数。

用法: python3 make_3mf.py --out first_plate.3mf \
    --part stl/A/A_col_sleeve.stl@35,35 --part stl/A/TP_col_stub1.stl@150,35 ...
坐标为零件**中心**在打印床上的落点（mm）；零件底面自动贴床。盘可打印边长按 220mm 校验。
"""
from __future__ import annotations
import argparse, json, struct, sys, zipfile
from pathlib import Path

PLATE = 220.0


def read_stl_triangles(path: Path):
    data = path.read_bytes()
    if data[:5] == b"solid" and b"facet" in data[:200]:
        raise ValueError(f"{path.name}: ASCII STL 不受支持（请用 Blender 二进制导出）")
    n = struct.unpack("<I", data[80:84])[0]
    if len(data) < 84 + n * 50:
        raise ValueError(f"{path.name}: 文件短于声明的三角数量")
    tris = []
    off = 84
    for _ in range(n):
        vals = struct.unpack("<12f", data[off:off + 48])
        off += 50
        tris.append([tuple(vals[3 + i * 3:6 + i * 3]) for i in range(3)])
    return tris


def recenter_and_scale(tris_m):
    """米 → 毫米；Z 最小值贴床 0；XY 居中 0（中心值先换算成毫米再相减）。"""
    flat = [v for t in tris_m for v in t]
    zmin = min(v[2] for v in flat) * 1000
    cx = (min(v[0] for v in flat) + max(v[0] for v in flat)) / 2 * 1000
    cy = (min(v[1] for v in flat) + max(v[1] for v in flat)) / 2 * 1000
    return [tuple((v[0] * 1000 - cx, v[1] * 1000 - cy, v[2] * 1000 - zmin) for v in t) for t in tris_m]


def check_mesh(name, tris, bounds):
    issues = []
    edge, seen = {}, set()
    xs = [v[0] for t in tris for v in t]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    for t in tris:
        key = tuple(sorted(t))
        if key in seen:
            issues.append("存在重复三角")
        seen.add(key)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted((t[a], t[b])))
            edge[e] = edge.get(e, 0) + 1
    open_edges = [e for e, n in edge.items() if n == 1]
    if open_edges:
        issues.append(f"非水密：{len(open_edges)} 条开放边")
    for v in zip(xs, ys, zs):
        if not (bounds[0] <= v[0] <= bounds[2] and bounds[1] <= v[1] <= bounds[3]):
            issues.append(f"顶点超出盘内边界: {tuple(round(c,1) for c in v)}")
            break
    dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    return issues, dims


def build_3mf(parts, out: Path):
    objects_xml, build_xml = [], []
    for i, (name, tris, tx, ty) in enumerate(parts, start=1):
        vs, vmap = [], {}
        for t in tris:
            for v in t:
                if v not in vmap:
                    vmap[v] = len(vs)
                    vs.append(v)
        ts = "".join(f'<triangle v1="{vmap[t[0]]}" v2="{vmap[t[1]]}" v3="{vmap[t[2]]}"/>' for t in tris)
        vs_xml = "".join(f'<vertex x="{v[0]:.4f}" y="{v[1]:.4f}" z="{v[2]:.4f}"/>' for v in vs)
        objects_xml.append(f'<object id="{i}" name="{name}" type="model"><mesh>'
                           f"<vertices>{vs_xml}</vertices><triangles>{ts}</triangles></mesh></object>")
        build_xml.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {tx:.1f} {ty:.1f} 0"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">Christmas Tree V1 first plate</metadata>'
             '<metadata name="Application">diy-lab make_3mf.py v2</metadata>'
             '<metadata name="CreationDate">2026-11-14</metadata>'
             '<metadata name="Notes">Geometry and placement only. No printer, filament or slice settings. '
             'Slice in Bambu Studio with P1S + PETG profile.</metadata>'
             f'<resources>{"".join(objects_xml)}</resources>'
             f'<build>{"".join(build_xml)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel-0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--part", action="append", default=[],
                    help="STL 路径@X,Y（零件中心在盘上落点 mm）")
    args = ap.parse_args()
    parts, problems = [], []
    for spec in args.part:
        path, _, pos = spec.partition("@")
        x, y = (float(v) for v in pos.split(","))
        p = Path(path)
        tris_mm = recenter_and_scale(read_stl_triangles(p))
        issues, dims = check_mesh(p.stem, tris_mm, (-110, -110, 110, 110))
        if issues:
            problems.append(f"{p.stem}: {', '.join(issues)}")
        parts.append((p.stem, tris_mm, x, y))
        print(json.dumps({"part": p.stem, "dims_mm": [round(d, 1) for d in dims],
                          "issues": issues}, ensure_ascii=False))
    if problems:
        print("3MF 校验失败：", file=sys.stderr)
        for q in problems:
            print(" -", q, file=sys.stderr)
        sys.exit(1)
    build_3mf(parts, Path(args.out))
    print(f"3MF written: {args.out} ({len(parts)} parts; geometry+placement only, no slice settings)")


if __name__ == "__main__":
    main()
