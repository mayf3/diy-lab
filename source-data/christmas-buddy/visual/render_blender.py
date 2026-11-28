# Blender 5.x headless 渲染：Christmas Buddy 两方案的 8 视图真实模型渲染。
# 渲染对象 = mech/outputs 的 CadQuery 导出 STL（同一几何源，非概念图）。
# 运行：blender --background --python source-data/christmas-buddy/visual/render_blender.py
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]  # .../diy-lab-xmas-buddy
MECH = ROOT / "source-data/christmas-buddy/mech/outputs"
OUT = ROOT / "renders_local/christmas-buddy"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {
    "cream_white": (0.953, 0.929, 0.886, 1.0),   # #F3EDE2
    "forest_green": (0.184, 0.322, 0.200, 1.0),  # #2F5233
    "christmas_red": (0.702, 0.192, 0.180, 1.0), # #B3312E
    "starlight_gold": (0.831, 0.686, 0.216, 1.0),# #D4AF37
    "pcb_green": (0.05, 0.28, 0.15, 1.0),
    "chip_black": (0.05, 0.05, 0.06, 1.0),
    "speaker_dark": (0.10, 0.10, 0.11, 1.0),
}

def mat(name, rgba, rough=0.55, metallic=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    return m

PART_COLOR = {
    "base": ("starlight_gold", 0.45, 0.6),
    "body_front": ("cream_white", 0.55, 0.0),
    "body_rear": ("cream_white", 0.55, 0.0),
    "head": ("cream_white", 0.55, 0.0),
    "brim": ("forest_green", 0.6, 0.0),
    "hat": ("forest_green", 0.6, 0.0),
    "scarf": ("christmas_red", 0.6, 0.0),
    "neck_ring": ("starlight_gold", 0.45, 0.5),
    "face_plate": ("cream_white", 0.35, 0.0),
    "pcb": ("pcb_green", 0.5, 0.0),
    "pi": ("pcb_green", 0.55, 0.0),
    "esp32": ("chip_black", 0.5, 0.0),
    "speaker": ("speaker_dark", 0.7, 0.0),
    "button_board": ("pcb_green", 0.5, 0.0),
    "star_module": ("pcb_green", 0.5, 0.0),
    "mic": ("chip_black", 0.5, 0.0),
    "btn_00": ("speaker_dark", 0.7, 0.0), "btn_01": ("speaker_dark", 0.7, 0.0),
    "btn_10": ("speaker_dark", 0.7, 0.0), "btn_11": ("speaker_dark", 0.7, 0.0),
}

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def import_part(path, name, loc=(0, 0, 0), scale=0.001):
    bpy.ops.wm.stl_import(filepath=str(path))
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.scale = (scale, scale, scale)
    ob.location = loc
    cname, rough, metallic = PART_COLOR[name]
    ob.data.materials.clear()
    ob.data.materials.append(mat(f"m_{cname}", COLORS[cname], rough, metallic))
    return ob

def light_scene():
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.92, 0.94, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.30
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN'))
    sun.data.energy = 1.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    sun.data.angle = math.radians(15)
    bpy.context.collection.objects.link(sun)
def camera(name, loc, target=(0, 0, 75), ortho=None):
    cam = bpy.data.cameras.new(name)
    if ortho:
        cam.type = 'ORTHO'
        cam.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cam)
    ob.location = loc
    ob.data.clip_start = 0.005
    d = [t - l for l, t in zip(loc, target)]
    import mathutils
    ob.rotation_euler = mathutils.Vector(d).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(ob)
    return ob

def render(cam, path, samples=40):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.view_settings.view_transform = 'Standard'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1280
    sc.render.resolution_y = 960
    sc.camera = cam
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)

def floor_plane():
    bpy.ops.mesh.primitive_plane_add(size=1.6, location=(0, 0, 0))
    f = bpy.context.selected_objects[0]
    f.name = "floor"
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.85, 0.86, 0.88, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    f.data.materials.append(fm)

