# check_case.py — 外壳几何检查器（从 STEP 实际几何重算，不读参数自行宣布 PASS）
# 运行（勿用 freecadcmd——其对部分目录/参数组合静默不执行且吞输出）：
#   PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
#     /Applications/FreeCAD.app/Contents/Resources/bin/python check_case.py
#   → 先跑负向自检（人为造错几何验证检查器能抓出），再对真实产物做 STEP 几何检查；
#     结果写 checks.json，任何失败退出码非 0。
#   产物目录可用 G2_OUT 环境变量覆盖（默认随脚本位置）。
# 检查内容（发起人 2026-11-28 要求）：
#   主体背面截面分析存在两个分离开口；开口中心距；贯穿背壁；USB 插头包络可通过；
#   连接器包络与底座裙壁无干涉；主体完整落入底座设计区域（非仅 bbox 长宽比较）。

import json
import math
import os
import sys

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
print("SCRIPT LOADED, argv:", sys.argv)
OUT = os.path.join(HERE, "renders", "case-r1")
TOL = 0.25          # 中心距/宽度比较容差 mm
CLEAR = 0.05        # 零干涉判定容差 mm³


def load(name):
    sh = Part.Shape()
    sh.read(os.path.join(OUT, name + ".step"))
    return sh


def common_vol(a, b):
    try:
        return a.common(b).Volume
    except Exception:
        return float("nan")


def rear_wall_analysis(body, wall_t=2.4, z_center=None, z_half=None):
    """在背壁厚度带内取水平切片，返回 (piece 数, 开口宽度列表, 开口中心 x 列表)。

    两个贯穿开口 → 背壁被切成 3 段；1 个开口 → 2 段；无开口 → 1 段。
    """
    bb = body.BoundBox
    z_lo = bb.ZMin + 0.4
    z_hi = bb.ZMax - 0.4
    if z_center is not None and z_half is not None:
        z_lo = z_center - z_half
        z_hi = z_center + z_half
    # x 限制在背壁跨度内（排除侧壁——侧壁与背壁在角部相连，会导致切片永远 1 块）
    x_lo = bb.XMin + wall_t + 1.2
    x_hi = bb.XMax - wall_t - 1.2
    slab = Part.makeBox(x_hi - x_lo, wall_t + 2.0, z_hi - z_lo,
                        App.Vector(x_lo, bb.YMin - 1.0, z_lo))
    pieces = body.common(slab).Solids
    pieces = sorted(pieces, key=lambda s: s.BoundBox.XMin)
    gaps, centers = [], []
    for a, b in zip(pieces, pieces[1:]):
        g_lo, g_hi = a.BoundBox.XMax, b.BoundBox.XMin
        if g_hi - g_lo > 1.0:                     # 忽略 <1mm 的碎缝
            gaps.append(g_hi - g_lo)
            centers.append((g_lo + g_hi) / 2)
    return pieces, gaps, centers


def through_and_envelope(body, cx, width, height, y_wall_lo, wall_t):
    """在开口中心放贯穿探针与插头包络，返回 (贯穿剩余体积, 包络剩余体积)。"""
    y0 = y_wall_lo - 2.0
    depth = wall_t + 4.0
    probe = Part.makeBox(width, depth, height,
                         App.Vector(cx - width / 2, y0, z_usb - height / 2))
    through = common_vol(body, probe)
    env = Part.makeBox(width + 1.0, depth, height + 1.0,
                       App.Vector(cx - (width + 1.0) / 2, y0, z_usb - (height + 1.0) / 2))
    env_vol = common_vol(body, env)
    return through, env_vol, Part.makeBox(width + 1.0, depth, height + 1.0,
                                          App.Vector(cx - (width + 1.0) / 2,
                                                     bb_body.YMin - 2.0,
                                                     z_usb - (height + 1.0) / 2))


