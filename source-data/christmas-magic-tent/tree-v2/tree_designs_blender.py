#!/usr/bin/env python3
"""圣诞魔法小屋｜帐篷旁圣诞树 V3：几何可装配验证的接口（Blender 5.2 headless）。

v3 相对 v2（94e385e）的结构修正（全部来自真实干涉测试结论，不是调公差）：
1. 梁圆榫 Ø16×24 插入 46 节点会与立柱（孔 30.7）干涉（榫尖越过孔壁 8mm+）
   → 改为 **短圆榫 Ø16×6 + 端面法兰 28×32×4 + 2×M4×8 螺栓压螺母**：
   插座 Ø16.4×6.5 只做定位，锁紧靠法兰端面螺栓；螺母袋开在节点侧面
   （六角 AF7.15×深4.6），螺母从节点顶/底面的竖直滑道装入，不受重力脱落。
2. v2 梁节点 z=250/530 与立柱套筒（z=265/530）实体重叠
   → 套筒取消独立件，边界处改为 **肩位承接组合节点**（46×46×70）：
   上下段各插 20mm、搁在 +/−15 肩环上，中段实心，竖向载荷经节点实体传递。
3. v2 平节点在光柱上无定位（会滑落）→ 立柱段加 **凸环 31.5×31.5×2**，
   节点/套环从上方滑下搁在凸环顶面。
4. v2 脚架旋转/位置数学不一致（腿、尾段、拼接套互不相连，基座插座
   水平而腿轴 58° 斜交）→ 重算为 **画架式**：柱上 z=334 领环出斜耳，
   腿沿轴向法兰+Ø16×6 榫入耳插座，2×M4×16 顺轴压袋内螺母（斜袋口朝上，
   螺母自重保持）；腿 196+拼接套 60+尾段 187（各 ≤245 可打印）。
5. 横撑：v2 SPREAD_HALF=225 与 58° 腿完全脱接 → 改为柱上滑环（凸环定位）
   ±X 出横向母头，腿尾段侧面带螺母袋短接 head，横撑两半 y=±25 水平插入
   （与腿杆 y=±12 错开，实测间隙 1mm）。
6. M4 全部停止依赖 Ø4.2 自攻：梁/枝 = M4×8+螺母；脚 = M4×16+螺母；
   立柱各段 **不锁紧**（肩位/凸环+重力承载），帽/星 = 摩擦插接。
7. 星星榫根部与板体重叠 3mm 重新布尔，消除三面共边非流形。
8. B 方案：六角枢纽（6 向水平插座，边界肩位承接）、枝=法兰短榫梁、
   三脚领环+单根腿（196），取消 v2「340 脚可平放/斜放」的不成立声明。

打印口径：全部零件最大外形 ≤245mm（P1S 256 平放）；方孔总隙 0.8、圆孔总隙 0.4。
螺纹未建模：验证以 Ø3.9 栓杆/Ø4.5 孔/AF7.0 螺母间隙代替，真实锁紧以实物试拧为准。

用法:
  blender --background --python tree_designs_blender.py -- --stage geometry|render|all
输出: generated/{stl,blends,stats.json,first_plate_layout.json,assembly_check.json}
     + renders_local/*.png（不入 git，精选复制到 public/media）
"""
from __future__ import annotations
import argparse, json, math, struct, sys
from pathlib import Path
import bpy
from mathutils import Vector, Euler

MM = 0.001
ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
RENDERS = ROOT / "renders_local"

# ---------- 公差与接口参数（mm） ----------
TOL_SQ_TOTAL = 0.8      # 方孔总隙（30 柱 → 30.7 孔）
TOL_RD_TOTAL = 0.4      # 圆孔总隙（Ø16 榫 → Ø16.4 孔）
COL = 30.0
TENON_D, TENON_L = 16.0, 6.0          # 短定位榫
SOC_D, SOC_L = 16.4, 6.5              # 插座（留 0.5 孔底隙）
FLANGE_T, FLANGE_Y, FLANGE_Z = 4.0, 28.0, 34.0
BOLT_HOLE_D = 4.5
POCKET_AF, POCKET_D = 7.15, 4.6       # 梁/枝螺母袋（顶/底滑道装入）
POCKET_D_LONG = 6.0                   # 脚袋（顺轴深袋，斜口朝上自重保持）
CHAN_W = 8.2                          # 螺母滑道宽（M4 螺母对角 8.08）
NUT_AF, NUT_H = 7.0, 3.2
RIDGE = 31.5                          # 立柱凸环边宽（> 30.7 孔即定位）
SHOULDER_INS = 20.0                   # 组合节点上下段各插入深度

A = dict(SEG=180.0, BASE_H=60.0,
         # 组合节点中心 z（=上下段肩位 ±15）；平节点搁在凸环上（中心=凸环顶+18）
         HUBS=[210.0, 390.0, 570.0],
         PLAIN=[149.0, 709.0],        # 凸环 130/690 顶面 +1 → 底 131/691 + 18
         RIDGES={"A_col_seg1": [78.0, 130.0], "A_col_seg2": [315.0], "A_col_seg4": [690.0]},
         RING_Z=91.0,                 # 横撑滑环中心（凸环 78 顶 79 + 12）
         LEG_PIVOT_Z=334.0, LEG_TIP_X=260.0, PIVOT_R=16.0, LEG_Y=46.0,
         LEG1=196.0, LEG_TAIL=187.0,  # 法兰+身 200；拼接套 s196..256；尾 s226..413
         SPLIT_S=226.0, SPLICE_LEN=60.0)
B = dict(SEG=204.0, BASE_H=80.0,
         HUBS=[229.0, 433.0, 637.0],
         BRANCH_R=[190.0, 160.0, 130.0], BRANCH_N=4,
         COLLAR_Z=169.0,              # 三脚领环（凸环 150 顶 151 + 18）
         LEG_ANG=40.0,                # 腿与竖直夹角
         PIVOT_R=16.0)
TENT = (1650.0, 1050.0, 1350.0)  # 已购买；三向尺寸待实测

bolt_reg = []   # {"part","name","bolt","nut"} —— 螺栓/螺母用量台账


# ---------- 基础工具 ----------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in ("A", "B", "A_X", "A_T", "B_X", "B_T", "TENT", "CUT", "TP", "first_plate"):
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)


def _link(coll_name, o):
    bpy.data.collections[coll_name].objects.link(o)


def mat(name, color):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color
    m.diffuse_color = color
    return m


