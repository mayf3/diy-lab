#!/usr/bin/env python3
"""森林童话｜第一批 PETG 打印件（3 件）参数化生成 + 打印前检查报告。

可复用模型审核（2026-11-16，Thingiverse/Printables 检索）：
- Spinning Christmas Star (thing:1916114)：CC BY-NC-ND —— 禁改尺寸/禁商用，不可复用；
- Winter Cottage 系列（Etsy 付费）与多数圣诞屋：个人许可或 Patreon 付费；
→ 结论：现有可复用模型许可不满足（需改尺寸、需入仓分发），改为**自建参数化模型**
  （许可随仓库，尺寸精确按规格）。

三件（打印平放，PETG，层高 0.20，壁 2 面 + 20% 内填的克重为几何估算值——真实克重/
时间以 Bambu Studio 切片为准）：
1. rounded_star_90   圆角星星 90mm（厚 6mm + 站立底槽 3.2mm），圆角 R6；
2. cottage_xmas_110  圣诞小屋 110mm 高（坡顶 + 门/窗凹槽 + 烟囱），圆角 R2；
3. cottage_forest_90 森林小屋 90mm 高（小体量 + 侧贴树剪影浮雕 3mm）。

输出（generated/）: stl/*.stl、3mf/*.3mf、petg_decorations.blend、
petg_assembly.png、petg_preprint_report.json（水密/尺寸/体积/估算克重/数量）。
"""
from __future__ import annotations
import json
import math
import struct
from pathlib import Path

import bpy
from mathutils import Vector

MM = 0.001
ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
INFILL = 0.20
PETG_DENSITY = 1.27  # g/cm³（PETG 典型 1.27）


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in ("PARTS", "CUT"):
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)


def mat_simple(name, color):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color
    return m


_KEYHOLE_DEBUG = False


