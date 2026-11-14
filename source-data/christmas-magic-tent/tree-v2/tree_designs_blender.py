#!/usr/bin/env python3
"""圣诞魔法小屋｜帐篷旁圣诞树 V2：真实可拆装接口（Blender 5.2 headless）。

v2 相对 v1（c59a5cc）的结构修正：
- 梁端圆榫 Ø16×24 + 梁节点侧圆插座（Ø16.4×26）+ 2×M4 顶丝 —— 可拆装横梁连接；
- 立柱套筒：外 40×40×70，内方孔 30.7 贯穿 + 2×M4 顶丝 —— 立柱对接；
- 基座节点：顶部立柱插座 + ±X 脚架圆榫插座 + 4×M4；
- 树顶帽：下接立柱 + 上承星星圆榫 + 2×M4；
- 图案板固定：横梁前侧面 Ø4 绑扎孔 ×2/根 —— 魔术贴/棉绳绑扎纸板（免胶免打孔）；
- 脚架 420 与横撑 460 分段（205/225 + 套筒）适配 P1S 256mm 床；
- 「脚架折叠」表述已删除（无铰链机构，脚架为插装分段）。

公差口径：方孔总间隙 0.8mm（单边 0.4）；圆孔总间隙 0.4mm（单边 0.2，Ø16 榫 → Ø16.4 孔）。

用法:
  blender --background --python tree_designs_blender.py -- --stage geometry|render|anim|all
输出: generated/{stl,blends,stats.json,assembly_tree_check.json} + renders_local/*.png
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Euler

MM = 0.001
ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
RENDERS = ROOT / "renders_local"

# ---------- 设计参数（mm） ----------
TOL_SQ_TOTAL = 0.8     # 方孔总间隙（单边 0.4）
TOL_RD_TOTAL = 0.4     # 圆孔总间隙（单边 0.2）
COL = 30.0
BEAM = 24.0
TENON_D, TENON_L = 16.0, 24.0
SCREW_D, SCREW_SEAT = 4.2, 7.5
A = dict(SEG=265.0, SEG_N=3, LAYERS=5, LAYER_H=140.0,
         FOOT_SEG=205.0, FOOT_TAIL=123.0, SPREAD_HALF=225.0)
B = dict(SEG=204.0, SEG_N=4, TIERS=3, TIER_START=210.0, TIER_PITCH=215.0,
         BRANCH_R=[190.0, 160.0, 130.0], BRANCH_N=6, FOOT3=340.0)
TENT = (1650.0, 1050.0, 1350.0)  # 已购买；三向尺寸待实测

PETG = (0.72, 0.76, 0.72, 1.0)
GREEN = (0.16, 0.42, 0.24, 1.0)
WHITE = (0.92, 0.94, 0.93, 1.0)
RED = (0.66, 0.17, 0.12, 1.0)
STAR = (0.91, 0.72, 0.22, 1.0)
TENTC = (0.72, 0.82, 0.80, 1.0)
COLORS = {"PETG": PETG, "GREEN": GREEN, "WHITE": WHITE, "RED": RED,
          "STAR": STAR, "TENT": TENTC, "CUT": (1.0, 0.1, 0.1, 1.0)}
COLLECTIONS = ("A", "B", "A_X", "A_T", "B_X", "B_T", "TENT", "CUT", "TP", "first_plate")
screw_seats = []


# ---------- 基础工具 ----------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in COLLECTIONS:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)


def mat(name, color):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    m.diffuse_color = color
    return m


def new_obj(name, coll):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    return o


def box(coll, name, w, d, h, center=(0, 0, 0), color_name="PETG"):
    """mm；center 为外接盒中心（位置在调用方换算为米后写入）。"""
    o = new_obj(name, coll)
    hx, hy, hz = w / 2000, d / 2000, h / 2000
    me = o.data
    me.from_pydata([
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)],
        [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    me.validate()
    o.data.materials.append(mat(color_name, COLORS[color_name]))
    return o


def place(o, center_mm):
    o.location = (center_mm[0] * MM, center_mm[1] * MM, center_mm[2] * MM)
    return o


def cyl_mesh(o, r, h, center, axis="Z"):
    me = o.data
    n = 28
    rr, hh = r * MM, h * MM / 2
    cx, cy, cz = center[0] * MM, center[1] * MM, center[2] * MM
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = rr * math.cos(a), rr * math.sin(a)
        if axis == "Z":
            verts += [(cx + ca, cy + sa, cz - hh), (cx + ca, cy + sa, cz + hh)]
        elif axis == "X":
            verts += [(cx - hh, cy + ca, cz + sa), (cx + hh, cy + ca, cz + sa)]
        else:
            verts += [(cx + ca, cy - hh, cz + sa), (cx + ca, cy + hh, cz + sa)]
    for i in range(n):
        j = (i + 1) % n
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    faces.append(tuple(range(0, 2 * n, 2))[::-1])
    faces.append(tuple(range(1, 2 * n, 2)))
    me.from_pydata(verts, [], faces)
    me.validate()
    return o


def cyl(coll, name, r, h, center, axis="Z"):
    o = new_obj(name, coll)
    cyl_mesh(o, r, h, center, axis)
    o.data.materials.append(mat("PETG", PETG))
    return o


def bool_op(target, cutters, op="DIFFERENCE"):
    for c in cutters:
        m = target.modifiers.new("bool", type="BOOLEAN")
        m.operation = op
        m.object = c
        m.solver = "EXACT"
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_apply(modifier=m.name)
        bpy.data.objects.remove(c, do_unlink=True)
    return target


def finish(part, color_name="PETG", coll="A"):
    part.data.materials.append(mat(color_name, COLORS[color_name]))
    if coll not in [c.name for c in part.users_collection]:
        bpy.data.collections[coll].objects.link(part)
    return part


def screw(part, name, center, axis="Z", d=SCREW_D, depth=14.0):
    """M4 顶丝孔（Ø4.2×14）贯穿登记；数量与孔位一一对应。"""
    cutter = cyl("CUT", name + "_hole", d / 2, depth + 6, center, axis)
    bool_op(part, [cutter])
    screw_seats.append({"part": part.name, "name": name, "mm": list(center), "axis": axis})
    return part


# ---------- 接口件（真实结构） ----------
def make_col_segment(name, length, coll="A"):
    return finish(box(coll, name, COL, COL, length, (0, 0, length / 2)), coll=coll)


def make_col_sleeve(name, coll="A"):
    o = box("CUT", name, 40, 40, 70, (0, 0, 0))
    hole = box("CUT", name + "_hole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 74, (0, 0, 0))
    bool_op(o, [hole])
    screw(o, name + "_sX", (20 - 1.8, 0, -14), axis="X")
    screw(o, name + "_sX2", (-20 + 1.8, 0, 14), axis="X")
    return finish(o, coll=coll)


def make_beam(name, length, coll="A", tie_holes=True):
    """横梁：24×24×length 梁身（中心=内端圆榫端面）+ 圆榫 Ø16×24 + 前侧 2×Ø4 绑扎孔。"""
    o = box(coll, name, length, BEAM, BEAM, (length / 2 + TENON_L, 0, 0))
    ten = cyl("CUT", name + "_tenon", TENON_D / 2, TENON_L, (TENON_L / 2, 0, 0), axis="X")
    bool_op(o, [ten], op="UNION")
    if tie_holes:
        for frac in (0.25, 0.75):
            c = cyl("CUT", name + f"_tie{frac}", 2.0, BEAM + 6, (TENON_L + length * frac, 0, 0), axis="Y")
            bool_op(o, [c])
    return o


def make_beam_joint(name, coll="A"):
    """横梁节点：46×46×36；竖孔过立柱（30.7×40）；±X 圆插座（Ø16.4×26）；顶底各 1×M4。"""
    o = box("CUT", name, 46, 46, 36, (0, 0, 0))
    cutters = [box("CUT", name + "_colhole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 44, (0, 0, 0))]
    for side in (-1, 1):
        cutters.append(cyl("CUT", name + f"_soc{side}", (TENON_D + TOL_RD_TOTAL) / 2, 30,
                           (side * (23 - 13), 0, 0), axis="X"))
    bool_op(o, cutters)
    screw(o, name + "_sTop", (0, 0, 18 - 1.4), axis="Z", depth=10)
    screw(o, name + "_sBot", (0, 0, -18 + 1.4), axis="Z", depth=10)
    return finish(o, coll=coll)


def make_base_joint(name, coll="A"):
    """基座节点：46×46×60；顶孔接立柱；±X 圆插座接脚架榫；4×M4。"""
    o = box("CUT", name, 46, 46, 60, (0, 0, 0))
    cutters = [box("CUT", name + "_colhole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 46, (0, 0, 7))]
    for side in (-1, 1):
        cutters.append(cyl("CUT", name + f"_soc{side}", (TENON_D + TOL_RD_TOTAL) / 2, 30,
                           (side * (23 - 13), 0, -8), axis="X"))
    bool_op(o, cutters)
    screw(o, name + "_sCol", (0, 0, 30 - 1.2), axis="Z", depth=10)
    screw(o, name + "_sFx", (-20 + 1.8, 0, -14), axis="X")
    screw(o, name + "_sFx2", (20 - 1.8, 0, -14), axis="X")
    screw(o, name + "_sFy", (0, -20 + 1.8, -10), axis="Y", depth=10)
    return finish(o, coll=coll)


def make_star_cap(name, coll="A"):
    """树顶帽：下孔接立柱，上孔承星星圆榫（Ø16.4×26），2×M4。"""
    o = box("CUT", name, 40, 40, 34, (0, 0, 0))
    cutters = [box("CUT", name + "_colhole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 40, (0, 0, -3)),
               cyl("CUT", name + "_ssoc", (TENON_D + TOL_RD_TOTAL) / 2, 26, (0, 0, 8), axis="Z")]
    bool_op(o, cutters)
    screw(o, name + "_sX", (-20 + 1.8, 0, 8), axis="X")
    screw(o, name + "_sX2", (20 - 1.8, 0, -8), axis="X")
    return finish(o, coll=coll)


def make_star(name, r_out=70.0, depth=10.0, coll="A", tenon=True):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_out * 0.42
        a = math.pi / 2 + i * math.pi / 5
        pts.append((r * math.cos(a), r * math.sin(a)))
    verts = [(x * MM, y * MM, 0) for x, y in pts] + [(x * MM, y * MM, depth * MM) for x, y in pts]
    n = len(pts)
    faces = [list(range(n)), [n + i for i in range(n)][::-1]]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    o = new_obj(name, coll)
    o.data.from_pydata(verts, [], faces)
    o.data.validate()
    if tenon:
        ten = cyl("CUT", name + "_tenon", TENON_D / 2, 22, (0, 0, -11), axis="Z")
        bool_op(o, [ten], op="UNION")
    o.data.materials.append(mat("STAR", STAR))
    return o


def make_foot_leg(name, length, coll="A", tenon_end="inner"):
    o = box(coll, name, length, BEAM, BEAM, (length / 2, 0, 0))
    if tenon_end == "inner":
        ten = cyl("CUT", name + "_tenon", TENON_D / 2, TENON_L, (TENON_L / 2, 0, 0), axis="X")
        bool_op(o, [ten], op="UNION")
    return o


def make_foot_splice(name, coll="A"):
    o = box("CUT", name, 30, 30, 60, (0, 0, 0))
    hole = box("CUT", name + "_hole", BEAM + TOL_SQ_TOTAL * 0.8, BEAM + TOL_SQ_TOTAL * 0.8, 64, (0, 0, 0))
    bool_op(o, [hole])
    screw(o, name + "_s1", (-15 + 1.5, 0, -12), axis="X")
    screw(o, name + "_s2", (15 - 1.5, 0, 12), axis="X")
    return finish(o, coll=coll)


def make_spreader_half(name, length, coll="A"):
    o = box(coll, name, length, BEAM, BEAM, (length / 2, 0, 0))
    for frac in (0.2, 0.8):
        c = cyl("CUT", name + f"_tie{frac}", 2.0, BEAM + 6, (length * frac, 0, 0), axis="Y")
        bool_op(o, [c])
    return finish(o)


def make_spreader_splice(name, coll="A"):
    o = box("CUT", name, 30, 30, 70, (0, 0, 0))
    hole = box("CUT", name + "_hole", BEAM + TOL_SQ_TOTAL * 0.8, BEAM + TOL_SQ_TOTAL * 0.8, 74, (0, 0, 0))
    bool_op(o, [hole])
    screw(o, name + "_s1", (-15 + 1.5, 0, 0), axis="X", depth=10)
    return finish(o, coll=coll)


# ---------- 方案 A 场景 ----------
def build_A(coll="A", decorated=False, explode=0.0):
    placed = []
    H = A["SEG"] * A["SEG_N"]                       # 795
    layer_z = [110 + i * A["LAYER_H"] for i in range(A["LAYERS"])]
    ex = explode * MM
    z = 0
    for i in range(A["SEG_N"]):
        o = finish(make_col_segment(f"A_col_seg{i+1}", A["SEG"]), coll=coll)
        place(o, (0, 0, z + A["SEG"] / 2))
        placed.append(o)
        z += A["SEG"]
        if i < A["SEG_N"] - 1:
            s = finish(make_col_sleeve(f"A_col_sleeve{i+1}"), coll=coll)
            place(s, (0, 0, z))
            placed.append(s)
    bj = finish(make_base_joint("A_base_joint"), coll=coll)
    place(bj, (0, 0, 30))
    placed.append(bj)
    for side in (-1, 1):
        ang = math.radians(58)
        inner_x = side * 23
        leg = finish(make_foot_leg(f"A_foot_leg{side>0 and 'R' or 'L'}", A["FOOT_SEG"]), coll=coll)
        leg.rotation_euler = Euler((0, math.radians(-58 if side < 0 else 58), 0))
        leg.location = (inner_x * MM + side * math.cos(math.radians(58)) * A["FOOT_SEG"] / 2 * MM,
                        0, (30 + math.sin(math.radians(58)) * A["FOOT_SEG"] / 2) * MM)
        placed.append(leg)
        tail = finish(make_foot_leg(f"A_foot_tail{side>0 and 'R' or 'L'}", A["FOOT_SEG"] * 0.6,
                                    coll=coll, tenon_end="outer"), coll=coll)
        tail.rotation_euler = leg.rotation_euler.copy()
        tail.location = (inner_x * MM + side * math.cos(math.radians(58)) * (A["FOOT_SEG"] + A["FOOT_SEG"] * 0.6) / 2 * MM,
                         0, (30 + math.sin(math.radians(58)) * (A["FOOT_SEG"] + A["FOOT_SEG"] * 0.6) / 2) * MM)
        placed.append(tail)
        sp = finish(make_foot_splice(f"A_foot_splice{side>0 and 'R' or 'L'}"), coll=coll)
        sp.rotation_euler = leg.rotation_euler.copy()
        sp.location = (inner_x * MM + side * math.cos(math.radians(58)) * A["FOOT_SEG"] * MM,
                       0, (30 + math.sin(math.radians(58)) * A["FOOT_SEG"]) * MM)
        placed.append(sp)
    spz = 30 + math.sin(math.radians(58)) * A["FOOT_SEG"] * 0.55
    for side in (-1, 1):
        o = finish(make_spreader_half(f"A_spreader{side>0 and 'R' or 'L'}", A["SPREAD_HALF"]), coll=coll)
        o.rotation_euler = Euler((0, math.radians(90 if side > 0 else -90), 0))
        o.location = (side * 30 * MM + side * A["SPREAD_HALF"] / 2 * MM, 0, spz * MM)
        placed.append(o)
    sps = finish(make_spreader_splice("A_spreader_splice"), coll=coll)
    place(sps, (0, 0, spz))
    placed.append(sps)
    for i, zz in enumerate(layer_z):
        j = finish(make_beam_joint(f"A_beam_joint_L{i+1}"), coll=coll)
        place(j, (0, 0, zz))
        placed.append(j)
        w_layer = 520 * (1 - i * (0.62 / A["LAYERS"]))
        beam_len = w_layer / 2 - 25
        for side in (-1, 1):
            b = finish(make_beam(f"A_beam_L{i+1}_{side>0 and 'R' or 'L'}", beam_len), coll=coll)
            b.rotation_euler = Euler((0, math.radians(180 if side < 0 else 0), 0))
            b.location = (side * (23 + TENON_L + beam_len / 2) * MM, 0, zz * MM)
            placed.append(b)
        if decorated:
            w_dec = w_layer - 100
            o = box(coll, f"A_dec_panel_L{i+1}", w_dec, 6, A["LAYER_H"] * 0.62, color_name="GREEN")
            place(o, (0, -20, zz - A["LAYER_H"] * 0.34))
            o.data.materials.append(mat("GREEN", GREEN))
            placed.append(o)
    if decorated:
        o = box(coll, "A_dec_snow", 220, 8, 60, color_name="WHITE")
        place(o, (0, -16, H - 40))
        o.data.materials.append(mat("WHITE", WHITE))
        o = box(coll, "A_dec_gift", 70, 50, 50, color_name="RED")
        place(o, (260, 0, 25))
        o.data.materials.append(mat("RED", RED))
    cap = finish(make_star_cap("A_star_cap"), coll=coll)
    place(cap, (0, 0, H + 17))
    placed.append(cap)
    star = make_star("A_star", 70, 10, coll=coll)
    star.location.z = (H + 34 + 5) * MM
    placed.append(star)
    if explode:
        for o in placed:
            o.location.z += ex * 0.4
            if "beam" in o.name or "dec_panel" in o.name:
                o.location.x += (1 if o.location.x >= 0 else -1) * ex * 0.8
    return placed


# ---------- 方案 B 场景 ----------
def build_B(coll="B", decorated=False, explode=0.0):
    placed = []
    H = B["SEG"] * B["SEG_N"] + 40
    ex = explode * MM
    z = 0
    for i in range(B["SEG_N"]):
        o = finish(make_col_segment(f"B_trunk_seg{i+1}", B["SEG"], coll=coll), coll=coll)
        place(o, (0, 0, z + B["SEG"] / 2))
        placed.append(o)
        z += B["SEG"]
        s = finish(make_col_sleeve(f"B_trunk_sleeve{i+1}", coll=coll), coll=coll)
        place(s, (0, 0, z))
        placed.append(s)
    for tier in range(B["TIERS"]):
        zz = B["TIER_START"] + tier * B["TIER_PITCH"]
        hub = finish(make_beam_joint(f"B_tier_hub_t{tier+1}", coll=coll), coll=coll)
        place(hub, (0, 0, zz))
        placed.append(hub)
        R = B["BRANCH_R"][tier]
        L = R - 15 - 13
        for k in range(B["BRANCH_N"]):
            ang = k * 2 * math.pi / B["BRANCH_N"] + tier * math.pi / B["BRANCH_N"]
            o = finish(make_beam(f"B_branch_t{tier+1}_{k+1}", L, coll=coll, tie_holes=False), coll=coll)
            o.rotation_euler = Euler((0, math.radians(78), ang))
            o.location = (math.cos(ang) * (23 + TENON_L + L / 2) * MM * math.cos(math.radians(12)),
                          math.sin(ang) * (23 + TENON_L + L / 2) * MM * math.cos(math.radians(12)),
                          zz * MM + math.sin(math.radians(12)) * (L / 2) * MM)
            placed.append(o)
            if decorated:
                o = box(coll, f"B_decor_t{tier+1}_{k+1}", 40, 8, 26,
                        (math.cos(ang) * (R - 8) * MM, math.sin(ang) * (R - 8) * MM, zz * MM + 18 * MM))
                o.rotation_euler = Euler((0, math.radians(80), ang))
                o.data.materials.append(mat(["GREEN", "RED", "WHITE"][(k + tier) % 3],
                                            COLORS[["GREEN", "RED", "WHITE"][(k + tier) % 3]]))
                placed.append(o)
    for k in range(3):
        ang = k * 2 * math.pi / 3
        o = finish(make_foot_leg(f"B_foot_{k+1}", B["FOOT3"], coll=coll, tenon_end="outer"), coll=coll)
        o.rotation_euler = Euler((0, math.radians(-64), ang))
        o.location = (math.cos(ang) * 160 * MM, math.sin(ang) * 160 * MM, 130 * MM)
        placed.append(o)
    star = make_star("B_star", 62, 9, coll=coll, tenon=False)
    star.location.z = (H + 15) * MM
    placed.append(star)
    if explode:
        for o in placed:
            o.location.z += ex * 0.3
    return placed


# ---------- 帐篷占位 ----------
def build_tent_placeholder():
    w, d, h = [v * MM for v in TENT]
    o = box("TENT", "TENT_Placeholder", w, d, h, (w / 2 + 0.55, d / 2 + 0.15, h / 2))
    o.data.materials.append(mat("TENT", TENTC))
    t = bpy.data.curves.new("TENT_txt", type="FONT")
    t.body = "帐篷占位 165×105×135 cm（已购买；三向尺寸待实测）"
    t.size = 0.085
    to = bpy.data.objects.new("TENT_label", t)
    to.location = (w / 2 + 0.55, d / 2 + 0.15, h + 0.05)
    bpy.data.collections["TENT"].objects.link(to)


# ---------- 相机与渲染 ----------
def setup_camera_light(loc=(1.55, -1.35, 1.12), target=(0, 0, 0.45), name="CAM_MAIN"):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = 34
    bpy.context.scene.collection.objects.link(cam)
    for nm, energy, rot in (("KEY", 3.2, (math.radians(52), 0, math.radians(-38))),
                            ("FILL", 1.1, (math.radians(80), 0, math.radians(120)))):
        li = bpy.data.lights.new(nm, type="SUN"); li.energy = energy; li.angle = 0.35
        lo = bpy.data.objects.new(nm, li)
        lo.rotation_euler = Euler(rot)
        bpy.context.scene.collection.objects.link(lo)
    return cam


def setup_render(cam, res=(1280, 960)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.world = bpy.data.worlds.new("W") if sc.world is None else sc.world
    sc.world.color = (0.90, 0.92, 0.93)


def render_to(path):
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered:", path)


# ---------- 装配检查（整树，含密闭性） ----------
def tree_check(coll_name, label):
    objs = [o for o in bpy.data.collections[coll_name].objects if o.type == "MESH"]
    parts, total_tris, issues = [], 0, []
    for o in objs:
        me = o.data
        d = o.dimensions
        parts.append({"name": o.name, "dims_mm": [round(v * 1000, 1) for v in d],
                      "tris": len(me.polygons)})
        if max(d) * 1000 > 245:
            issues.append(f"{o.name} 超出 P1S 行程")
        tris_n = len(me.polygons)
        total_tris += tris_n
        edge_use = {}
        for p in me.polygons:
            ks = p.edge_keys
            for k in ks:
                edge_use[k] = edge_use.get(k, 0) + 1
        open_edges = sum(1 for v in edge_use.values() if v == 1)
        if open_edges:
            issues.append(f"{o.name}: {open_edges} 条开放边（非水密）")
    return {"label": label, "mesh_parts": len(objs), "triangles": total_tris,
            "parts": parts, "issues": issues}


# ---------- 主流程 ----------
def stage_geometry():
    reset_scene()
    build_A()
    build_B()
    (GEN / "blends").mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "blends" / "tree_designs.blend"))
    stl_dir = GEN / "stl"
    for d in ("A", "B", "first_plate"):
        (stl_dir / d).mkdir(parents=True, exist_ok=True)
    count = 0
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.name.startswith(("A_", "B_")):
            continue
        target = "first_plate" if obj.name.startswith("TP") else obj.name[:1]
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.stl_export(filepath=str(stl_dir / target / f"{obj.name}.stl"),
                              export_selected_objects=True, ascii_format=False)
        count += 1
    # 整树装配检查（两方案；必须在首盘 reset 之前）
    check_a = tree_check("A", "方案A")
    check_b = tree_check("B", "方案B")
    (GEN / "assembly_tree_check.json").write_text(
        json.dumps({"A": check_a, "B": check_b}, ensure_ascii=False, indent=2), encoding="utf-8")
    (GEN / "stats.json").write_text(json.dumps(
        {"screw_seats": screw_seats, "screw_total": len(screw_seats)}, ensure_ascii=False, indent=2), encoding="utf-8")
    # 首盘试件（接口参数与整树一致；柱短样两段）
    reset_scene()
    finish(make_col_sleeve("TP1_col_sleeve", coll="first_plate"), coll="first_plate")
    finish(make_beam_joint("TP2_beam_joint", coll="first_plate"), coll="first_plate")
    finish(make_beam("TP3_beam_stub_L5", 80, coll="first_plate", tie_holes=True), coll="first_plate")
    s1 = finish(make_col_segment("TP4a_col_stub1", 80, coll="first_plate"), coll="first_plate"); s1.location.y = -60 * MM
    s2 = finish(make_col_segment("TP4b_col_stub2", 80, coll="first_plate"), coll="first_plate"); s2.location.y = -120 * MM
    st = finish(make_star("TP5_star_opt", 70, 10, coll="first_plate", tenon=True), coll="first_plate"); st.location.x = 120 * MM
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not obj.name.startswith("TP"):
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.stl_export(filepath=str(GEN / "stl" / "first_plate" / f"{obj.name}.stl"),
                              export_selected_objects=True, ascii_format=False)
        count += 1
    print(f"GEOMETRY DONE: {count} STL exported; screws={len(screw_seats)}")


def stage_render():
    jobs = [
        (dict(design="A", decorated=False), "tree_A_bare.png", (1280, 960)),
        (dict(design="A", decorated=True), "tree_A_decorated.png", (1280, 960)),
        (dict(design="B", decorated=False), "tree_B_bare.png", (1280, 960)),
        (dict(design="B", decorated=True), "tree_B_decorated.png", (1280, 960)),
    ]
    for kw, out, res in jobs:
        reset_scene()
        if kw["design"] == "A":
            build_A(decorated=kw["decorated"])
        else:
            build_B(decorated=kw["decorated"])
        cam = setup_camera_light()
        setup_render(cam, res)
        render_to(RENDERS / out)
    # 同尺度并排
    reset_scene()
    build_A()
    for o in bpy.data.collections["A"].objects:
        o.location.x -= 0.45
    build_B()
    for o in bpy.data.collections["B"].objects:
        o.location.x += 0.45
    cam = setup_camera_light(loc=(2.35, -2.05, 1.28), target=(0.1, 0.1, 0.5))
    setup_render(cam, res=(1600, 1000))
    render_to(RENDERS / "compare_side_by_side.png")
    # 比例图
    reset_scene()
    build_A(decorated=True)
    build_tent_placeholder()
    cam = setup_camera_light(loc=(2.9, -2.4, 1.35), target=(0.35, 0.15, 0.55))
    setup_render(cam, res=(1600, 1000))
    render_to(RENDERS / "scale_with_tent.png")
    # 接头剖视图
    reset_scene()
    j = finish(make_beam_joint("SEC_joint"), coll="A")
    b = finish(make_beam("SEC_beam", 120, coll="A"), coll="A")
    c = finish(make_col_segment("SEC_col", 200), coll="A")
    place(c, (0, 0, -100))
    cut = box("CUT", "SEC_cutaway", 60, 60, 200)
    place(cut, (30, 0, 0))
    bool_op(j, [cut], op="INTERSECT")
    bcut = box("CUT", "SEC_bcut", 60, 60, 200)
    place(bcut, (60, 0, 0))
    bool_op(b, [bcut], op="INTERSECT")
    cam = setup_camera_light(loc=(0.4, -0.32, 0.15), target=(0.015, 0, 0), name="CAM_SEC")
    setup_render(cam, res=(1100, 900))
    render_to(RENDERS / "joint_section.png")
    # 爆炸图（完整入镜）
    reset_scene()
    build_A(decorated=True, explode=240.0)
    cam = setup_camera_light(loc=(2.6, -2.3, 1.3), target=(0, 0, 0.55))
    setup_render(cam, res=(1400, 1100))
    render_to(RENDERS / "tree_A_exploded_full.png")


def stage_anim():
    reset_scene()
    build_A(coll="A_X", decorated=False, explode=240.0)
    build_A(coll="A_T", decorated=False, explode=0.0)
    cam = setup_camera_light(loc=(2.2, -1.9, 1.15), target=(0, 0, 0.5))
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.fps = 24
    sc.frame_start, sc.frame_end = 1, 108
    xs = list(bpy.data.collections["A_X"].objects)
    ts = list(bpy.data.collections["A_T"].objects)
    assert len(xs) == len(ts), "两集合零件数不一致"
    for i, o in enumerate(xs):
        o.keyframe_insert(data_path="location", frame=1)
        o.location = ts[i].location.copy()
        o.rotation_euler = ts[i].rotation_euler.copy()
        o.keyframe_insert(data_path="location", frame=90)
        o.keyframe_insert(data_path="rotation_euler", frame=90)
    for o in ts:
        o.hide_render = True
        o.hide_viewport = True
    sc.frame_set(100)
    outdir = RENDERS / "anim_frames"
    outdir.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(outdir / "frame_")
    bpy.ops.render.render(animation=True)
    (RENDERS / "assembly_A.mp4.note").write_text(
        "ffmpeg -framerate 24 -i anim_frames/frame_%04d.png -c:v libx264 -pix_fmt yuv420p assembly_A.mp4（MP4 不入 git）", encoding="utf-8")
    print("ANIM DONE")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["geometry", "render", "anim", "all"])
    args = ap.parse_args(argv)
    GEN.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    if args.stage in ("geometry", "all"):
        stage_geometry()
    if args.stage in ("render", "all"):
        stage_render()
    if args.stage in ("anim", "all"):
        stage_anim()


main()