def new_obj(name, coll="CUT"):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    _link(coll, o)
    return o


def box(coll, name, w, d, h, center=(0, 0, 0), color_name="PETG"):
    """mm；center 烘焙进顶点（外接盒中心）。"""
    o = new_obj(name, coll)
    hx, hy, hz = w / 2000, d / 2000, h / 2000
    cx, cy, cz = center[0] * MM, center[1] * MM, center[2] * MM
    me = o.data
    me.from_pydata([
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz), (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz), (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)],
        [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    me.validate()
    o.data.materials.append(mat(color_name, COLORS[color_name]))
    return o


def place(o, center_mm):
    o.location = (center_mm[0] * MM, center_mm[1] * MM, center_mm[2] * MM)
    return o


def prism_mesh(o, r, h, center, axis="Z", n=28, phase=0.0):
    """n 棱柱（n=6 且 af 口径时传 r=af/√3）；phase 转角。"""
    me = o.data
    rr, hh = r * MM, h * MM / 2
    cx, cy, cz = center[0] * MM, center[1] * MM, center[2] * MM
    verts, faces = [], []
    for i in range(n):
        a = phase + 2 * math.pi * i / n
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
    prism_mesh(o, r, h, center, axis)
    o.data.materials.append(mat("PETG", COLORS["PETG"]))
    return o


def hex_prism(coll, name, af, h, center, axis="X"):
    """六角棱柱，对边距 = af。"""
    o = new_obj(name, coll)
    prism_mesh(o, af / math.sqrt(3.0), h, center, axis, n=6)
    o.data.materials.append(mat("PETG", COLORS["PETG"]))
    return o


def orient(o, axis, roll=0.0):
    """把对象局部 +Z 转到 axis；roll 绕轴。"""
    q = Vector(axis).normalized().to_track_quat("Z", "Y")
    e = q.to_euler()
    if roll:
        e.rotate_axis("Z", roll) if False else None
    o.rotation_euler = e
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
    target.data.validate()
    return target


def finish(part, color_name="PETG", coll="A"):
    part.data.materials.append(mat(color_name, COLORS[color_name]))
    if coll not in [c.name for c in part.users_collection]:
        _link(coll, part)
    return part


def reg_bolt(part, name, bolt, nut=True):
    bolt_reg.append({"part": part.name, "name": name, "bolt": bolt, "nut": nut})


_KEYHOLE_DEBUG = True
COLORS = {"PETG": (0.72, 0.76, 0.72, 1.0), "GREEN": (0.16, 0.42, 0.24, 1.0),
          "WHITE": (0.92, 0.94, 0.93, 1.0), "RED": (0.66, 0.17, 0.12, 1.0),
          "STAR": (0.91, 0.72, 0.22, 1.0), "TENT": (0.72, 0.82, 0.80, 1.0)}
PETG = COLORS["PETG"]



def _ray_parity_inside(obj, pt_m, dir_m):
    """+dir 射线奇偶：True=点在实体内（被封闭）。"""
    import numpy as np
    mw = obj.matrix_world
    vs = np.array([tuple(mw @ v.co) for v in obj.data.vertices])
    polys = [np.array([vs[i] for i in p.vertices]) for p in obj.data.polygons]
    p0 = np.array(pt_m)
    d = np.array(dir_m, float)
    d = d / np.linalg.norm(d)
    cnt = 0
    for tri in polys:
        if len(tri) < 3:
            continue
        n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
        nn = np.linalg.norm(n)
        if nn < 1e-12:
            continue
        n = n / nn
        denom = float(d @ n)
        if abs(denom) < 1e-9:
            continue
        t = float((tri[0] - p0) @ n / denom)
        if t <= 1e-9:
            continue
        pt = p0 + d * t
        ax = int(np.argmax(np.abs(n)))
        u, v = [k for k in range(3) if k != ax]
        a2 = [(tr[ u], tr[v]) for tr in tri]
        p2 = (pt[u], pt[v])
        s = 0.0
        inside = True
        for i in range(len(a2)):
            x1, y1 = a2[i]
            x2, y2 = a2[(i + 1) % len(a2)]
            s += x1 * y2 - x2 * y1
        if s < 0:
            a2 = a2[::-1]
        for i in range(len(a2)):
            x1, y1 = a2[i]
            x2, y2 = a2[(i + 1) % len(a2)]
            cr = (x2 - x1) * (p2[1] - y1) - (y2 - y1) * (p2[0] - x1)
            if cr < -1e-9:
                inside = False
                break
        if inside:
            cnt += 1
    return cnt % 2 == 1


def unseal(obj, probes):
    """布尔 EXACT 求解器会把「面上开孔」输出为：孔口环面 + 一张封住孔的内接方面，
    使孔变成封闭内腔（无法装配）。本函数按设计意图的探针点做射线奇偶校验，
    若被封闭则删除沿射线方向的第一个命中面，直到探针通向外。"""
    changed = True
    rounds = 0
    while changed and rounds < 8:
        changed = False
        rounds += 1
        for pt_mm, dir_v in probes:
            pt = [c * MM for c in pt_mm]
            dv = [c * MM for c in dir_v]
            if not _ray_parity_inside(obj, pt, dv):
                continue
            # 沿 dir 找第一个命中面并删除
            hit_idx = None
            best_t = 1e30
            mw = obj.matrix_world
            for pi, p in enumerate(obj.data.polygons):
                vs = [mw @ obj.data.vertices[i].co for i in p.vertices]
                n = p.normal
                denom = n.dot(Vector(dv))
                if abs(denom) < 1e-12:
                    continue
                a = vs[0] - Vector([c * MM for c in pt_mm])
                t = a.dot(n) / denom
                if t <= 1e-9 or t >= best_t:
                    continue
                pt_hit = Vector([c * MM for c in pt_mm]) + Vector(dv) * t
                # 命中点是否在面内（2D 投影）
                ax = max(range(3), key=lambda k: abs(n[k]))
                u, v = [k for k in range(3) if k != ax]
                poly2 = [(vv[u], vv[v]) for vv in vs]
                p2 = (pt_hit[u], pt_hit[v])
                s = 0.0
                for i in range(len(poly2)):
                    x1, y1 = poly2[i]
                    x2, y2 = poly2[(i + 1) % len(poly2)]
                    s += x1 * y2 - x2 * y1
                if s < 0:
                    poly2 = poly2[::-1]
                inside = True
                for i in range(len(poly2)):
                    x1, y1 = poly2[i]
                    x2, y2 = poly2[(i + 1) % len(poly2)]
                    if (x2 - x1) * (p2[1] - y1) - (y2 - y1) * (p2[0] - x1) < -1e-9:
                        inside = False
                        break
                if inside:
                    best_t = t
                    hit_idx = pi
            if hit_idx is not None:
                me = obj.data
                bm_out = [list(p.vertices) for i, p in enumerate(me.polygons) if i != hit_idx]
                used = sorted({vi for f in bm_out for vi in f})
                remap = {old: new for new, old in enumerate(used)}
                verts = [me.vertices[i].co.copy() for i in used]
                new_me = bpy.data.meshes.new(me.name)
                new_me.from_pydata(verts, [], [[remap[i] for i in f] for f in bm_out])
                new_me.validate()
                for m_ in me.materials:
                    new_me.materials.append(m_)
                obj.data = new_me
                changed = True
                break
    return obj


# ---------- 可复用接口：法兰短榫杆（梁/枝/腿） ----------
def flanged_bar(coll, name, body_len, tie_holes=True, leg=False):
    """杆件，局部 +X 为杆身方向，原点=法兰内端面：
    榫 Ø16×6（local −6..0）+ 法兰 28×32×4（0..4，2×Ø4.5 孔 z=±11）+ 身 24×24（4..4+L）。"""
    o = box(coll, name, body_len, 24, 24, (4 + body_len / 2, 0, 0))
    cutters = [box("CUT", name + "_flange", FLANGE_T, FLANGE_Y, FLANGE_Z, (2, 0, 0)),
               cyl("CUT", name + "_tenon", TENON_D / 2, TENON_L + 2, (-2, 0, 0), axis="X")]  # local −6..+2，入法兰 2mm
    bool_op(o, cutters, op="UNION")
    holes = [cyl("CUT", name + f"_bh{z}", BOLT_HOLE_D / 2, 10, (2, 0, z), axis="X") for z in (-12.5, 12.5)]
    bool_op(o, holes)
    unseal(o, [((2, 0, z), (1, 0, 0)) for z in (-12.5, 12.5)] + [((2, 0, z), (-1, 0, 0)) for z in (-12.5, 12.5)])
    if tie_holes:
        for frac in (0.25, 0.75):
            c = cyl("CUT", name + f"_tie{frac}", 2.0, 30, (4 + body_len * frac, 0, 0), axis="Y")
            bool_op(o, [c])
    if leg:  # 脚：2×M4×16 顺轴（梁/枝的螺栓在节点面侧登记，避免重复计数）
        reg_bolt(o, "bolt1", "M4x16")
        reg_bolt(o, "bolt2", "M4x16")
    return o


# ---------- 可复用接口：节点侧面（插座 + 螺母袋 + 装袋滑道） ----------
def joint_face(part, name, side, half_h, z_pocket=12.5):
    """±X 面：插座 Ø16.4×6.5（x 16.5..23）+ 两螺母袋 AF7.15×4.6（z=±z_pocket）
    + 顶/底竖直滑道（供螺母装入，宽 8.2）。half_h=半高（滑道到顶/底面）。"""
    cutters = [cyl("CUT", name + f"_soc{side}", SOC_D / 2, SOC_L + 2,
                   (side * (24 - SOC_L / 2), 0, 0), axis="X")]
    for zz in (-z_pocket, z_pocket):
        cutters.append(hex_prism("CUT", name + f"_pk{side}_{zz}", POCKET_AF, POCKET_D + 2,
                                 (side * (24 - POCKET_D / 2), 0, zz), axis="X"))
        for face_z in (half_h, -half_h):
            cz = (z_pocket + half_h) / 2 if face_z > 0 else -(z_pocket + half_h) / 2
            ch = half_h - z_pocket
            cutters.append(box("CUT", name + f"_chan{side}_{zz}_{face_z}",
                               POCKET_D, CHAN_W, ch + 2, (side * (23 - POCKET_D / 2), 0, cz)))
    bool_op(part, cutters)
    unseal(part, [((21, 0, z), (1, 0, 0)) for z in (-12.5, 12.5)] if True else [])
    unseal(part, [((21, 0, z), (0, 0, 1)) for z in (-12.5, 12.5)] + [((21, 0, z), (0, 0, -1)) for z in (-12.5, 12.5)])
    reg_bolt(part, "bolt1", "M4x8")
    reg_bolt(part, "bolt2", "M4x8")
    return part


def make_plain_joint(name, coll="A"):
    """平节点 46×46×36：立柱孔贯穿（30.7×44），搁在立柱凸环上。"""
    o = box("CUT", name, 46, 46, 36)
    bool_op(o, [box("CUT", name + "_colhole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 44)])
    joint_face(o, name, 1, 18)
    joint_face(o, name, -1, 18)
    unseal(o, [((0, 0, 0), (0, 0, 1)), ((0, 0, 0), (0, 0, -1)),
               ((20, 0, 0), (1, 0, 0)), ((-20, 0, 0), (-1, 0, 0))])  # 柱孔上下贯通 + 两向插座口
    return finish(o, coll=coll)


def make_combined_joint(name, coll="A"):
    """组合节点（原套筒位置）46×46×70：上下段各插 20 搁 ±15 肩环，中段实心。"""
    o = box("CUT", name, 46, 46, 70)
    bool_op(o, [box("CUT", name + "_up", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, SHOULDER_INS + 2,
                    (0, 0, 26)),
               box("CUT", name + "_lo", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, SHOULDER_INS + 2,
                   (0, 0, -26))])
    joint_face(o, name, 1, 35)
    joint_face(o, name, -1, 35)
    unseal(o, [((0, 0, 25), (0, 0, 1)), ((0, 0, -25), (0, 0, -1)),
               ((20, 0, 0), (1, 0, 0)), ((-20, 0, 0), (-1, 0, 0))])
    return finish(o, coll=coll)


# ---------- 方案 A 零件 ----------
def make_col_segment(name, length, ridges=(), spigot=False, coll="A"):
    """立柱段 30×30；ridges=z 列表（31.5 凸环 ×2 高）；spigot=顶部 30×30×6 插头。"""
    o = box("CUT", name, COL, COL, length, (0, 0, length / 2))
    cutters = []
    for i, z in enumerate(ridges):
        cutters.append(box("CUT", name + f"_ridge{i}", RIDGE, RIDGE, 2.0, (0, 0, z)))
    if spigot:
        cutters.append(box("CUT", name + "_spigot", COL, COL, 8.0, (0, 0, length + 2)))
    bool_op(o, cutters, op="UNION")
    return finish(o, coll=coll)


def make_base(name, coll="A"):
    """底座 46×46×60（局部 ±30）：顶面立柱插座（30.7×40，承重台）。"""
    o = box("CUT", name, 46, 46, 60)
    bool_op(o, [box("CUT", name + "_hole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 42, (0, 0, 10))])
    unseal(o, [((0, 0, 25), (0, 0, 1))])  # 立柱孔须通顶面（局部坐标）
    return finish(o, coll=coll)


def make_cap(name, coll="A"):
    """树顶帽 40×40×34：底孔 30.7×8（承接段顶插头），顶孔承星榫 Ø16.4×22。"""
    o = box("CUT", name, 40, 40, 34)
    bool_op(o, [box("CUT", name + "_hole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 10, (0, 0, -12)),
                cyl("CUT", name + "_ssoc", SOC_D / 2, 24, (0, 0, 7), axis="Z")])
    unseal(o, [((0, 0, -13), (0, 0, -1)), ((0, 0, 10), (0, 0, 1))])  # 底孔与星插座须通
    return finish(o, coll=coll)


def make_star(name, r_out=70.0, depth=10.0, coll="A", tenon=True):
    """星星：榫 Ø16×20 与板体重叠 3mm 布尔（v2 的共面 union 是非流形根源）。"""
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
        ten = cyl("CUT", name + "_tenon", TENON_D / 2, 23, (0, 0, -8.5), axis="Z")  # −20..+3，与板体重叠 3mm
        bool_op(o, [ten], op="UNION")
    o.data.materials.append(mat("STAR", COLORS["STAR"]))
    return o


def leg_frame(side):
    """腿的局部姿态：返回 (u 轴向, 面内垂直 nrm=杆局部+Z, 仰角)。
    旋转约定：右侧 Euler(0, θ, 0)，左侧 Euler(0, θ, π)，θ=90°−与竖直夹角。"""
    drop = Vector((A["LEG_TIP_X"] - A["PIVOT_R"], 0, -A["LEG_PIVOT_Z"]))
    ang = math.atan2(drop.x, -drop.z)          # 与竖直夹角
    theta = math.pi / 2 - ang
    u = Vector((math.sin(ang) * side, 0, -math.cos(ang)))
    nrm = Vector((math.cos(ang) * side, 0, math.sin(ang)))
    eul = Euler((0, theta, 0 if side > 0 else math.pi))
    return u, nrm, eul


def make_leg_hub(name, coll="A"):
    """脚领环 46×46×36 + +Y 悬臂臂（腿平面 y=+46，避开梁层 y=±16）；双斜耳画架腿。"""
    o = box("CUT", name, 46, 46, 36)
    bool_op(o, [box("CUT", name + "_colhole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 44)])
    arm_y0, arm_y1 = 23.0, A["LEG_Y"] + 15.0     # 23..61
    bool_op(o, [box("CUT", name + "_arm", 24, arm_y1 - arm_y0, 24,
                    (0, (arm_y0 + arm_y1) / 2, 0))], op="UNION")
    for side in (-1, 1):
        u, nrm, eul = leg_frame(side)
        p = Vector((side * A["PIVOT_R"], A["LEG_Y"], 0))
        lug = box("CUT", name + f"_lug{side}", 30, 30, 34)
        lug.location = (p + u * 11) * MM
        lug.rotation_euler = eul
        bool_op(o, [lug], op="UNION")
        cuts = []
        soc = cyl("CUT", name + f"_soc{side}", SOC_D / 2, SOC_L + 4, (0, 0, 0))
        soc.location = (p + u * (26 - SOC_L / 2 + 2)) * MM
        orient(soc, u)
        cuts.append(soc)
        for sgn in (-1, 1):   # 顺轴深袋（斜口朝上，螺母自重保持）
            pk = hex_prism("CUT", name + f"_pk{side}_{sgn}", POCKET_AF, POCKET_D_LONG, (0, 0, 0), axis="Z")
            pk.location = (p + u * (26 - SOC_L - POCKET_D_LONG / 2) + nrm * (sgn * 11)) * MM
            orient(pk, u)
            cuts.append(pk)
        bool_op(o, cuts)
    probes = [((0, 0, 0), (0, 0, 1)), ((0, 0, 0), (0, 0, -1))]
    for side in (-1, 1):
        u, nrm, eul = leg_frame(side)
        pt = Vector((side * A["PIVOT_R"], A["LEG_Y"], 0)) + u * 22
        probes.append((tuple(pt), tuple(u)))
    unseal(o, probes)  # 柱孔贯通 + 两斜耳插座口顺腿轴
    return finish(o, coll=coll)


def make_leg_splice(name, eul, origin_mm, u_axis, coll="A"):
    """腿拼接套 30×30×60：手工 from_pydata（外盒 + 方孔 24.6 贯穿），零布尔。
    全部在局部系构建（腿轴=局部 X），位姿由 build 侧 transform 决定。"""
    import bmesh
    o = box("CUT", name, 60, 30, 30)  # 60 沿局部 X（腿轴）；两端 30×30 为插入口
    o.rotation_euler = eul
    o.location = Vector(origin_mm) * MM
    bm = bmesh.new()
    bm.from_mesh(o.data)
    h = 12.3
    iv = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                iv[(sx, sy, sz)] = bm.verts.new((sx * 30.0 * MM, sy * h * MM, sz * h * MM))
    # 内壁（法向指向孔内空腔）
    bm.faces.new((iv[(1, -1, -1)], iv[(1, -1, 1)], iv[(-1, -1, 1)], iv[(-1, -1, -1)]))   # −Y 壁
    bm.faces.new((iv[(-1, 1, -1)], iv[(-1, 1, 1)], iv[(1, 1, 1)], iv[(1, 1, -1)]))       # +Y 壁
    bm.faces.new((iv[(-1, -1, -1)], iv[(1, -1, -1)], iv[(1, 1, -1)], iv[(-1, 1, -1)]))   # −Z 壁
    bm.faces.new((iv[(-1, 1, 1)], iv[(1, 1, 1)], iv[(1, -1, 1)], iv[(-1, -1, 1)]))       # +Z 壁
    # 两端开口环（键孔 8 边面，导出时用皇冠三角化）
    ring_lo = [(-30 * MM, -15 * MM, -15 * MM), (-30 * MM, -15 * MM, 15 * MM), (-30 * MM, 15 * MM, 15 * MM), (-30 * MM, 15 * MM, -15 * MM),
               (-30 * MM, 12.3 * MM, 12.3 * MM), (-30 * MM, 12.3 * MM, -12.3 * MM), (-30 * MM, -12.3 * MM, -12.3 * MM), (-30 * MM, -12.3 * MM, 12.3 * MM)]
    bm.faces.new([bm.verts.new(v) for v in ring_lo])
    ring_hi = [(30 * MM, -15 * MM, -15 * MM), (30 * MM, -15 * MM, 15 * MM), (30 * MM, 15 * MM, 15 * MM), (30 * MM, 15 * MM, -15 * MM),
               (30 * MM, -12.3 * MM, 12.3 * MM), (30 * MM, -12.3 * MM, -12.3 * MM), (30 * MM, 12.3 * MM, -12.3 * MM), (30 * MM, 12.3 * MM, 12.3 * MM)]
    bm.faces.new([bm.verts.new(v) for v in ring_hi])
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    u = Vector(u_axis).normalized()
    pr = Vector(origin_mm)
    p1 = (pr + u * 20) * MM
    p2 = (pr - u * 20) * MM
    unseal(o, [(tuple(p1), tuple(u)), (tuple(p2), tuple(-u))])
    return finish(o, coll=coll)


def make_leg_tail(name, length, eul, origin_mm, boss_world=None, coll="A"):
    """腿尾段直杆 24×24 + 横撑 boss 四壁（免布尔手工盒体，杜绝 EXACT 偶发错面）。"""
    import bmesh
    from mathutils import Matrix
    o = box(coll, name, length, 24, 24, (length / 2, 0, 0))
    o.rotation_euler = eul
    o.location = Vector(origin_mm) * MM
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if boss_world:
        bx, by, bz = boss_world
        bm = bmesh.new()
        bm.from_mesh(o.data)
        for w, d, h, c in ((16, 30, 2.7, (bx, by, bz - 13.65)),
                           (16, 30, 2.7, (bx, by, bz + 13.65)),
                           (16, 2.7, 24.6, (bx, by - 13.65, bz)),
                           (16, 2.7, 24.6, (bx, by + 13.65, bz))):
            mat = Matrix.Translation(Vector(c) * MM) @ Matrix.Diagonal((w * MM, d * MM, h * MM, 1.0))
            bmesh.ops.create_cube(bm, size=1.0, matrix=mat)
        bm.to_mesh(o.data)
        bm.free()
        o.data.validate()
    return finish(o, coll=coll)


def make_spreader(name, length, coll="A"):
    """横撑半边 24×24 杆（无榫，两端直插）。"""
    return finish(box(coll, name, length, 24, 24, (length / 2, 0, 0)), coll=coll)


def make_b_base(name, coll="B"):
    """B 底座 46×46×80（局部 ±40）：顶面立柱插座 30.7×50。"""
    o = box("CUT", name, 46, 46, 80)
    bool_op(o, [box("CUT", name + "_hole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 52, (0, 0, 14))])
    unseal(o, [((0, 0, 25), (0, 0, 1))])
    return finish(o, coll=coll)


def make_b_collar(name, coll="B"):
    """B 三脚领环 46×46×36：柱孔贯通，120° 三斜耳（腿 40°，法兰孔=面内径向）。"""
    o = box("CUT", name, 46, 46, 36)
    bool_op(o, [box("CUT", name + "_colhole", COL + TOL_SQ_TOTAL, COL + TOL_SQ_TOTAL, 44)])
    ang_v = math.radians(B["LEG_ANG"])
    for k in range(3):
        az = k * 2 * math.pi / 3
        u = Vector((math.sin(ang_v) * math.cos(az), math.sin(ang_v) * math.sin(az), -math.cos(ang_v)))
        nrm = Vector((math.cos(ang_v) * math.cos(az), math.cos(ang_v) * math.sin(az), math.sin(ang_v)))
        p = Vector((math.cos(az), math.sin(az), 0)) * B["PIVOT_R"]
        eul = Euler((0, math.pi / 2 - ang_v, az))  # 局部 +X → u（Rz·Ry）
        lug = box("CUT", name + f"_lug{k}", 30, 30, 34)
        lug.location = (p + u * 11) * MM
        lug.rotation_euler = eul
        bool_op(o, [lug], op="UNION")
        cuts = []
        soc = cyl("CUT", name + f"_soc{k}", SOC_D / 2, SOC_L + 4, (0, 0, 0))
        soc.location = (p + u * (26 - SOC_L / 2 + 2)) * MM
        orient(soc, u)
        cuts.append(soc)
        for sgn in (-1, 1):
            pk = hex_prism("CUT", name + f"_pk{k}_{sgn}", POCKET_AF, POCKET_D_LONG, (0, 0, 0), axis="Z")
            pk.location = (p + u * (26 - SOC_L - POCKET_D_LONG / 2) + nrm * (sgn * 11)) * MM
            orient(pk, u)
            cuts.append(pk)
        bool_op(o, cuts)
    probes = [((0, 0, 0), (0, 0, 1)), ((0, 0, 0), (0, 0, -1))]
    for k in range(3):
        az = k * 2 * math.pi / 3
        u = Vector((math.sin(ang_v) * math.cos(az), math.sin(ang_v) * math.sin(az), -math.cos(ang_v)))
        p = Vector((math.cos(az), math.sin(az), 0)) * B["PIVOT_R"]
        pt = p + u * 22
        probes.append((tuple(pt), tuple(u)))
    unseal(o, probes)  # 柱孔贯通 + 三斜耳插座口顺腿轴
    return finish(o, coll=coll)


# ---------- 方案 A 装配 ----------
def crown_w(z):
    return 520.0 * (1 - 0.75 * (z - 149.0) / 560.0)


def build_A(coll="A", decorated=False, explode=0.0):
    P = {}
    ex = explode * MM
    base = finish(make_base("A_base"), coll=coll); place(base, (0, 0, 30)); P["A_base"] = base
    # 立柱 4 段：底承 z=20；肩位 195/375/555 → 段体 20..195, 225..375, 405..555, 585..735
    segs = [("A_col_seg1", 20.0, 175.0, [78.0, 130.0], False),
            ("A_col_seg2", 225.0, 150.0, [315.0], False),
            ("A_col_seg3", 405.0, 150.0, [], False),
            ("A_col_seg4", 585.0, 150.0, [690.0], True)]
    for nm, z0, ln, rg, sp in segs:
        o = finish(make_col_segment(nm, ln, ridges=[z - z0 for z in rg], spigot=sp), coll=coll)
        place(o, (0, 0, z0)); P[nm] = o  # 网格局部 0..length，原点=段底
    joints = {}
    for z in A["HUBS"]:
        nm = f"A_joint_{int(z)}"
        o = finish(make_combined_joint(nm), coll=coll); place(o, (0, 0, z)); P[nm] = o; joints[z] = o
    for z in A["PLAIN"]:
        nm = f"A_joint_{int(z)}"
        o = finish(make_plain_joint(nm), coll=coll); place(o, (0, 0, z)); P[nm] = o; joints[z] = o
    # 脚领环（凸环 315 顶 316 → 环底 316，中心 334）
    lh = finish(make_leg_hub("A_leg_hub"), coll=coll); place(lh, (0, 0, A["LEG_PIVOT_Z"])); P["A_leg_hub"] = lh
    # 腿：平面 y=+46，P=(±16,46,334) → 地面 (±260,46,0)；长 413（205+拼接套+187）
    for side in (-1, 1):
        p = Vector((side * A["PIVOT_R"], A["LEG_Y"], A["LEG_PIVOT_Z"]))
        uu, nrm, eul = leg_frame(side)
        # 腿前段：法兰内端面在 s=26（耳插座口），身 s 30..226（196）
        leg = finish(flanged_bar(coll, f"A_leg_{side>0 and 'R' or 'L'}", A["LEG1"], tie_holes=False, leg=True), coll=coll)
        leg.rotation_euler = eul
        leg.location = (p + uu * 26) * MM
        P[leg.name] = leg
        # 拼接套 s196..256（孔沿 u）
        s_c = A["SPLIT_S"]
        sp = finish(make_leg_splice(f"A_leg_splice_{side>0 and 'R' or 'L'}", eul,
                                    tuple(p + uu * s_c), tuple(uu), coll=coll), coll=coll)
        P[sp.name] = sp
        # 尾段 s226..413，带横撑 boss（横撑 z=91 → s=(334−91)/cos ≈ 300.7，孔沿世界 X，y=46）
        boss_z = A["RING_Z"]
        s_boss = (A["LEG_PIVOT_Z"] - boss_z) / (-uu.z)
        qb = p + uu * s_boss
        tail = make_leg_tail(f"A_leg_tail_{side>0 and 'R' or 'L'}", A["LEG_TAIL"], eul,
                             tuple(p + uu * s_c), boss_world=(qb.x, A["LEG_Y"] + 0.0, boss_z), coll=coll)
        P[tail.name] = tail
    # 横撑：两半 + 中央连接套（y=46 平面，独立系杆，不再挂立柱）
    boss_z = A["RING_Z"]
    for side in (-1, 1):
        spr = finish(make_spreader(f"A_spreader_{side>0 and 'R' or 'L'}", 182.5), coll=coll)
        spr.location = Vector(((7.5 + 182.5 / 2) * side, A["LEG_Y"], boss_z)) * MM
        P[spr.name] = spr
    ctr = finish(box(coll, "A_spreader_center", 30, 30, 30, (0, A["LEG_Y"], boss_z)), coll=coll)
    bool_op(ctr, [box("CUT", "A_spreader_center_hole", 34, 24.6, 24.6, (0, A["LEG_Y"], boss_z))])
    P["A_spreader_center"] = ctr
    # 横梁 5 层
    for z, jo in joints.items():
        w = crown_w(z)
        body = max(35.0, w / 2 - 30)
        for side in (-1, 1):
            nm = f"A_beam_{int(z)}_{side>0 and 'R' or 'L'}"
            b = finish(flanged_bar(coll, nm, body), coll=coll)
            b.rotation_euler = Euler((0, 0, 0 if side > 0 else math.pi))
            b.location = (side * 23 * MM, 0, z * MM)
            P[nm] = b
    # 帽 + 星（帽 735..769 承 seg4 插头 735..741；星板 771..781）
    cap = finish(make_cap("A_cap"), coll=coll); place(cap, (0, 0, 752)); P["A_cap"] = cap
    star = make_star("A_star", 70, 10, coll=coll)
    star.location.z = 776 * MM; P["A_star"] = star
    if decorated:
        for z, jo in joints.items():
            w = crown_w(z)
            o = box(coll, f"A_panel_{int(z)}", max(40.0, w - 80), 6, 96, color_name="GREEN")
            place(o, (0, -18, z - 34))
            o.data.materials.append(mat("GREEN", COLORS["GREEN"]))
            P[o.name] = o
        o = box(coll, "A_snow", 240, 8, 56, (0, -16, 690), color_name="WHITE")
        o.data.materials.append(mat("WHITE", COLORS["WHITE"])); P[o.name] = o
        o = box(coll, "A_gift", 70, 50, 50, (280, 0, 25), color_name="RED")
        o.data.materials.append(mat("RED", COLORS["RED"])); P[o.name] = o
    if explode:
        for o in P.values():
            o.location.z += ex * 0.4
            if "beam" in o.name or "panel" in o.name:
                o.location.x += (1 if o.location.x >= 0 else -1) * ex * 0.8
    return P


# ---------- 方案 B 装配 ----------
def build_B(coll="B", decorated=False, explode=0.0):
    P = {}
    base = finish(make_b_base("B_base"), coll=coll); place(base, (0, 0, 40)); P["B_base"] = base
    segs = [("B_trunk_seg1", 30.0, 184.0, [150.0], False),
            ("B_trunk_seg2", 244.0, 174.0, [], False),
            ("B_trunk_seg3", 448.0, 174.0, [], False),
            ("B_trunk_seg4", 652.0, 174.0, [], True)]
    for nm, z0, ln, rg, sp in segs:
        o = finish(make_col_segment(nm, ln, ridges=[z - z0 for z in rg], spigot=sp, coll=coll), coll=coll)
        place(o, (0, 0, z0)); P[nm] = o  # 网格局部 0..length，原点=段底
    hubs = {}
    for i, z in enumerate(B["HUBS"]):
        o = finish(make_combined_joint(f"B_hub_t{i+1}", coll=coll), coll=coll)
        place(o, (0, 0, z)); P[o.name] = o; hubs[i] = (z, o)
    # 三脚领环（凸环 150 顶 151 → 中心 169）
    col = finish(make_b_collar("B_collar"), coll=coll); place(col, (0, 0, B["COLLAR_Z"])); P["B_collar"] = col
    ang_v = math.radians(B["LEG_ANG"])
    leg_len = B["COLLAR_Z"] / math.cos(ang_v)
    for k in range(3):
        az = k * 2 * math.pi / 3
        d = Vector((math.cos(az), math.sin(az), 0))
        p = d * B["PIVOT_R"] + Vector((0, 0, B["COLLAR_Z"]))
        u = Vector((math.sin(ang_v) * math.cos(az), math.sin(ang_v) * math.sin(az), -math.cos(ang_v)))
        # 局部 +X → u：绕轴（Y 后 Z）
        q = u.to_track_quat("X", "Z")  # 局部 X → u
        eul = q.to_euler()
        leg = finish(flanged_bar(coll, f"B_leg_{k+1}", leg_len, tie_holes=False, leg=True), coll=coll)
        leg.rotation_euler = eul
        leg.location = (p + u * 26) * MM
        P[leg.name] = leg
    # 枝 3 层 × 6
    for tier, (z, hub) in hubs.items():
        R = B["BRANCH_R"][tier]
        body = max(30.0, R - 23 - 16)
        for k in range(B["BRANCH_N"]):
            az = k * math.pi / 2
            b = finish(flanged_bar(coll, f"B_branch_t{tier+1}_{k+1}", body, tie_holes=False), coll=coll)
            b.rotation_euler = Euler((0, 0, az))
            b.location = (math.cos(az) * 23 * MM, math.sin(az) * 23 * MM, z * MM)
            P[b.name] = b
    cap = finish(make_cap("B_cap", coll=coll), coll=coll); place(cap, (0, 0, 843)); P["B_cap"] = cap
    star = make_star("B_star", 62, 9, coll=coll)
    star.location.z = 866 * MM; P["B_star"] = star
    if decorated:
        for tier, (z, hub) in hubs.items():
            R = B["BRANCH_R"][tier]
            for k in range(B["BRANCH_N"]):
                az = k * math.pi / 2
                o = box(coll, f"B_decor_t{tier+1}_{k+1}", 44, 8, 28,
                        ((math.cos(az) * (R - 6)) * MM, (math.sin(az) * (R - 6)) * MM, (z + 16) * MM),
                        color_name=["GREEN", "RED", "WHITE"][(k + tier) % 3])
                o.data.materials.append(mat(["GREEN", "RED", "WHITE"][(k + tier) % 3],
                                            COLORS[["GREEN", "RED", "WHITE"][(k + tier) % 3]]))
                P[o.name] = o
    if explode:
        for o in P.values():
            o.location.z += ex * 0.3
    return P


# ---------- 帐篷占位 ----------
def build_tent_placeholder():
    w, d, h = [v * MM for v in TENT]
    o = box("TENT", "TENT_Placeholder", w, d, h, (w / 2 + 0.55, d / 2 + 0.15, h / 2))
    o.data.materials.append(mat("TENT", COLORS["TENT"]))
    t = bpy.data.curves.new("TENT_txt", type="FONT")
    t.body = "帐篷占位 165×105×135 cm（已购买；三向尺寸待实测）"
    t.size = 0.085
    to = bpy.data.objects.new("TENT_label", t)
    to.location = (w / 2 + 0.55, d / 2 + 0.15, h + 0.05)
    _link("TENT", to)


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


def export_stl(obj, path):
    """自定义 STL 导出：逐面耳剪三角化，正确处理布尔键孔环面（Blender 自带
    导出器对环面三角化会覆盖孔区，产生自重叠三角）。"""
    mw = obj.matrix_world
    tris_out = []
    for p in obj.data.polygons:
        loop = [tuple(mw @ obj.data.vertices[i].co) for i in p.vertices]  # 米：与读取侧 ×1000 约定一致
        tris_out += ear_clip_loop(loop)
    out = bytearray()
    out += b"\x00" * 80
    out += struct.pack("<I", len(tris_out))
    for t in tris_out:
        u = np_cross(t)
        out += struct.pack("<3f", u[0], u[1], u[2])
        for v in t:
            out += struct.pack("<3f", v[0], v[1], v[2])
        out += struct.pack("<H", 0)
    Path(path).write_bytes(bytes(out))


def np_cross(t):
    a, b, c = t
    u = [(b[0] - a[0]), (b[1] - a[1]), (b[2] - a[2])]
    v = [(c[0] - a[0]), (c[1] - a[1]), (c[2] - a[2])]
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


# ---------- 网格自检 ----------
def tree_check(coll_name, label):
    objs = [o for o in bpy.data.collections[coll_name].objects if o.type == "MESH"]
    parts, total_tris, issues = [], 0, []
    for o in objs:
        me = o.data
        d = o.dimensions
        parts.append({"name": o.name, "dims_mm": [round(v * 1000, 1) for v in d],
                      "tris": len(me.loop_triangles) or len(me.polygons)})
        if max(d) * 1000 > 245:
            issues.append(f"{o.name} 超出 P1S 行程")
        total_tris += len(me.polygons)
        edge_use = {}
        for p in me.polygons:
            for k in p.edge_keys:
                edge_use[k] = edge_use.get(k, 0) + 1
        open_edges = sum(1 for v in edge_use.values() if v == 1)
        nm3 = sum(1 for v in edge_use.values() if v > 2)
        if open_edges:
            issues.append(f"{o.name}: {open_edges} 条开放边（非水密）")
        if nm3:
            issues.append(f"{o.name}: {nm3} 条三面共边（非流形）")
    return {"label": label, "mesh_parts": len(objs), "triangles": total_tris,
            "parts": parts, "issues": issues}


# ---------- 首盘试件 ----------
FIRST_PLATE = [
    # (name, builder, 盘面落点 mm（|x|,|y| ≤ 110），z=零件底面贴床高度)
    ("TP1_combined_joint", lambda: make_combined_joint("TP1_combined_joint", coll="first_plate"), (-58, 62), 35),
    ("TP2_plain_joint", lambda: make_plain_joint("TP2_plain_joint", coll="first_plate"), (-58, -10), 18),
    ("TP3_beam_stub", lambda: flanged_bar("first_plate", "TP3_beam_stub", 80), (-39, -60), 16),
    ("TP4a_col_stub_ridge", lambda: make_col_segment("TP4a_col_stub_ridge", 80, ridges=[40.0], coll="first_plate"), (30, 80), 40),
    ("TP4b_col_stub", lambda: make_col_segment("TP4b_col_stub", 80, coll="first_plate"), (80, 80), 40),
]


def stage_first_plate(count_ref):
    reset_scene()
    placed = []
    for nm, fn, (x, y), z0 in FIRST_PLATE:
        o = fn()
        place(o, (x, y, z0))
        placed.append(o)
    # 盘面边界与重叠检查（XY 包围盒）
    boxes = []
    placed_dims = {}
    for o in placed:
        d = o.dimensions
        hx, hy = d.x * 500, d.y * 500
        wx, wy = o.location.x * 1000, o.location.y * 1000
        if max(d) * 1000 > 245:
            raise RuntimeError(f"首盘件 {o.name} 超出行程")
        placed_dims[o.name] = d
        boxes.append((o.name, wx - hx, wy - hy, wx + hx, wy + hy))
    for i in range(len(boxes)):
        n1, a0, b0, a1, b1 = boxes[i]
        if a0 < -110 or b0 < -110 or a1 > 110 or b1 > 110:
            raise RuntimeError(f"首盘件 {n1} 超出 220mm 盘面: box=({a0:.1f},{b0:.1f})..({a1:.1f},{b1:.1f}) dims={[round(v*1000,1) for v in placed_dims[n1]]}")
        for j in range(i + 1, len(boxes)):
            n2, c0, d0, c1, d1 = boxes[j]
            if not (a1 <= c0 or c1 <= a0 or b1 <= d0 or d1 <= b0):
                raise RuntimeError(f"首盘摆盘重叠: {n1} × {n2}")
    layout = []
    for o in placed:
        d = o.dimensions
        layout.append({"name": o.name, "stl": f"stl/first_plate/{o.name}.stl",
                       "pos_mm": [round(o.location.x * 1000, 1), round(o.location.y * 1000, 1)],
                       "dims_mm": [round(v * 1000, 1) for v in d]})
    (GEN / "first_plate_layout.json").write_text(
        json.dumps({"bed": 220.0, "parts": layout,
                    "note": "星形件移装饰盘（v2 非流形问题，见 README 状态账本）"},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    for obj in placed:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        export_stl(obj, GEN / "stl" / "first_plate" / f"{obj.name}.stl")
        count_ref[0] += 1


# ---------- 主流程 ----------
def stage_geometry():
    reset_scene()
    PA = build_A()
    PB = build_B()
    (GEN / "blends").mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "blends" / "tree_designs.blend"))
    stl_dir = GEN / "stl"
    import shutil
    for d in ("A", "B", "first_plate"):
        if (stl_dir / d).exists():
            shutil.rmtree(stl_dir / d)
        (stl_dir / d).mkdir(parents=True)
    count = 0
    for coll_name in ("A", "B"):
        for obj in list(bpy.data.collections[coll_name].objects):
            if obj.type != "MESH":
                continue
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            export_stl(obj, stl_dir / coll_name / f"{obj.name}.stl")
            count += 1
    check_a = tree_check("A", "方案A")
    check_b = tree_check("B", "方案B")
    (GEN / "assembly_check.json").write_text(
        json.dumps({"A": check_a, "B": check_b}, ensure_ascii=False, indent=2), encoding="utf-8")
    # 螺栓台账去重（同类合并计数）
    from collections import Counter
    cnt = Counter((b["bolt"], b["nut"]) for b in bolt_reg)
    stats = {
        "A_parts": len(check_a["parts"]), "B_parts": len(check_b["parts"]),
        "A_issues": check_a["issues"], "B_issues": check_b["issues"],
        "A_layers": [{"z_mm": z, "joint": "combined" if z in A["HUBS"] else "plain",
                      "crown_w_mm": round(crown_w(z), 1)} for z in sorted(set(A["HUBS"]) | set(A["PLAIN"]))],
        "legs": {"pivot_z": A["LEG_PIVOT_Z"], "tip_x": A["LEG_TIP_X"],
                 "angle_deg": round(math.degrees(math.atan2(A["LEG_TIP_X"] - A["PIVOT_R"], A["LEG_PIVOT_Z"])), 2),
                 "len_mm": round(math.hypot(A["LEG_TIP_X"] - A["PIVOT_R"], A["LEG_PIVOT_Z"]), 1)},
        "fasteners": [{"bolt": k[0], "nut": k[1], "count": v} for k, v in sorted(cnt.items())],
        "first_plate": [p[0] for p in FIRST_PLATE],
        "tolerances": {"square_total": TOL_SQ_TOTAL, "round_total": TOL_RD_TOTAL},
        "notes": ["螺纹未建模：以 Ø3.9 栓杆/Ø4.5 孔/AF7.0 螺母间隙验证；实物试拧为准",
                  "立柱各段不锁紧：肩位/凸环+重力承载，抗倾覆由画架脚承担",
                  "星形件移装饰盘（v2 非流形问题待装饰盘轮次处理）"],
    }
    (GEN / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    stage_first_plate([count])
    print(f"GEOMETRY DONE: {count} STL exported; bolts={len(bolt_reg)}")


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
    reset_scene()
    build_A(decorated=True)
    build_tent_placeholder()
    cam = setup_camera_light(loc=(2.9, -2.4, 1.35), target=(0.35, 0.15, 0.55))
    setup_render(cam, res=(1600, 1000))
    render_to(RENDERS / "scale_with_tent.png")
    reset_scene()
    build_A(decorated=True, explode=240.0)
    cam = setup_camera_light(loc=(2.6, -2.3, 1.3), target=(0, 0, 0.55))
    setup_render(cam, res=(1400, 1100))
    render_to(RENDERS / "tree_A_exploded_full.png")
    reset_scene()
    stage_first_plate([0])
    cam = setup_camera_light(loc=(0.18, -0.18, 0.28), target=(0.115, 0.11, 0))
    setup_render(cam, res=(1400, 1000))
    render_to(GEN / "3mf" / "first_plate_preview.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["geometry", "render", "all"])
    args = ap.parse_args(argv)
    GEN.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    if args.stage in ("geometry", "all"):
        stage_geometry()
    if args.stage in ("render", "all"):
        stage_render()


if __name__ == "__main__":
    main()
