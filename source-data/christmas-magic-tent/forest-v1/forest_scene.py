#!/usr/bin/env python3
"""森林童话｜总体布局场景 v2（KURA 低床 + 床旁墙展示板 + 毛毡树 + PETG + 台灯暖光）。

布局（房间坐标 mm；y≈1060 为墙内面；x 沿墙向右，z 向上）：
- KURA 低床（无屋顶、开放矩形木框）：2090×990，床长边贴墙（间距 <6.5cm 合规）；
- 展示板 600×900：床旁墙（床右侧同一面墙），板面朝房间；
- 毛毡圣诞树 450×650：贴展示板中央（3 层树冠 + 3 积雪带 + 红圆片 + PETG 星）；
- PETG 小屋×2 + 圆角星：展示板前矮凳/家具面（z≈450，TM-09 待实测）；
- 台灯（已有）：暖光指向展示板；窗口自发光 = 概念（灯光模块另案）。

渲染：forest_layout.png（正交立面+尺寸标注）、forest_day.png、forest_night.png。
可制作 vs 概念在图上以标注区分；睡眠区（床垫顶面及护栏内侧）零添加。

用法: blender --background --python forest_scene.py
输出: generated/forest_scene.blend + renders_local/*.png
"""
from __future__ import annotations
import math
from pathlib import Path

import bpy
from mathutils import Vector

MM = 0.001
ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
RENDERS = ROOT / "renders_local"

COL = ("BED", "BOARD", "TREE", "PETG", "LAMP", "CONCEPT", "CUT", "LABEL")

C = {
    "pine": (0.36, 0.30, 0.24, 1),
    "matt": (0.90, 0.90, 0.88, 1),
    "wall": (0.93, 0.94, 0.92, 1),
    "board": (0.97, 0.97, 0.95, 1),
    "dgreen": (0.13, 0.34, 0.24, 1),
    "mgreen": (0.24, 0.48, 0.32, 1),
    "lgreen": (0.42, 0.62, 0.44, 1),
    "white": (0.96, 0.96, 0.94, 1),
    "red": (0.75, 0.22, 0.18, 1),
    "gold": (0.87, 0.70, 0.26, 1),
    "warm": (1.0, 0.80, 0.50, 1),
    "concept": (0.62, 0.62, 0.66, 1),
    "dark": (0.10, 0.11, 0.13, 1),
    "win_glow": (1.0, 0.80, 0.45, 1),
}


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
    o.rotation_euler = rot
    o.data.materials.append(mat(m))
    return o


def star(coll, name, r, center, m, t=6.0):
    import bmesh
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


CFG_MATT = (2020.0, 940.0)
WALL_Y = 1060.0
BX, BZ = 2550.0, 450.0
BENCH_Z = 450.0
NIGHT = False


def build_room_and_bed():
    box("BOARD", "wall", 6000, 20, 2400, (1900, WALL_Y + 10, 1200), "wall")
    box("BOARD", "floor", 6000, 3600, 4, (1900, 700, -2), "wall")
    L, W = 2090.0, 990.0
    by = WALL_Y - W / 2
    box("BED", "bed_frame", L, W, 60, (L / 2, by, 370), "pine")
    box("BED", "bed_matt", CFG_MATT[0], CFG_MATT[1], 240, (L / 2, by, 370 + 30 + 120), "matt")
    for sx in (-1, 1):
        for sy in (-1, 1):
            box("BED", f"bed_post{sx}{sy}", 50, 50, 400,
                (L / 2 + sx * (L / 2 - 25), by + sy * (W / 2 - 25), 200), "pine")
    box("CONCEPT", "concept_garland", 500, 20, 20, (L / 2, by - W / 2 - 12, 430), "concept")


def build_board_and_tree():
    by_b = WALL_Y - 13
    box("BOARD", "display_board", 600, 15, 900, (BX, by_b, BZ), "board")
    face_y = by_b - 7.5
    for k, (dx, h, m) in enumerate(((-210, 330, "dgreen"), (-70, 260, "mgreen"),
                                    (80, 300, "dgreen"), (220, 240, "mgreen"))):
        box("BOARD", f"bg_pine{k}", 150, 8, h, (BX + dx, face_y + 1, 120 + h / 2), m)
    box("BOARD", "bg_snow1", 560, 9, 70, (BX, face_y + 2, 150), "white")
    box("BOARD", "bg_snow2", 480, 9, 55, (BX - 30, face_y + 3, 120), "white")
    box("BOARD", "window_glow", 180, 6, 220, (BX - 120, face_y + 1, 620),
        "win_glow" if NIGHT else "warm")
    box("BOARD", "window_cross_v", 14, 9, 220, (BX - 120, face_y + 4, 620), "white")
    box("BOARD", "window_cross_h", 180, 9, 14, (BX - 120, face_y + 4, 620), "white")
    box("BOARD", "window_frame_l", 14, 9, 240, (BX - 214, face_y + 4, 620), "white")
    box("BOARD", "window_frame_r", 14, 9, 240, (BX - 26, face_y + 4, 620), "white")
    cx = BX + 60
    face = face_y - 4
    layers = [(650 * 0.30, 450, "dgreen", 0),
              (650 * 0.33, 315, "mgreen", 130),
              (650 * 0.37, 212, "lgreen", 300)]
    for k, (lh, lw, m, y0) in enumerate(layers):
        box("TREE", f"felt_crown{k}", lw, 5, lh, (cx, face + 2.5 + k * 0.8, 90 + 650 - y0 - lh / 2), m)
    for k, (sy, sw) in enumerate(((182, 414), (332, 270), (512, 188))):
        box("TREE", f"felt_snow{k}", sw, 6.5, 26, (cx, face + 2.5 + 1.5, 90 + 650 - sy), "white")
    for k, (dx, dz) in enumerate(((-60, 404), (55, 293), (10, 228))):
        box("TREE", f"felt_red{k}", 40, 6, 40, (cx + dx, face + 3, 90 + 650 - dz), "red")
    star("TREE", "felt_star", 55, (cx, face + 3, 90 + 650 + 46), "gold", 6.0)