def build(scheme, exploded=False, hide_front=False, core_only=False):
    clear()
    d = MECH / f"scheme_{scheme}"
    parts = ["base", "body_front", "body_rear", "head", "brim", "hat", "scarf",
             "neck_ring", "face_plate"]
    for p in parts:
        if (d / f"{p}.stl").exists():
            loc = (0, 0, 0)
            if exploded:
                if p == "body_front":
                    loc = (0, 0.06, 0)
                elif p in ("head", "brim", "hat", "face_plate"):
                    loc = (0, 0, 0.055)
                elif p in ("scarf", "neck_ring"):
                    loc = (0, 0, 0.018)
            if core_only and p not in ("base",):
                continue
            ob = import_part(d / f"{p}.stl", p, loc)
            if hide_front and p == "body_front":
                ob.hide_render = True
    if not core_only:
        cdir = d / "core"
        for p, off in (("pcb", (0, 0, 0)), ("pi", (0, 0, 0)), ("esp32", (0, 0, 0)),
                       ("speaker", (0, 0, 0)), ("button_board", (0, 0, 0)),
                       ("btn_00", (0, 0, 0)), ("btn_01", (0, 0, 0)),
                       ("btn_10", (0, 0, 0)), ("btn_11", (0, 0, 0)),
                       ("star_module", (0, 0, 0)), ("mic", (0, 0, 0))):
            f = cdir / f"{p}.stl"
            if f.exists():
                loc = off
                if exploded:
                    loc = (off[0], off[1] - 0.025 if p in ("pi",) else off[1], off[2] + (0.012 if p in ("speaker", "button_board", "star_module") else 0))
                import_part(f, p, loc)
    light_scene()
    floor_plane()
    return d

def shoot(scheme, tag, d):
    # 8 视图
    views = {
        "front": camera("c", (0, -0.42, 0.085), (0, 0, 0.075)),
        "side": camera("c", (0.42, 0, 0.085), (0, 0, 0.075)),
        "back": camera("c", (0, 0.42, 0.085), (0, 0, 0.075)),
        "deg45": camera("c", (-0.30, -0.30, 0.17), (0, 0, 0.070)),
        "exploded": camera("c", (-0.30, -0.40, 0.18), (0, 0, 0.085)),
        "case_open": camera("c", (0, -0.40, 0.10), (0, 0, 0.05)),
        "pcb_assembly": camera("c", (-0.15, -0.24, 0.09), (-0.01, 0, 0.042), ortho=0.16),
        "base_scene": camera("c", (-0.26, -0.30, 0.11), (0, 0, 0.05)),
    }
    for name, cam in views.items():
        render(cam, OUT / f"{scheme}_{tag}_{name}.png")

# 每方案：5 个整装视图 + 开壳 + 爆炸 + PCB 内核特写
for scheme, tag in (("a", "v1"), ("b", "v2")):
    build(scheme)
    d = None
    views_full = {
        "front": camera("c", (0, -0.42, 0.085), (0, 0, 0.075)),
        "side": camera("c", (0.42, 0, 0.085), (0, 0, 0.075)),
        "back": camera("c", (0, 0.42, 0.085), (0, 0, 0.075)),
        "deg45": camera("c", (-0.30, -0.30, 0.17), (0, 0, 0.070)),
        "base_scene": camera("c", (-0.26, -0.30, 0.11), (0, 0, 0.05)),
    }
    for name, cam in views_full.items():
        render(cam, OUT / f"{scheme}_{tag}_{name}.png")
    build(scheme, hide_front=True)
    render(camera("c", (0, -0.40, 0.10), (0, 0, 0.05)), OUT / f"{scheme}_{tag}_case_open.png")
    build(scheme, exploded=True)
    render(camera("c", (-0.30, -0.40, 0.18), (0, 0, 0.085)), OUT / f"{scheme}_{tag}_exploded.png")
    build(scheme, core_only=True)
    render(camera("c", (-0.15, -0.24, 0.09), (-0.01, 0, 0.042), ortho=0.16), OUT / f"{scheme}_{tag}_pcb_assembly.png")
print("RENDER DONE ->", OUT)
