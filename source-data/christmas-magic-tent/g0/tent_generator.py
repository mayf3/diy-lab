# -*- coding: utf-8 -*-
"""
Project Christmas Magic Tent — G0 parametric geometry generator (Blender, headless).

阶段 G0：零采购数字模拟。只做可参数化的几何模型与几何检查，
不做结构力学验证、不做布料物理仿真、不生成采购单。

数据状态分类（贯穿注释/CSV/JSON）:
  [INPUT]        用户提供，可能还会改（如房间 10m x 10m 待复核）
  [ASSUMPTION]   暂定占位值，需真实商品/房间数据确认
  [DERIVED]      由本脚本从输入纯几何推导
  [LIMIT]        模型主动发现的几何限制

用法:
  blender --background --python tent_generator.py -- \
      --variant A|B [--out DIR] [--blend-name FILE] [--room-w M] [--room-d M] \
      [--tag PREFIX] [--only view1,view2] [--no-save] [--no-data] [--skip-render]

单位约定：内部一律使用米(m)，Blender 界面显示设为厘米(cm)。
所有 3D 文字标注使用 ASCII（Blender 内置字体不含 CJK）。
"""

import bpy
import sys
import os
import csv
import json
import math
import argparse
from mathutils import Vector, Matrix

# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["A", "B"], default="A")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--blend-name", default=None)
    ap.add_argument("--room-w", type=float, default=None, help="房间宽(米)，覆盖默认 10m")
    ap.add_argument("--room-d", type=float, default=None, help="房间进深(米)，覆盖默认 10m")
    ap.add_argument("--tag", default=None, help="渲染文件名前缀，默认取 variant")
    ap.add_argument("--only", default=None, help="只渲染指定视图，逗号分隔")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--no-data", action="store_true", help="不写 CSV/JSON（辅助运行用）")
    ap.add_argument("--skip-render", action="store_true")
    return ap.parse_args(argv)

ARGS = parse_args()

# ----------------------------------------------------------------------------
# CONFIG —— 单一参数区（改这里即可重建整个模型）
# ----------------------------------------------------------------------------

CFG = {
    # --- 房间 [INPUT: 1000x1000cm 待复核] ---
    "room_w": ARGS.room_w if ARGS.room_w else 10.0,
    "room_d": ARGS.room_d if ARGS.room_d else 10.0,
    "room_wall_h": 2.5,
    "room_wall_t": 0.10,
    "room_door_w": 0.90,       # [ASSUMPTION] 房间门假定在南墙
    "room_door_h": 2.10,
    "room_door_swing": 0.90,   # [ASSUMPTION] 门扇旋转半径

    # --- 帐篷主体 ---
    "E": 0.80,                 # 檐高 m [INPUT 可调]
    "H": 1.35,                 # 屋脊高 m [INPUT 可调]
    "door_w": 0.70,            # 门宽 [ASSUMPTION 暂定]
    "door_h": 0.90,            # 门高 [ASSUMPTION 暂定]
    "win_w": 0.30,             # 侧通风窗宽 [ASSUMPTION 暂定]
    "win_h": 0.40,             # 侧通风窗高 [ASSUMPTION 暂定]
    "win_z0": 0.30,            # 窗台高（窗体 0.30~0.70m）
    "magic_win_r": 0.10,       # 魔法窗(后山墙圆窗)半径 [ASSUMPTION]
    "magic_win_z": 1.10,       # 魔法窗中心高 [ASSUMPTION]

    # --- 骨架/面料占位 [ASSUMPTION: 无实物资料] ---
    "post_r": 0.02,            # 杆件截面半径占位 4cm 直径
    "panel_t": 0.01,           # 布面板厚占位
    "over": 0.05,              # 屋檐出檐 m
    "ridge_cap": 0.03,         # 屋脊包裹量 m

    # --- 儿童/动线 ---
    "path_len": 0.80,          # 门口进出通道深 [ASSUMPTION]
    "child_h_min": 1.00,       # 测试范围，非实测
    "child_h_max": 1.15,
    "child_body_r": 0.16,

    # --- 电子占位 [ASSUMPTION] ---
    "elec_box": (0.15, 0.10, 0.06),
    "elec_psu": (0.20, 0.08, 0.05),
    "elec_speaker": (0.12, 0.10, 0.08),
    "elec_pir": (0.05, 0.03, 0.03),
    "button_r": 0.035,
    "button_h": 0.80,          # 按钮操作高度

    # --- 判定阈值（设计目标，非安全认证）---
    "req_door_clear": 0.05,    # 门洞顶与屋面最小净空
    "headroom": 0.10,          # 站立头顶最小净空

    # --- 候选 A/B（占地相同，朝向不同）---
    "variants": {
        "A": {"F": 1.10, "D": 1.60},   # 窄门面、深小屋
        "B": {"F": 1.60, "D": 1.10},   # 宽门面、浅小屋
    },
}

ENGINE = ["WORKBENCH"]  # 渲染失败时自动降级为 CYCLES

# ----------------------------------------------------------------------------
# 纯几何推导（不依赖 bpy；A/B 都算，供 CSV/JSON/标注使用）
# ----------------------------------------------------------------------------

def rect_dist(ax0, ax1, ay0, ay1, bx0, bx1, by0, by1):
    """两个轴对齐矩形表面间的最小距离（重叠时为 0）。"""
    dx = max(ax0 - bx1, bx0 - ax1, 0.0)
    dy = max(ay0 - by1, by0 - ay1, 0.0)
    return math.hypot(dx, dy)


