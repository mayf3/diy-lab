#!/usr/bin/env python3
"""把二进制 STL 打包为 3MF（几何 + 摆盘；不含切片配置）。

3MF 状态声明：本脚本生成的 3MF 只含网格几何与摆放位置，
**不含打印机/耗材/切片参数**；切片请在 Bambu Studio 导入后自行设置。

用法: python3 make_3mf.py --out first_plate.3mf \
    --part stl/A/A_joint_L1.stl@35,35 --part stl/A/A_col_sleeve1.stl@150,35 \
    --part stl/A/A_beam_L5.stl@30,170 --part stl/A/A_star.stl@150,150
"""
from __future__ import annotations
import argparse, struct, zipfile
from pathlib import Path


def read_stl(path: Path):
    """读取二进制 STL：每条记录 50 字节 = 法线(12) + 三顶点(36) + 属性(2)。"""
    verts, tris = [], {}
    data = path.read_bytes()
    n = struct.unpack("<I", data[80:84])[0]
    off = 84
    for _ in range(n):
        vals = struct.unpack("<12f", data[off:off + 48])
        off += 50
        idx = []
        for vi in range(3):
            v = tuple(round(vals[3 + vi * 3 + k], 4) for k in range(3))
            if v not in tris:
                tris[v] = len(verts)
                verts.append(v)
            idx.append(tris[v])
        tris_model.append(idx)
    return verts, tris_model


tris_model: list = []


def build_3mf(parts, out: Path):
    objects_xml, build_xml = [], []
    verts_all: list = []
    v_offset = 0
    for i, (name, stl_path, tx, ty) in enumerate(parts, start=1):
        verts, tris = read_stl(stl_path)
        vs = "".join(f'<vertex x="{v[0]:.4f}" y="{v[1]:.4f}" z="{v[2]:.4f}"/>' for v in verts)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
        objects_xml.append(
            f'<object id="{i}" name="{name}" type="model"><mesh>'
            f"<vertices>{vs}</vertices><triangles>{ts}</triangles></mesh></object>")
        build_xml.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {tx:.1f} {ty:.1f} 0"/>')
        v_offset += len(verts)
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">Christmas Tree V1 first plate</metadata>'
        '<metadata name="Application">diy-lab make_3mf.py</metadata>'
        '<metadata name="CreationDate">2026-11-14</metadata>'
        f'<resources>{"".join(objects_xml)}</resources>'
        f'<build>{"".join(build_xml)}</build></model>')
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel-0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--part", action="append", default=[],
                    help="STL 路径@X,Y（盘内坐标 mm，零件中心）")
    args = ap.parse_args()
    parts = []
    for spec in args.part:
        path, _, pos = spec.partition("@")
        x, y = (float(v) for v in pos.split(","))
        parts.append((Path(path).stem, Path(path), x, y))
    build_3mf(parts, Path(args.out))
    print(f"3MF written: {args.out} ({len(parts)} parts, geometry only — no slice settings)")


if __name__ == "__main__":
    main()
