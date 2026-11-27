# G2-1 外壳参数化建模 v2（FreeCAD Part API）
# 运行（勿用 freecadcmd——其对部分目录的脚本会静默不执行）：
#   PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
#     /Applications/FreeCAD.app/Contents/Resources/bin/python g2-case-r1.py
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
BASE = dict(W=94.0, D=84.0, H=9.5, R=8.0, floor=2.4)   # 托盘式：总高 9.5=floor2.4+裙壁7.1；裙壁顶 9.5 < USB 插拔包络下缘 9.77
KEYS = dict(pitch_x=33.0, pitch_y=33.0, hole=24.4, cap=24.0, cap_h=6.0, stub=4.0)
USB = dict(count=2, w=11.2, h=8.5, spacing=12.5, z=8.0,   # 开孔 11.2<中心距12.5（两孔间 1.3mm 壁），高度含 7.5 插头+公差；占位不冻结
           left="UART(J2,Micro-USB)", right="USB-OTG(J4,Micro-USB)")
PLUG_ENV = dict(w=10.6, h=8.0)   # 单插头通过包络（须窄且矮于开孔 11.2×8.5）——待插头实物测量校核
BOSS = dict(d=6.0, h=7.0, pos_x=30.0, pos_y=28.0, hole_d=2.6)  # 位置避让内腔 R7.6 圆角，待 G4 板框定稿
RELIEF = dict(helmet_r=13.0, visor_r=8.6, visor_off_y=1.5, torso_w=30.0, torso_h=18.0,
              panel_w=14.0, panel_h=6.0, port_r=10.0, port_hole=7.6, recess=0.6,
              star_out=2.6, star_in=1.1, h=0.8)

SOURCES = {
    "board_outline": {
        "value": "PCB 板框 25.40 × 62.74 mm（62.74 尺寸线两端=板框上/下边，含 USB 区段在内）",
        "source": "official-doc", "status": "confirmed-official",
        "doc": "Espressif PCB_ESP32-S3-DevKitC-1_V1.1_20220429.pdf 第 1 页（正面铜层图，SHA256 3f6716…）",
        "measure": "图纸标注值；矢量重建复核（标注线端点=板框边）", "freeze": "unfrozen（到货实测终判）"},
    "usb_zone_8mm": {
        "value": "8.00 mm = 板框内 USB 连接器区段（连接器区顶边→板框底边）——与 62.74 同在板框内，不可与 62.74 相加",
        "source": "official-doc", "status": "confirmed-official",
        "doc": "同上第 1 页（8.00 延伸线端点：连接器区顶边/板框底边）",
        "measure": "图纸标注值；延伸线端点矢量复核", "freeze": "unfrozen"},
    "connector_protrusion": {
        "value": "≈8 mm：Micro-USB 壳体与焊盘悬出板框底边之外（板外另绘有连接器外形线，几何读数 8.1mm）",
        "source": "official-drawing-read", "status": "awaiting-measure",
        "doc": "同上第 1 页（连接器外形线在板框外 ≈8mm；焊盘行跨板底边）",
        "measure": "图纸比例读数（该 PDF 渲染与标注存在约 4% 比例偏差，估读须实测）",
        "freeze": "unfrozen", "awaiting": "DevKitC 到货卡尺实测突出长度"},
    "board_envelope": {
        "value": "整板最大包络 ≈25.40 × ≈70.7 mm（板框 62.74 + 连接器板外突出 ≈8，综合估读）",
        "source": "official-drawing-read", "status": "awaiting-measure",
        "doc": "同上第 1 页几何重建综合", "measure": "图纸估读综合（非标注值）",
        "freeze": "unfrozen", "awaiting": "到货实测"},
    "usb_types": {
        "value": "J2 = USB-to-UART（Micro-USB，5 脚+屏蔽壳）；J4 = ESP32-S3 原生 USB/OTG（Micro-USB）",
        "source": "official-doc", "status": "confirmed-official",
        "doc": "Espressif SCH_ESP32-S3-DevKitC-1_V1.1_20220413.pdf（SHA256 5f25ae…）原理图：J2 挂 USB-to-UART 桥网络、J4 挂 ESP USB(GPIO19/20) 网络，两符号均标 MICRO USB",
        "measure": "原理图符号与网络提取（pdftotext）", "freeze": "unfrozen"},
    "usb_ports": {
        "value": "双口并排于板底短边，中心距 ≈12.5 mm（图纸丝印层估读 ±1mm）",
        "source": "official-drawing-read", "status": "awaiting-measure",
        "doc": "同上 PCB 图第 3 页丝印层（J2 左 / J4 右）",
        "measure": "图纸比例读数", "freeze": "unfrozen",
        "awaiting": "DevKitC 到货实测：中心距/高度/左右序校核"},
    "usb_opening": {
        "value": "每口 11.2 × 8.5 mm——开孔宽必须 < 中心距 12.5（两孔间留 1.3 mm 壁）；初版 13.5 宽使两孔重叠合并为单一开口，几何检查器检出后修正",
        "source": "standard-plus-tolerance", "status": "awaiting-measure",
        "doc": "USB Micro-B 插头外廓推算 + FDM/SLA 公差；与 usb_ports 中心距 12.5（图纸估读）联动约束",
        "measure": "标准外廓推算 + 经验公差 + 几何检查器验证两孔分离", "freeze": "unfrozen——占位开孔，不冻结不下单",
        "awaiting": "DevKitC 实物插拔验证后定稿；若插头宽 >11.2 需改为单 elongated 开口并重新评审"},
    "usb_plug_envelope": {
        "value": "单插头通过包络 10.6 × 8.0 mm（Micro-B 插头外廓 ≈10.2 宽 × 7.5 高 + 公差；须窄/矮于开孔 11.2×8.5）",
        "source": "standard-plus-tolerance", "status": "awaiting-measure",
        "doc": "USB Micro-B 标准插头公称外廓", "measure": "标准外廓推算（非实测）",
        "freeze": "unfrozen", "awaiting": "插头实物卡尺测量校核"},
    "skirt_usb_clearance": {
        "value": "底座改托盘式总高 9.5（floor 2.4 + 裙壁 7.1）：裙壁顶 9.5 < USB 插拔包络下缘 9.77——检查器检出裙壁后角挡插头后修正（初版总高 14）",
        "source": "placeholder", "status": "awaiting-measure",
        "doc": "包络下缘 = 开孔 z 10.52 − 0.75 插拔角余量；裙壁高度按此避让",
        "measure": "几何检查验证零干涉；高度选择无实物依据", "freeze": "unfrozen",
        "awaiting": "DevKitC 实测插座高度与插头外形后复核裙壁高度与外观比例"},
    "body": {
        "value": "外形 88×78×26 R10，壁厚 2.4，顶厚 2.4",
        "source": "placeholder", "status": "placeholder",
        "doc": "G0 视觉基准比例", "measure": "参数设定（无实物依据）", "freeze": "unfrozen",
        "awaiting": "G4 板框 + DevKitC 载板高度定外形"},
    "keys": {
        "value": "键距 33×33；键帽孔 24.4 方孔；键帽 24×24；stub 为矩形占位（非 MX 十字）",
        "source": "placeholder", "status": "awaiting-measure",
        "doc": "视觉占位", "measure": "参数设定", "freeze": "unfrozen",
        "awaiting": "样轴实测（Boba U4/国产静音段落）：十字孔、裙边、按压行程"},
    "boss": {
        "value": "4×M2.5 螺柱（d6 孔 2.6），现位 ±30/±28（避让内腔 R7.6 圆角）",
        "source": "placeholder", "status": "placeholder",
        "doc": "热熔铜螺母 M2.5×4×3.5 级（HachimoDock 参考用料）",
        "measure": "参数设定", "freeze": "unfrozen",
        "awaiting": "G4 真实板框与安装孔位后冻结——当前坐标不得用于 PCB 布局"},
}