def derive(v):
    F = CFG["variants"][v]["F"]
    D = CFG["variants"][v]["D"]
    E, H = CFG["E"], CFG["H"]
    dw, dh = CFG["door_w"], CFG["door_h"]
    half = F / 2.0
    rise = H - E
    S = math.hypot(half, rise)
    ang = math.degrees(math.atan2(rise, half))

    # 门洞两侧屋面高度（门高 0.90 > 檐高 0.80，门顶进入山墙区域，必须真查）
    rl_door = E + rise * (1.0 - (dw / 2.0) / half)   # 门洞边 x=±dw/2 处屋面高度
    door_clear = rl_door - dh
    door_margin = half - dw / 2.0

    def strip(h):
        """中央站立带总宽：屋面高度 >= h + headroom 的 |x| 范围。"""
        need = h + CFG["headroom"]
        if need <= E:
            return F
        if need >= H:
            return 0.0
        return F * (1.0 - (need - E) / rise)

    strip110 = strip(1.10)
    strip115 = strip(CFG["child_h_max"])

    # 面料面积（估算，供裁剪对比）
    gable_a = F * rise / 2.0
    front_rect = F * E
    door_a = dw * dh
    win_a = CFG["win_w"] * CFG["win_h"]
    front_a = front_rect + gable_a - door_a
    back_a = front_rect + gable_a
    side_each = D * E - win_a
    panel_slope = S + CFG["over"] + CFG["ridge_cap"]   # 单块屋面料斜向裁剪长(估)
    panel_width = D + 2 * CFG["over"]                  # 单块屋面料宽度(估)
    roof_a = 2 * panel_slope * panel_width
    fabric_total = front_a + back_a + 2 * side_each + roof_a

    win_top = CFG["win_z0"] + CFG["win_h"]
    win_margin_top = E - win_top
    win_post_clr = (D - CFG["win_w"]) / 2.0

    floor_in_w = F - 2 * CFG["post_r"]
    floor_in_d = D - 2 * CFG["post_r"]

    # --- 房间布置 ---
    rw, rd = CFG["room_w"], CFG["room_d"]
    x_ext = half + 0.50           # 左右装饰区外缘（树/礼物/按钮）
    y_ext = D / 2.0 + CFG["path_len"]
    clr_x = rw / 2.0 - x_ext
    clr_y = rd / 2.0 - y_ext

    door_cx = -rw / 2.0 + 0.90    # 房间门中心 [ASSUMPTION]
    swing_rect = (door_cx - CFG["room_door_w"] / 2, door_cx + CFG["room_door_w"] / 2,
                  -rd / 2, -rd / 2 + CFG["room_door_swing"])
    tent_rect = (-half, half, -D / 2, D / 2)
    path_rect = (-dw / 2, dw / 2, -D / 2 - CFG["path_len"], -D / 2)
    d_swing_tent = rect_dist(swing_rect[0], swing_rect[1], swing_rect[2], swing_rect[3],
                             tent_rect[0], tent_rect[1], tent_rect[2], tent_rect[3])
    d_swing_path = rect_dist(swing_rect[0], swing_rect[1], swing_rect[2], swing_rect[3],
                             path_rect[0], path_rect[1], path_rect[2], path_rect[3])

    big_room = rw >= 4.0 and rd >= 4.0
    if big_room:
        furn = [  # (x0,x1,y0,y1) 与 build_room() 保持一致
            (rw / 2 - 1.00, rw / 2 - 0.05, -0.975, 0.975),          # 沙发
            (-rw / 2 + 0.05, -rw / 2 + 0.40, 0.60, 1.80),           # 书架
            (1.80, 2.80, rd / 2 - 0.60, rd / 2 - 0.10),             # 玩具箱
            (-2.20, -1.00, -rd / 2 + 0.10, -rd / 2 + 0.70),         # 小桌
        ]
        d_furn = min(rect_dist(f[0], f[1], f[2], f[3],
                               tent_rect[0], tent_rect[1], tent_rect[2], tent_rect[3])
                     for f in furn)
    else:
        d_furn = None

    elec_gap = 0.03   # 电子盒外侧离侧墙距离（与 build_electronics 一致）

    return {
        "variant": v, "F": F, "D": D, "E": E, "H": H,
        "rise": rise, "half": half,
        "slope_angle_deg": round(ang, 1), "roof_slope_len": round(S, 4),
        "roofline_at_door_edge": round(rl_door, 4),
        "door_clear": round(door_clear, 4), "door_margin": round(door_margin, 4),
        "standing_strip_110": round(strip110, 3),
        "standing_strip_115": round(strip115, 3),
        "ridge_headroom_115": round(H - CFG["child_h_max"], 3),
        "ridge_headroom_110": round(H - 1.10, 3),
        "fabric": {
            "front_gable_with_door": round(front_a, 3),
            "back_gable": round(back_a, 3),
            "side_walls_total": round(2 * side_each, 3),
            "roof_panels_total": round(roof_a, 3),
            "total_estimate": round(fabric_total, 3),
            "curtain": round(door_a, 3),
            "panel_slope_cut": round(panel_slope, 3),
            "panel_width_cut": round(panel_width, 3),
        },
        "floor_inner": [round(floor_in_w, 3), round(floor_in_d, 3)],
        "floor_inner_area": round(floor_in_w * floor_in_d, 3),
        "footprint_area": round(F * D, 3),
        "window": {"w": CFG["win_w"], "h": CFG["win_h"], "z0": CFG["win_z0"],
                   "top_margin": round(win_margin_top, 3),
                   "clr_to_post": round(win_post_clr, 3)},
        "room": {
            "w": rw, "d": rd, "big_room": big_room,
            "clr_x": round(clr_x, 3), "clr_y": round(clr_y, 3),
            "door_swing_to_tent": round(d_swing_tent, 3),
            "door_swing_to_path": round(d_swing_path, 3),
            "furniture_min_dist": None if d_furn is None else round(d_furn, 3),
            "elec_gap": elec_gap,
        },
    }


def build_checks(d):
    """输出结构化几何检查结果（cm 为单位便于阅读）。"""
    c = []

    def add(cid, desc, value, threshold, status, cls, note=""):
        c.append({"id": cid, "desc": desc, "value_cm": value,
                  "threshold_cm": threshold, "status": status,
                  "class": cls, "note": note})

    add("door_top_vs_roof",
        "门洞顶角处屋面高度 - 门高（门顶已进入山墙区域，按实际屋面线检查）",
        d["door_clear"] * 100, CFG["req_door_clear"] * 100,
        "PASS" if d["door_clear"] >= CFG["req_door_clear"] else "FAIL",
        "GEOMETRY_VERIFIED",
        "净空最小点位于门洞两个上角 x=±35cm 处")

    add("door_side_margin", "门洞边到帐篷正面外缘净宽",
        d["door_margin"] * 100, 10.0,
        "PASS" if d["door_margin"] >= 0.10 else "WARN",
        "GEOMETRY_VERIFIED",
        "A 方案每侧约 20cm，需确认真实商品门框/立柱不吃掉门口宽度")

    add("window_top_margin", "通风窗顶到檐口净空",
        d["window"]["top_margin"] * 100, 5.0,
        "PASS" if d["window"]["top_margin"] >= 0.05 else "WARN",
        "GEOMETRY_VERIFIED", "避免与檐口横杆重叠")

    add("window_to_post", "通风窗边到前后立柱净宽",
        d["window"]["clr_to_post"] * 100, 10.0,
        "PASS" if d["window"]["clr_to_post"] >= 0.10 else "WARN",
        "GEOMETRY_VERIFIED", "B 方案侧墙较短，富余较小但仍通过")

    add("ridge_vs_child115", "屋脊净高 - 儿童占位上限(115cm)",
        d["ridge_headroom_115"] * 100, 10.0,
        "PASS" if d["ridge_headroom_115"] >= 0.10 else "WARN",
        "GEOMETRY_VERIFIED", "儿童占位高度为测试范围，非实测")

    add("standing_strip_110", "110cm 儿童可站立头顶净空的中央条带总宽",
        d["standing_strip_110"] * 100, None, "LIMIT", "GEOMETRY_VERIFIED",
        "仅在屋脊下方中央条带可直立，靠两侧需跪/坐——儿童帐篷常态")

    add("standing_strip_115", "115cm 儿童对应中央条带总宽",
        d["standing_strip_115"] * 100, None, "LIMIT", "GEOMETRY_VERIFIED", "")

    add("door_height_vs_child", "门高 90cm vs 儿童站立高度 100~115cm",
        CFG["door_h"] * 100, CFG["child_h_min"] * 100, "NOTE", "GEOMETRY_VERIFIED",
        "进入必须弯腰/爬行，属产品类型常态；如需成人直立进入须提高门高")

    add("adult_entry", "成人维护进入（门高 90cm、屋脊 135cm）",
        CFG["H"] * 100, 170.0, "NOTE", "GEOMETRY_VERIFIED",
        "成人无法直立进入，收拾/维护需从门口伸手或蹲入")

    add("room_wall_clear_x", "帐篷+装饰区外缘 到 左右墙净距（房间尺寸[INPUT]待复核）",
        d["room"]["clr_x"] * 100, 30.0,
        "PASS" if d["room"]["clr_x"] >= 0.30 else "WARN",
        "ASSUMPTION_DEPENDENT", "房间 10m x 10m 为待复核输入")

    add("room_wall_clear_y", "帐篷+门前通道 到 前后墙净距",
        d["room"]["clr_y"] * 100, 30.0,
        "PASS" if d["room"]["clr_y"] >= 0.30 else "WARN",
        "ASSUMPTION_DEPENDENT", "")

    st = d["room"]["door_swing_to_tent"]
    add("room_door_swing_vs_tent", "房间门开启扇 旋转范围 与 帐篷本体最小距离",
        st * 100, 30.0,
        "PASS" if st >= 0.30 else "WARN",
        "ASSUMPTION_DEPENDENT",
        "房间门位置为假设；小房间压力测试中该值仅 5cm，触发 WARN")

    sp = d["room"]["door_swing_to_path"]
    add("room_door_swing_vs_path", "门扇旋转范围 与 门前通道重叠距离",
        sp * 100, 15.0,
        "PASS" if sp >= 0.15 else "WARN",
        "ASSUMPTION_DEPENDENT",
        "小房间(3.0x3.5m)压力测试中通道与门扇范围重叠，进出会互相干扰")

    if d["room"]["furniture_min_dist"] is not None:
        add("furniture_min_dist", "帐篷本体到（假设的）最近家具占位距离",
            d["room"]["furniture_min_dist"] * 100, 30.0,
            "PASS" if d["room"]["furniture_min_dist"] >= 0.30 else "WARN",
            "ASSUMPTION_DEPENDENT", "家具位置纯假设，待真实房间照片校核")

    add("elec_box_gap", "电子盒(帐外)离侧墙间隙",
        d["room"]["elec_gap"] * 100, 3.0, "PASS", "DESIGN_ASSUMPTION",
        "控制盒/电源默认放帐外，帐内只留低压发光件（设计决策）")

    add("button_height", "按钮操作高度 80cm（儿童可达性）",
        CFG["button_h"] * 100, None, "INFO", "DESIGN_ASSUMPTION",
        "80cm 在常见 3~6 岁儿童可及范围内，属设计假设")

    add("interior_floor", "帐内可用地面（近似，扣除角柱占位）",
        d["floor_inner_area"] * 10000, None, "INFO", "DERIVED", "单位 cm^2")

    add("roof_slope_len", "屋面斜长 S=sqrt((F/2)^2+(H-E)^2)",
        d["roof_slope_len"] * 100, None, "INFO", "DERIVED", "屋顶面料斜向裁剪参考")

    return c