def build_petg_and_lamp():
    bench_z = BENCH_Z
    box("PETG", "bench", 500, 300, bench_z, (BX + 40, 880, bench_z / 2), "pine")
    star("PETG", "petg_star", 45, (BX - 180, 920, bench_z + 33), "gold", 6.0)
    box("PETG", "petg_house1", 110, 60, 100, (BX + 40, 920, bench_z + 50), "white")
    box("PETG", "petg_house2", 90, 55, 85, (BX + 170, 920, bench_z + 42.5), "white")
    box("LAMP", "lamp_stand", 60, 60, 1200, (BX + 420, 950, 600), "dark")
    box("LAMP", "lamp_head", 160, 90, 60, (BX + 380, 940, 1230), "dark",
        rot=(0, math.radians(35), 0))
    if NIGHT:
        li = bpy.data.lights.new("lamp_warm", type="SPOT")
        li.energy = 3000.0
        li.color = (1.0, 0.75, 0.45)
        li.spot_size = math.radians(60)
        lo = bpy.data.objects.new("lamp_warm", li)
        lo.location = ((BX + 380) * MM, 940 * MM, 1230 * MM)
        lo.rotation_euler = (math.radians(-115), 0, math.radians(-15))
        bpy.context.scene.collection.objects.link(lo)
    else:
        li = bpy.data.lights.new("sun", type="SUN")
        li.energy = 1.8
        lo = bpy.data.objects.new("sun", li)
        lo.rotation_euler = (math.radians(88), 0, 0)
        bpy.context.scene.collection.objects.link(lo)
        li2 = bpy.data.lights.new("fill", type="SUN")
        li2.energy = 0.5
        lo2 = bpy.data.objects.new("fill", li2)
        lo2.rotation_euler = (math.radians(70), 0, math.radians(-20))
        bpy.context.scene.collection.objects.link(lo2)


def label(text, world_mm, size=0.10):
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
    build_room_and_bed()
    build_board_and_tree()
    build_petg_and_lamp()


def render(cam, path, res, engine="BLENDER_EEVEE", world=(0.92, 0.93, 0.94)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = engine
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.world = bpy.data.worlds.new("W")
    sc.world.color = world
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered:", path)


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)

    global NIGHT
    # 1) 布局图（正交立面 + 尺寸标注）
    NIGHT = False
    reset()
    build_all()
    label("森林展示板 600×900", (2550, 940, 1000))
    label("毛毡圣诞树 450×650", (2550, 940, 660))
    label("PETG 星 + 小屋×2（前景家具）", (2550, 940, 380))
    label("暖光台灯（已有）", (3300, 940, 1290))
    label("概念：护栏花环（不安装）", (1045, 900, 240))
    cam_data = bpy.data.cameras.new("C1")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 4.2
    c1 = bpy.data.objects.new("C1", cam_data)
    c1.location = (1900 * MM, -2400 * MM, 560 * MM)
    c1.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(c1)
    sc = bpy.context.scene
    sc.camera = c1
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
    sc.world = bpy.data.worlds.new("W")
    sc.world.color = (0.92, 0.93, 0.94)
    sc.render.filepath = str(RENDERS / "forest_layout.png")
    bpy.ops.render.render(write_still=True)
    print("rendered:", RENDERS / "forest_layout.png")

    # 2/3) 白天与夜晚（同机位）
    for name, night in (("day", False), ("night", True)):
        NIGHT = night
        reset()
        build_all()
        cam = bpy.data.cameras.new("C2")
        cam.lens = 26
        c2 = bpy.data.objects.new("C2", cam)
        c2.location = (2550 * MM, -1250 * MM, 520 * MM)
        c2.rotation_euler = (Vector((2550 * MM, 1050 * MM, 440 * MM))
                             - Vector((2550 * MM, -1250 * MM, 520 * MM))).to_track_quat("-Z", "Y").to_euler()
        cam.lens = 35
        bpy.context.scene.collection.objects.link(c2)
        sc = bpy.context.scene
        sc.camera = c2
        sc.render.engine = "BLENDER_EEVEE"
        sc.render.resolution_x, sc.render.resolution_y = 1280, 900
        sc.world = bpy.data.worlds.new("W2")
        sc.world.color = (0.92, 0.93, 0.94) if not night else (0.05, 0.06, 0.08)
        sc.render.filepath = str(RENDERS / f"forest_{name}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered:", RENDERS / f"forest_{name}.png")

    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "forest_scene.blend"))
    print("FOREST DONE")


main()
