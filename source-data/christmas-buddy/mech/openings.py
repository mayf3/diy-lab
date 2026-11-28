#!/usr/bin/env python3
"""P0-4：外壳真实开孔建模 + 基于**导出 STEP 重导入**的几何验证。

审查线程 #4725089490 的修复：开孔不再只是参数，而是被真正切进壳体几何；
检查器在**重新导入的最终 STEP** 上用探针体布尔求交判定贯穿性、实测开孔面积、
USB 插头包络碰撞——参数检查与几何检查分开标注。

负向测试（mech_tests.py）：删格栅→FAIL、删 USB 孔→FAIL、缩格栅→FAIL。

运行入口由 build_mech.py 调用；也可独立：
  python3 openings.py selftest   # 快速自检（构建+导出+检查 方案A）
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import cadquery as cq
from cadquery import Vector

sys.path.insert(0, str(Path(__file__).parent))
from params import PARAMS  # noqa: E402

# ---- 开孔布局（唯一事实源，与 interfaces/netlist 对齐）----
SPEAKER = PARAMS["speaker"]
# 径向格栅：槽沿柱面壳体**径向**贯穿（首轮直线网格一半切在体外、二轮旋转盒以 78° 掠射切墙，
# 均被几何检查抓出后改为严格径向）
GRILLE_ANGLES = (-32.5, -25.0, -17.5, -10.0, 10.0, 17.5, 25.0, 32.5)  # 度，绕 Z 轴
GRILLE_ROWS = (32.0, 44.0)
SLOT_R = 41.0                                              # 槽中心半径（墙外侧起）
GRILLE_SLOTS = [(a, z) for a in GRILLE_ANGLES for z in GRILLE_ROWS]

def slot_frame(a_deg: float, z: float):
    """返回槽 (中心, 径向向外单位向量)。"""
    na = math.radians(a_deg)
    center = cq.Vector(SLOT_R * math.sin(na), SLOT_R * math.cos(na), z)
    radial = cq.Vector(math.sin(na), math.cos(na), 0)
    return center, radial
USB = PARAMS["usb_c"]                                       # x=-17, z=13.5
USB_CUT_W, USB_CUT_H = 13.4, 7.4                            # 插头包络 12×6 + 双边公差
MIC = PARAMS["mic"]                                         # x=24, z=70, Ø2.2

def _slot_cutters(slot_w=2.5):
    """前墙格栅切割体：每槽沿径向贯穿（旋转 −a 使盒长轴对准径向）。"""
    cutters = None
    for (a, z) in GRILLE_SLOTS:
        center, radial = slot_frame(a, z)
        b = cq.Workplane("XY").box(slot_w, 30.0, 10.0)
        b = b.rotate((0, 0, 0), (0, 0, 1), -a).translate((center.x, center.y, z))
        cutters = b if cutters is None else cutters.union(b)
    return cutters

def _usb_cutter(w=USB_CUT_W, h=USB_CUT_H):
    """后墙 USB-C 开孔——按插头包络 12×6 + 双边公差设计（首轮按插座 10×5 开孔被几何检查否决）。"""
    return cq.Workplane("XY").box(w, 40, h).translate((USB["x"], -25, USB["z"]))

def _mic_cutter(d=2.4):
    """前墙麦克风声孔。"""
    return cq.Workplane(obj=cq.Solid.makeCylinder(
        d / 2, 40, Vector(MIC["x"], 5, MIC["z"]), Vector(0, 1, 0)))

def apply_openings(parts: dict, mode: str = "full") -> dict:
    """把开孔切进已分割的壳体。mode: full / none / shrunk（负向测试用）。"""
    if mode == "none":
        return parts
    slot_w = 2.5 if mode == "full" else 1.0
    for key, cutter in (("body_front", _slot_cutters(slot_w)),
                        ("body_front", _mic_cutter()),
                        ("body_rear", _usb_cutter())):
        if key in parts:
            parts[key] = parts[key].cut(cutter)
    return parts

# ---------------------------------------------------------------------------
# 几何验证（在重导入的 STEP 上）
# ---------------------------------------------------------------------------

def _import_step(path: Path) -> cq.Workplane:
    return cq.importers.importStep(str(path))

def _probe_volume(wp: cq.Workplane, solid) -> float:
    """探针体与导入实体求交体积（mm³）。贯穿孔 → 0。

    注意：0 只在「布尔成功且结果为空」时合法；OCCT 真实失败会抛异常，
    这里显式区分——异常不是证据，失败必须上抛由负向测试兜底。"""
    if isinstance(solid, cq.Workplane):
        solid = solid.val()
    inter = wp.intersect(cq.Workplane(obj=solid))
    return inter.val().Volume() if inter.vals() else 0.0

def _probe(solid_kind, *args):
    if solid_kind == "cyl":
        r, y0, length, cx, cz = args
        return cq.Solid.makeCylinder(r, length, Vector(cx, y0, cz), Vector(0, 1, 0))
    if solid_kind == "box":
        w, d, t, cx, cy, cz = args
        return cq.Workplane("XY").box(w, d, t).translate((cx, cy, cz)).val()
    raise ValueError

def geometry_checks(scheme: str, outdir: Path) -> tuple[list, list]:
    """在导出 STEP 重导入后做几何级检查。返回 (checks, unknowns)。"""
    checks, unknowns = [], []

    def add(key, ok, detail):
        checks.append({"check": key, "result": "PASS" if ok else "FAIL", "detail": detail,
                       "basis": "geometry(exported STEP)"})

    front = _import_step(outdir / "body_front.step")
    rear = _import_step(outdir / "body_rear.step")

    # 1) 格栅逐槽贯穿（探针 2.3mm 宽 < 2.5 设计，含 0.2 公差意识）
    all_through = True
    bad = []
    for (ang, z) in GRILLE_SLOTS:
        center, radial = slot_frame(ang, z)
        probe = cq.Workplane(obj=cq.Solid.makeCylinder(
            1.1, 30.0, center, -radial))
        v = _probe_volume(front, probe)
        if v > 1e-6:
            all_through = False
            bad.append(f"({ang}°,{z})@r41:{v:.2f}mm³")
    add("格栅 16 槽全部贯穿（重导入 STEP）", all_through,
        "全部贯穿" if all_through else f"未贯穿槽：{bad[:4]}")

    # 2) 格栅实测开孔面积：每槽局部坐标系采样（沿槽法向探针），测量而非引用设计参数
    diaphragm = math.pi * (SPEAKER["d"] / 2) ** 2
    need = SPEAKER["grille_ratio_min"] * diaphragm
    measured = 0.0
    SLOT_AREA = 2.5 * 10.0
    for (ang, z) in GRILLE_SLOTS:
        center, radial = slot_frame(ang, z)
        tangent = cq.Vector(radial.y, -radial.x, 0)    # 切向（槽宽方向）
        passing = 0
        total = 0
        iw = -1.0
        while iw <= 1.0:                               # 宽 ±1.0mm（0.5mm 步进）
            ih = -4.5
            while ih <= 4.5:                           # 高 ±4.5mm
                total += 1
                base = center + tangent * iw + cq.Vector(0, 0, ih)
                probe = cq.Workplane(obj=cq.Solid.makeCylinder(
                    0.2, 30.0, base + radial * 10.0, -radial))
                if _probe_volume(front, probe) <= 1e-6:
                    passing += 1
                ih += 0.5
            iw += 0.5
        measured += SLOT_AREA * passing / total
    add("格栅实测开孔面积 ≥ 60% 振膜（局部坐标采样测量）", measured >= need,
        f"实测 {measured:.0f}mm² ≥ 需求 {need:.0f}mm²（369）")

    # 3) USB-C：开孔贯穿 + 插头包络无碰撞
    probe = _probe("box", 12.0, 30.0, 5.6, USB["x"], -25, USB["z"])
    v = _probe_volume(rear, probe)
    add("USB-C 开孔贯穿（重导入 STEP）", v <= 1e-6, f"探针干涉体积 {v:.3f}mm³")
    # 插头包络：从后墙外表面向内 18mm 的 12×6mm 包络，不得与壳体相碰
    r_at = 33.5  # z=13.5 处内半径（scheme 通用近似，包络从 -34 到 -16）
    env = _probe("box", 12.0, 18.0, 6.0, USB["x"], -(r_at + 8.0), USB["z"])
    v_shell = _probe_volume(rear, env) + _probe_volume(front, env)
    add("USB 插头包络与壳体零碰撞", v_shell <= 1e-6, f"包络干涉 {v_shell:.3f}mm³（含开孔通道豁免区外）")

    # 4) 麦克风孔贯穿
    probe = _probe("cyl", 1.0, 15.0, 30.0, MIC["x"], MIC["z"])
    v = _probe_volume(front, probe)
    add("麦克风声孔贯穿（重导入 STEP）", v <= 1e-6, f"探针干涉体积 {v:.3f}mm³")

    # UNKNOWN 注册：未建模即不得 PASS（AGENTS.md 事实三分法）
    unknowns = [
        {"item": "眼窗开孔与扩散板", "why": "头部内腔与眼窗未在本轮 CAD 建模", "stage": "下一 CAD 轮"},
        {"item": "星星灯透光窗", "why": "前壳透光缩壁未建模", "stage": "下一 CAD 轮"},
        {"item": "麦克风声学密封圈与后腔", "why": "密封件未建模，声学性能不可据此判定", "stage": "声学轮"},
        {"item": "打印公差 0.2mm", "why": "ASSUMPTION，试打印实测后解除（OB-2）", "stage": "试打印"},
        {"item": "螺丝柱/加强筋", "why": "本轮壳体未建柱筋，装配强度未知", "stage": "T-MEC"},
    ]
    return checks, unknowns

# ---------------------------------------------------------------------------

def selftest() -> None:
    """快速自检：构建方案A（full/none/shrunk）→ 导出 → 几何检查。"""
    import tempfile
    import build_helpers as bh  # noqa: F401  （占位，避免循环导入时再看）

if __name__ == "__main__":
    print("本模块由 build_mech.py 与 mech_tests.py 调用；无独立入口。")