def build_data():
    data = {}
    for v in ("A", "B"):
        dv = derive(v)
        data[v] = {"config": {k: CFG[k] for k in
                              ("room_w", "room_d", "E", "H", "door_w", "door_h",
                               "win_w", "win_h", "win_z0", "post_r", "panel_t",
                               "over", "path_len", "child_h_min", "child_h_max",
                               "button_h", "req_door_clear", "headroom")},
                   "variant_dims": CFG["variants"][v],
                   "derived": dv,
                   "checks": build_checks(dv)}
    meta = {"generated_by": "tent_generator.py (G0)",
            "blender": bpy.app.version_string,
            "note": "几何检查仅验证模型内几何关系，不是儿童产品安全认证。"}
    return {"meta": meta, "variants": data}


def cm(v, nd=1):
    return f"{v * 100:.{nd}f}"


def write_csv(out, data):
    path = os.path.join(out, "dimension_comparison.csv")
    rows = [("section", "item", "unit", "A", "B", "source")]
    A = data["variants"]["A"]["derived"]
    B = data["variants"]["B"]["derived"]

    rows += [
        ("tent", "F 正面宽", "cm", cm(A["F"], 0), cm(B["F"], 0), "输入(候选)"),
        ("tent", "D 进深", "cm", cm(A["D"], 0), cm(B["D"], 0), "输入(候选)"),
        ("tent", "E 檐高", "cm", cm(A["E"], 0), cm(B["E"], 0), "输入(可调)"),
        ("tent", "H 屋脊高", "cm", cm(A["H"], 0), cm(B["H"], 0), "输入(可调)"),
        ("tent", "占地面积", "m2", f"{A['footprint_area']:.2f}", f"{B['footprint_area']:.2f}", "推导"),
        ("door", "门宽 x 门高", "cm", "70 x 90", "70 x 90", "暂定假设"),
        ("window", "侧通风窗(每侧1个)", "cm", "30 x 40 (z=30~70)", "30 x 40 (z=30~70)", "暂定假设"),
        ("roof", "屋面倾角", "deg", f"{A['slope_angle_deg']}", f"{B['slope_angle_deg']}", "推导"),
        ("roof", "屋面斜长 S", "cm", cm(A["roof_slope_len"]), cm(B["roof_slope_len"]), "推导"),
        ("roof", "单块屋面料裁剪(斜向x宽向)", "cm",
         f"{cm(A['fabric']['panel_slope_cut'])} x {cm(A['fabric']['panel_width_cut'], 0)}",
         f"{cm(B['fabric']['panel_slope_cut'])} x {cm(B['fabric']['panel_width_cut'], 0)}", "推导(估,含出檐/包脊)"),
        ("clearance", "门洞上角屋面高度", "cm", cm(A["roofline_at_door_edge"]), cm(B["roofline_at_door_edge"]), "推导"),
        ("clearance", "门洞顶净空", "cm", cm(A["door_clear"]), cm(B["door_clear"]), "推导"),
        ("clearance", "门洞侧边净宽(每侧)", "cm", cm(A["door_margin"], 0), cm(B["door_margin"], 0), "推导"),
        ("clearance", "110cm儿童站立条带宽", "cm", cm(A["standing_strip_110"], 0), cm(B["standing_strip_110"], 0), "推导"),
        ("clearance", "115cm儿童站立条带宽", "cm", cm(A["standing_strip_115"], 0), cm(B["standing_strip_115"], 0), "推导"),
        ("interior", "帐内可用地面(近似)", "cm x cm",
         f"{cm(A['floor_inner'][0], 0)} x {cm(A['floor_inner'][1], 0)}",
         f"{cm(B['floor_inner'][0], 0)} x {cm(B['floor_inner'][1], 0)}", "推导"),
        ("interior", "帐内可用面积", "m2", f"{A['floor_inner_area']:.2f}", f"{B['floor_inner_area']:.2f}", "推导"),
        ("fabric", "前山墙(含门洞)面积", "m2", f"{A['fabric']['front_gable_with_door']:.2f}", f"{B['fabric']['front_gable_with_door']:.2f}", "推导"),
        ("fabric", "后山墙面积", "m2", f"{A['fabric']['back_gable']:.2f}", f"{B['fabric']['back_gable']:.2f}", "推导"),
        ("fabric", "两侧墙合计", "m2", f"{A['fabric']['side_walls_total']:.2f}", f"{B['fabric']['side_walls_total']:.2f}", "推导"),
        ("fabric", "两块屋面料合计", "m2", f"{A['fabric']['roof_panels_total']:.2f}", f"{B['fabric']['roof_panels_total']:.2f}", "推导"),
        ("fabric", "面料总量估算(不含门帘/地垫)", "m2", f"{A['fabric']['total_estimate']:.2f}", f"{B['fabric']['total_estimate']:.2f}", "推导(估)"),
        ("child", "儿童占位测试高度", "cm", "100~115", "100~115", "测试范围,非实测"),
        ("room", "房间 宽 x 进深", "cm", f"{cm(A['room']['w'], 0)} x {cm(A['room']['d'], 0)}",
         f"{cm(B['room']['w'], 0)} x {cm(B['room']['d'], 0)}", "输入(待复核)"),
        ("room", "帐篷+装饰 到左右墙净距", "cm", cm(A["room"]["clr_x"], 0), cm(B["room"]["clr_x"], 0), "推导(基于待复核房间)"),
        ("room", "帐篷+通道 到前后墙净距", "cm", cm(A["room"]["clr_y"], 0), cm(B["room"]["clr_y"], 0), "推导(基于待复核房间)"),
        ("room", "门扇范围到帐篷最小距离", "cm", cm(A["room"]["door_swing_to_tent"], 0), cm(B["room"]["door_swing_to_tent"], 0), "推导(门位为假设)"),
        ("elec", "电子盒占位(帐外)", "cm", "15 x 10 x 6", "15 x 10 x 6", "暂定假设"),
        ("elec", "按钮高度", "cm", "80", "80", "暂定假设"),
        ("elec", "PIR(门楣上方)", "cm", "5 x 3 x 3 @z≈102", "同左", "暂定假设"),
    ]

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"[OUT] {path}")