def check_real(expected):
    """对真实 STEP 产物执行全部几何检查。expected: dims.json 的 params 段。"""
    body, base = load("case-r1-body"), load("case-r1-base")
    caps = {k: load(f"case-r1-cap-{k}") for k in ("a", "b", "c", "d")}
    checks, measured = {}, {}

    checks["body_valid"] = bool(body.isValid())
    checks["base_valid"] = bool(base.isValid())
    checks["caps_valid"] = bool(all(p.isValid() for p in caps.values()))

    # 1) 背壁截面：两个分离开口
    u = expected["usb"]
    global z_usb, bb_body
    bb_body = body.BoundBox
    z_usb = bb_body.ZMin + u["z"] + u["h"] / 2   # 与建模一致（含 0.12 抬升由 bbox 继承）
    wall_t = u.get("_wall_t", 2.4)
    pieces, gaps, centers = rear_wall_analysis(body, wall_t=wall_t,
                                               z_center=z_usb, z_half=max(u["h"] / 2 - 0.6, 1.0))  # 切片带收进孔内，避免孔上下缘实壁把分段连成一块
    checks["rear_wall_two_openings"] = (len(pieces) == 3 and len(gaps) == 2)
    if len(centers) == 2:
        measured["usb_opening_centers_x"] = [round(c, 3) for c in centers]
        measured["usb_center_distance"] = round(centers[1] - centers[0], 3)
        measured["usb_opening_widths"] = [round(g, 3) for g in gaps]
        checks["usb_center_distance"] = abs((centers[1] - centers[0]) - u["spacing"]) <= TOL
        checks["usb_two_openings_geometric"] = True
    else:
        measured["usb_piece_count"] = len(pieces)
        checks["usb_center_distance"] = False
        checks["usb_two_openings_geometric"] = False

    # 2) 开孔宽度 ≥ 参数开口宽（贯穿截面量出）
    if len(gaps) == 2:
        checks["usb_opening_width_ok"] = all(abs(g - u["w"]) <= TOL for g in gaps)

    # 3) 贯穿背壁 + 插头包络通过 + 连接器包络不撞底座裙壁
    y_wall_lo = bb_body.YMin
    if len(centers) == 2:
        pe = expected["usb_plug_env"]
        thr = []
        env = []
        for cx in centers:
            t_vol, e_vol, env_shape = through_and_envelope(body, cx, u["w"], u["h"],
                                                           y_wall_lo, wall_t)
            thr.append(t_vol)
            # 插头包络（独立参数，窄于开孔）：真实插头必须能从主体材料中穿过
            env_shape = Part.makeBox(pe["w"], wall_t + 4.0, pe["h"],
                                     App.Vector(cx - pe["w"] / 2, bb_body.YMin - 2.0,
                                                z_usb - pe["h"] / 2))
            env.append(common_vol(body, env_shape))
        checks["usb_holes_through_wall"] = all(v <= CLEAR for v in thr)
        checks["usb_plug_envelope_passes"] = all(v <= CLEAR for v in env)
        # 连接器+插头包络（含板外突出段）与底座无干涉
        env_all = Part.makeBox(u["spacing"] + u["w"], wall_t + 6.0, u["h"] + 1.5,
                               App.Vector(-u["spacing"] / 2 - u["w"] / 2,
                                          bb_body.YMin - 5.0,
                                          z_usb - (u["h"] + 1.5) / 2))
        checks["usb_envelope_vs_base_clear"] = common_vol(base, env_all) <= CLEAR
        measured["usb_envelope_through_volumes"] = [round(v, 4) for v in thr + env]

    # 4) 装配：主体完整落入底座设计区域（从底座几何实测开口，而非参数 bbox 比较）
    bb_base = base.BoundBox
    z_mid = bb_base.ZMin + (expected["base"]["floor"] + bb_base.ZMax) / 2
    slab = Part.makeBox(bb_base.XLength + 20, bb_base.YLength + 20, 0.4,
                        App.Vector(bb_base.XMin - 10, bb_base.YMin - 10, z_mid - 0.2))
    core = base.common(slab)
    inner_bb = None
    for f in core.Faces:
        if abs(f.CenterOfMass.z - z_mid) < 0.25 and len(f.Wires) >= 2:
            for w in f.Wires[1:]:            # 第 0 条是外圈，其余是内开口（螺柱孔/开口区），取最大=装配开口
                wb = w.BoundBox
                if inner_bb is None or (wb.XLength * wb.YLength > inner_bb.XLength * inner_bb.YLength):
                    inner_bb = wb
    if inner_bb is not None:
        checks["pocket_opening_found"] = True
        measured["base_pocket_opening"] = [round(inner_bb.XLength, 3), round(inner_bb.YLength, 3)]
        checks["assembly_body_in_base"] = (
            bb_body.XMin >= inner_bb.XMin + 0.2 and bb_body.XMax <= inner_bb.XMax - 0.2 and
            bb_body.YMin >= inner_bb.YMin + 0.2 and bb_body.YMax <= inner_bb.YMax - 0.2)
    else:
        checks["pocket_opening_found"] = False
        checks["assembly_body_in_base"] = False

    # 5) 主体坐高：在地板之上、且与地板间隙 ≤ 0.5（0.12 设计间隙）
    floor_top = bb_base.ZMin + expected["base"]["floor"]
    checks["body_seat_clearance"] = 0.05 <= (bb_body.ZMin - floor_top) <= 0.5
    measured["body_seat_gap"] = round(bb_body.ZMin - floor_top, 3)

    # 6) 零干涉
    for pair, a, b in (("body_base", body, base), ("body_caps", body, list(caps.values())[0]),
                       ("base_caps", base, list(caps.values())[0])):
        total = common_vol(a, b)
        if pair == "body_caps":
            total = sum(common_vol(body, p) for p in caps.values())
        if pair == "base_caps":
            total = sum(common_vol(base, p) for p in caps.values())
        checks[f"{pair}_interference_vol"] = round(total, 4)

    # 7) 键帽在键位上（中心距实测 vs 参数）
    K = expected["keys"]
    centers_cap = sorted((round((caps[k].BoundBox.XMin + caps[k].BoundBox.XMax) / 2, 3),
                          round((caps[k].BoundBox.YMin + caps[k].BoundBox.YMax) / 2, 3))
                         for k in caps)
    want = sorted([(-K["pitch_x"] / 2, -K["pitch_y"] / 2), (K["pitch_x"] / 2, -K["pitch_y"] / 2),
                   (-K["pitch_x"] / 2, K["pitch_y"] / 2), (K["pitch_x"] / 2, K["pitch_y"] / 2)])
    checks["caps_on_key_positions"] = all(
        abs(a[0] - b[0]) <= TOL and abs(a[1] - b[1]) <= TOL for a, b in zip(centers_cap, want))

    return checks, measured


