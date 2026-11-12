#!/usr/bin/env python3
"""Generate tent-side decoration STL/STEP-surrogates (V1) with assembly checks.

全部模型为纯三角面片（binary STL），可在 Bambu Studio 直接切片。
装配尺寸检查输出 assembly_check.json；背板厚度 BOARD_T 尚未实测，
默认按 5mm 瓦楞板假设，到货实测后改参数重跑。

用法: python3 make_decorations.py [--board-t 5.0] [--out generated]
"""
from __future__ import annotations
import json, math, struct, sys
from pathlib import Path

BOARD_T = 5.0          # 背板厚度假设值（待实测）
TOLERANCE = 0.6        # 卡扣内宽 = 背板厚 + 公差（双侧）
OUT = Path(__file__).resolve().parent / "generated"


def tri_strip(tris):
    buf = bytearray()
    buf += b"decoration v1".ljust(80, b"\0")
    buf += struct.pack("<I", len(tris))
    for n, a, b, c in tris:
        buf += struct.pack("<3f", *n)
        for v in (a, b, c):
            buf += struct.pack("<3f", *v)
    return bytes(buf)


def normal(a, b, c):
    ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
    vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
    n = (uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx)
    l = math.sqrt(sum(x*x for x in n)) or 1.0
    return tuple(x/l for x in n)


def extrude(points, depth, z0=0.0):
    """闭合多边形沿 Z 拉伸为带顶/底/侧面的实体三角面片列表。"""
    tris = []
    n = len(points)
    cx = sum(p[0] for p in points)/n
    cy = sum(p[1] for p in points)/n
    top, bot = [(x, y, z0+depth) for x, y in points], [(x, y, z0) for x, y in points]
    for i in range(n):
        a, b = top[i], top[(i+1) % n]
        tris.append((normal((cx, cy, z0+depth), b, a), (cx, cy, z0+depth), b, a))
        a2, b2 = bot[i], bot[(i+1) % n]
        tris.append((normal((cx, cy, z0), a2, b2), (cx, cy, z0), a2, b2))
    for i in range(n):
        p1, p2 = points[i], points[(i+1) % n]
        quad = [(p1[0], p1[1], z0), (p2[0], p2[1], z0), (p2[0], p2[1], z0+depth), (p1[0], p1[1], z0+depth)]
        tris.append((normal(*quad[:3]), *quad[:3]))
        tris.append((normal(quad[0], quad[3], quad[2]), quad[0], quad[3], quad[2]))
    return tris


def star_pts(r_out, r_in, points_n=5, cx=0.0, cy=0.0):
    pts = []
    for i in range(points_n*2):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi/2 + i*math.pi/points_n
        pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return pts


def snowflake_pts(r, arm_w, arms=6, cx=0.0, cy=0.0):
    pts = []
    for i in range(arms):
        a = i*2*math.pi/arms
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa, ca                     # 垂直方向
        pts.append((cx + ca*r*0.18, cy + sa*r*0.18))
        pts.append((cx + ca*r*0.30 + px*arm_w, cy + sa*r*0.30 + py*arm_w))
        pts.append((cx + ca*r*0.62 + px*arm_w*0.7, cy + sa*r*0.62 + py*arm_w*0.7))
        pts.append((cx + ca*r + px*arm_w*0.35, cy + sa*r + py*arm_w*0.35))
        pts.append((cx + ca*r, cy + sa*r))
        pts.append((cx + ca*r - px*arm_w*0.35, cy + sa*r - py*arm_w*0.35))
        pts.append((cx + ca*r*0.62 - px*arm_w*0.7, cy + sa*r*0.62 - py*arm_w*0.7))
        pts.append((cx + ca*r*0.30 - px*arm_w, cy + sa*r*0.30 - py*arm_w))
        pts.append((cx + ca*r*0.18, cy + sa*r*0.18))
    return pts


def gift_pts(w, d, lid_over=6.0):
    # 顶视图：盒体+横向丝带凸出（挤出后成丝带立体）
    h = d/2
    return [(-w/2, -d/2), (w/2, -d/2), (w/2, -h), (w/2+lid_over, -h),
            (w/2+lid_over, h), (w/2, h), (w/2, d/2), (-w/2, d/2),
            (-w/2, h), (-w/2-lid_over, h), (-w/2-lid_over, -h), (-w/2, -h)]


def clip_tris(board_t):
    """安全固定件：挂在背板上缘的倒钩卡扣（免胶免打孔）。"""
    inner = board_t + TOLERANCE
    hook = 8.0
    top_w = 60.0
    pts = [(0, 0), (inner, 0), (inner, hook), (inner+5, hook+6), (inner+5, hook+10),
           (-6, hook+10), (-6, 6), (0, 6)]
    depth = top_w
    tris = extrude(pts, depth, z0=-depth/2)
    # 旋转到 Z 上方向不必要——STL 只要求法线一致，直接输出即可
    return tris


def bbox_volume(tris):
    xs = [v[0] for t in tris for v in t[1:]]
    ys = [v[1] for t in tris for v in t[1:]]
    zs = [v[2] for t in tris for v in t[1:]]
    return (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))


def volume_cm3(tris):
    vol = 0.0
    for n, a, b, c in tris:
        vol += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6.0
    return abs(vol)/1000.0


def main():
    board_t = float(sys.argv[sys.argv.index("--board-t")+1]) if "--board-t" in sys.argv else BOARD_T
    out = Path(sys.argv[sys.argv.index("--out")+1]) if "--out" in sys.argv else OUT
    out.mkdir(parents=True, exist_ok=True)
    models = {
        "star_topper":      (star_pts(55, 22), 8.0),      # 树顶星：外径 110mm，厚 8mm
        "snowflake":        (snowflake_pts(48, 7), 5.0),  # 雪花：外径 96mm，厚 5mm
        "gift_box":         (gift_pts(60, 42, 6), 12.0),  # 礼物盒：60×42mm，厚 12mm
        "backboard_clip":   (None, 0),                    # 安全固定件：参数化卡扣
    }
    report = {"board_thickness_assumed_mm": board_t,
              "clip_inner_width_mm": board_t + TOLERANCE,
              "note": "BOARD_T 为 5mm 瓦楞板假设值；真实背板厚度实测后用 --board-t 重跑。切片需在 Bambu Studio 完成，本报告只是几何检查。",
              "models": {}}
    for name, (pts, depth) in models.items():
        tris = clip_tris(board_t) if pts is None else extrude(pts, depth)
        data = tri_strip(tris)
        (out / f"{name}.stl").write_bytes(data)
        bx, by, bz = bbox_volume(tris)
        report["models"][name] = {"stl": f"{name}.stl", "extents_mm": [round(bx, 1), round(by, 1), round(bz, 1)],
                                  "approx_solid_volume_cm3": round(volume_cm3(tris), 1),
                                  "triangles": len(tris)}
    report["models"]["backboard_clip"]["mount"] = f"挂在背板上缘，内宽 {board_t + TOLERANCE}mm（背板厚 {board_t}mm + 公差 {TOLERANCE}mm）"
    (out / "assembly_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