def write_json(out, data):
    path = os.path.join(out, "geometry_checks.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OUT] {path}")
    for v in ("A", "B"):
        dv = data["variants"][v]
        bad = [c for c in dv["checks"] if c["status"] == "FAIL"]
        warn = [c for c in dv["checks"] if c["status"] == "WARN"]
        print(f"[CHECK] {v}: {len(dv['checks'])} checks, "
              f"PASS={sum(1 for c in dv['checks'] if c['status']=='PASS')}, "
              f"WARN={len(warn)}, FAIL={len(bad)}")

# ----------------------------------------------------------------------------
# bpy 基础设施
# ----------------------------------------------------------------------------

COLL_NAMES = ["01_Room", "02_Tent_Frame", "03_Fabric_Cover", "04_Openings",
              "05_Child_And_Path", "06_Decorations", "07_Electronics",
              "08_Cameras", "09_Annotations_Detail", "10_Annotations_Room"]

C = {
    "floor":   (0.78, 0.76, 0.73, 1), "wall":   (0.70, 0.68, 0.66, 1),
    "furn":    (0.52, 0.52, 0.56, 1), "swing":  (0.45, 0.70, 0.45, 1),
    "frame":   (0.55, 0.38, 0.22, 1),
    "fab_gable": (0.82, 0.28, 0.26, 1), "fab_side": (0.92, 0.88, 0.80, 1),
    "roof":    (0.24, 0.48, 0.30, 1),
    "curtain": (0.93, 0.91, 0.86, 1), "dframe": (0.45, 0.30, 0.18, 1),
    "snow":    (0.96, 0.96, 0.97, 1),
    "child":   (0.28, 0.50, 0.88, 1), "path":   (0.95, 0.80, 0.25, 1),
    "infloor": (0.55, 0.78, 0.90, 1),
    "tree":    (0.18, 0.42, 0.24, 1), "trunk":  (0.40, 0.28, 0.16, 1),
    "gift1":   (0.82, 0.22, 0.22, 1), "gift2":  (0.88, 0.68, 0.18, 1),
    "sign":    (0.92, 0.78, 0.35, 1), "star":   (0.98, 0.82, 0.25, 1),
    "elec":    (0.95, 0.50, 0.12, 1),
    "ink":     (0.05, 0.05, 0.05, 1), "dim":    (0.15, 0.15, 0.15, 1),
}


def get_coll(name):
    return bpy.data.collections[name]


def setup_scene():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "CENTIMETERS"   # 内部米、界面厘米
    for n in COLL_NAMES:
        c = bpy.data.collections.new(n)
        scene.collection.children.link(c)
    world = bpy.data.worlds.new("G0World")
    world.color = (0.88, 0.90, 0.93)
    scene.world = world
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except Exception:
        ENGINE[0] = "CYCLES"
    sh = getattr(scene.display, "shading", None)
    if sh is not None:
        for attr, val in (("light", "STUDIO"), ("color_type", "OBJECT"),
                          ("background_type", "WORLD"), ("show_cavity", True),
                          ("cavity_type", "SCREEN")):
            try:
                setattr(sh, attr, val)
            except Exception:
                pass
    try:
        scene.display.render_aa = "8"
    except Exception:
        try:
            scene.display.render_aa = "FXAA"
        except Exception:
            pass


def _link(ob, coll):
    get_coll(coll).objects.link(ob)
    ob.color = (1, 1, 1, 1)
    return ob


