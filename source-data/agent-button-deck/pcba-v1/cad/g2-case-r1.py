# G2-0 第一版外壳参数化建模（FreeCAD Part API）
# 运行：freecadcmd g2-case-r1.py
# 产物：case-r1-body.step/.stl（奶油白主体）、case-r1-base.step/.stl（薰衣草紫底座）、
#       case-r1-cap-a..d.step/.stl（四色键帽，已放键位）、placeholders.json（占位尺寸清单）
# 纪律：凡 PLACE=True 的尺寸是视觉占位，待真实元件（样轴/DevKitC 实测/G4 板框）确定后更新，
#       不进入任何冻结口径（见 g2-case-cad-taskbook.md G2-0）。

import json
import math
import os

import FreeCAD as App
import Part

PLACE = {
    "body":  dict(W=88.0, D=78.0, H=26.0, R=10.0, wall=2.4, top=2.4),      # PLACE 外形占位
    "base":  dict(W=94.0, D=84.0, H=14.0, R=8.0, pocket=6.0, floor=2.4, skirt=6.0),  # PLACE
    "keys":  dict(pitch_x=33.0, pitch_y=33.0, hole=24.4, cap=24.0, cap_h=6.0, stub=4.0),  # PLACE 待样轴
    "usb":   dict(w=18.0, h=7.5, y=6.0),                                    # PLACE 待 DevKitC 实测
    "boss":  dict(d=6.0, h=7.0, inset=9.0, hole_d=2.6),                     # PLACE 待 G4 板框
    "relief":dict(helmet_r=13.0, visor_r=8.6, visor_off=(0.0, 1.5), torso_w=30.0,
                  torso_h=18.0, port_r=10.0, port_hole=7.6, star_r=1.6, h=0.8),
}

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders", "case-r1")
os.makedirs(OUT, exist_ok=True)
doc = App.newDocument("case_r1")


def rr(w, d, h, r, z=0.0, x=0.0, y=0.0):
    b = Part.makeBox(w, d, h, App.Vector(x - w / 2, y - d / 2, z))
    if r > 0:
        # 只倒竖直四棱——本 FreeCAD 版本对盒体全边 makeFillet 会产生退化几何
        vertical = [e for e in b.Edges
                    if abs(abs(e.tangentAt(e.FirstParameter).z) - 1) < 0.5]
        try:
            b = b.makeFillet(r, vertical)
        except Exception:
            pass
    return b


def cyl(r, h, x, y, z, dir_y=False):
    """圆柱；dir_y=True 时沿 +y 方向（用于正面浮雕，避免绕原点旋转）。"""
    v = App.Vector(0, 1, 0) if dir_y else App.Vector(0, 0, 1)
    return Part.makeCylinder(r, h, App.Vector(x, y, z), v)


def save(shape, name):
    step = os.path.join(OUT, name + ".step")
    stl = os.path.join(OUT, name + ".stl")
    shape.exportStep(step)
    import MeshPart
    m = doc.addObject("Mesh::Feature", name + "_mesh")
    m.Mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.3, AngularDeflection=0.6)
    m.Mesh.write(stl)
    bb = shape.BoundBox
    print("saved", name, os.path.getsize(stl),
          "bbox x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]" % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))


B, S = PLACE["body"], PLACE["relief"]
# ── 主体（奶油白）：壳体，顶部键帽孔 + 背部双 USB 开孔，正面浮雕 ──
# 装配：主体坐在底座地板上（z 抬升 base.floor），底座裙壁开口 = 主体外形 + 0.6 间隙
body_out = rr(B["W"], B["D"], B["H"], B["R"])
body_in = rr(B["W"] - 2 * B["wall"], B["D"] - 2 * B["wall"],
             B["H"] - B["top"], B["R"] - B["wall"], z=B["H"] - B["top"])
body = body_out.cut(body_in)
front = B["D"] / 2  # 正面 y+

# 正面浮雕（凸出 0.8mm，方向 +y 即向外）
dec = []
dec.append(cyl(S["helmet_r"], S["h"], 0, front - 0.01, B["H"] * 0.52, dir_y=True))
dec.append(cyl(S["visor_r"], S["h"] * 1.3, S["visor_off"][0], front - 0.01,
               B["H"] * 0.52 + S["visor_off"][1], dir_y=True))
