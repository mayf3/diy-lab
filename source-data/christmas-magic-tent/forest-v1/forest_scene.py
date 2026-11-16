#!/usr/bin/env python3
"""森林童话｜总体布局场景 v3（复用真实几何）。

- KURA 开放框架床：复用 kura-v1 结构（四立柱 1160mm + 顶平台护栏带 + 板条底 +
  下铺洞屋板 + 平梯），无屋顶；床垫置顶平台（睡眠区，零添加）。
- 森林树冠/积雪/背景松：复用 felt_templates 的真实图案轮廓（棱柱拉伸贴板面）。
- 前景家具：台面 + 四腿（不再是实心方块），PETG 星与小屋置于台面。
- 渲染：forest_layout.png（正交立面+错位标注）、forest_day.png、forest_night.png。

用法: blender --background --python forest_scene.py
输出: generated/forest_scene.blend + renders_local/*.png
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

MM = 0.001
ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
RENDERS = ROOT / "renders_local"
sys.path.insert(0, str(ROOT))
import felt_templates as FT  # noqa: E402  真实图案轮廓来源

COL = ("BED", "BOARD", "TREE", "PETG", "LAMP", "CONCEPT", "CUT", "LABEL")
C = {
    "pine": (0.34, 0.27, 0.20, 1),
    "pine_light": (0.45, 0.37, 0.28, 1),
    "matt": (0.93, 0.93, 0.91, 1),
    "wall": (0.93, 0.94, 0.92, 1),
    "board": (0.88, 0.91, 0.94, 1),
    "dgreen": (0.07, 0.26, 0.17, 1),
    "mgreen": (0.15, 0.40, 0.25, 1),
    "lgreen": (0.30, 0.54, 0.35, 1),
    "white": (0.96, 0.96, 0.94, 1),
    "red": (0.65, 0.15, 0.12, 1),
    "gold": (0.87, 0.70, 0.26, 1),
    "warm": (1.0, 0.80, 0.50, 1),
    "concept": (0.62, 0.62, 0.66, 1),
    "dark": (0.10, 0.11, 0.13, 1),
    "win_glow": (1.0, 0.80, 0.45, 1),
}
FELT2MAT = {"dark_green": "dgreen", "mid_green": "mgreen", "light_green": "lgreen",
            "white": "white", "red": "red"}

KURA = dict(L=2090.0, W=990.0, H=1160.0, POST=70.0, GUARD=100.0, RAIL=90.0,
            SLAT=20.0, DEN_H=800.0, DEN_T=18.0)
CFG_MATT = (2000.0, 940.0, 120.0)
WALL_Y = 1060.0
BX, BZ = 2550.0, 450.0            # 展示板中心（床旁墙）
BOARD_W, BOARD_H, BOARD_T = 600.0, 900.0, 15.0
NIGHT = False
BENCH_Z = 450.0            # 前景台面高（TM-09 待实测）


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in COL:
        bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(bpy.data.collections[name])


def mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = C[name]
    if name == "win_glow":
        bsdf.inputs["Emission Color"].default_value = C["win_glow"]
        bsdf.inputs["Emission Strength"].default_value = 6.0
    m.diffuse_color = C[name]
    return m


def box(coll, name, w, d, h, center, m="pine", rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    hx, hy, hz = w * MM / 2, d * MM / 2, h * MM / 2
    bm = bmesh.new()
    v8 = [bm.verts.new((sx * hx, sy * hy, sz * hz))
          for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    for q in ((0, 2, 3, 1), (7, 5, 4, 6), (0, 1, 5, 4), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v8[i] for i in q])
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    o.location = (center[0] * MM, center[1] * MM, center[2] * MM)
    o.rotation_euler = rot
    o.data.materials.append(mat(m))
    return o


def poly_prism(coll, name, pts, thickness, cx, top_z, face_y, m):
    """2D 图案轮廓（felt 局部坐标，y 向下）→ 竖直棱柱贴板面。
    cx=形状在墙面的 x 中心；top_z=图案顶边世界 z；face_y=贴附面 y。"""
    xs = [p[0] for p in pts]
    scx = (min(xs) + max(xs)) / 2
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    bm = bmesh.new()
    verts = [bm.verts.new(((cx + px - scx) * MM, face_y * MM, (top_z - py) * MM)) for px, py in pts]
    f = bm.faces.new(verts)
    res = bmesh.ops.extrude_face_region(bm, geom=[f])
    newv = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=newv, vec=(0, -thickness * MM, 0))  # 朝观众（−Y）
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    o.data.materials.append(mat(m))
    return o


def star(coll, name, r, center, m, t=6.0):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    bm = bmesh.new()
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.pi / 2 + i * math.pi / 5
        pts.append((rr * math.cos(a) * MM, rr * math.sin(a) * MM))
    vf = [bm.verts.new((x, y, 0)) for x, y in pts]
    vb = [bm.verts.new((x, y, t * MM)) for x, y in pts]
    k = len(pts)
    bm.faces.new(vf)
    bm.faces.new(vb[::-1])
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((vf[i], vf[j], vb[j], vb[i]))
    bm.to_mesh(o.data)
    bm.free()
    o.data.validate()
    o.location = (center[0] * MM, center[1] * MM, center[2] * MM)
    o.data.materials.append(mat(m))
    return o


def build_kura_frame():
    """KURA 开放框架（复用 kura-v1 结构）：四立柱 + 顶平台护栏带 + 板条底 +
    下铺洞屋板 + 平梯；床垫置顶平台。无屋顶。"""
    L, W, H, POST = KURA["L"], KURA["W"], KURA["H"], KURA["POST"]
    by = WALL_Y - W / 2
    px, py = L / 2 - POST / 2, W / 2 - POST / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            box("BED", f"post_{sx}_{sy}", POST, POST, H,
                (L / 2 + sx * px, by + sy * py, H / 2), "pine")
    # 顶平台框架（上沿 = H）
    rail_h = KURA["RAIL"]
    for sy in (-1, 1):
        box("BED", f"rail_long_{sy}", L, POST, rail_h, (L / 2, by + sy * py, H - rail_h / 2), "pine_light")
    for sx in (-1, 1):
        box("BED", f"rail_end_{sx}", POST, W - 2 * POST, rail_h, (L / 2 + sx * px, by, H - rail_h / 2), "pine_light")
    # 顶部护栏带（护栏带上沿 = H + GUARD）
    g = KURA["GUARD"]
    for sy in (-1, 1):
        box("BED", f"guard_long_{sy}", L, 20, g, (L / 2, by + sy * (W / 2 - 10), H + g / 2), "pine_light")
    for sx in (-1, 1):
        box("BED", f"guard_end_{sx}", 20, W - 40, g, (L / 2 + sx * (L / 2 - 10), by, H + g / 2), "pine_light")
    # 板条底
    box("BED", "slat_base", L - 2 * POST, W - 2 * POST, KURA["SLAT"],
        (L / 2, by, H - rail_h - KURA["SLAT"] / 2), "pine")
    # 下铺洞屋板（前后 + 端部背板）
    t, dh = KURA["DEN_T"], KURA["DEN_H"]
    for sy in (-1, 1):
        box("BED", f"den_side_{sy}", L - 2 * POST - 40, t, dh,
            (L / 2, by + sy * (W / 2 - t / 2), dh / 2), "pine")
    box("BED", "den_back", t, W - 2 * POST, dh, (POST + t / 2, by, dh / 2), "pine")
    # 平梯（床尾外侧，倾角 8°）
    lx = L + 30
    box("BED", "ladder_rail_1", 20, 100, H + 60, (lx, by - 120, (H + 60) / 2 - 30), "pine",
        rot=(0, math.radians(-8), 0))
    box("BED", "ladder_rail_2", 20, 100, H + 60, (lx, by + 120, (H + 60) / 2 - 30), "pine",
        rot=(0, math.radians(-8), 0))
    for k in range(5):
        box("BED", f"ladder_rung_{k}", 20, 240, 40, (lx, by, 60 + k * 180), "pine")
    # 床垫（顶平台，睡眠区：顶面 z≈1250；护栏内侧零添加）
    box("BED", "mattress", CFG_MATT[0], CFG_MATT[1], CFG_MATT[2],
        (L / 2, by, H - rail_h + 60), "matt")
    # 概念（不安装）：护栏上沿花环
    box("CONCEPT", "concept_garland", 500, 20, 20, (L / 2 - 300, by - W / 2 - 12, H + g + 10), "concept")


def build_board_and_felt_tree():
    """展示板 + 森林背景（真实松/雪轮廓）+ 毛毡圣诞树（真实树冠/积雪轮廓）。"""
    by_b = WALL_Y - 13
    box("BOARD", "display_board", BOARD_W, BOARD_T, BOARD_H, (BX, by_b, BZ), "board")
    face = by_b - BOARD_T / 2          # 板前表面
    # 背景：远景松 A/B（真实轮廓棱柱）
    tree_groups = dict((n, (c, p)) for n, c, p in FT.board_shapes() + FT.tree_shapes() + FT.red_dots())
    for k, (dx, tag) in enumerate(((-210, "board_pine_a_0"), (220, "board_pine_a_1"),
                                   (-60, "board_pine_b_0"), (230, "board_pine_b_1"))):
        c, p = tree_groups[tag]
        h = max(q[1] for q in p)
        poly_prism("BOARD", f"bg_{tag}", p, 8, BX + dx, 130 + h, face - 1, FELT2MAT[c])
    # 雪坡（600 宽轮廓 ×2）
    for k in (0, 1):
        c, p = tree_groups[f"board_snow_{k}"]
        poly_prism("BOARD", f"bg_snow_{k}", p, 9, BX, 300 - k * 30, face - 2 - k, FELT2MAT[c])
    # 童话窗户（框 + 暖芯；夜间发光=概念）
    box("BOARD", "window_glow", 180, 6, 220, (BX - 120, face - 1, 620),
        "win_glow" if NIGHT else "warm")
    box("BOARD", "window_cross_v", 14, 9, 220, (BX - 120, face - 4, 620), "white")
    box("BOARD", "window_cross_h", 180, 9, 14, (BX - 120, face - 4, 620), "white")
    box("BOARD", "window_frame_l", 14, 9, 240, (BX - 214, face - 4, 620), "white")
    box("BOARD", "window_frame_r", 14, 9, 240, (BX - 26, face - 4, 620), "white")
    # 毛毡圣诞树 450×650（真实轮廓；树顶 z=820，底 170）
    cx = BX + 60
    top = 820.0
    tree_tags = [
        ("tree_crown_bottom", face - 0.0, 5), ("tree_crown_mid", face - 1.0, 5),
        ("tree_crown_top", face - 2.0, 5),
        ("tree_snow_bottom", face - 3.5, 6), ("tree_snow_mid", face - 4.0, 6),
        ("tree_snow_top", face - 4.5, 6), ("tree_trunk", face - 0.5, 5),
    ]
    for tag, fy, t in tree_tags:
        c, p = tree_groups[tag]
        poly_prism("TREE", f"felt_{tag}", p, t, cx, top, fy, FELT2MAT[c])
    # 红圆片（真实 Ø40 轮廓）×3 + PETG 星（树顶）
    for k, (dx, dz) in enumerate(((-60, 404), (55, 293), (10, 228))):
        c, p = tree_groups[f"red_dot_d40_{k}"]
        poly_prism("TREE", f"felt_red_{k}", p, 6, cx + dx, top - dz + 20, face - 5.5, FELT2MAT[c])
    star("TREE", "felt_star", 55, (cx, face - 8, top + 46), "gold", 6.0)


def build_petg_and_lamp():
    """前景家具（台面 + 四腿）+ PETG 件 + 台灯。"""
    tz = BENCH_Z                     # 台面高 450（TM-09 待实测）
    tx, ty = BX + 40, 880
    box("PETG", "bench_top", 500, 300, 25, (tx, ty, tz - 12.5), "pine_light")
    for sx in (-1, 1):
        for sy in (-1, 1):
            box("PETG", f"bench_leg_{sx}_{sy}", 40, 40, tz - 25,
                (tx + sx * 210, ty + sy * 110, (tz - 25) / 2), "pine")
    star("PETG", "petg_star", 45, (tx - 180, ty + 40, tz + 33), "gold", 6.0)
    box("PETG", "petg_house1", 110, 60, 100, (tx + 40, ty + 40, tz + 50), "white")
    box("PETG", "petg_house2", 90, 55, 85, (tx + 170, ty + 40, tz + 42.5), "white")
    box("LAMP", "lamp_stand", 60, 60, 1200, (BX + 420, 950, 600), "dark")
    box("LAMP", "lamp_head", 160, 90, 60, (BX + 380, 940, 1230), "dark",
        rot=(0, math.radians(35), 0))
    if NIGHT:
        li = bpy.data.lights.new("lamp_warm", type="SPOT")
        li.energy = 4200.0
        li.color = (1.0, 0.75, 0.45)
        li.spot_size = math.radians(60)
        li.shadow_soft_size = 0.05
        lo = bpy.data.objects.new("lamp_warm", li)
        lo.location = ((BX + 380) * MM, 940 * MM, 1230 * MM)
        # 精确指向展示板中心（2550,1040,450）
        target = Vector((BX * MM, (WALL_Y - 13) * MM, 450 * MM))
        lo.rotation_euler = (target - lo.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(lo)
        li2 = bpy.data.lights.new("night_fill", type="SUN")
        li2.energy = 0.12
        li2.color = (0.55, 0.65, 1.0)
        lo2 = bpy.data.objects.new("night_fill", li2)
        lo2.rotation_euler = (math.radians(70), 0, math.radians(30))
        bpy.context.scene.collection.objects.link(lo2)
    else:
        li = bpy.data.lights.new("sun", type="SUN")
        li.energy = 1.0
        li.color = (1.0, 0.96, 0.90)
        lo = bpy.data.objects.new("sun", li)
        lo.rotation_euler = (math.radians(12), 0, 0)
        bpy.context.scene.collection.objects.link(lo)
        li2 = bpy.data.lights.new("fill", type="SUN")
        li2.energy = 0.3
        lo2 = bpy.data.objects.new("fill", li2)
        lo2.rotation_euler = (math.radians(88), 0, 0)
        bpy.context.scene.collection.objects.link(lo2)


def label(text, world_mm, size=0.09):
    c = bpy.data.curves.new("L", type="FONT")
    c.body = text
    c.size = size
    c.align_x = "CENTER"
    o = bpy.data.objects.new("L" + text[:10], c)
    o.location = (world_mm[0] * MM, world_mm[1] * MM, world_mm[2] * MM)
    o.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new("LM")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1)
    o.data.materials.append(m)


def build_all():
    build_kura_frame()
    build_board_and_felt_tree()
    build_petg_and_lamp()


def render(cam, path, res, engine="BLENDER_EEVEE", world=(0.92, 0.93, 0.94)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*world, 1.0)
    bg.inputs["Strength"].default_value = 0.3
    sc.world = w
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered:", path)


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    global NIGHT

    # 1) 布局图（正交立面 + 错位标注）
    NIGHT = False
    reset()
    build_all()
    # 顶部图例（两行，避开场景）+ 物体编号标记
    ly1, ly2, ls = 2020, 1880, 0.07
    label("① KURA 开放框架床 2090×990×1160（四柱·无屋顶）", (900, 940, ly1), ls)
    label("③ 暖光台灯（已有）", (2380, 940, ly1), ls)
    label("⑤ 花环（概念·不安装）", (3230, 940, ly1), ls)
    label("② 森林展示板 600×900 + 毛毡树 450×650", (980, 940, ly2), ls)
    label("④ PETG 前景（台面+四腿）", (2620, 940, ly2), ls)
    label("1", (1045, 940, 1330), 0.12)
    label("2", (2550, 940, 940), 0.12)
    label("3", (2980, 940, 1310), 0.12)
    label("4", (2590, 940, 235), 0.12)
    label("5", (1245, 940, 1285), 0.12)
    cam_data = bpy.data.cameras.new("C1")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 3.8
    c1 = bpy.data.objects.new("C1", cam_data)
    c1.location = (1700 * MM, -2600 * MM, 820 * MM)
    c1.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(c1)
    sc = bpy.context.scene
    sc.camera = c1
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1500, 1050
    w = bpy.data.worlds.new("W")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.92, 0.93, 0.94, 1.0)
    sc.world = w
    sc.render.filepath = str(RENDERS / "forest_layout.png")
    bpy.ops.render.render(write_still=True)
    print("rendered:", RENDERS / "forest_layout.png")

    # 2/3) 白天与夜晚（同机位：床架 + 展示板全景）
    for name, night in (("day", False), ("night", True)):
        NIGHT = night
        reset()
        build_all()
        cam = bpy.data.cameras.new("C2")
        cam.lens = 22
        c2 = bpy.data.objects.new("C2", cam)
        c2.location = (2350 * MM, -1450 * MM, 1250 * MM)
        c2.rotation_euler = (Vector((1600 * MM, 950 * MM, 600 * MM))
                             - Vector((2350 * MM, -1450 * MM, 1250 * MM))).to_track_quat("-Z", "Y").to_euler()
        cam.lens = 20
        bpy.context.scene.collection.objects.link(c2)
        sc = bpy.context.scene
        sc.camera = c2
        sc.render.engine = "BLENDER_EEVEE"
        sc.render.resolution_x, sc.render.resolution_y = 1280, 900
        try:
            sc.view_settings.look = "AgX - Medium High Contrast"
        except TypeError:
            pass
        sc.view_settings.exposure = -0.8
        w2 = bpy.data.worlds.new("W2")
        w2.use_nodes = True
        w2.node_tree.nodes["Background"].inputs["Color"].default_value = \
            ((0.92, 0.93, 0.94, 1.0) if not night else (0.07, 0.08, 0.11, 1.0))
        sc.world = w2
        sc.render.filepath = str(RENDERS / f"forest_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered:", RENDERS / f"forest_{name}.png")

    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "forest_scene.blend"))
    print("FOREST DONE")


main()