def box(name, x0, x1, y0, y1, z0, z1, coll, color):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
         (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    ob = bpy.data.objects.new(name, me)
    _link(ob, coll)
    ob.color = color
    return ob


def gable_prism(name, xw, y0, y1, zb, zt, coll, color):
    """三角形山墙棱柱，脊顶在 x=0。"""
    v = [(-xw, y0, zb), (xw, y0, zb), (0, y0, zt),
         (-xw, y1, zb), (xw, y1, zb), (0, y1, zt)]
    f = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (0, 3, 5, 2), (1, 2, 5, 4)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    ob = bpy.data.objects.new(name, me)
    _link(ob, coll)
    ob.color = color
    return ob


def sloped_slab(name, p0, p1, y0, y1, t, coll, color):
    """在 XZ 剖面上由 p0=(x,z) 到 p1=(x,z) 的斜面板，沿 Y 挤出 y0..y1，厚 t。"""
    x0, z0 = p0
    x1, z1 = p1
    dx, dz = x1 - x0, z1 - z0
    L = math.hypot(dx, dz)
    nx, nz = -dz / L * t / 2, dx / L * t / 2
    v = [(x0 + nx, y0, z0 + nz), (x1 + nx, y0, z1 + nz),
         (x1 - nx, y0, z1 - nz), (x0 - nx, y0, z0 - nz),
         (x0 + nx, y1, z0 + nz), (x1 + nx, y1, z1 + nz),
         (x1 - nx, y1, z1 - nz), (x0 - nx, y1, z0 - nz)]
    f = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
         (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    ob = bpy.data.objects.new(name, me)
    _link(ob, coll)
    ob.color = color
    return ob


def cyl_between(name, p0, p1, r0, r1, coll, color, seg=16):
    """任意两点间的圆台/圆柱杆件。"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    mid = (p0 + p1) / 2
    verts, faces = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        verts.append((r0 * math.cos(a), r0 * math.sin(a), -L / 2))
    for i in range(seg):
        a = 2 * math.pi * i / seg
        verts.append((r1 * math.cos(a), r1 * math.sin(a), L / 2))
    verts.append((0, 0, -L / 2))
    verts.append((0, 0, L / 2))
    cb, ct = 2 * seg, 2 * seg + 1
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((i, j, seg + j, seg + i))
        faces.append((cb, j, i))
        faces.append((ct, seg + i, seg + j))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    _link(ob, coll)
    ob.color = color
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    ob.matrix_world = Matrix.Translation(mid) @ q.to_matrix().to_4x4()
    return ob


def sphere(name, center, r, coll, color, seg=16, rings=6):
    cx, cy, cz = center
    verts, faces = [], []
    for j in range(rings + 1):
        th = math.pi * j / rings
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((cx + r * math.sin(th) * math.cos(a),
                          cy + r * math.sin(th) * math.sin(a),
                          cz + r * math.cos(th)))
    for j in range(rings):
        for i in range(seg):
            i2 = (i + 1) % seg
            faces.append((j * seg + i, j * seg + i2, (j + 1) * seg + i2, (j + 1) * seg + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    _link(ob, coll)
    ob.color = color
    return ob


def flat_arc(name, center, r0, r1, a0, a1, z, coll, color, seg=14):
    """地板上的门扇扫掠扇形（平面标注）。"""
    cx, cy = center
    verts, faces = [], []
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg
        verts.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z))
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg
        verts.append((cx + r1 * math.cos(a), cy + r1 * math.sin(a), z))
    n = seg + 1
    for i in range(seg):
        faces.append((i, i + 1, n + i + 1, n + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    _link(ob, coll)
    ob.color = color
    return ob


def add_text(name, body, loc, rot, size, coll, color=None, align="CENTER"):
    cu = bpy.data.curves.new(name, type="FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new(name, cu)
    ob.location = loc
    ob.rotation_euler = rot
    _link(ob, coll)
    ob.color = color if color else C["ink"]
    return ob


def dim(name, p0, p1, facing, label, coll, size=0.07, off=(0, 0, 0), color=None,
        text_loc=None):
    """尺寸线 + 居中文字。facing: TOP / FRONT / SIDE。text_loc 可覆盖文字位置。"""
    t = 0.006
    if abs(p1[0] - p0[0]) >= abs(p1[1] - p0[1]) and abs(p1[0] - p0[0]) >= abs(p1[2] - p0[2]):
        box(f"{name}_line", min(p0[0], p1[0]), max(p0[0], p1[0]),
            p0[1] - t, p0[1] + t, p0[2] - t, p0[2] + t, coll, color or C["dim"])
        rot = {"TOP": (0, 0, 0), "FRONT": (math.pi / 2, 0, 0),
               "SIDE": (math.pi / 2, 0, -math.pi / 2)}[facing]
    elif abs(p1[1] - p0[1]) >= abs(p1[2] - p0[2]):
        box(f"{name}_line", p0[0] - t, p0[0] + t, min(p0[1], p1[1]), max(p0[1], p1[1]),
            p0[2] - t, p0[2] + t, coll, color or C["dim"])
        rot = (0, 0, math.pi / 2) if facing == "TOP" else None
    else:
        box(f"{name}_line", p0[0] - t, p0[0] + t, p0[1] - t, p0[1] + t,
            min(p0[2], p1[2]), max(p0[2], p1[2]), coll, color or C["dim"])
        rot = None
    if rot is None:
        rot = {"TOP": (0, 0, 0), "FRONT": (math.pi / 2, 0, 0),
               "SIDE": (math.pi / 2, 0, -math.pi / 2)}[facing]
    mid = ((p0[0] + p1[0]) / 2 + off[0], (p0[1] + p1[1]) / 2 + off[1],
           (p0[2] + p1[2]) / 2 + off[2])
    add_text(f"{name}_txt", label, text_loc if text_loc else mid, rot, size, coll,
             color or C["ink"])


def boolean_cut(target, cutter):
    """数据级布尔差集（不依赖操作符上下文）。"""
    md = target.modifiers.new("cut", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.object = cutter
    try:
        md.solver = "EXACT"
    except Exception:
        pass
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    old = target.data
    target.modifiers.remove(md)
    target.data = me
    me.name = old.name + "_cut"
    bpy.data.meshes.remove(old)


def materials_from_colors():
    """CYCLES 降级时把 Workbench 对象色转成材质。"""
    cache = {}
    for ob in bpy.data.objects:
        if ob.type not in {"MESH", "FONT"}:
            continue
        key = tuple(round(c, 3) for c in ob.color)
        if key not in cache:
            mat = bpy.data.materials.new(f"mat_{len(cache)}")
            mat.use_nodes = True
            try:
                bsdf = mat.node_tree.nodes["Principled BSDF"]
                bsdf.inputs["Base Color"].default_value = (ob.color[0], ob.color[1], ob.color[2], 1)
                bsdf.inputs["Roughness"].default_value = 0.9
            except Exception:
                pass
            cache[key] = mat
        if ob.type == "MESH":
            ob.data.materials.clear()
            ob.data.materials.append(cache[key])


# ----------------------------------------------------------------------------
# 场景构建
# ----------------------------------------------------------------------------

def build_room():
    w, d = CFG["room_w"], CFG["room_d"]
    h, t = CFG["room_wall_h"], CFG["room_wall_t"]
    cl = "01_Room"
    box("Room_Floor", -w / 2 - t, w / 2 + t, -d / 2 - t, d / 2 + t, -0.06, 0, cl, C["floor"])
    # 北墙 / 东西墙
    box("Wall_N", -w / 2 - t, w / 2 + t, d / 2, d / 2 + t, 0, h, cl, C["wall"])
    box("Wall_E", w / 2, w / 2 + t, -d / 2, d / 2, 0, h, cl, C["wall"])
    box("Wall_W", -w / 2 - t, -w / 2, -d / 2, d / 2, 0, h, cl, C["wall"])
    # 南墙（含房间门洞，门位为假设）
    dx = -w / 2 + 0.90
    x0, x1 = dx - CFG["room_door_w"] / 2, dx + CFG["room_door_w"] / 2
    box("Wall_S_L", -w / 2 - t, x0, -d / 2 - t, -d / 2, 0, h, cl, C["wall"])
    box("Wall_S_R", x1, w / 2 + t, -d / 2 - t, -d / 2, 0, h, cl, C["wall"])
    box("Wall_S_Header", x0, x1, -d / 2 - t, -d / 2, CFG["room_door_h"], h, cl, C["wall"])
    # 门扇开启范围标注（假设）
    flat_arc("Room_Door_Swing", (x0, -d / 2), 0.06, CFG["room_door_swing"],
             0.0, math.pi / 2, 0.004, cl, C["swing"])
    box("Room_Door_Leaf", x0 - 0.015, x0 + 0.015, -d / 2, -d / 2 + CFG["room_door_swing"],
        0.002, 0.01, cl, C["swing"])
    # 家具占位 [ASSUMPTION]，小房间压力测试时跳过
    if w >= 4.0 and d >= 4.0:
        box("Furn_Sofa", w / 2 - 1.00, w / 2 - 0.05, -0.975, 0.975, 0, 0.72, cl, C["furn"])
        box("Furn_Sofa_Back", w / 2 - 0.22, w / 2 - 0.05, -0.975, 0.975, 0.72, 1.02, cl, C["furn"])
        box("Furn_Shelf", -w / 2 + 0.05, -w / 2 + 0.40, 0.60, 1.80, 0, 1.85, cl, C["furn"])
        box("Furn_ToyChest", 1.80, 2.80, d / 2 - 0.60, d / 2 - 0.10, 0, 0.50, cl, C["furn"])
        box("Furn_Desk", -2.20, -1.00, -d / 2 + 0.10, -d / 2 + 0.70, 0, 0.74, cl, C["furn"])


def build_tent(v):
    F = CFG["variants"][v]["F"]
    D = CFG["variants"][v]["D"]
    E, H = CFG["E"], CFG["H"]
    dw, dh = CFG["door_w"], CFG["door_h"]
    t, o = CFG["panel_t"], CFG["over"]
    half, Dh = F / 2, D / 2
    rise = H - E
    S = math.hypot(half, rise)
    frame, fab, op = "02_Tent_Frame", "03_Fabric_Cover", "04_Openings"

    # --- 骨架（杆径为占位假设）---
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl_between(f"Post_{sx}_{sy}", (sx * half, sy * Dh, 0),
                        (sx * half, sy * Dh, E), CFG["post_r"], CFG["post_r"], frame, C["frame"])
    for sx in (-1, 1):
        cyl_between(f"Eave_{sx}", (sx * half, -Dh, E), (sx * half, Dh, E),
                    CFG["post_r"] * 0.9, CFG["post_r"] * 0.9, frame, C["frame"])
    cyl_between("Ridge", (0, -Dh, H), (0, Dh, H), CFG["post_r"] * 0.9, CFG["post_r"] * 0.9,
                frame, C["frame"])
    for sy in (-1, 1):
        for sx in (-1, 1):
            cyl_between(f"Rafter_{sx}_{sy}", (0, sy * Dh, H), (sx * half, sy * Dh, E),
                        CFG["post_r"] * 0.7, CFG["post_r"] * 0.7, frame, C["frame"])

    # --- 外罩 ---
    front_wall = box("Fabric_FrontWall", -half, half, -Dh - t, -Dh, 0, E, fab, C["fab_gable"])
    front_gable = gable_prism("Fabric_FrontGable", half, -Dh - t, -Dh, E, H, fab, C["fab_gable"])
    box("Fabric_BackWall", -half, half, Dh, Dh + t, 0, E, fab, C["fab_gable"])
    gable_prism("Fabric_BackGable", half, Dh, Dh + t, E, H, fab, C["fab_gable"])
    east = box("Fabric_Wall_E", half, half + t, -Dh, Dh, 0, E, fab, C["fab_side"])
    west = box("Fabric_Wall_W", -half - t, -half, -Dh, Dh, 0, E, fab, C["fab_side"])

    # 门洞（0.90 高 > 檐高 0.80，切进山墙）与通风窗真实开孔
    door_cutter = box("Cutter_Door", -dw / 2, dw / 2, -Dh - t - 0.05, -Dh + 0.05, -0.05, dh,
                      op, (1, 0, 1, 1))
    wc_e = box("Cutter_Win_E", half - 0.05, half + t + 0.05, -CFG["win_w"] / 2, CFG["win_w"] / 2,
               CFG["win_z0"], CFG["win_z0"] + CFG["win_h"], op, (1, 0, 1, 1))
    wc_w = box("Cutter_Win_W", -half - t - 0.05, -half + 0.05, -CFG["win_w"] / 2, CFG["win_w"] / 2,
               CFG["win_z0"], CFG["win_z0"] + CFG["win_h"], op, (1, 0, 1, 1))
    boolean_cut(front_wall, door_cutter)
    boolean_cut(front_gable, door_cutter)
    boolean_cut(east, wc_e)
    boolean_cut(west, wc_w)
    for ob in ("Cutter_Door", "Cutter_Win_E", "Cutter_Win_W"):
        bpy.data.objects.remove(bpy.data.objects[ob], do_unlink=True)

    # 屋顶两块斜面板（含出檐）
    ex = half + o * half / S
    ez = E - o * rise / S
    sloped_slab("Fabric_Roof_R", (0, H), (ex, ez), -Dh - o, Dh + o, t, fab, C["roof"])
    sloped_slab("Fabric_Roof_L", (0, H), (-ex, ez), -Dh - o, Dh + o, t, fab, C["roof"])

    # 门帘（关闭状态，双开）
    box("Door_Curtain_L", -dw / 2, -0.02, -Dh + 0.002, -Dh + 0.008, 0, dh, fab, C["curtain"])
    box("Door_Curtain_R", 0.02, dw / 2, -Dh + 0.002, -Dh + 0.008, 0, dh, fab, C["curtain"])

    # --- 门窗框与魔法窗 ---
    for sx in (-1, 1):
        box(f"Door_Jamb_{sx}", sx * dw / 2, sx * (dw / 2 + 0.035),
            -Dh - t - 0.004, -Dh + 0.004, 0, dh + 0.03, op, C["dframe"])
    box("Door_Header", -dw / 2 - 0.035, dw / 2 + 0.035, -Dh - t - 0.004, -Dh + 0.004,
        dh, dh + 0.03, op, C["dframe"])
    for sx, nm in ((1, "E"), (-1, "W")):
        xa, xb = sorted((sx * half - 0.008, sx * (half + t) + 0.008))
        wz0, wz1 = CFG["win_z0"], CFG["win_z0"] + CFG["win_h"]
        wy = CFG["win_w"] / 2
        box(f"WinFrame_T_{nm}", xa, xb, -wy - 0.02, wy + 0.02, wz1, wz1 + 0.02, op, C["dframe"])
        box(f"WinFrame_B_{nm}", xa, xb, -wy - 0.02, wy + 0.02, wz0 - 0.02, wz0, op, C["dframe"])
        box(f"WinFrame_L_{nm}", xa, xb, -wy - 0.02, -wy, wz0, wz1, op, C["dframe"])
        box(f"WinFrame_R_{nm}", xa, xb, wy, wy + 0.02, wz0, wz1, op, C["dframe"])
    # 魔法窗（后山墙圆窗占位，内部可放低压灯）
    cyl_between("Magic_Window", (0, Dh + t - 0.002, CFG["magic_win_z"]),
                (0, Dh + t + 0.008, CFG["magic_win_z"]),
                CFG["magic_win_r"], CFG["magic_win_r"], op, C["star"])


def build_child_path(v):
    F = CFG["variants"][v]["F"]
    D = CFG["variants"][v]["D"]
    dw = CFG["door_w"]
    half, Dh = F / 2, D / 2
    cl = "05_Child_And_Path"

    box("Interior_Floor_Zone", -half + 0.04, half - 0.04, -Dh + 0.04, Dh - 0.04,
        0.001, 0.003, cl, C["infloor"])
    box("Entry_Path", -dw / 2, dw / 2, -Dh - CFG["path_len"], -Dh, 0.001, 0.003, cl, C["path"])

    def child(name, x, y, kneeling=False):
        hb = 0.585 if kneeling else 0.92
        hh = 0.645 if kneeling else 1.01
        cyl_between(f"{name}_body", (x, y, 0), (x, y, hb),
                    CFG["child_body_r"], CFG["child_body_r"] * 0.85, cl, C["child"])
        sphere(f"{name}_head", (x, y, hh), 0.09, cl, C["child"])

    child("Child_In_Stand", 0.0, 0.30)            # 屋脊下站立
    child("Child_In_Kneel", -0.30, -0.20, True)   # 侧区跪坐游戏
    child("Child_Entry", 0.0, -Dh - 0.30)         # 门口进出占位


def build_decor(v):
    F = CFG["variants"][v]["F"]
    D = CFG["variants"][v]["D"]
    t, o = CFG["panel_t"], CFG["over"]
    half, Dh = F / 2, D / 2
    E, H = CFG["E"], CFG["H"]
    cl = "06_Decorations"

    # 圣诞树（帐外右侧）
    tx, ty = 0.75, -Dh - 0.40
    cyl_between("Tree_Trunk", (tx, ty, 0), (tx, ty, 0.12), 0.04, 0.04, cl, C["trunk"])
    for i, (r, hgt, z0) in enumerate(((0.26, 0.38, 0.10), (0.20, 0.34, 0.40),
                                      (0.14, 0.30, 0.66), (0.09, 0.24, 0.88))):
        cyl_between(f"Tree_Cone_{i}", (tx, ty, z0), (tx, ty, z0 + hgt), r, 0.012, cl, C["tree"])
    sphere("Tree_Star", (tx, ty, 1.16), 0.05, cl, C["star"])

    # 礼物盒（帐外左侧）
    box("Gift_1", -1.01, -0.79, -Dh - 0.46, -Dh - 0.24, 0, 0.22, cl, C["gift1"])
    box("Gift_2", -0.96, -0.82, -Dh - 0.41, -Dh - 0.29, 0.22, 0.32, cl, C["gift2"])
    box("Gift_3", -0.70, -0.54, -Dh - 0.42, -Dh - 0.30, 0, 0.10, cl, C["gift1"])

    # 门牌（门楣上方）
    box("Door_Sign", -0.14, 0.14, -Dh - t - 0.006, -Dh - t, 0.96, 1.06, cl, C["sign"])

    # 雪檐（可拆装饰白边）
    box("Snow_Ridge", -0.03, 0.03, -Dh - o, Dh + o, H - 0.02, H + 0.035, cl, C["snow"])
    for sx in (-1, 1):
        xa, xb = sorted((sx * (half - 0.03), sx * (half + 0.05)))
        box(f"Snow_Eave_{sx}", xa, xb, -Dh - o, Dh + o, E - 0.012, E + 0.02, cl, C["snow"])


def build_electronics(v):
    """全部电子占位集中在 07_Electronics，可整层隐藏。
    设计决策：控制盒/电源放帐外，帐内只留低压发光件。"""
    F = CFG["variants"][v]["F"]
    D = CFG["variants"][v]["D"]
    t = CFG["panel_t"]
    half, Dh = F / 2, D / 2
    E = CFG["E"]
    cl = "07_Electronics"

    # 帐外右侧：控制盒 / 电源 / 扬声器
    box("Elec_Box", half + 0.03, half + 0.03 + CFG["elec_box"][0],
        Dh - 0.20, Dh - 0.10, 0, CFG["elec_box"][2], cl, C["elec"])
    box("Elec_PSU", half + 0.03, half + 0.03 + CFG["elec_psu"][0],
        Dh - 0.32, Dh - 0.24, 0, CFG["elec_psu"][2], cl, C["elec"])
    box("Elec_Speaker", half + 0.03, half + 0.03 + CFG["elec_speaker"][0],
        Dh - 0.46, Dh - 0.36, 0, CFG["elec_speaker"][2], cl, C["elec"])
    # 门楣上方 PIR
    box("Elec_PIR", -0.025, 0.025, -Dh - t - 0.035, -Dh - t - 0.005, 1.01, 1.04, cl, C["elec"])
    # 门口左侧按钮（立杆 + 按钮，80cm 儿童可及高度）
    box("Elec_Button_Stand", -0.59, -0.51, -Dh - 0.54, -Dh - 0.46, 0, CFG["button_h"] - 0.02,
        cl, C["elec"])
    cyl_between("Elec_Button", (-0.55, -Dh - 0.50, CFG["button_h"] - 0.02),
                (-0.55, -Dh - 0.50, CFG["button_h"]), CFG["button_r"], CFG["button_r"],
                cl, C["star"])
    # 星星灯（低压发光件，沿两侧檐口）
    for sx in (-1, 1):
        for i, y in enumerate((-0.45, -0.15, 0.15, 0.45)):
            if abs(y) <= Dh:
                sphere(f"Star_{sx}_{i}", (sx * (half + 0.012), y, E + 0.042), 0.018, cl, C["star"])


def build_cameras(v):
    F = CFG["variants"][v]["F"]
    D = CFG["variants"][v]["D"]
    half, Dh = F / 2, D / 2
    cl = "08_Cameras"
    scene = bpy.context.scene

    def cam(name, loc, look_at=None, rot=None, ortho=None, lens=40, clip_start=0.02):
        c = bpy.data.cameras.new(name)
        if ortho:
            c.type = "ORTHO"
            c.ortho_scale = ortho
        else:
            c.lens = lens
        c.clip_start, c.clip_end = clip_start, 100
        ob = bpy.data.objects.new(name, c)
        ob.location = loc
        if look_at:
            ob.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        else:
            ob.rotation_euler = rot if rot else (0.0, 0.0, 0.0)
        _link(ob, cl)
        return ob

    cams = {
        "top_tent": cam("CAM_Top_Tent", (0, -0.40, 8), ortho=max(F + 0.9, D + 1.4) + 0.2),
        "top_room": cam("CAM_Top_Room", (0, 0, 12), ortho=max(CFG["room_w"], CFG["room_d"]) + 1.2),
        "front": cam("CAM_Front", (0, -Dh - 3.0, 0.75), rot=(math.pi / 2, 0, 0), ortho=F + 1.4),
        "side": cam("CAM_Side", (-Dh - 3.0, 0, 0.66), rot=(math.pi / 2, 0, -math.pi / 2), ortho=D + 1.2),
        # 儿童视角 = 蹲姿眼高 0.72m（门高 0.90 < 站立眼高，进入必须弯腰/蹲行）
        "child_entry": cam("CAM_Child_Entry", (0, -Dh - 0.75, 0.72),
                           look_at=(0, 0.30, 0.50), lens=28, clip_start=0.05),
        # 帐内视角 = 从后角看向门口（检查入口净空与活动空间）
        "interior": cam("CAM_Interior", (0.22, Dh - 0.12, 0.88),
                        look_at=(-0.06, -Dh - 0.30, 0.50), lens=24),
        "overview": cam("CAM_Overview", (2.7, -2.9, 1.9), look_at=(0, -0.15, 0.55), lens=38),
    }
    scene["g0_cameras"] = json.dumps(list(cams.keys()))


def build_annotations(v):
    d = derive(v)
    F, D = d["F"], d["F"]  # noqa
    F = CFG["variants"][v]["F"]
    D = CFG["variants"][v]["D"]
    E, H = CFG["E"], CFG["H"]
    dw, dh = CFG["door_w"], CFG["door_h"]
    half, Dh = F / 2, D / 2
    det, room = "09_Annotations_Detail", "10_Annotations_Room"
    yf = -Dh - 0.72   # 标注平面放在全部装饰物(树前缘-Dh-0.66)之前，避免遮挡

    # ---- 正面视图标注 ----
    dim("F_front", (-half, yf, 0.02), (half, yf, 0.02), "FRONT",
        f"F = {cm(F, 0)} cm", det, 0.075, (0, -0.06, 0))
    dim("E_front", (-half - 0.14, yf, 0), (-half - 0.14, yf, E), "FRONT",
        f"E = {cm(E, 0)}", det, 0.07, (-0.055, 0, 0))
    dim("H_front", (half + 0.16, yf, 0), (half + 0.16, yf, H), "FRONT",
        f"H = {cm(H, 0)}", det, 0.07, (0.06, 0, 0))
    dim("DoorW_front", (-dw / 2, yf, dh + 0.12), (dw / 2, yf, dh + 0.12), "FRONT",
        "door w = 70", det, 0.055, (0, -0.05, 0))
    dim("DoorH_front", (dw / 2 + 0.10, yf, 0), (dw / 2 + 0.10, yf, dh), "FRONT",
        "door h = 90", det, 0.055, (0.055, 0, 0))
    add_text("Slope_Note", f"roof slope {d['slope_angle_deg']:.1f} deg | S = {cm(d['roof_slope_len'])} cm",
             (0, yf, H + 0.18), (math.pi / 2, 0, 0), 0.075, det)
    add_text("Clear_Note", f"roof at door edge = {cm(d['roofline_at_door_edge'])} cm -> clearance {cm(d['door_clear'])} cm",
             (0, yf, H + 0.10), (math.pi / 2, 0, 0), 0.06, det)
    add_text("Door_Note", "door 70 x 90 cm", (0, yf, 0.45), (math.pi / 2, 0, 0), 0.06, det)

    # ---- 侧面视图标注 ----
    xs = -half - 0.16
    dim("D_side", (xs, -Dh, 0.02), (xs, Dh, 0.02), "SIDE",
        f"D = {cm(D, 0)} cm", det, 0.075, (0, 0, 0.07))
    wz0, wz1 = CFG["win_z0"], CFG["win_z0"] + CFG["win_h"]
    dim("WinH_side", (-half - 0.10, -CFG["win_w"] / 2 - 0.07, wz0),
        (-half - 0.10, -CFG["win_w"] / 2 - 0.07, wz1), "SIDE", "40 cm", det, 0.05, (-0.05, 0, 0))
    dim("WinW_side", (-half - 0.10, -CFG["win_w"] / 2, wz0 - 0.07),
        (-half - 0.10, CFG["win_w"] / 2, wz0 - 0.07), "SIDE", "30 cm", det, 0.05, (0, 0, -0.05))
    add_text("Win_Note", f"window z = {cm(wz0, 0)}..{cm(wz1, 0)} cm",
             (-half - 0.10, 0, wz1 + 0.10), (math.pi / 2, 0, -math.pi / 2), 0.05, det)
    add_text("Ang_Note", f"roof {d['slope_angle_deg']:.0f} deg", (0, 0, H + 0.15),
             (math.pi / 2, 0, -math.pi / 2), 0.06, det)

    # ---- 俯视（帐篷级）标注 ----
    dim("F_top", (-half, -Dh - 0.50, 0.005), (half, -Dh - 0.50, 0.005), "TOP",
        f"F = {cm(F, 0)} cm", det, 0.09, (0, -0.08, 0))
    dim("D_top", (half + 0.30, -Dh, 0.005), (half + 0.30, Dh, 0.005), "TOP",
        f"D = {cm(D, 0)} cm", det, 0.09, (0.12, 0, 0))
    dim("DoorW_top", (-dw / 2, -Dh - 0.24, 0.005), (dw / 2, -Dh - 0.24, 0.005), "TOP",
        "door 70", det, 0.055, text_loc=(0, -Dh - 0.12, 0.005))
    dim("Path_top", (-0.47, -Dh, 0.005), (-0.47, -Dh - CFG["path_len"], 0.005), "TOP",
        "path 80", det, 0.055, (-0.10, 0, 0))
    labels = [
        ("elec box", (half + 0.24, Dh - 0.15)), ("speaker", (half + 0.24, Dh - 0.41)),
        ("psu", (half + 0.28, Dh - 0.28)), ("PIR", (-0.10, -Dh - 0.06)),
        ("button@80cm", (-0.72, -Dh - 0.50)), ("tree", (1.02, -Dh - 0.40)),
        ("gifts", (-1.10, -Dh - 0.35)), ("sign", (0.34, -Dh - 0.02)),
        ("magic window (back)", (0, Dh + 0.14)), ("star lights (eaves)", (-(half)-0.16, 0.62)),
    ]
    for txt, (x, y) in labels:
        add_text(f"Lbl_{txt.replace(' ', '_')}", txt, (x, y, 0.005), (0, 0, 0), 0.05, det)
    add_text("Footprint_Note",
             f"footprint {cm(F, 0)} x {cm(D, 0)} cm = {F * D:.2f} m2 | interior floor "
             f"{cm(d['floor_inner'][0], 0)} x {cm(d['floor_inner'][1], 0)} cm",
             (0, Dh + 0.34, 0.005), (0, 0, 0), 0.075, det)
    add_text("Title_Note",
             f"TENT {v}: F={cm(F, 0)} D={cm(D, 0)} E={cm(E, 0)} H={cm(H, 0)} (cm)  [G0 geometry only]",
             (0, Dh + 0.52, 0.005), (0, 0, 0), 0.09, det)

    # ---- 俯视（房间级）标注 ----
    rw, rd = CFG["room_w"], CFG["room_d"]
    s = rw * 0.03
    dim("RoomW_top", (-rw / 2, -rd / 2 - 0.7, 0.005), (rw / 2, -rd / 2 - 0.7, 0.005), "TOP",
        f"room width {cm(rw, 0)} cm (UNVERIFIED)", room, s,
        text_loc=(0, rd / 2 - 0.9, 0.005))
    dim("RoomD_top", (rw / 2 + 0.7, -rd / 2, 0.005), (rw / 2 + 0.7, rd / 2, 0.005), "TOP",
        f"room depth {cm(rd, 0)} cm (UNVERIFIED)", room, s,
        text_loc=(rw / 2 + 0.35, 0, 0.005))
    dx = -rw / 2 + 0.90
    add_text("RoomDoor_Note", "room door + swing (ASSUMED)",
             (dx + 0.5, -rd / 2 - 0.30, 0.005), (0, 0, 0), s * 0.6, room)
    if rw >= 4.0 and rd >= 4.0:
        add_text("Furn_Note", "furniture: ASSUMED placeholders",
                 (rw / 2 - 1.6, 1.30, 0.005), (0, 0, 0), s * 0.7, room)
    add_text("TentFp_Note", f"tent {v} footprint {cm(F, 0)} x {cm(D, 0)} cm",
             (0, Dh + 0.62, 0.005), (0, 0, 0), s * 0.8, room)
    add_text("Clr_Note",
             f"min wall clearance: X {cm(d['room']['clr_x'], 0)} / Y {cm(d['room']['clr_y'], 0)} cm",
             (0, -Dh - 1.15, 0.005), (0, 0, 0), s * 0.7, room)


# ----------------------------------------------------------------------------
# 渲染
# ----------------------------------------------------------------------------

CHILD_OBJS = ("Child_Entry_body", "Child_Entry_head",
              "Child_In_Stand_body", "Child_In_Stand_head",
              "Child_In_Kneel_body", "Child_In_Kneel_head")
RENDER_PLAN = [
    ("top_tent", "top_tent", (1500, 1500), "detail", False, ()),
    ("top_room", "top_room", (1400, 1400), "room", False, ()),
    ("front", "front", (1600, 1200), "detail", False, ()),
    ("side", "side", (1600, 1200), "detail", False, ()),
    # child_entry / interior 两个透视视角渲染空帐篷（相机即儿童位置；
    # 帐内 1.1 x 1.6m 放三个人形会遮挡任何机位，净空由几何检查覆盖）；
    # child_entry 同时隐藏门帘 = 帘子拉开进入的状态
    ("child_entry", "child_entry", (1280, 960), None, False,
     CHILD_OBJS + ("Door_Curtain_L", "Door_Curtain_R")),
    ("interior", "interior", (1280, 960), None, False, CHILD_OBJS),
    ("full_layout", "overview", (1600, 1200), None, False, ()),
    ("base_no_electronics", "overview", (1600, 1200), None, True, ()),
]


def set_ann(mode):
    get_coll("09_Annotations_Detail").hide_render = mode != "detail"
    get_coll("10_Annotations_Room").hide_render = mode != "room"


def do_render(cam_ob, path, res):
    scene = bpy.context.scene
    scene.camera = cam_ob
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = path
    scene.render.image_settings.file_format = "PNG"
    try:
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        if ENGINE[0] == "WORKBENCH":
            print(f"[RENDER] Workbench failed ({e}); falling back to CYCLES")
            ENGINE[0] = "CYCLES"
            scene.render.engine = "CYCLES"
            scene.cycles.samples = 48
            materials_from_colors()
            scene.world.use_nodes = True
            try:
                bg = scene.world.node_tree.nodes["Background"]
                bg.inputs[0].default_value = (0.88, 0.90, 0.93, 1)
            except Exception:
                pass
            bpy.ops.render.render(write_still=True)
        else:
            raise


def render_all(v, out, tag, only):
    scene = bpy.context.scene
    cams = {ob.name[4:].lower(): ob for ob in bpy.data.objects
            if ob.name.startswith("CAM_")}
    rdir = os.path.join(out, "renders")
    os.makedirs(rdir, exist_ok=True)
    done = []
    for name, cam, res, ann, hide_elec, hide_objs in RENDER_PLAN:
        if only and name not in only:
            continue
        set_ann(ann)
        get_coll("07_Electronics").hide_render = hide_elec
        for hn in hide_objs:
            bpy.data.objects[hn].hide_render = True
        do_render(cams[cam], os.path.join(rdir, f"{tag}_{name}.png"), res)
        for hn in hide_objs:
            bpy.data.objects[hn].hide_render = False
        done.append(f"{tag}_{name}.png")
    get_coll("07_Electronics").hide_render = False
    set_ann("detail")
    print("[RENDER] wrote: " + ", ".join(done))
    return done


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main():
    args = ARGS
    out = os.path.abspath(args.out)
    os.makedirs(os.path.join(out, "renders"), exist_ok=True)
    tag = args.tag or args.variant

    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    except Exception:
        pass
    setup_scene()

    data = build_data()
    if not args.no_data:
        write_csv(out, data)
        write_json(out, data)

    build_room()
    build_tent(args.variant)
    build_child_path(args.variant)
    build_decor(args.variant)
    build_electronics(args.variant)
    build_cameras(args.variant)
    build_annotations(args.variant)

    if not args.skip_render:
        only = set(args.only.split(",")) if args.only else None
        render_all(args.variant, out, tag, only)

    # 恢复可见状态并保存工程
    get_coll("07_Electronics").hide_render = False
    set_ann("detail")
    scene = bpy.context.scene
    scene["g0_variant"] = args.variant
    scene["g0_note"] = "G0 geometry study - not a structural or child-product safety certification"
    if not args.no_save:
        bname = args.blend_name or f"christmas_tent_G0_{args.variant}.blend"
        bpath = os.path.join(out, bname)
        bpy.ops.wm.save_as_mainfile(filepath=bpath)
        print(f"[OUT] {bpath}")

    dv = data["variants"][args.variant]["derived"]
    print(f"[SUMMARY] variant {args.variant}: F={dv['F']} D={dv['D']} E={dv['E']} H={dv['H']} | "
          f"slope {dv['slope_angle_deg']} deg S={dv['roof_slope_len']}m | "
          f"door clear {dv['door_clear']}m | margin {dv['door_margin']}m | "
          f"strip110 {dv['standing_strip_110']}m strip115 {dv['standing_strip_115']}m | "
          f"fabric ~{dv['fabric']['total_estimate']} m2")


main()
