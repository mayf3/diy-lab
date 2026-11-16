#!/usr/bin/env python3
"""森林童话｜总体布局场景（KURA 低床 + 床旁墙展示板 + 可制作/概念分层）。

布局（房间坐标，mm；y=0 为墙线，x 沿墙向右，z 向上）：
- KURA 低床（无屋顶、开放矩形木框）：床沿墙，床外侧朝房间；低床板面 ~400，
  床垫顶 ~640（TM-02 实测后回填）。
- 床旁墙展示板 600×900（5mm 泡沫板建议补购）：贴墙立于床侧，森林背景层。
- 圣诞树 450×650 毛毡（3 层树冠 + 3 积雪带 + 红圆片 + PETG 星）挂展示板中央。
- PETG 小屋×3（本轮打印件）放展示板前的矮凳/家具面（z≈450，TM-09 家具面高待实测）。
- 暖光：床外已有台灯（示意模型），灯头指向展示板。

可制作 / 概念分层（渲染中标注）：
- 可制作（本轮交付）：展示板森林背景、毛毡树、PETG 三件、台灯暖位；
- 概念（不安装）：护栏上沿花环、窗口自发光（后续独立低压灯光模块另案验收）。

用法:
  blender --background --python forest_scene.py
输出: generated/forest_scene.blend + renders_local/
  forest_layout.png（正交布局+尺寸）、forest_day.png、forest_night.png
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
    "pine": (0.36, 0.30, 0.24, 1),      # 床架木（深松）
    "matt": (0.90, 0.90, 0.88, 1),
    "wall": (0.88, 0.89, 0.87, 1),
    "board": (0.96, 0.96, 0.94, 1),
    "dgreen": (0.13, 0.34, 0.24, 1),
    "mgreen": (0.24, 0.48, 0.32, 1),
    "lgreen": (0.42, 0.62, 0.44, 1),
    "white": (0.95, 0.95, 0.93, 1),
    "red": (0.75, 0.22, 0.18, 1),
    "gold": (0.87, 0.70, 0.26, 1),
    "warm": (1.0, 0.78, 0.45, 1),
    "concept": (0.55, 0.55, 0.60, 1),
    "dark": (0.06, 0.08, 0.10, 1),
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in COL:
        bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(name and bpy.data.collections[name])


def mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = C[name]
    if name == "win_glow":
        bsdf.inputs["Emission Color"].default_value = C["warm"]
        bsdf.inputs["Emission Strength"].default_value = 6.0
    m.diffuse_color = C[name]
    return m


C.setdefault("win_glow", (1.0, 0.80, 0.45, 1))


def box(coll, name, w, d, h, center, m="pine", rot=(0, 0, 0)):
    o = bpy.data.objects.new(name, bpy.data.meshes.new(name))
    bpy.data.collections[coll].objects.link(o)
    hx, hy, hz = w * MM / 2, d * MM / 2, h * MM / 2
    import bmesh
    from mathutils import Matrix
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


def tree_felt(coll, prefix, cx, z0, w=450.0, h=650.0, t=5.0, y_face=1040.0):
    """毛毡圣诞树 3 层 + 3 积雪带（贴板面 y_face，厚 5mm 示意）。"""
    layers = [(h * 0.30, w, "dgreen", h * 0.0),
              (h * 0.33, w * 0.70, "mgreen", h * 0.20),
              (h * 0.37, w * 0.47, "lgreen", h * 0.42)]
    for k, (lh, lw, m, y0) in enumerate(layers):
        box(coll, f"{prefix}_crown{k}", lw, t, lh, (cx, y_face + t / 2 + k * 0.8, z0 + h - y0 - lh / 2), m)
    snow_y = [h * 0.28, h * 0.50, h * 0.72]
    for k, sy in enumerate(snow_y):
        box(coll, f"{prefix}_snow{k}", w * (0.92 - 0.22 * k), t + 1.5, 26,
            (cx, y_face + t / 2 + 1.5, z0 + h - sy), "white")
    for k, (dx, dz) in enumerate(((-60, h * 0.62), (55, h * 0.45), (10, h * 0.35))):
        box(coll, f"{prefix}_red{k}", 40, t + 1, 40, (cx + dx, y_face + t / 2 + 2, z0 + h - dz), "red")
    star(coll, f"{prefix}_star", 55, (cx, y_face + t / 2 + 2, z0 + h + 40), "gold", 6.0)


def build_layout(day=True, night=False):
    L, W = 2090.0, 990.0
    LOW_BASE, MATT_T = 400.0, 240.0   # 低床板面/床垫厚（TM-02/09 待实测）
    WALL_Y = 1060.0                    # 墙内表面（床长边贴墙；KURA 与墙间距 <6.5cm 合规）
    # 墙（场景远端，相机可透视看到全屋）+ 地板
    box("BOARD", "wall", 4200, 20, 2400, (900, WALL_Y + 10, 1200), "wall")
    box("BOARD", "floor", 4200, 3200, 4, (900, 500, -2), "wall")
    # KURA 低床（床沿墙）
    by = WALL_Y - W / 2
    box("BED", "bed_frame", L, W, 60, (L / 2, by, LOW_BASE - 30), "pine")
    box("BED", "bed_matt", CFG_MATT[0], CFG_MATT[1], MATT_T, (L / 2, by, LOW_BASE + MATT_T / 2), "matt")
    for sx in (-1, 1):
        for sy in (-1, 1):
            box("BED", f"bed_post{sx}{sy}", 50, 50, LOW_BASE,
                (L / 2 + sx * (L / 2 - 25), by + sy * (W / 2 - 25), LOW_BASE / 2), "pine")
    # 展示板 600×900（床旁墙面 = 床右侧同一面墙，x 2250..2850，板面朝房间 = −y）
    bx, bz = 2550, 450
    by_board = WALL_Y - 13
    box("BOARD", "display_board", 600, 15, 900, (bx, by_board, bz), "board")
    face_y = by_board - 7.5            # 板面（朝房间）
    for k, (dx, h, m) in enumerate(((-210, 330, "dgreen"), (-70, 260, "mgreen"), (80, 300, "dgreen"), (220, 240, "mgreen"))):
        box("BOARD", f"bg_pine{k}", 150, 8, h, (bx + dx, face_y + 1, 120 + h / 2), m)
    box("BOARD", "bg_snow1", 560, 9, 70, (bx, face_y + 2, 150), "white")
    box("BOARD", "bg_snow2", 480, 9, 55, (bx - 30, face_y + 3, 120), "white")
    box("BOARD", "window_glow", 180, 6, 220, (bx - 120, face_y + 1, 620), "win_glow" if night else "warm")
    box("BOARD", "window_cross_v", 14, 9, 220, (bx - 120, face_y + 4, 620), "white")
    box("BOARD", "window_cross_h", 180, 9, 14, (bx - 120, face_y + 4, 620), "white")
    box("BOARD", "window_frame_l", 14, 9, 240, (bx - 214, face_y + 4, 620), "white")
    box("BOARD", "window_frame_r", 14, 9, 240, (bx - 26, face_y + 4, 620), "white")
    tree_felt("TREE", "felt", bx + 60, 90, y_face=face_y - 4)  # 贴板面（背景层前方）
    bench_z = 450.0
    box("PETG", "petg_bench", 500, 300, bench_z, (bx + 40, 880, bench_z / 2), "pine")
    star("PETG", "petg_star", 45, (bx - 180, 920, bench_z + 33), "gold", 6.0)
    box("PETG", "petg_house1", 110, 60, 100, (bx + 40, 920, bench_z + 50), "white")
    box("PETG", "petg_house2", 90, 55, 85, (bx + 170, 920, bench_z + 42.5), "white")
    box("CONCEPT", "concept_garland", 500, 20, 20, (L / 2, by - W / 2 - 10, LOW_BASE + 20), "concept")
    box("LAMP", "lamp_stand", 60, 60, 1200, (bx + 420, 950, 600), "dark")
    box("LAMP", "lamp_head", 160, 90, 60, (bx + 380, 940, 1230), "dark", rot=(0, math.radians(35), 0))
    if night:
        li = bpy.data.lights.new("lamp_warm", type="SPOT")
        li.energy = 3000.0
        li.color = (1.0, 0.75, 0.45)
        li.spot_size = math.radians(60)
        lo = bpy.data.objects.new("lamp_warm", li)
        lo.location = ((bx + 380) * MM, 940 * MM, 1230 * MM)
        lo.rotation_euler = (math.radians(-115), 0, math.radians(-15))
        bpy.context.scene.collection.objects.link(lo)
    if not night:
        li = bpy.data.lights.new("sun", type="SUN")
        li.energy = 1.8
        lo = bpy.data.objects.new("sun", li)
        lo.rotation_euler = (math.radians(88), 0, 0)  # 近水平正面光（海报式立面照明）
        bpy.context.scene.collection.objects.link(lo)
        li2 = bpy.data.lights.new("fill", type="SUN")
        li2.energy = 0.5
        lo2 = bpy.data.objects.new("fill", li2)
        lo2.rotation_euler = (math.radians(70), 0, math.radians(-20))
        bpy.context.scene.collection.objects.link(lo2)


CFG_MATT = (2020.0, 940.0)


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


def render(cam, path, res, flat=False):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.world = bpy.data.worlds.new("W") if sc.world is None else sc.world
    sc.world.color = (0.92, 0.93, 0.94)
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered:", path)


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)

    # 1) 布局图（正交正面 + 尺寸标注）
    reset()
    build_layout(day=True)
    label("展示板 600×900（泡沫板 5mm 建议补购）", (2550, 900, 980))
    label("毛毡圣诞树 450×650（三层树冠+三积雪带）", (2610, 900, 780))
    label("PETG 三件（矮凳/家具面 z≈450 TM-09）", (2650, 900, 520))
    label("暖光台灯（已有）", (3300, 900, 1290))
    label("概念：护栏花环（不安装）", (1045, 900, 260))
    cam = bpy.data.cameras.new("C1")
    cam.type = "ORTHO"
    cam.ortho_scale = 4.2
    c1 = bpy.data.objects.new("C1", cam)
    c1.location = (1600 * MM, -2400 * MM, 600 * MM)
    c1.rotation_euler = (math.radians(90), 0, 0)
    c1.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(c1)
    sc0 = bpy.context.scene
    render(c1, RENDERS / "forest_layout.png", (1400, 1000), flat=True)

    # 2) 白天
    reset()
    build_layout(day=True)
    cam = bpy.data.cameras.new("C2")
    cam.lens = 28
    c2 = bpy.data.objects.new("C2", cam)
    c2.location = (3300 * MM, -1500 * MM, 1500 * MM)
    c2.rotation_euler = (Vector((1900 * MM, 900 * MM, 650 * MM)) - Vector((2100 * MM, -1700 * MM, 1500 * MM))).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(c2)
    render(c2, RENDERS / "forest_day.png", (1280, 900))

    # 3) 夜晚（台灯暖光 + 窗芯发光=概念）
    reset()
    build_layout(day=False, night=True)
    cam3 = bpy.data.cameras.new("C3")
    cam3.lens = 28
    c3 = bpy.data.objects.new("C3", cam3)
    c3.location = (3300 * MM, -1500 * MM, 1500 * MM)
    c3.rotation_euler = (Vector((1900 * MM, 900 * MM, 650 * MM)) - Vector((3300 * MM, -1500 * MM, 1500 * MM))).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(c3)
    sc = bpy.context.scene
    sc.world = bpy.data.worlds.new("NW")
    sc.world.color = (0.05, 0.06, 0.08)
    sc.render.engine = "BLENDER_EEVEE"
    render(c3, RENDERS / "forest_night.png", (1280, 900))

    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "forest_scene.blend"))
    print("FOREST DONE")


main()
