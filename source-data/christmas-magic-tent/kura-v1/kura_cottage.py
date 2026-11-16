#!/usr/bin/env python3
"""KURA 低床 · 无屋顶圣诞装饰预览（数字设计，非施工/安全认证）。

事实：IKEA KURA 502.665.06，参考外形 2090×990×1160 mm；床垫 900×2000 mm。
用户纠正：不使用斜屋顶、不增加屋顶布或三角木梁；只在开放式矩形框架上做节日设计。
床架细部为示意，实际连接件、间距及安装限制以实物和产品说明书为准。

输出：generated/kura_cottage.blend + renders_local/kura_{structure_labeled,deco_minimal,deco_fabric}.png。
使用：blender --background --python kura_cottage.py -- --deco both
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

# 毫米。仅外形尺寸和床垫平面尺寸是已确定的型号参考；所有截面/床垫高度为可调视觉参数。
CFG = {
    "L": 2090.0, "W": 990.0, "FRAME_H": 1160.0,
    "POST": 65.0, "TOP_RAIL": 58.0, "LOW_RAIL_H": 140.0,
    "MATT_L": 2000.0, "MATT_W": 900.0,
    "MATT_T": 115.0, "MATT_BOTTOM": 125.0,
}
COLORS = {
    "PINE": (0.77, 0.58, 0.37, 1),
    "PINE_LIGHT": (0.90, 0.76, 0.56, 1),
    "WHITE": (0.97, 0.96, 0.91, 1),
    "MATTRESS": (0.94, 0.91, 0.83, 1),
    "DEEP_GREEN": (0.13, 0.34, 0.22, 1),
    "LIGHT_GREEN": (0.35, 0.53, 0.28, 1),
    "CREAM": (0.98, 0.96, 0.83, 1),
    "RED": (0.72, 0.19, 0.17, 1),
    "GOLD": (0.89, 0.67, 0.28, 1),
    "SNOW": (0.95, 0.95, 0.92, 1),
    "FLOOR": (0.87, 0.82, 0.73, 1),
}
COLLECTIONS = ("FRAME_LOW_NO_ROOF", "MATTRESS_LOW", "DECO_MINIMAL", "DECO_FABRIC", "BACKGROUND")

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in COLLECTIONS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)

def material(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.diffuse_color = COLORS[name]
    return m

def mesh_object(coll, name, verts, faces, color):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.data.collections[coll].objects.link(ob)
    ob.data.materials.append(material(color))
    return ob

def box(coll, name, w, d, h, center, color="PINE"):
    x, y, z = (v * MM for v in center)
    wx, dy, hz = (v * MM / 2 for v in (w, d, h))
    verts = [
        (x-wx,y-dy,z-hz),(x+wx,y-dy,z-hz),(x+wx,y+dy,z-hz),(x-wx,y+dy,z-hz),
        (x-wx,y-dy,z+hz),(x+wx,y-dy,z+hz),(x+wx,y+dy,z+hz),(x-wx,y+dy,z+hz),
    ]
    return mesh_object(coll,name,verts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],color)

def flat_triangle(coll, name, x, y, zbase, w, h, color, thickness=7):
    # 竖立在前侧外部的轻量纸板/不织布造型；并非悬挂于床上方。
    x,y,zbase,w,h,t = [v*MM for v in (x,y,zbase,w,h,thickness)]
    verts=[(x-w/2,y-t/2,zbase),(x+w/2,y-t/2,zbase),(x,y-t/2,zbase+h),
           (x-w/2,y+t/2,zbase),(x+w/2,y+t/2,zbase),(x,y+t/2,zbase+h)]
    return mesh_object(coll,name,verts,[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],color)

def star(coll, name, center, radius, color="GOLD", t=8):
    cx,cy,cz = center
    pts=[]
    for i in range(10):
        a=math.pi/2+i*math.pi/5
        r=radius if i%2==0 else radius*0.43
        pts.append(((cx+r*math.cos(a))*MM,(cy-t/2)*MM,(cz+r*math.sin(a))*MM))
    verts=pts+[(x,(cy+t/2)*MM,z) for x,_,z in pts]
    n=len(pts)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh_object(coll,name,verts,faces,color)

def tree(coll, name, cx, cy, base, height=460, width=310, color="DEEP_GREEN"):
    # 三级重叠树冠，底部在地面；软材造型可不依赖大型3D骨架。
    for i,(frac,ww) in enumerate(((0,1.0),(0.28,0.80),(0.54,0.61))):
        flat_triangle(coll,f"{name}_tier{i}",cx,cy,base+height*frac,width*ww,height*0.46,color)
    box(coll,f"{name}_trunk",44,14,75,(cx,cy,base+36),"PINE_LIGHT")
    star(coll,f"{name}_star",(cx,cy,base+height+16),45)
    for i,(dx,dz,shade) in enumerate(((-60,135,"RED"),(52,115,"GOLD"),(3,222,"CREAM"),(-18,320,"LIGHT_GREEN"))):
        box(coll,f"{name}_felt_dot{i}",28,12,28,(cx+dx,cy-9,base+dz),shade)

def make_frame():
    L,W,H,POST=CFG["L"],CFG["W"],CFG["FRAME_H"],CFG["POST"]
    px,py=L/2-POST/2,W/2-POST/2
    # 标准低床模式的开放矩形框架示意；没有屋脊、斜梁、顶棚或上铺平台。
    for sx in (-1,1):
        for sy in (-1,1):
            box("FRAME_LOW_NO_ROOF",f"post_{sx}_{sy}",POST,POST,H,(sx*px,sy*py,H/2),"PINE")
    for sy in (-1,1):
        box("FRAME_LOW_NO_ROOF",f"top_rail_long_{sy}",L-POST,CFG["TOP_RAIL"],CFG["TOP_RAIL"],
            (0,sy*py,H-CFG["TOP_RAIL"]/2),"PINE_LIGHT")
        box("FRAME_LOW_NO_ROOF",f"lower_rail_long_{sy}",L-POST,30,95,
            (0,sy*py,CFG["LOW_RAIL_H"]),"PINE")
    for sx in (-1,1):
        box("FRAME_LOW_NO_ROOF",f"top_rail_end_{sx}",CFG["TOP_RAIL"],W-POST,CFG["TOP_RAIL"],
            (sx*px,0,H-CFG["TOP_RAIL"]/2),"PINE_LIGHT")
        box("FRAME_LOW_NO_ROOF",f"lower_rail_end_{sx}",33,W-POST,95,
            (sx*px,0,CFG["LOW_RAIL_H"]),"PINE")
    box("FRAME_LOW_NO_ROOF","slat_platform_visual",L-2*POST,W-2*POST,20,
        (0,0,CFG["MATT_BOTTOM"]-12),"PINE_LIGHT")

def make_mattress():
    box("MATTRESS_LOW","mattress_low",CFG["MATT_L"],CFG["MATT_W"],CFG["MATT_T"],
        (0,0,CFG["MATT_BOTTOM"]+CFG["MATT_T"]/2),"MATTRESS")
    box("MATTRESS_LOW","duvet_visual",CFG["MATT_L"]*0.56,CFG["MATT_W"]*0.90,22,
        (240,0,CFG["MATT_BOTTOM"]+CFG["MATT_T"]+10),"WHITE")

def make_backdrop():
    box("BACKGROUND","ground",3400,2400,8,(0,0,-12),"FLOOR")

def flat_garland(coll,name,y,z):
    # 示意图里的松枝是贴合外侧横梁的平面造型，不能视为实际可安全安装的灯串/花环。
    for j in range(16):
        x=-850+j*(1700/15)
        color="DEEP_GREEN" if j%3 else "LIGHT_GREEN"
        box(coll,f"{name}_leaf{j}",110,8,38,(x,y,z+3*math.sin(j)),"DEEP_GREEN" if j%3 else "LIGHT_GREEN")
    for j,x in enumerate((-630,-210,240,690)):
        box(coll,f"{name}_berry{j}",27,12,27,(x,y-9,z-6),"RED")

def make_minimal():
    c="DECO_MINIMAL"
    w=CFG["W"]
    # 贴在外侧的低位造型树（地面到 ~60cm），不需要独立大树骨架。
    tree(c,"felt_tree",cx=-685,cy=-w/2-61,base=35,height=485,width=345)
    flat_garland(c,"outer_top_rail",y=-w/2-39,z=1103)
    for i,x in enumerate((110,470,800)):
        star(c,f"low_rail_star{i}",(x,-w/2-49,CFG["LOW_RAIL_H"]+63),32,"CREAM")
    for i,x in enumerate((-690,-525)):
        box(c,f"paper_gift_{i}",115,80,112,(x,-w/2-105,62),"RED" if i==0 else "CREAM")
        box(c,f"ribbon_{i}",14,85,113,(x,-w/2-149,63),"GOLD")
    # 不添加电线、床头悬挂灯具、布顶、垂帘

def make_fabric():
    c="DECO_FABRIC"
    w=CFG["W"]
    tree(c,"forest_tree",cx=-770,cy=-w/2-58,base=35,height=420,width=265,color="DEEP_GREEN")
    tree(c,"forest_tree_small",cx=770,cy=-w/2-60,base=35,height=280,width=175,color="LIGHT_GREEN")
    # 全部是外侧水平木框面上的纸样/软质贴片；非床内垂帘
    box(c,"snow_on_lower_rail",640,10,35,(90,-w/2-49,CFG["LOW_RAIL_H"]+55),"SNOW")
    for i,x in enumerate((-200,95,395)):
        star(c,f"snowflake_paper{i}",(x,-w/2-52,CFG["LOW_RAIL_H"]+93),30,"SNOW",t=5)
    flat_garland(c,"flat_felt_spruce",y=-w/2-40,z=1090)
    for i,x in enumerate((-440,0,445)):
        star(c,f"felt_high_star{i}",(x,-w/2-52,1026),31,"GOLD" if i==1 else "CREAM",t=5)

def camera():
    cam_data=bpy.data.cameras.new("Camera")
    cam=bpy.data.objects.new("Camera",cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location=(3.1,-3.25,1.90)
    cam.rotation_euler=(Vector((0,0,0.60))-cam.location).to_track_quat("-Z","Y").to_euler()
    cam_data.lens=38
    return cam

def render(cam,filename):
    scene=bpy.context.scene
    scene.camera=cam
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=False
    scene.render.resolution_x=1440
    scene.render.resolution_y=960
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.film_transparent=False
    scene.world = bpy.data.worlds.new("KuraNeutral") if scene.world is None else scene.world
    scene.world.color=(0.91,0.92,0.92)
    scene.render.filepath=str(RENDERS/filename)
    bpy.ops.render.render(write_still=True)

def visibility(which):
    bpy.data.collections["DECO_MINIMAL"].hide_render = which!="minimal"
    bpy.data.collections["DECO_FABRIC"].hide_render = which!="fabric"

def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser()
    p.add_argument("--deco",choices=("none","minimal","fabric","both"),default="both")
    opt=p.parse_args(argv)
    GEN.mkdir(parents=True,exist_ok=True)
    RENDERS.mkdir(parents=True,exist_ok=True)
    reset()
    make_backdrop()
    make_frame()
    make_mattress()
    make_minimal()
    make_fabric()
    cam=camera()
    visibility("minimal")
    bpy.ops.wm.save_as_mainfile(filepath=str(GEN/"kura_cottage.blend"))
    visibility("none")
    render(cam,"kura_structure_labeled.png")  # 图像名保持兼容；这是无屋顶裸框架，标签由页面提供
    if opt.deco in ("minimal","both"):
        visibility("minimal")
        render(cam,"kura_deco_minimal.png")
    if opt.deco in ("fabric","both"):
        visibility("fabric")
        render(cam,"kura_deco_fabric.png")
    meta={
        "model":"IKEA KURA 502.665.06; LOW configuration; NO roof",
        "reference_outer_mm":[2090,990,1160],
        "mattress_nominal_mm":[2000,900],
        "model_warning":"床架细部/床垫高度是概念参数，非结构施工图；没有三角屋顶、斜梁、床篷",
        "decorations":"外侧平面毛毡/纸样、床旁独立软质树；灯光仅后续阶段评估，当前无电器布线",
        "safety":"概念图不证明外侧上横梁装饰安全；固定、抗拉、通风、睡眠及逃生空间均待实物评估",
        "status":{"modeled":True,"rendered":True,"sliced":False,"printed":False,"installed":False},
        "outputs":["kura_cottage.blend","kura_structure_labeled.png","kura_deco_minimal.png","kura_deco_fabric.png"]
    }
    (GEN/"kura_scene_meta.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print("KURA LOW NO ROOF: generated 3 previews and editable .blend")

if __name__=="__main__":
    main()