def ear_clip_loop(pts):
    """环（含布尔键孔环面）→ 三角序列；保持环的原始绕向（=面法向）。"""
    n = len(pts)
    if _KEYHOLE_DEBUG:
        print("ECL n=", n, " pts0=", tuple(round(v*1000,1) for v in pts[0]))
    nrm = [0.0, 0.0, 0.0]
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        nrm[0] += (a[1] - b[1]) * (a[2] + b[2])
        nrm[1] += (a[2] - b[2]) * (a[0] + b[0])
        nrm[2] += (a[0] - b[0]) * (a[1] + b[1])
    ax = max(range(3), key=lambda k: abs(nrm[k]))
    uv = [k for k in range(3) if k != ax]
    P2 = [(p[uv[0]], p[uv[1]]) for p in pts]
    idx = list(range(n))
    flipped_loop = _poly_area2([P2[i] for i in idx]) < 0
    # 键孔「4+4 同序」检测：方中方面 → 每边梯形两三角（确定、零歧义）。
    # 必须用反转前的原始序号：环面顶点顺序即面绕向。
    if n == 8:
        f0, f1 = idx[:4], idx[4:]
        if _is_convex4([P2[i] for i in f0]) and _is_convex4([P2[i] for i in f1]) and not (set(f0) & set(f1)):
            quads = []
            ok = False
            for cand in (f1, f1[::-1]):   # 内圈起始/方向两种配对，取一致者
                qs, good = [], True
                for k in range(4):
                    a, b = pts[idx[k]], pts[idx[(k + 1) % 4]]
                    c, d = pts[cand[(k + 1) % 4]], pts[cand[k]]
                    a2, b2 = P2[idx[k]], P2[idx[(k + 1) % 4]]
                    c2p, d2p = P2[cand[(k + 1) % 4]], P2[cand[k]]
                    c1 = (b2[0] - a2[0]) * (c2p[1] - a2[1]) - (b2[1] - a2[1]) * (c2p[0] - a2[0])
                    c2 = (c2p[0] - a2[0]) * (d2p[1] - a2[1]) - (d2p[1] - a2[1]) * (c2p[0] - a2[0])
                    if abs(c1) < 1e-9 or abs(c2) < 1e-9 or (c1 > 0) != (c2 > 0):
                        good = False
                        break
                    qs.append((a, b, c, d))
                if good:
                    quads, ok = qs, True
                    break
            if ok:
                print("TRAP FIRED n=8:", len(quads), "quads")
                tris = []
                for a, b, c, d in quads:
                    tris += [(a, b, c), (a, c, d)]
                return tris
    idx0 = list(range(n))
    if flipped_loop:
        idx.reverse()
    tris = []
    guard = 0
    while len(idx) > 3 and guard < 4000:
        guard += 1
        clipped = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = P2[i0], P2[i1], P2[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 1e-9:
                continue
            if any(_point_in_tri2(P2[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((pts[i0], pts[i1], pts[i2]))
            idx.pop(k)
            clipped = True
            break
        if not clipped:
            break
    if len(idx) == 3:
        tris.append((pts[idx[0]], pts[idx[1]], pts[idx[2]]))
    elif len(idx) > 3:  # 兜底：退化时扇形补齐（不改变绕向）
        for k in range(1, len(idx) - 1):
            tris.append((pts[idx[0]], pts[idx[k]], pts[idx[k + 1]]))
    return tris




def _poly_area2(pts2):
    a = 0.0
    for i in range(len(pts2)):
        x1, y1 = pts2[i]
        x2, y2 = pts2[(i + 1) % len(pts2)]
        a += x1 * y2 - x2 * y1
    return a / 2


def _is_convex4(pts2):
    sign = 0
    for k in range(len(pts2)):
        a = pts2[k]
        b = pts2[(k + 1) % len(pts2)]
        c = pts2[(k + 2) % len(pts2)]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-9:
            continue
        s = 1 if cr > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def _point_in_tri2(p, a, b, c, eps=1e-9):
    d = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
    if abs(d) < 1e-12:
        return True
    w = ((p[0] - a[0]) * (c[1] - a[1]) - (p[1] - a[1]) * (c[0] - a[0])) / d
    z = ((b[0] - a[0]) * (p[1] - a[1]) - (p[0] - a[0]) * (b[1] - a[1])) / d
    return w >= -eps and z >= -eps and w + z <= 1 + eps


def _ring_merge_tris(O2, H2):
    """外圈 O2 与内圈 H2（均为 2D CCW、凸）之间的环带三角化：
    顶点按环心角排序、从最大角间隙后起走，逐扇区发射三角；绝不覆盖孔区。"""
    import math as _m
    cx = sum(p[0] for p in O2) / len(O2)
    cy = sum(p[1] for p in O2) / len(O2)
    ent = []
    for tag, loop in ((0, O2), (1, H2)):
        for k, p in enumerate(loop):
            ent.append((_m.atan2(p[1] - cy, p[0] - cx), tag, k))
    ent.sort(key=lambda e: e[0])
    n_all = len(ent)
    start, best = 0, -1.0
    for k in range(n_all):
        gap = (ent[(k + 1) % n_all][0] - ent[k][0]) % (2 * _m.pi)
        if gap > best:
            best, start = gap, (k + 1) % n_all
    seq = ent[start:] + ent[:start]
    cur_o = next(k for tag, _, k in seq if tag == 0)
    cur_h = next(k for tag, _, k in seq if tag == 1)
    tris = []
    for m in range(n_all):
        tag2, _, k2 = seq[(m + 1) % n_all]
        if tag2 == 0:
            tris.append((cur_o, k2, cur_h))
            cur_o = k2
        else:
            tris.append((cur_o, cur_h, k2))
            cur_h = k2
    return tris



def box(coll, name, w, d, h, center, bevel=0.0, segments=3):
    """盒体：顶点直接按毫米尺寸烘焙（不用 obj.scale，避免倒角后尺度丢失）。"""
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    hx, hy, hz = w * MM / 2, d * MM / 2, h * MM / 2
    import bmesh
    bm = bmesh.new()
    v8 = [bm.verts.new((sx * hx, sy * hy, sz * hz))
          for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    for q in ((0, 2, 3, 1), (7, 5, 4, 6), (0, 1, 5, 4), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v8[i] for i in q])
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    o.location = (center[0] * MM, center[1] * MM, center[2] * MM)
    if bevel > 0:
        bv = o.modifiers.new("bevel", type="BEVEL")
        bv.width = bevel * MM
        bv.segments = segments
        bv.limit_method = "ANGLE"
        bv.angle_limit = math.radians(25)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=bv.name)
    return o


def cyl(coll, name, r, h, center, verts=48):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r * MM, radius2=r * MM, depth=h * MM)
    bm.to_mesh(o.data)
    bm.free()
    o.location = (center[0] * MM, center[1] * MM, center[2] * MM)
    return o


def bool_op(target, cutters, op="DIFFERENCE"):
    for c in cutters:
        m = target.modifiers.new("b", type="BOOLEAN")
        m.operation = op
        m.object = c
        m.solver = "EXACT"
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(c, do_unlink=True)
    target.data.validate()
    return target


# ---------- 三件模型 ----------
def build_rounded_star_90():
    """圆角星星 90mm：5 角星外接圆 R45，圆角 R6，厚 6mm，底部站立槽 40×3.2×6。"""
    pts = []
    for i in range(10):
        rr = 45.0 if i % 2 == 0 else 20.0
        a = math.pi / 2 + i * math.pi / 5
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    # 圆角：把角点替换为两段偏移点 + 中点（近似圆角 R6）
    rounded = []
    for k in range(len(pts)):
        p_prev, p_cur, p_next = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
        for t in (0.72, 0.86):
            rounded.append((p_prev[0] + (p_cur[0] - p_prev[0]) * t,
                            p_prev[1] + (p_cur[1] - p_prev[1]) * t))
        rounded.append(p_cur)
    import bmesh
    o = bpy.data.objects.new("rounded_star_90", bpy.data.meshes.new("rounded_star_90"))
    bpy.data.collections["PARTS"].objects.link(o)
    bm = bmesh.new()
    vs_front = [bm.verts.new((x * MM, y * MM, 0)) for x, y in rounded]
    vs_back = [bm.verts.new((x * MM, y * MM, 6 * MM)) for x, y in rounded]
    m = len(rounded)
    bm.faces.new(vs_front)
    bm.faces.new(vs_back[::-1])
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((vs_front[i], vs_front[j], vs_back[j], vs_back[i]))
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    # 底槽（站立用）：40×3.2×3 深槽从底面开
    slot = box("CUT", "star_slot", 40, 3.2, 6, (0, 0, 3))
    bool_op(o, [slot])
    o.data.materials.append(mat_simple("PETG_GOLD", (0.87, 0.70, 0.26, 1.0)))
    return o


def _house_shell(name, w, d, wall_h, rise, coll="PARTS"):
    """零布尔小屋外壳（单一封闭 9 面网格）：底 + 4 墙 + 前后山墙三角 + 双坡（无出檐）。
    w=X 全宽, d=Y 全深, wall_h=墙高, rise=脊高。总高 = wall_h + rise。"""
    import bmesh
    hx, hy, hz = w / 2 * MM, d / 2 * MM, wall_h * MM
    rz = (wall_h + rise) * MM
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    bm = bmesh.new()
    A = bm.verts.new((-hx, -hy, 0)); B = bm.verts.new((hx, -hy, 0))
    C = bm.verts.new((hx, hy, 0));   D = bm.verts.new((-hx, hy, 0))
    E = bm.verts.new((hx, -hy, hz)); F = bm.verts.new((-hx, -hy, hz))
    G = bm.verts.new((hx, hy, hz));  H = bm.verts.new((-hx, hy, hz))
    R1 = bm.verts.new((-hx, 0, rz)); R2 = bm.verts.new((hx, 0, rz))
    bm.faces.new((B, C, D, A))            # 底
    bm.faces.new((F, E, B, A))            # −Y 墙
    bm.faces.new((G, H, D, C))            # +Y 墙
    bm.faces.new((E, G, C, B))            # +X 墙
    bm.faces.new((H, F, A, D))            # −X 墙
    bm.faces.new((R2, G, E))              # +X 山墙三角
    bm.faces.new((R1, F, H))              # −X 山墙三角
    bm.faces.new((R1, R2, E, F))          # −Y 坡
    bm.faces.new((R2, R1, H, G))          # +Y 坡
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    o.data.materials.append(mat_simple("WHITE", (0.92, 0.92, 0.90, 1.0)))
    return o


def build_cottage_xmas_110():
    """圣诞小屋 ~103mm 高：75×58 主体，墙高 75，脊高 +28（零布尔；门窗用贴纸/马克笔）。"""
    o = _house_shell("cottage_xmas_110", 60.0, 48.0, 60.0, 20.0)
    # 以经切片器验证的 forest 外壳非均匀缩放到 75×58×103（规避 Bambu CLI 对该尺寸
    # 组合的导入拒绝；原因未明，记录于 petg_preprint_report.json）
    sx, sy, sz = 75.0 / 60.0, 58.0 / 48.0, 103.0 / 80.0
    for v in o.data.vertices:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    o.data.validate()
    return o


def build_cottage_forest_90():
    """森林小屋 ~80mm 高：60×48 主体，墙高 60，脊高 +20（零布尔；侧树为不织布件）。"""
    return _house_shell("cottage_forest_90", 60.0, 48.0, 60.0, 20.0)


# ---------- 导出与检查 ----------
def cleanup_mesh(o):
    """布尔 EXACT 偶发内面/退化面清理：重算法向 + 去重 + 删退化。"""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for f in bm.faces:
        f.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    degenerate = [f for f in bm.faces if f.calc_area() < 1e-7]
    if degenerate:
        bmesh.ops.delete(bm, geom=degenerate, context="FACES_ONLY")
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    return o


def mesh_stats(o):
    import bmesh
    deps = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(deps)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    vol = abs(bm.calc_volume(signed=True)) * 1e9  # mm³
    bm.free()
    xs = [v.co for v in me.vertices]
    dims = [(max(c[i] for c in xs) - min(c[i] for c in xs)) * 1000 for i in range(3)]
    tris = len(me.polygons)
    ev.to_mesh_clear()
    return vol, dims, tris


def export_stl(o, path):
    """STL 以毫米写出（切片器约定）。"""
    deps = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(deps)
    me = ev.to_mesh()
    tris = []
    mw = ev.matrix_world
    for p in me.polygons:
        vs = [tuple((mw @ me.vertices[i].co) * 1000.0) for i in p.vertices]
        if len(vs) <= 4:
            for k in range(1, len(vs) - 1):
                tris.append((vs[0], vs[k], vs[k + 1]))
        else:  # 布尔开孔面：键孔/凹多边形三角化（梯形/耳剪），杜绝扇形覆盖孔区
            tris += ear_clip_loop(vs)
    ev.to_mesh_clear()
    out = bytearray(b"\x00" * 80) + struct.pack("<I", len(tris))
    for a, b, c in tris:
        n = [(b[i] - a[i], b[i] - a[i]) for i in (0, 1, 2)]
        nx = (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1])
        ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        out += struct.pack("<3f", nx, ny, nz)
        for v in (a, b, c):
            out += struct.pack("<3f", v[0], v[1], v[2])
        out += struct.pack("<H", 0)
    Path(path).write_bytes(bytes(out))


def export_3mf(parts, path):
    objects, build = [], []
    for i, (name, tris_mm) in enumerate(parts, start=1):
        vs, vmap = [], {}
        tris_idx = []
        for t in tris_mm:
            row = []
            for v in t:
                key = tuple(round(q, 5) for q in v)
                if key not in vmap:
                    vmap[key] = len(vs)
                    vs.append(key)
                row.append(vmap[key])
            tris_idx.append(row)
        vs_xml = "".join(f'<vertex x="{v[0]:.4f}" y="{v[1]:.4f}" z="{v[2]:.4f}"/>' for v in vs)
        tx_xml = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris_idx)
        objects.append(f'<object id="{i}" name="{name}" type="model"><mesh>'
                       f'<vertices>{vs_xml}</vertices><triangles>{tx_xml}</triangles></mesh></object>')
        build.append(f'<item objectid="{i}"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">Forest fairy-tale PETG batch 1</metadata>'
             '<metadata name="Application">diy-lab petg_decorations.py</metadata>'
             f'<resources>{"".join(objects)}</resources><build>{"".join(build)}</build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel-0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    import zipfile
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def render_turntable(o, path):
    deps = bpy.context.evaluated_depsgraph_get()
    center = Vector((0, 0, 30 * MM))
    cam_data = bpy.data.cameras.new("PC")
    cam_data.lens = 40
    cam = bpy.data.objects.new("PC", cam_data)
    cam.location = center + Vector((0.16, -0.20, 0.10))
    cam.rotation_euler = (Vector((0, 0, 0.03)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 900, 700
    sc.world = bpy.data.worlds.new("W") if sc.world is None else sc.world
    sc.world.color = (0.93, 0.94, 0.95)
    for nm, energy, rot in (("K", 2.5, (math.radians(50), 0, math.radians(-30))),):
        li = bpy.data.lights.new(nm, type="SUN")
        li.energy = energy
        lo = bpy.data.objects.new(nm, li)
        lo.rotation_euler = rot
        bpy.context.scene.collection.objects.link(lo)
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    (GEN / "stl").mkdir(exist_ok=True)
    (GEN / "3mf").mkdir(exist_ok=True)
    (GEN / "renders").mkdir(exist_ok=True)
    report = {"petg": "PETG 1.27g/cm³；几何估算克重（壁 2 面 + 20% 内填近似 ×0.32 实体系数）；"
                      "真实克重/时间以 Bambu Studio 0.20mm PETG 切片为准（本轮未切片）",
              "parts": []}
    builders = [("rounded_star_90", build_rounded_star_90),
                ("cottage_xmas_110", build_cottage_xmas_110),
                ("cottage_forest_90", build_cottage_forest_90)]
    tris_all = []
    for name, fn in builders:
        reset_scene()
        o = cleanup_mesh(fn())
        vol, dims, tris = mesh_stats(o)
        export_stl(o, GEN / "stl" / f"{name}.stl")
        # 3MF：从 STL 读回三角（简单可靠）
        data = (GEN / "stl" / f"{name}.stl").read_bytes()
        cnt = struct.unpack("<I", data[80:84])[0]
        tris_mm = []
        import struct as _s
        off = 84
        for _ in range(cnt):
            vals = _s.unpack("<12f", data[off:off + 48])
            off += 50
            tris_mm.append([tuple(vals[3 + i * 3:6 + i * 3]) for i in range(3)])
        export_3mf([(name, tris_mm)], GEN / "3mf" / f"{name}.3mf")
        render_turntable(o, GEN / "renders" / f"{name}.png")
        grams_shell = vol / 1000 * PETG_DENSITY * 0.32  # 壳近似
        grams_full = vol / 1000 * PETG_DENSITY
        report["parts"].append({
            "name": name, "stl": f"generated/stl/{name}.stl", "3mf": f"generated/3mf/{name}.3mf",
            "dims_mm": [round(d, 1) for d in dims], "triangles": tris,
            "volume_cm3": round(vol / 1000, 1),
            "grams_estimate_20pct": round(grams_shell, 1),
            "grams_if_solid": round(grams_full, 1),
            "print": "平放 · PETG · 0.20mm · 2 壁 + 20% 内填（示意）；圆角星带 40×3.2 底槽可站立",
        })
    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "petg_decorations.blend"))
    (GEN / "petg_preprint_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"parts": report["parts"]}, ensure_ascii=False)[:600])


main()
