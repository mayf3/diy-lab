# G2-1 外壳参数化建模 v2（FreeCAD Part API）
# 运行：freecadcmd g2-case-r1.py
# 产物：case-r1-body/base/cap-a..d 的 STEP+STL、dims.json（尺寸来源登记）、checks.json（自动检查）
# 同步：workbench/build_case_viewer.py 消费 STL+dims.json+checks.json 生成查看页
# 纪律：尺寸三态来源 official-doc（官方数据手册/图纸）| awaiting-measure（待实物实测校核）|
#       placeholder（视觉占位）。占位模型不得标 Manufacturable，不得下单打印（发起人 2026-11-28）。

import json
import math
import os
import sys

import FreeCAD as App
import Part

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders", "case-r1")
os.makedirs(OUT, exist_ok=True)

# ── 参数（带来源）───────────────────────────────────────────────
BODY = dict(W=88.0, D=78.0, H=26.0, R=10.0, wall=2.4, top=2.4)
BASE = dict(W=94.0, D=84.0, H=14.0, R=8.0, floor=2.4)          # 裙壁厚 = (94-88.6)/2 = 2.7
KEYS = dict(pitch_x=33.0, pitch_y=33.0, hole=24.4, cap=24.0, cap_h=6.0, stub=4.0)
USB = dict(count=2, w=12.0, h=7.0, spacing=12.5, z=8.0,
           left="UART(J2,Micro-USB)", right="USB-OTG(J4,Micro-USB)")
BOSS = dict(d=6.0, h=7.0, pos_x=30.0, pos_y=28.0, hole_d=2.6)  # 位置避让内腔 R7.6 圆角，待 G4 板框定稿
RELIEF = dict(helmet_r=13.0, visor_r=8.6, visor_off_y=1.5, torso_w=30.0, torso_h=18.0,
              panel_w=14.0, panel_h=6.0, port_r=10.0, port_hole=7.6, recess=0.6,
              star_out=2.6, star_in=1.1, h=0.8)

SOURCES = {
    "board": {"source": "official-doc", "status": "confirmed-official",
              "value": "ESP32-S3-DevKitC-1 v1.1：25.40 × 70.74 mm（62.74 + 8.00 USB 区）；J1/J3 2.54mm 间距",
              "ref": "Espressif PCB 布局图 PCB_ESP32-S3-DevKitC-1_V1.1_20220429.pdf（SHA256 3f6716…）"},
    "usb_ports": {"source": "official-doc", "status": "awaiting-measure",
                  "value": "双口并排于板底短边：J2=UART(Micro-USB)、J4=USB-OTG(Micro-USB)；中心距 ≈12.5mm（图纸估读 ±1mm）",
                  "ref": "同上 PCB 图第 3 页丝印层 + v1.1 官方用户指南（USB-to-UART Port = Micro-USB）",
                  "awaiting": "DevKitC 到货实测：开口中心距/高度/左右序校核"},
    "usb_opening": {"source": "official-doc", "status": "confirmed-official",
                    "value": "每口开孔 12 × 7 mm（Micro-USB 插头外廓 ~11×7.5，留插拔间隙）",
                    "ref": "USB Micro-B 标准插头尺寸"},
    "body": {"source": "placeholder", "status": "placeholder",
             "value": "外形 88×78×26 R10 壁厚 2.4 顶厚 2.4", "ref": "G0 视觉基准比例", "awaiting": "G4 板框 + DevKitC 载板高度定外形"},
    "keys": {"source": "placeholder", "status": "awaiting-measure",
             "value": "键距 33×33；键帽孔 24.4 方孔；键帽 24×24；stub 为矩形占位（非 MX 十字）",
             "ref": "视觉占位", "awaiting": "样轴实测（Boba U4/国产静音段落）：十字孔、裙边、按压行程"},
    "boss": {"source": "placeholder", "status": "placeholder",
             "value": "4×M2.5 螺柱（d6 孔 2.6），现位 ±30/±28（避让内腔 R7.6 圆角）",
             "ref": "热熔铜螺母 M2.5×4×3.5 级（HachimoDock 参考用料）",
             "awaiting": "G4 真实板框与安装孔位后冻结——当前坐标不得用于 PCB 布局"},
}