dec.append(rr(S["torso_w"], S["h"], S["torso_h"], 4, z=B["H"] * 0.18, x=0, y=front - S["h"] / 2))
for dx in (-S["port_r"] * 2.6, S["port_r"] * 2.6):  # 左右舷窗（圆环=外柱减内柱，沿 +y）
    ring_o = cyl(S["port_r"], S["h"], dx, front - 0.01, B["H"] * 0.5, dir_y=True)
    ring_i = cyl(S["port_hole"], S["h"] * 2, dx, front - 0.02, B["H"] * 0.5, dir_y=True)
    dec.append(ring_o.cut(ring_i))
for i in range(6):  # 星星（小圆柱占位，v2 换五角星浮雕）
    ang = i * math.pi / 3
    dec.append(cyl(S["star_r"], S["h"], math.cos(ang) * (B["W"] / 2 - 8),
                   front - 0.01, B["H"] * (0.30 + 0.4 * (i % 2)), dir_y=True))
body = body.fuse(dec)

# 顶部 2×2 键帽孔（占位 24.4mm 方孔，待样轴定稿）
K = PLACE["keys"]
for ix in (-1, 1):
    for iy in (-1, 1):
        hole = rr(K["hole"], K["hole"], B["top"] * 2, 2.0,
                  z=B["H"] - B["top"] - 0.1, x=ix * K["pitch_x"] / 2, y=iy * K["pitch_y"] / 2)
        body = body.cut(hole)

# 背部双 USB 开孔（占位 18×7.5，待 DevKitC 实物测量定稿）
U = PLACE["usb"]
usb = rr(U["w"], B["wall"] * 2, U["h"], 1.2, z=U["y"], x=0, y=-B["D"] / 2 - B["wall"] / 2)
body = body.cut(usb)
body.translate(App.Vector(0, 0, PLACE["base"]["floor"]))
save(body, "case-r1-body")

# ── 底座（薰衣草紫）：四周裙壁包覆主体下缘 + 中央地板 + 4×M2.5 螺柱 + 2 脚垫槽 ──
BA = PLACE["base"]
base_out = rr(BA["W"], BA["D"], BA["H"], BA["R"])
pocket = rr(B["W"] + 0.6, B["D"] + 0.6,          # 开口 = 主体 + 0.6 间隙，裙壁自然成厚
            BA["H"] - BA["floor"], 3.0, z=BA["floor"] + 0.01)
base = base_out.cut(pocket)
BZ = PLACE["boss"]
for sx in (-1, 1):
    for sy in (-1, 1):
        bx, by = sx * (BA["W"] / 2 - BZ["inset"]), sy * (BA["D"] / 2 - BZ["inset"])
        base = base.fuse(cyl(BZ["d"] / 2, BZ["h"], bx, by, BA["floor"]))       # 螺柱自地板升起
        base = base.cut(cyl(BZ["hole_d"] / 2, BA["H"], bx, by, -0.01))         # M2.5 通孔
for fx in (-BA["W"] / 4, BA["W"] / 4):  # 防滑脚垫槽占位
    base = base.cut(cyl(5.0, 1.0, fx, 0, -0.01))
save(base, "case-r1-base")

# ── 四色键帽（放在键位上；十字 stub 占位伸入键帽孔）──
z_off = PLACE["base"]["floor"] + B["H"] - B["top"] + 0.4 + (1.2 + K["stub"])
for name, color, ix, iy in (("a", "coral-orange", -1, -1), ("b", "starry-blue", 1, -1),
                            ("c", "mint-green", -1, 1), ("d", "warm-yellow", 1, 1)):
    cap = rr(K["cap"], K["cap"], K["cap_h"], 3.0)
    skirt = rr(K["cap"] + 1.2, K["cap"] + 1.2, 1.2, 3.4, z=-1.2)
    stub = rr(11.0, 5.6, K["stub"], 1.0, z=-1.2 - K["stub"])  # MX 十字占位（非最终）
    part = cap.fuse([skirt, stub])
    part.translate(App.Vector(ix * K["pitch_x"] / 2, iy * K["pitch_y"] / 2, z_off))
    save(part, f"case-r1-cap-{name}")

with open(os.path.join(OUT, "placeholders.json"), "w") as f:
    json.dump({"generated_by": "g2-case-r1.py v1 (G2-0)",
               "rule": "PLACE 尺寸为视觉占位，不冻结；待样轴/DevKitC实测/G4板框更新",
               "params": PLACE}, f, ensure_ascii=False, indent=2)
print("placeholders.json written")