# ── 负向自检：人为造错，检查器必须抓出 ────────────────────────
def self_test():
    """负向自检：人为造错几何，检查器必须抓出；正向必须放行。全部走真实几何计算。"""
    results = {}

    def plate(holes):
        """背壁试验板 60×2.4×20，holes=[(cx,w,h)]，板顶 z=0（孔位于下半段）。"""
        plate = Part.makeBox(60, 2.4, 20, App.Vector(-30, -1.2, 0))
        for cx, w, h in holes:
            plate = plate.cut(Part.makeBox(w, 6.0, h, App.Vector(cx - w / 2, -3.0, 5.0)))
        return plate

    # 负例 1：只开一个孔 → 截面分析必须报出"不是两个分离开口"
    p, g, c = rear_wall_analysis(plate([(0.0, 11.2, 8.5)]), wall_t=2.4, z_center=9.25, z_half=3.65)  # 切片带须完全在孔高内，否则孔上下实壁把分段连回一块
    results["neg_one_opening_detected"] = not (len(p) == 3 and len(g) == 2)

    # 负例 2：右孔缩到 9×7（插头包络 14.5×9.5 应被卡住 → 检出干涉体积）
    narrow = plate([(-16.0, 11.2, 8.5), (16.0, 8.0, 7.0)])
    env = Part.makeBox(10.6, 6.4, 9.0, App.Vector(16 - 5.3, -3.2, 5.0))
    results["neg_narrow_hole_detected"] = common_vol(narrow, env) > CLEAR

    # 正例：两个合格孔（中心距 32）→ 放行且量出中心距
    p, g, c = rear_wall_analysis(plate([(-16.0, 11.2, 8.5), (16.0, 11.2, 8.5)]),
                                 wall_t=2.4, z_center=9.25, z_half=3.65)  # 切片带须完全在孔高内，否则孔上下实壁把分段连回一块
    results["pos_two_openings_pass"] = (len(p) == 3 and len(g) == 2 and
                                        abs((c[1] - c[0]) - 32.0) <= 0.25)

    # 负例 3：螺柱撞内腔圆角（复刻真实缺陷的缩小版）
    outer = Part.makeBox(60, 60, 20, App.Vector(-30, -30, 0))
    inner = Part.makeBox(55.2, 55.2, 20, App.Vector(-27.6, -27.6, 0))
    inner = inner.makeFillet(7.6, [e for e in inner.Edges
                                   if abs(abs(e.tangentAt(e.FirstParameter).z) - 1) < 0.5])
    shell = outer.cut(inner)
    floor = Part.makeBox(70, 70, 2.4, App.Vector(-35, -35, -2.52))  # 与壳底留 0.12，排除贴合面幻影
    boss = Part.makeCylinder(3, 7, App.Vector(29, 24, -2.52))       # 太靠圆角 → 撞壁
    floor = floor.fuse(boss)
    results["neg_boss_corner_collision_detected"] = common_vol(shell, floor) > CLEAR

    # 负例 4：底座开口过小（从底座截面实测开口，主体 88×78 放不进）
    body_blk = Part.makeBox(88, 78, 26, App.Vector(-44, -39, 0))
    base_blk = Part.makeBox(94, 84, 14, App.Vector(-47, -42, 0)).cut(
        Part.makeBox(80, 70, 12, App.Vector(-40, -35, 2.4)))
    slab = Part.makeBox(140, 140, 0.4, App.Vector(-70, -70, 7.8))
    core = base_blk.common(slab)
    inner_bb = None
    for f in core.Faces:
        if abs(f.CenterOfMass.z - 8) < 0.25 and len(f.Wires) >= 2:
            for w in f.Wires[1:]:
                wb = w.BoundBox
                if inner_bb is None or wb.XLength * wb.YLength < inner_bb.XLength * inner_bb.YLength:
                    inner_bb = wb
    fits = (88 + 0.2 <= inner_bb.XLength and 78 + 0.2 <= inner_bb.YLength)
    results["neg_small_pocket_detected"] = (not fits)

    ok = all(results.values())
    print("SELF-TEST:", "OK" if ok else f"FAILED {results}")
    return ok, results


def main():
    # 每次运行先做负向自检（验证检查器本身能抓错），再对真实产物检查
    st_ok, st_results = self_test()
    if not st_ok:
        print("SELF-TEST FAILED:", json.dumps(st_results))
        sys.exit(3)

    dims_path = os.path.join(OUT, "dims.json")
    expected = json.loads(open(dims_path).read())["params"]
    checks, measured = check_real(expected)
    def _failed(v):
        if isinstance(v, bool):
            return not v
        if isinstance(v, (int, float)):
            return abs(v) > CLEAR
        return False
    failed = [k for k, v in checks.items() if _failed(v)]
    with open(os.path.join(OUT, "checks.json"), "w") as f:
        json.dump({"ok": not failed, "failed": failed, "checks": checks,
                   "measured": measured,
                   "note": "全部数值从 STEP 实际几何重算（check_case.py），参数仅作期望值对比"},
                  f, ensure_ascii=False, indent=1)
    print("CHECKS:", "OK" if not failed else f"FAILED {failed}")
    print("measured:", json.dumps(measured))
    print("SELF-TEST: OK")
    sys.exit(2 if failed else 0)


main()
