#!/usr/bin/env python3
"""圣诞魔法小屋｜帐篷旁圣诞树 双方案参数化建模与渲染（Blender 5.2 headless）。

设计单位 mm（Blender 内部 m）。所有零件为独立 Object，命名可追溯：
  A_*  方案A 平面开放骨架树（A 字脚架 + 中央方管立柱 + 5 层双侧横梁 + 2D 图案夹层）
  B_*  方案B 立体骨架树（中央树干 4 段 + 3 层×6 辐射枝 + 六边形圈 + 三脚底座）
  TENT_Placeholder  帐篷占位体（165×105×135cm，待实测）

用法（headless）:
  blender --background --python tree_designs_blender.py -- --stage geometry   # 建模+STL+统计
  blender --background --python tree_designs_blender.py -- --stage render     # 静帧渲染
  blender --background --python tree_designs_blender.py -- --stage anim       # 推荐方案装配动画
  blender --background --python tree_designs_blender.py -- --stage all
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Euler

MM = 0.001
ROOT = Path(__file__).resolve().parent
GEN = ROOT / "generated"
OUT_RENDER = ROOT / "renders_local"

# ---------- 设计参数（mm） ----------
A = dict(H=850, WIDTH_BASE=520, LAYERS=5, COL=30.0, COL_SEG=3, BEAM=24.0,
         FOOT_LEN=420.0, FOOT_SPAN=460.0, JOINT=44.0)
B = dict(H=850, TRUNK=36.0, TRUNK_SEG=4, TIERS=3, TIER_START=210, TIER_PITCH=215,
         BRANCH_R=[190.0, 160.0, 130.0], BRANCH_N=6, RING_T=14.0, FOOT3_LEN=380.0)
TENT = (1650.0, 1050.0, 1350.0)   # 占位：165×105×135cm，待实测
PETG = (0.72, 0.76, 0.72, 1.0)
GREEN = (0.16, 0.42, 0.24, 1.0)
WHITE = (0.92, 0.94, 0.93, 1.0)
RED = (0.66, 0.17, 0.12, 1.0)
STAR = (0.91, 0.72, 0.22, 1.0)
TENTC = (0.72, 0.82, 0.80, 1.0)

stats = {"A": {"parts": {}, "fasteners": 0}, "B": {"parts": {}, "fasteners": 0}}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Alpha"].default_value = alpha
    m.diffuse_color = color            # Workbench MATERIAL 模式读取视口色
    if alpha < 1.0:
        m.blend_method = "BLEND"
    return m


def add_box(name, w, d, h, loc, rot=(0, 0, 0), mat_name="PETG", coll=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0]*MM, loc[1]*MM, loc[2]*MM), rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (w / 1000, d / 1000, h / 1000)
    o.data.materials.append(mat(mat_name, {"PETG": PETG, "GREEN": GREEN, "WHITE": WHITE,
                                           "RED": RED, "STAR": STAR, "TENT": TENTC}[mat_name]))
    if coll:
        move(o, coll)
    return o


def add_cyl(name, r, h, loc, rot=(0, 0, 0), mat_name="PETG", vertices=24, coll=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=r * MM, depth=h * MM, location=(loc[0]*MM, loc[1]*MM, loc[2]*MM), rotation=rot, vertices=vertices)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat(mat_name, {"PETG": PETG, "GREEN": GREEN, "WHITE": WHITE,
                                           "RED": RED, "STAR": STAR, "TENT": TENTC}[mat_name]))
    if coll:
        move(o, coll)
    return o


def move(obj, coll_name):
    c = bpy.data.collections.get(coll_name)
    if not c:
        c = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(c)
    for uc in list(obj.users_collection):
        uc.objects.unlink(obj)
    c.objects.link(obj)


def star_pts(r_out, r_in, n=5):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi / 2 + i * math.pi / n
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def make_star(name, r_out, depth, loc, coll, mat_name="STAR"):
    pts = star_pts(r_out, r_out * 0.42)
    verts = [(x * MM, y * MM, 0) for x, y in pts] + [(x * MM, y * MM, depth * MM) for x, y in pts]
    n = len(pts)
    faces = [list(range(n)), [n + i for i in range(n)][::-1]]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, n + j, n + i])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    o = bpy.data.objects.new(name, me)
    o.location = loc
    o.data.materials.append(mat(mat_name, {"STAR": STAR, "GREEN": GREEN}[mat_name]))
    bpy.context.scene.collection.objects.link(o)
    move(o, coll)
    return o


# ---------- 方案 A：平面开放骨架树 ----------
def build_A(coll="A", decorated=False, explode=0.0):
    objs = []
    H, W, L, C, B = A["H"], A["WIDTH_BASE"], A["LAYERS"], A["COL"], A["BEAM"]
    layer_h = (H - 60) / L
    ex = explode * MM
    # 中央立柱 3 段（0 → H）
    seg_h = H / A["COL_SEG"]
    for i in range(A["COL_SEG"]):
        o = add_box(f"A_col_seg{i+1}", C, C, seg_h - 4,
                    (0, 0, seg_h * i + seg_h / 2), mat_name="PETG", coll=coll)
        if explode:
            o.location.z += ex * (i + 1) * 0.5
        objs.append(o)
        stats["A"]["parts"][f"A_col_seg{i+1}"] = 1
    # 层横梁 ×2 面 ×5 层（水平，沿 X 双向外伸）
    for layer in range(L):
        z = 120 + layer * layer_h
        w_layer = W * (1 - layer * (0.62 / L))
        beam_len = w_layer / 2 - C / 2
        for side in (-1, 1):
            o = add_box(f"A_beam_L{layer+1}_{side>0 and 'R' or 'L'}", beam_len, B, B,
                        (side * (C / 2 + beam_len / 2), 0, z),
                        mat_name="GREEN" if decorated else "PETG", coll=coll)
            if explode:
                o.location.x += side * ex
                o.location.z += ex * 0.3
            objs.append(o)
            stats["A"]["parts"][f"A_beam_L{layer+1}"] = stats["A"]["parts"].get(f"A_beam_L{layer+1}", 0) + 1
    # 横梁节点（套柱双插座）×5
    for layer in range(L):
        z = 120 + layer * layer_h
        o = add_box(f"A_joint_L{layer+1}", C + 16, C + 16, B + 12, (0, 0, z), coll=coll)
        if explode:
            o.location.z += ex * 0.3
        objs.append(o)
        stats["A"]["fasteners"] += 2   # 每节点 2×M4 顶丝
        stats["A"]["parts"][f"A_joint_L{layer+1}"] = 1
    # 立柱接头 ×2
    for i in range(1, A["COL_SEG"]):
        o = add_box(f"A_col_sleeve{i}", C + 14, C + 14, 60, (0, 0, seg_h * i), coll=coll)
        objs.append(o)
        stats["A"]["fasteners"] += 2
        stats["A"]["parts"][f"A_col_sleeve{i}"] = 1
    # 底座：A 字双脚 + 横撑 + 底部节点
    for side in (-1, 1):
        ang = math.radians(65)
        o = add_box(f"A_foot_{side>0 and 'R' or 'L'}", A["FOOT_LEN"], 40, B + 10,
                    (side * A["FOOT_SPAN"] / 4, 0, (A["FOOT_LEN"] * math.sin(ang)) / 2 - 5),
                    rot=(0, side * math.radians(90 - 65), 0), coll=coll)
        objs.append(o)
        stats["A"]["parts"][f"A_foot"] = stats["A"]["parts"].get("A_foot", 0) + 1
    o = add_box("A_foot_spread", A["FOOT_SPAN"], 36, 14, (0, 0, 14), coll=coll)
    objs.append(o)
    stats["A"]["parts"]["A_foot_spread"] = 1
    o = add_box("A_base_joint", C + 20, C + 20, 50, (0, 0, 34), coll=coll)
    objs.append(o)
    stats["A"]["fasteners"] += 2
    stats["A"]["parts"]["A_base_joint"] = 1
    # 树顶星
    star = make_star("A_star", 70, 10, (0, 0, (H + 24) * MM), coll)
    if explode:
        star.location.z += ex * 1.6
    objs.append(star)
    stats["A"]["parts"]["A_star"] = 1
    # 装饰：每层绿色"图案板"夹在两面横梁之间（示意布料层）+ 顶层白雪板 + 红色小礼盒
    if decorated:
        for layer in range(L):
            z = 120 + layer * layer_h
            w_layer = W * (1 - layer * (0.62 / L))
            o = add_box(f"A_dec_panel_L{layer+1}", w_layer - 60, 6, layer_h * 0.72,
                        (0, 0, z - layer_h * 0.42), mat_name="GREEN", coll=coll)
            objs.append(o)
        o = add_box("A_dec_snow", W * 0.42, 8, 70, (0, 0, H - 12), mat_name="WHITE", coll=coll)
        objs.append(o)
        o = add_box("A_dec_gift", 70, 50, 50, (W * 0.24, 0, 25), mat_name="RED", coll=coll)
        objs.append(o)
        stats["A"]["parts"]["A_decor_set"] = 1   # 装饰为 2D 打印/布艺一套计
    return objs


# ---------- 方案 B：立体骨架树 ----------
def build_B(coll="B", decorated=False, explode=0.0):
    objs = []
    H, T, SEG, TIERS = B["H"], B["TRUNK"], B["TRUNK_SEG"], B["TIERS"]
    ex = explode * MM
    seg_h = H / SEG
    for i in range(SEG):
        o = add_box(f"B_trunk_seg{i+1}", T, T, seg_h - 6, (0, 0, seg_h * i + seg_h / 2), coll=coll)
        if explode:
            o.location.z += ex * (i + 1) * 0.5
        objs.append(o)
        stats["B"]["parts"][f"B_trunk_seg{i+1}"] = 1
    for tier in range(TIERS):
        z = B["TIER_START"] + tier * B["TIER_PITCH"]
        R = B["BRANCH_R"][tier]
        # 层接头（六向插座）
        o = add_box(f"B_tier_hub_t{tier+1}", T + 26, T + 26, T + 14, (0, 0, z), coll=coll)
        if explode:
            o.location.z += ex * (0.6 + tier * 0.2)
        objs.append(o)
        stats["B"]["fasteners"] += 3
        stats["B"]["parts"][f"B_tier_hub_t{tier+1}"] = 1
        for k in range(B["BRANCH_N"]):
            ang = k * 2 * math.pi / B["BRANCH_N"] + tier * math.pi / B["BRANCH_N"]
            L = R - T / 2 - 30
            cx = math.cos(ang) * (T / 2 + L / 2)
            cy = math.sin(ang) * (T / 2 + L / 2)
            cz = z + L * math.sin(math.radians(12)) / 2
            rot = (0, math.radians(90 - 12), ang)
            o = add_box(f"B_branch_t{tier+1}_{k+1}", L, B["RING_T"], B["RING_T"],
                        (cx, cy, cz), rot=rot, coll=coll)
            if explode:
                o.location.x += math.cos(ang) * ex * 1.4
                o.location.y += math.sin(ang) * ex * 1.4
            objs.append(o)
            stats["B"]["parts"][f"B_branch_t{tier+1}"] = stats["B"]["parts"].get(f"B_branch_t{tier+1}", 0) + 1
            # 圈段（枝端外接，近似直梁段）
            cx2 = math.cos(ang) * (T / 2 + L + 32)
            cy2 = math.sin(ang) * (T / 2 + L + 32)
            o = add_box(f"B_ring_t{tier+1}_{k+1}", 64, B["RING_T"], B["RING_T"] - 4,
                        (cx2, cy2, cz + 6), rot=rot, mat_name="GREEN" if decorated else "PETG", coll=coll)
            if explode:
                o.location.x += math.cos(ang) * ex * 2.0
                o.location.y += math.sin(ang) * ex * 2.0
            objs.append(o)
            stats["B"]["parts"][f"B_ring_t{tier+1}"] = stats["B"]["parts"].get(f"B_ring_t{tier+1}", 0) + 1
            if decorated:
                o = add_box(f"B_decor_t{tier+1}_{k+1}", 46, 8, 30,
                            (cx2 * 0.92, cy2 * 0.92, cz + 26), rot=rot,
                            mat_name=["GREEN", "RED", "WHITE"][(k + tier) % 3], coll=coll)
                objs.append(o)
        stats["B"]["fasteners"] += B["BRANCH_N"]   # 每枝端头 1 顶丝
    # 底部三脚
    for k in range(3):
        ang = k * 2 * math.pi / 3
        o = add_box(f"B_foot_{k+1}", B["FOOT3_LEN"], 34, 12,
                    (math.cos(ang) * B["FOOT3_LEN"] / 2.6, math.sin(ang) * B["FOOT3_LEN"] / 2.6, 26),
                    rot=(0, math.radians(58), ang + math.radians(90)), coll=coll)
        objs.append(o)
        stats["B"]["parts"]["B_foot"] = stats["B"]["parts"].get("B_foot", 0) + 1
    o = add_box("B_base_hub", T + 30, T + 30, 56, (0, 0, 40), coll=coll)
    objs.append(o)
    stats["B"]["fasteners"] += 3
    stats["B"]["parts"]["B_base_hub"] = 1
    star = make_star("B_star", 62, 9, (0, 0, (H + 20) * MM), coll)
    if explode:
        star.location.z += ex * 2.2
    objs.append(star)
    stats["B"]["parts"]["B_star"] = 1
    return objs


# ---------- 帐篷占位 ----------
def build_tent_placeholder():
    w, d, h = [v * MM for v in TENT]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(w / 2 + 0.55, d / 2 + 0.15, h / 2))
    o = bpy.context.active_object
    o.name = "TENT_Placeholder"
    o.scale = (w, d, h)
    o.data.materials.append(mat("TENTC", TENTC, alpha=0.35))
    txt = bpy.data.curves.new("TENT_txt", type="FONT")
    txt.body = "帐篷占位 165×105×135 cm（待实测）"
    txt.size = 0.09
    to = bpy.data.objects.new("TENT_label", txt)
    to.location = (w / 2 + 0.55, d / 2 + 0.15, h + 0.06)
    bpy.context.scene.collection.objects.link(to)
    move(o, "TENT")
    move(to, "TENT")


# ---------- 相机/灯光/渲染 ----------
def setup_camera_light(name="CAM_MAIN", loc=(1.55, -1.35, 1.12), target=(0, 0, 0.45)):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    cam.location = loc
    direction = Vector(target) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = 38
    bpy.context.scene.collection.objects.link(cam)
    light = bpy.data.lights.new("KEY", type="SUN")
    light.energy = 3.2
    light.angle = 0.35
    lo = bpy.data.objects.new("KEY", light)
    lo.rotation_euler = Euler((math.radians(52), 0, math.radians(-38)))
    bpy.context.scene.collection.objects.link(lo)
    fill = bpy.data.lights.new("FILL", type="SUN")
    fill.energy = 1.1
    fo = bpy.data.objects.new("FILL", fill)
    fo.rotation_euler = Euler((math.radians(80), 0, math.radians(120)))
    bpy.context.scene.collection.objects.link(fo)
    return cam


def setup_render(cam, res=(1280, 960)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("W") if not sc.world else sc.world
    sc.world.color = (0.90, 0.92, 0.93)


def render_to(path):
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("rendered:", path)


def hide_collection(name, hide):
    c = bpy.data.collections.get(name)
    if c:
        c.hide_viewport = hide
        c.hide_render = hide


# ---------- 主流程 ----------
def stage_geometry():
    reset_scene()
    build_A()
    build_B()
    (GEN / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    # STL 导出：每个独立零件单文件
    stl_dir = GEN / "stl"
    for d in ("A", "B", "first_plate"):
        (stl_dir / d).mkdir(parents=True, exist_ok=True)
    for obj in list(bpy.data.objects):
        if obj.name.startswith(("A_", "B_")) and obj.type == "MESH":
            target = "A" if obj.name.startswith("A_") else "B"
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.wm.stl_export(filepath=str(stl_dir / target / f"{obj.name}.stl"),
                                  export_selected_objects=True, ascii_format=False)
    (GEN / "blends").mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(GEN / "blends" / "tree_designs.blend"))
    print("GEOMETRY DONE:", json.dumps(stats, ensure_ascii=False))


def stage_render():
    # blend 已包含全部几何；按方案/视图分别隐藏集合渲染
    views = [("bare", False, 0.0), ("decorated", True, 0.0), ("exploded", False, 240.0), ("scale", False, 0.0)]
    for view, deco, explode in views:
        reset_scene()
        build_A(decorated=deco, explode=explode)
        build_B(decorated=deco, explode=explode)
        if view == "scale":
            build_tent_placeholder()
        cam = setup_camera_light()
        setup_render(cam)
        render_to(OUT_RENDER / f"tree_{view}.png")
    # 对比合成图：同场景两树并排（A 左 B 右）
    reset_scene()
    objs_a = build_A(coll="A_CMP")
    for o in objs_a:
        o.location.x -= 0.42
    objs_b = build_B(coll="B_CMP")
    for o in objs_b:
        o.location.x += 0.42
    build_tent_placeholder()
    cam = setup_camera_light(loc=(2.35, -2.05, 1.28), target=(0.1, 0.1, 0.5))
    setup_render(cam, res=(1600, 1000))
    render_to(OUT_RENDER / "compare_side_by_side.png")
    print("RENDER DONE")


def stage_anim():
    """推荐方案 A 装配动画：爆炸位(f1) → 平滑装配(f90) → 停留(f108)。"""
    reset_scene()
    build_A(coll="ANIM_X", explode=260.0)   # 动画用：初始爆炸位
    build_A(coll="ANIM_T", explode=0.0)     # 目标装配位（隐藏，仅作位置参照）
    cam = setup_camera_light(loc=(1.8, -1.5, 1.0), target=(0, 0, 0.45))
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    sc.render.fps = 24
    sc.frame_start, sc.frame_end = 1, 108
    for o in bpy.data.collections["ANIM_X"].objects:
        o.keyframe_insert(data_path="location", frame=1)
        tgt = bpy.data.collections["ANIM_T"].objects.get(o.name)
        if tgt:
            o.location = tgt.location.copy()
            o.keyframe_insert(data_path="location", frame=90)
    for o in bpy.data.collections["ANIM_T"].objects:
        o.hide_render = True
        o.hide_viewport = True
    sc.frame_set(100)
    outdir = OUT_RENDER / "anim_frames"
    outdir.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(outdir / "frame_")
    bpy.ops.render.render(animation=True)
    (OUT_RENDER / "assembly_A.mp4.note").write_text(
        "合成命令：ffmpeg -framerate 24 -i anim_frames/frame_####.png -c:v libx264 -pix_fmt yuv420p assembly_A.mp4。MP4 不入 git 历史。",
        encoding="utf-8")
    print("ANIM DONE")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["geometry", "render", "anim", "all"])
    args = ap.parse_args(argv)
    GEN.mkdir(parents=True, exist_ok=True)
    OUT_RENDER.mkdir(parents=True, exist_ok=True)
    if args.stage in ("geometry", "all"):
        stage_geometry()
    if args.stage in ("render", "all"):
        stage_render()
    if args.stage in ("anim", "all"):
        stage_anim()


main()