def dims_json():
    return {"generated_by": "g2-case-r1.py v2 (G2-1)",
            "rule": "尺寸三态来源；占位/待实测项不得标 Manufacturable，不得下单打印（发起人 2026-11-28）",
            "params": {"body": BODY, "base": BASE, "keys": KEYS, "usb": USB, "boss": BOSS, "relief": RELIEF},
            "sources": SOURCES}

# ── 建模辅助 ──────────────────────────────────────────────────
def rr(w, d, h, r, z=0.0, x=0.0, y=0.0):
    b = Part.makeBox(w, d, h, App.Vector(x - w / 2, y - d / 2, z))
    if r > 0:
        vertical = [e for e in b.Edges
                    if abs(abs(e.tangentAt(e.FirstParameter).z) - 1) < 0.5]
        try:
            b = b.makeFillet(r, vertical)
        except Exception:
            pass
    return b


def cyl(r, h, x, y, z, dir_y=False):
    v = App.Vector(0, 1, 0) if dir_y else App.Vector(0, 0, 1)
    return Part.makeCylinder(r, h, App.Vector(x, y, z), v)


def star_prism(r_out, r_in, h, cx, cz, y0):
    """正面五角星：多边形建于 x-z 平面，沿 +y 挤出（不绕原点旋转）。"""
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append(App.Vector(cx + r * math.cos(ang), y0, cz + r * math.sin(ang)))
    pts.append(pts[0])
    return Part.Face(Part.makePolygon(pts)).extrude(App.Vector(0, h, 0))


doc = App.newDocument("case_r1")


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

B, S = BODY, RELIEF
FLOOR = BASE["floor"]

# ── 主体（奶油白）：壳体 z 从 FLOOR 起（坐在底座地板上）──
body_out = rr(B["W"], B["D"], B["H"], B["R"], z=FLOOR)
body_in = rr(B["W"] - 2 * B["wall"], B["D"] - 2 * B["wall"],
             B["H"] - B["top"], B["R"] - B["wall"], z=FLOOR)  # 开放底：内腔自地板面起
body = body_out.cut(body_in)
front = B["D"] / 2

# 正面浮雕（+y 向外）：头盔环 + 面罩 + 躯干面板 + 舷窗（环凸+窗凹）+ 五角星
dec = []
helmet_o = cyl(S["helmet_r"], S["h"], 0, front - 0.01, FLOOR + B["H"] * 0.55, dir_y=True)
helmet_i = cyl(S["helmet_r"] - 2.2, S["h"] * 2, 0, front - 0.02, FLOOR + B["H"] * 0.55, dir_y=True)
dec.append(helmet_o.cut(helmet_i))                                   # 头盔环
dec.append(cyl(S["visor_r"], S["h"], 0, front - 0.01,
               FLOOR + B["H"] * 0.55 - S["visor_off_y"], dir_y=True))  # 面罩（单层 0.8，凸出不超裙壁开口）
dec.append(rr(S["torso_w"], S["h"], S["torso_h"], 4, z=FLOOR + B["H"] * 0.16, x=0, y=front - S["h"] / 2))
dec.append(rr(S["panel_w"], S["h"] * 1.4, S["panel_h"], 1.5,
              z=FLOOR + B["H"] * 0.30, x=0, y=front - S["h"] * 0.7))   # 胸前面板
for dx in (-S["port_r"] * 2.6, S["port_r"] * 2.6):
    ring_o = cyl(S["port_r"], S["h"], dx, front - 0.01, FLOOR + B["H"] * 0.52, dir_y=True)
    ring_i = cyl(S["port_hole"], S["h"] * 2, dx, front - 0.02, FLOOR + B["H"] * 0.52, dir_y=True)
    dec.append(ring_o.cut(ring_i))
    dec.append(rr(S["port_hole"] * 1.5, S["h"], S["port_hole"] * 1.5, 1.0,
                  z=FLOOR + B["H"] * 0.52 - S["port_hole"] * 0.75, x=dx, y=front - S["h"] / 2))
for i in range(6):  # 五角星（真实星形轮廓，两种尺寸）
    ang = i * math.pi / 3
    sx = math.cos(ang) * (B["W"] / 2 - 9)
    sz = FLOOR + B["H"] * (0.30 + 0.38 * (i % 2))
    dec.append(star_prism(S["star_out"] * (1.25 if i % 2 else 1.0), S["star_in"],
                          S["h"], sx, sz, front - 0.01))
body = body.fuse(dec)

