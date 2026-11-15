#!/usr/bin/env python3
"""AI 圣诞魔法小屋｜设计基准 v2：宜家 KURA 库拉两用床（502.665.06）可编辑场景。

基准口径：
- 用户确认（2026-11-15）：209×99×116 cm，床垫 90×200 cm —— 作为设计基准；
- 宜家 HK 同款页（2026-11-15 查证）：长 199 × 宽 100 × 高 116，床底高 83，
  最大承重 100 kg，床垫最大 189×92×12 —— 与用户口径存在 209/199 差异
  → 记 TM-01 待实测（包装尺寸 vs 本体尺寸口径差）。
- 实拍中的斜屋顶**不属于 KURA 标准平顶矩形结构**：官方产品为平顶高床（护板 +
  平板梯）。斜屋顶按「疑似加装件」独立组件建模（琥珀色），几何全部参数化待实测。

组件区分（本场景的结构化事实）：
1. KURA_FRAME  标准床架：4 立柱 + 顶平台框架 + 护栏带 + 下铺侧板（洞屋）+ 板条底 + 平梯；
2. MATTRESS    床垫睡眠区（床垫顶面 = 睡眠区，禁止任何绳环/垂布/悬挂件）；
3. ROOF_SUSPECT 疑似加装斜屋顶（双坡板 + 脊梁；脊高/斜梁长/连接位置全部待实测）；
4. DECO_*      两版装饰（不动床架承重、无挂钩、全部可拆卸，位于睡眠区外）。

装饰合规红线（设计约束，逐条落实）：
- 不修改床架承重结构（无螺丝、无开孔）；
- 不在床上安装额外挂钩；
- 睡眠区（床垫顶面 ± 护栏内侧）不加绳环、垂布、悬挂硬件；
- 装饰固定 = PETG 免工具板缘夹（适配板材厚度，TM-06 待实测）/ 可移除魔术贴 /
  配重立放，单件 ≤50 g，全部位于下铺洞屋外侧与护栏外侧。

用法:
  blender --background --python kura_cottage.py -- --deco minimal|fabric|both|none
输出: generated/kura_cottage.blend + renders_local/*.png（不入 git，精选复制到 public/media）
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

MM = 0.001
ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
RENDERS = ROOT / "renders_local"

# ---------- 基准尺寸（mm） ----------
CFG = {
    "L": 2090.0,            # TM-01：用户口径 2090；宜家 HK 口径 1990，待实测
    "W": 990.0,
    "H": 1160.0,            # 高床模式平台高度
    "POST": 70.0,           # 立柱截面（示意，TM-08 待实测）
    "GUARD_H": 100.0,       # 顶护栏带高度（示意）
    "SLAT_T": 20.0,         # 板条底厚度（示意）
    "MATT_L": 2000.0,       # TM-02 床垫实测待回填
    "MATT_W": 900.0,
    "MATT_T": 120.0,
    "DEN_PANEL_T": 18.0,    # TM-06 下铺侧板厚度（夹具选型依据）
    "DEN_H": 800.0,         # TM-07 下铺净空（示意 800，HK 口径床底高 830）
    # 疑似加装斜屋顶（全部待实测）
    "ROOF_RIDGE_H": 420.0,  # TM-03 平台面→屋脊净高（参数化占位）
    "ROOF_EAVE_OVERHANG": 60.0,
    "ROOF_PANEL_T": 15.0,
    "ROOF_RIDGE_BEAM": 40.0,  # TM-04 斜梁长度/根数待实测
}

MAT_COLORS = {
    "PINE": (0.82, 0.70, 0.52, 1.0),     # 松木本色
    "WHITE": (0.92, 0.92, 0.90, 1.0),    # 白色漆面
    "MATT": (0.95, 0.95, 0.94, 1.0),     # 床垫
    "ROOF_SUSPECT": (0.85, 0.62, 0.20, 1.0),  # 疑似加装件（琥珀标注）
    "FELT_GREEN": (0.20, 0.45, 0.28, 1.0),
    "FELT_RED": (0.72, 0.20, 0.16, 1.0),
    "FELT_WHITE": (0.94, 0.94, 0.92, 1.0),
    "PETG_GOLD": (0.85, 0.68, 0.25, 1.0),
    "WOOD_DARK": (0.45, 0.36, 0.26, 1.0),
}
COLLECTIONS = ("KURA_FRAME", "MATTRESS", "ROOF_SUSPECT", "DECO", "CUT")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in COLLECTIONS:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)


def mat(name):
    color = MAT_COLORS[name]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = color
    m.diffuse_color = color
    return m


def box(coll, name, w, d, h, center, mat_name="PINE", rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    hx, hy, hz = w * MM / 2, d * MM / 2, h * MM / 2
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=__import__("mathutils").Matrix.Diagonal(
        (w * MM, d * MM, h * MM, 1.0)))
    bm.to_mesh(o.data)
    bm.free()
    o.location = (center[0] * MM, center[1] * MM, center[2] * MM)
    o.rotation_euler = rot
    o.data.materials.append(mat(mat_name))
    return o


def label(text, world_mm, size=0.09):
    import bpy
    c = bpy.data.curves.new("LBL", type="FONT")
    c.body = text
    c.size = size
    c.align_x = "CENTER"
    o = bpy.data.objects.new("LBL_" + text[:12], c)
    o.location = (world_mm[0] * MM, world_mm[1] * MM, world_mm[2] * MM)
    o.rotation_euler = (0, 0, 0)
    bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new("LBLM")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.1, 0.1, 0.1, 1)
    o.data.materials.append(m)
    return o


# ---------- 结构 ----------
def build_kura():
    """标准 KURA 高床床架（平顶矩形结构），返回对象表。"""
    P = {}
    L, W, H, POST = CFG["L"], CFG["W"], CFG["H"], CFG["POST"]
    px, py = L / 2 - POST / 2, W / 2 - POST / 2
    # 4 立柱
    for sx in (-1, 1):
        for sy in (-1, 1):
            o = box("KURA_FRAME", f"post_{sx}_{sy}", POST, POST, H, (sx * px, sy * py, H / 2),
                    "PINE" if (sx > 0) == (sy > 0) else "WHITE")
            P[o.name] = o
    # 顶部平台框架（上沿 = H）
    rail_h = 90.0
    for sy in (-1, 1):
        o = box("KURA_FRAME", f"rail_long_{sy}", L, POST, rail_h, (0, sy * py, H - rail_h / 2), "WHITE")
        P[o.name] = o
    for sx in (-1, 1):
        o = box("KURA_FRAME", f"rail_end_{sx}", POST, W - 2 * POST, rail_h, (sx * px, 0, H - rail_h / 2), "WHITE")
        P[o.name] = o
    # 顶护栏带（护栏带上沿 = H；护栏内侧面 = 睡眠区边界）
    for sy in (-1, 1):
        o = box("KURA_FRAME", f"guard_long_{sy}", L, 20, CFG["GUARD_H"], (0, sy * (W / 2 - 10), H + CFG["GUARD_H"] / 2), "WHITE")
        P[o.name] = o
    for sx in (-1, 1):
        o = box("KURA_FRAME", f"guard_end_{sx}", 20, W - 40, CFG["GUARD_H"], (sx * (L / 2 - 10), 0, H + CFG["GUARD_H"] / 2), "WHITE")
        P[o.name] = o
    # 板条底（示意：整板）
    o = box("KURA_FRAME", "slat_base", L - 2 * POST, W - 2 * POST, CFG["SLAT_T"], (0, 0, H - rail_h - CFG["SLAT_T"] / 2), "PINE")
    P[o.name] = o
    # 下铺洞屋侧板（KURA 标志外形，示意直角板 + 上沿圆角略）
    t, dh = CFG["DEN_PANEL_T"], CFG["DEN_H"]
    for sy in (-1, 1):
        o = box("KURA_FRAME", f"den_side_{sy}", L - 2 * POST - 40, t, dh,
                (0, sy * (W / 2 - t / 2), dh / 2), "PINE")
        P[o.name] = o
    o = box("KURA_FRAME", "den_back", t, W - 2 * POST, dh, (-L / 2 + POST + t / 2, 0, dh / 2), "PINE")
    P[o.name] = o
    # 平梯（一端，示意平板梯）
    lx = L / 2 + 20
    o = box("KURA_FRAME", "ladder_rail_1", 20, 100, H + 60, (lx, -120, (H + 60) / 2 - 30), "PINE", rot=(0, math.radians(-8), 0))
    o = box("KURA_FRAME", "ladder_rail_2", 20, 100, H + 60, (lx, 120, (H + 60) / 2 - 30), "PINE", rot=(0, math.radians(-8), 0))
    P["ladder"] = o
    for k in range(5):
        o = box("KURA_FRAME", f"ladder_rung_{k}", 20, 240, 40, (lx, 0, 60 + k * 180), "PINE")
    return P


def build_mattress():
    """床垫睡眠区：床垫顶面 = 睡眠区上边界。"""
    o = box("MATTRESS", "mattress", CFG["MATT_L"], CFG["MATT_W"], CFG["MATT_T"],
            (0, 0, CFG["H"] + CFG["MATT_T"] / 2), "MATT")
    return {"mattress": o}


def build_roof_suspect():
    """疑似加装斜屋顶：双坡板 + 脊梁（独立组件；几何全部 TM 待实测）。"""
    P = {}
    L, W, H = CFG["L"], CFG["W"], CFG["H"]
    ridge = CFG["ROOF_RIDGE_H"]
    eave_y = W / 2 + CFG["ROOF_EAVE_OVERHANG"]
    base_z = H + CFG["GUARD_H"]
    # 双坡板：从两侧檐口到中央屋脊
    slope_len = math.hypot(eave_y, ridge)
    ang = math.atan2(ridge, eave_y)
    for sy in (-1, 1):
        c_y = sy * eave_y / 2
        c_z = base_z + ridge / 2
        o = box("ROOF_SUSPECT", f"roof_slope_{sy}", L + 2 * CFG["ROOF_EAVE_OVERHANG"],
                slope_len, CFG["ROOF_PANEL_T"], (0, c_y, c_z), "ROOF_SUSPECT",
                rot=(math.radians(math.degrees(ang) * sy), 0, 0))
        P[o.name] = o
    # 脊梁
    o = box("ROOF_SUSPECT", "roof_ridge_beam", L + 2 * CFG["ROOF_EAVE_OVERHANG"],
            CFG["ROOF_RIDGE_BEAM"], CFG["ROOF_RIDGE_BEAM"], (0, 0, base_z + ridge + CFG["ROOF_RIDGE_BEAM"] / 2),
            "ROOF_SUSPECT")
    P[o.name] = o
    return P


# ---------- 装饰（睡眠区外；PETG 板缘夹 / 魔术贴 / 配重，全部可拆卸） ----------
def _tree_shape(coll, name, h, w, pos, mat_name, t=6.0):
    """不织布小圣诞树：三层叠梯形剪影，贴在下侧板外表面。"""
    z0 = pos[2]
    layers = 3
    for k in range(layers):
        lh = h / layers
        lw = w * (1 - 0.32 * k)
        box(coll, f"{name}_{k}", lw, t, lh * 1.15, (pos[0], pos[1], z0 + h - lh * (k + 0.5)), mat_name)


def _snowflake(coll, name, r, pos, mat_name, t=5.0):
    for k in range(3):
        box(coll, f"{name}_{k}", r * 2, t, r * 0.28, (pos[0], pos[1], pos[2]),
            mat_name, rot=(0, 0, math.radians(60 * k)))


def _star(coll, name, r, pos, mat_name, t=8.0):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.pi / 2 + i * math.pi / 5
        pts.append((rr * math.cos(a) * MM, rr * math.sin(a) * MM))
    import bmesh
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    bm = bmesh.new()
    vs = [bm.verts.new((px, py, 0)) for px, py in pts]
    vs += [bm.verts.new((px, py, t * MM)) for px, py in pts]
    m = len(pts)
    bm.faces.new(vs[:m])
    bm.faces.new(vs[m:][::-1])
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((vs[i], vs[j], vs[m + j], vs[m + i]))
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    o.location = (pos[0] * MM, pos[1] * MM, pos[2] * MM)
    o.data.materials.append(mat(mat_name))
    return o


def build_deco_minimal():
    """①极简原木森林圣诞屋：原木/白双色剪影小树沿下侧板外表面排列 + 板缘夹。"""
    D = {}
    L, W, DH = CFG["L"], CFG["W"], CFG["DEN_H"]
    y = -(W / 2) - 3.5      # 外侧板外表面外 3.5mm（板缘夹厚度示意）
    xs = [-820, -560, -300, 260, 520, 780]
    hs = [300, 220, 170, 190, 250, 320]
    for k, (x, h) in enumerate(zip(xs, hs)):
        m = "WOOD_DARK" if k % 2 == 0 else "FELT_WHITE"
        _tree_shape("DECO", f"deco_tree_{k}", h, h * 0.62, (x, y, 20), m)
    # 山墙端一颗 PETG 星（配重/夹具，待实测）
    _star("DECO", "deco_star_gable", 90, (CFG["L"] / 2 - CFG["POST"] / 2, CFG["W"] / 2 + 4, CFG["DEN_H"] + 80), "PETG_GOLD")
    # 雪花两枚（白色不织布）
    _snowflake("DECO", "deco_snow_1", 70, (130, y, 420), "FELT_WHITE")
    _snowflake("DECO", "deco_snow_2", 55, (660, y, 380), "FELT_WHITE")
    return D


def build_deco_fabric():
    """②局部布艺魔法小屋：红/白不织布贴面 + 门形剪影 + 顶檐星，全部睡眠区外。"""
    D = {}
    L, W, DH = CFG["L"], CFG["W"], CFG["DEN_H"]
    y_out = -(W / 2) - CFG["DEN_PANEL_T"] / 2 - 3.0
    # 洞屋开口「门形」布艺框（左右两柱 + 上楣，不织布红色）
    box("DECO", "fabric_door_l", 60, 6, DH - 120, (-CFG["L"] / 2 + 200, y_out - 3, (DH - 120) / 2 + 40), "FELT_RED")
    box("DECO", "fabric_door_r", 60, 6, DH - 120, (CFG["L"] / 2 - 200, y_out - 3, (DH - 120) / 2 + 40), "FELT_RED")
    box("DECO", "fabric_lintel", L - 320, 6, 70, (0, y_out - 3, DH - 50), "FELT_RED")
    # 白色小树贴面（不对称两株）
    _tree_shape("DECO", "fabric_tree_1", 260, 160, (-420, y_out - 9, 30), "FELT_WHITE", t=5.0)
    _tree_shape("DECO", "fabric_tree_2", 180, 110, (390, y_out - 9, 40), "FELT_WHITE", t=5.0)
    # 雪花（白）×3
    for k, (x, z) in enumerate([(-150, 300), (100, 380), (330, 250)]):
        _snowflake("DECO", f"fabric_snow_{k}", 60 - k * 8, (x, y_out - 9, z), "FELT_WHITE", t=4.0)
    # 顶檐 PETG 星（护栏外侧面，睡眠床垫顶面以下 ≥200mm，睡眠区外）
    _star("DECO", "fabric_star_rail", 70, (0, -(W / 2) + 2, CFG["H"] + 20), "PETG_GOLD", t=6.0)
    return D


# ---------- 相机与渲染 ----------
def setup_camera_light(loc, target, name="CAM"):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = 30
    cam = bpy.data.objects.new(name, cam_data)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    for nm, energy, rot in (("KEY", 3.0, (math.radians(50), 0, math.radians(-30))),
                            ("FILL", 1.0, (math.radians(70), 0, math.radians(140)))):
        li = bpy.data.lights.new(nm, type="SUN")
        li.energy = energy
        li.angle = 0.35
        lo = bpy.data.objects.new(nm, li)
        lo.rotation_euler = rot
        bpy.context.scene.collection.objects.link(lo)
    return cam


def render_to(cam, path, res=(1280, 960)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.world = bpy.data.worlds.new("W") if sc.world is None else sc.world
    sc.world.color = (0.92, 0.93, 0.94)
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered:", path)


CAM_DIST = 3.4


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--deco", default="both", choices=["none", "minimal", "fabric", "both"])
    args = ap.parse_args(argv)
    GEN.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)

    reset_scene()
    build_kura()
    build_mattress()
    build_roof_suspect()
    if args.deco in ("minimal", "both"):
        build_deco_minimal()
    if args.deco in ("fabric", "both"):
        build_deco_fabric()
    (GEN / "kura_cottage.blend").parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "kura_cottage.blend"))

    L = CFG["L"] * MM
    # 1) 结构区分标注图（裸架，隐藏装饰由 blend 保存时已包含 → 单独重建 none 场景）
    reset_scene()
    build_kura()
    build_mattress()
    build_roof_suspect()
    label("疑似加装斜屋顶（TM-03/04/05 待实测）", (0, -CFG["W"] / 2 - 10, CFG["H"] + CFG["ROOF_RIDGE_H"] + 60))
    label("床垫睡眠区（顶面=睡眠区上界）", (0, -CFG["W"] / 2 - 10, CFG["H"] + CFG["MATT_T"] + 10))
    label("KURA 标准床架（不动承重）", (0, -CFG["W"] / 2 - 10, 40))
    cam = setup_camera_light((L * 1.1, -L * 1.0, 2.3), (0, 0, 0.95))
    render_to(cam, RENDERS / "kura_structure_labeled.png", (1280, 960))

    # 2/3) 两版装饰
    variants = []
    if args.deco in ("minimal", "both"):
        variants.append(("minimal", build_deco_minimal))
    if args.deco in ("fabric", "both"):
        variants.append(("fabric", build_deco_fabric))
    for name, fn in variants:
        reset_scene()
        build_kura()
        build_mattress()
        build_roof_suspect()
        fn()
        cam = setup_camera_light((L * 1.15, -L * 0.95, 2.15), (0, -0.02, 0.88))
        render_to(cam, RENDERS / f"kura_deco_{name}.png", (1280, 960))

    meta = {
        "baseline": "IKEA KURA 502.665.06（用户确认 209×99×116，床垫 90×200）",
        "official_hk": "199×100×116，床底高 83，承重 100kg，床垫最大 189×92×12（TM-01 长度口径待实测）",
        "roof_suspect": "斜屋顶非 KURA 标准结构；脊高/斜梁/连接位置待实测（TM-03/04/05）",
        "deco_rules": "不动承重/无挂钩/睡眠区无绳环垂布悬挂件；PETG 板缘夹 + 魔术贴 + 配重，≤50g/件",
        "outputs": ["kura_cottage.blend", "kura_structure_labeled.png"] + [f"kura_deco_{n}.png" for n, _ in variants],
    }
    (GEN / "kura_scene_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("KURA DONE")


main()