def dims_json():
    return {"generated_by": "g2-case-r1.py v3 (G2-1)",
            "rule": "尺寸三态来源（confirmed-official / awaiting-measure / placeholder），逐项登记文档页码、测量方式与冻结状态；"
                    "占位/待实测模型不得标 Manufacturable，不得下单打印（发起人 2026-11-28）",
            "params": {"body": BODY, "base": BASE, "keys": KEYS, "usb": USB, "usb_plug_env": PLUG_ENV, "boss": BOSS, "relief": RELIEF},
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
    hole = rr(U["w"], B["wall"] * 2 + 2.4, U["h"], 1.2, z=FLOOR + U["z"],
              x=side * U["spacing"] / 2, y=-B["D"] / 2)   # 深度越过内侧面 1.2mm，确保贯穿
    body = body.cut(hole)
body.translate(App.Vector(0, 0, 0.12))  # 与底座地板留 0.12 装配间隙（避免贴合面幻影公共体）
save(body, "case-r1-body")

# ── 底座（薰衣草紫）：裙壁开口按主体实际 bbox（含浮雕）+1.4 间隙，浮雕不被裙壁遮挡 ──
bb_body = body.BoundBox
base_out = rr(BASE["W"], BASE["D"], BASE["H"], BASE["R"])
pocket = rr(bb_body.XLength + 1.4, bb_body.YLength + 1.4,
            BASE["H"] - FLOOR, 3.0, z=FLOOR + 0.01)   # 开放托盘：裙壁 7.1，避让 USB 插头包络（待实物校核）
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

# 基础有效性（深度几何/干涉/装配检查由 check_case.py 从 STEP 重算）
for nm, sh in (("body", body), ("base", base), ("cap-a", caps["a"]), ("cap-b", caps["b"]),
               ("cap-c", caps["c"]), ("cap-d", caps["d"])):
    if not sh.isValid():
        print("INVALID SHAPE:", nm)
        sys.exit(2)
print("basic validity OK")

with open(os.path.join(OUT, "dims.json"), "w") as f:
    json.dump(dims_json(), f, ensure_ascii=False, indent=2)
print("dims.json written")