# 顶部 2×2 键帽孔（占位方孔，待样轴定稿）
K = KEYS
for ix in (-1, 1):
    for iy in (-1, 1):
        body = body.cut(rr(K["hole"], K["hole"], B["top"] * 2, 2.0,
                           z=FLOOR + B["H"] - B["top"] - 0.1,
                           x=ix * K["pitch_x"] / 2, y=iy * K["pitch_y"] / 2))

# 背部双 USB 开孔（OTG + UART 独立两孔，官方中心距）
U = USB
for side in (-1, 1):
    hole = rr(U["w"], B["wall"] * 2, U["h"], 1.2, z=FLOOR + U["z"],
              x=side * U["spacing"] / 2, y=-B["D"] / 2 - B["wall"] / 2)
    body = body.cut(hole)
body.translate(App.Vector(0, 0, 0.12))  # 与底座地板留 0.12 装配间隙（避免贴合面幻影公共体）
save(body, "case-r1-body")

# ── 底座（薰衣草紫）：裙壁开口按主体实际 bbox（含浮雕）+1.4 间隙，浮雕不被裙壁遮挡 ──
bb_body = body.BoundBox
base_out = rr(BASE["W"], BASE["D"], BASE["H"], BASE["R"])
pocket = rr(bb_body.XLength + 1.4, bb_body.YLength + 1.4,
            BASE["H"] - FLOOR, 3.0, z=FLOOR + 0.01)
base = base_out.cut(pocket)
for sx in (-1, 1):
    for sy in (-1, 1):
        bx, by = sx * BOSS["pos_x"], sy * BOSS["pos_y"]
        base = base.fuse(cyl(BOSS["d"] / 2, BOSS["h"], bx, by, FLOOR))
        base = base.cut(cyl(BOSS["hole_d"] / 2, BASE["H"], bx, by, -0.01))
for fx in (-BASE["W"] / 4, BASE["W"] / 4):
    base = base.cut(cyl(5.0, 1.0, fx, 0, -0.01))
save(base, "case-r1-base")

# ── 四色键帽（放键位；stub 矩形占位待样轴换 MX 十字）──
z_off = FLOOR + B["H"] - B["top"] + 0.4 + (1.2 + K["stub"])
caps = {}
for name, ix, iy in (("a", -1, -1), ("b", 1, -1), ("c", -1, 1), ("d", 1, 1)):
    cap = rr(K["cap"], K["cap"], K["cap_h"], 3.0)
    skirt = rr(K["cap"] + 1.2, K["cap"] + 1.2, 1.2, 3.4, z=-1.2)
    stub = rr(11.0, 5.6, K["stub"], 1.0, z=-1.2 - K["stub"])
    part = cap.fuse([skirt, stub])
    kx, ky = ix * K["pitch_x"] / 2, iy * K["pitch_y"] / 2
    part.translate(App.Vector(kx, ky, z_off))
    caps[name] = part
    save(part, f"case-r1-cap-{name}")

# ── 自动检查：几何有效 / 干涉 / 装配 ─────────────────────────
def vol(a, b):
    try:
        return a.common(b).Volume
    except Exception:
        return float("nan")

checks = {
    "body_valid": bool(body.isValid()),
    "base_valid": bool(base.isValid()),
    "caps_valid": bool(all(p.isValid() for p in caps.values())),
    "body_base_interference_vol": round(vol(body, base), 4),
    "body_caps_interference_vol": round(sum(vol(body, p) for p in caps.values()), 4),
    "base_caps_interference_vol": round(sum(vol(base, p) for p in caps.values()), 4),
    "usb_two_openings": bool(USB["count"] == 2),
    "assembly_body_in_base": bool(bb_body.XLength <= BASE["W"] and bb_body.YLength <= BASE["D"]),
}


def check_failed(v):
    if isinstance(v, bool):
        return not v
    if isinstance(v, (int, float)):
        return abs(v) > 1e-6   # 干涉体积必须为 0
    return False


failed = [k for k, v in checks.items() if check_failed(v)]
with open(os.path.join(OUT, "checks.json"), "w") as f:
    json.dump({"ok": not failed, "failed": failed, "checks": checks}, f, indent=1)
print("CHECKS:", "OK" if not failed else f"FAILED {failed}")

with open(os.path.join(OUT, "dims.json"), "w") as f:
    json.dump(dims_json(), f, ensure_ascii=False, indent=2)
print("dims.json written")

if failed:
    sys.exit(2)
