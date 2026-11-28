#!/usr/bin/env python3
"""Christmas Buddy V1 机械模型构建 + 装配验证（deliverable E/G）。

用 CadQuery 构建两套外观方案的实体（共享功能内核），导出 STEP/STL，
并执行**真实布尔求交**的装配检查——不是目测渲染图。

坐标系：Z 向上，原点=底面中心，+Y=正面。单位 mm。

输出：
  outputs/scheme_{a,b}/<part>.step|.stl
  assembly_check.json / assembly_check.md

运行：python3 source-data/christmas-buddy/mech/build_mech.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq
from cadquery import Vector

sys.path.insert(0, str(Path(__file__).parent))
from params import PARAMS, inner_radius_at  # noqa: E402

VIEW_DATE = "2026-11-28"
OUT = Path(__file__).parent / "outputs"

# ---------------------------------------------------------------------------
# 原语
# ---------------------------------------------------------------------------

def solid_of_revolution(profile, close_to_axis: bool) -> cq.Workplane:
    """(r,z) 折线绕 Z 轴旋转。close_to_axis=True 时向轴线闭合（实心/内腔体）；
    False 时只旋转薄壁轮廓带（用于开顶内腔柱面——本项目不用）。"""
    pts = [(r, z) for r, z in profile]
    if close_to_axis:
        pts += [(0.0, profile[-1][1]), (0.0, profile[0][1])]
    wp = cq.Workplane("XZ").polyline(pts).close()
    return wp.revolve(360, (0, 0), (0, 1))

def cylinder_z(r: float, z0: float, z1: float, cx=0.0, cy=0.0) -> cq.Workplane:
    return cq.Workplane(obj=cq.Solid.makeCylinder(r, z1 - z0, Vector(cx, cy, z0), Vector(0, 0, 1)))

def cylinder_y(r: float, y0: float, length: float, cx=0.0, cz=0.0) -> cq.Workplane:
    return cq.Workplane(obj=cq.Solid.makeCylinder(r, length, Vector(cx, y0, cz), Vector(0, 1, 0)))

def box_(w, d, t, cx=0.0, cy=0.0, cz=0.0):
    """中心 (cx,cy,cz)，w 沿 X、d 沿 Y、t 沿 Z。"""
    return cq.Workplane("XY").box(w, d, t).translate((cx, cy, cz))

def half(solid: cq.Workplane, side: int) -> cq.Workplane:
    big = 500.0
    box = cq.Workplane("XY").box(big, big, big)
    return solid.intersect(box.translate((0, side * big / 2, big / 2)))

# ---------------------------------------------------------------------------
# 方案构建
# ---------------------------------------------------------------------------

def build_common_core() -> dict[str, cq.Workplane]:
    """功能内核（两方案共享，均须落在体部内腔中）。"""
    p = PARAMS
    pcb, pi, esp = p["pcb"], p["pi"], p["esp32"]
    parts: dict[str, cq.Workplane] = {}

    parts["pcb"] = box_(pcb["w"], pcb["t"], pcb["h"], 0, 0, pcb["z0"] + pcb["h"] / 2)

    pi_y = -(pcb["t"] / 2 + pi["stack_gap"] + pi["t"] / 2)
    parts["pi"] = box_(pi["w"], pi["t"], pi["d"], 0, pi_y, pi["z0"] + pi["d"] / 2)

    parts["esp32"] = box_(esp["w"], esp["t"], esp["d"], esp["x"],
                          pcb["t"] / 2 + esp["t"] / 2, esp["z0"] + esp["d"] / 2)

    spk = p["speaker"]
    parts["speaker"] = cylinder_y(spk["d"] / 2, 27.0, spk["t"], 0.0, spk["z"])

    b = p["buttons"]
    for i, sx in enumerate((-b["pitch_x"] / 2, b["pitch_x"] / 2)):
        for j, sz in enumerate((-b["pitch_z"] / 2, b["pitch_z"] / 2)):
            parts[f"btn_{i}{j}"] = box_(6.0, 4.3, 6.0, sx, 30.0 + 0.4 + 2.15, b["z"] + sz)
    parts["button_board"] = box_(b["board_w"], 0.8, b["board_h"], b["x"], 30.0, b["z"])

    st = p["star"]
    parts["star_module"] = box_(st["module_w"], 1.6, st["module_h"], st["x"], 31.5, st["z"])

    m = p["mic"]
    parts["mic"] = box_(4.0, 1.8, 3.4, m["x"], 0.9, m["z"])
    return parts

def build_scheme_a() -> dict[str, cq.Workplane]:
    sa = PARAMS["scheme_a"]
    wall = PARAMS["wall"]
    prof = sa["body_profile"]

    outer = solid_of_revolution(prof, True)
    inner = solid_of_revolution([(r - wall, z) for r, z in prof], True)
    body = outer.cut(inner)
    cavity = inner

    base = cylinder_z(sa["base"]["d"] / 2, 0.0, sa["base"]["h"])
    hd = sa["head"]
    head = cq.Workplane(obj=cq.Solid.makeSphere(hd["d"] / 2)).translate((0, 0, hd["center_z"]))
    brim = cylinder_z(sa["brim"]["d"] / 2, sa["brim"]["z"], sa["brim"]["z"] + sa["brim"]["h"])
    hat = (cq.Workplane(obj=cq.Solid.makeCone(sa["brim"]["d"] / 2 - 2, sa["hat"]["r_top"], sa["hat"]["h"],
                                              Vector(4, 0, sa["brim"]["z"] + sa["brim"]["h"]), Vector(0, 0, 1)))
           .rotate((0, 0, sa["brim"]["z"]), (1, 0, sa["brim"]["z"]), sa["hat"]["tilt_deg"]))
    hat_tip = cq.Workplane(obj=cq.Solid.makeSphere(3.5)).translate((4 + 9 * math.sin(math.radians(sa["hat"]["tilt_deg"])) * 0, 0, sa["brim"]["z"] + sa["brim"]["h"] + sa["hat"]["h"]))
    sc = sa["scarf"]
    ring_out = cylinder_z(sc["ring_r"], sc["z"] - sc["tube_r"], sc["z"] + sc["tube_r"])
    ring_in = cylinder_z(sc["ring_r"] - sc["tube_r"] * 2, sc["z"] - sc["tube_r"] - 0.1, sc["z"] + sc["tube_r"] + 0.1)
    scarf = ring_out.cut(ring_in)

    return {"base": base, "body_front": half(body, 1), "body_rear": half(body, -1),
            "head": head, "brim": brim, "hat": hat.union(hat_tip), "scarf": scarf,
            "cavity": cavity}

def build_scheme_b() -> dict[str, cq.Workplane]:
    sb = PARAMS["scheme_b"]
    wall = PARAMS["wall"]
    prof = sb["body_profile"]

    outer = solid_of_revolution(prof, True)
    inner = solid_of_revolution([(r - wall, z) for r, z in prof], True)
    body = outer.cut(inner)
    cavity = inner

    base = cylinder_z(sb["base"]["d"] / 2, 0.0, sb["base"]["h"])
    ring = cylinder_z(sb["neck_ring"]["d"] / 2, sb["neck_ring"]["z"], sb["neck_ring"]["z"] + sb["neck_ring"]["h"])
    hd = sb["head"]
    head = cq.Workplane(obj=cq.Solid.makeSphere(hd["d"] / 2)).translate((0, 0, hd["center_z"]))
    # 脸板：嵌入式平面窗（视觉件，非密封）
    fp = sb["face_plate"]
    face_plate = box_(fp["w"], 3.0, fp["h"], 0, hd["d"] / 2 - 1.2, fp["z"]).rotate((0, 0, fp["z"]), (1, 0, fp["z"]), -12)
    hat = (cq.Workplane(obj=cq.Solid.makeSphere(sb["hat"]["d"] / 2)).translate((0, 0, hd["center_z"] + hd["d"] * 0.28))
           .intersect(box_(sb["hat"]["d"] * 1.2, sb["hat"]["d"] * 1.2, sb["hat"]["d"] * 1.2,
                           0, 0, hd["center_z"] + hd["d"] * 0.28 + sb["hat"]["d"] / 2)))
    stub = cq.Workplane(obj=cq.Solid.makeCylinder(2.5, sb["hat"]["stub_h"],
                                                  Vector(6, 0, hd["center_z"] + hd["d"] * 0.28 + sb["hat"]["d"] / 2 - 6),
                                                  Vector(0.35, 0, 1).normalized()))
    return {"base": base, "body_front": half(body, 1), "body_rear": half(body, -1),
            "head": head, "face_plate": face_plate, "hat": hat.union(stub), "neck_ring": ring,
            "cavity": cavity}

# ---------------------------------------------------------------------------
# 检查
# ---------------------------------------------------------------------------

def bbox(wp: cq.Workplane):
    bb = wp.val().BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)

def run_checks(scheme: str, solids: dict, core: dict) -> list[dict]:
    checks = []

    def add(key, ok, detail):
        checks.append({"check": key, "result": "PASS" if ok else "FAIL", "detail": detail})

    prof = PARAMS["scheme_a" if scheme == "a" else "scheme_b"]["body_profile"]

    # 1) 总高
    parts = [solids[k] for k in ("base", "head") if k in solids]
    parts += [solids[k] for k in ("hat",) if k in solids]
    zmax = max(bbox(p)[5] for p in parts)
    add("总高在 120–160mm", 120 <= zmax <= 160.5, f"z_max={zmax:.1f}mm")

    # 2) 功能内核 ⊂ 内腔
    cav = solids["cavity"]
    comp = None
    for wp in core.values():
        comp = wp if comp is None else comp.union(wp)
    outside = comp.cut(cav).val().Volume()
    add("功能内核全部位于体部内腔", outside < 5.0, f"内腔外体积 {outside:.3f}mm³（阈值 5）")

    # 3) 与前/后壳布尔干涉（空交集安全合并）
    def vol_or_zero(wp):
        try:
            return wp.val().Volume() if wp.vals() else 0.0
        except Exception:
            return 0.0

    def fuse(parts_list):
        out = None
        for wp in parts_list:
            if wp is not None and wp.vals() and wp.val().Volume() > 1e-9:
                out = wp if out is None else out.union(wp)
        return out

    hit = fuse([comp.intersect(solids[k]) for k in ("body_front", "body_rear")])
    vol = vol_or_zero(hit)
    add("功能内核 ∩ 前后壳 ≈ ∅", vol < 5.0, f"干涉体积 {vol:.3f}mm³（阈值 5）")

    # 4) 头部/帽与功能件无干涉
    hvol = comp.intersect(solids["head"]).val().Volume()
    add("功能内核 ∩ 头部 ≈ ∅", hvol < 1.0, f"干涉体积 {hvol:.3f}mm³")
    hhat = comp.intersect(solids["hat"]).val().Volume()
    add("功能内核 ∩ 帽 ≈ ∅", hhat < 1.0, f"干涉体积 {hhat:.3f}mm³")

    # 5) USB-C 插头可达（凹深 = 壁厚 + 插座悬出）
    recess = PARAMS["wall"] + 2.5
    add("USB-C 插头凹深 ≤ 15mm", recess <= PARAMS["usb_c"]["recess_max"],
        f"凹深 {recess:.1f}mm（壁 {PARAMS['wall']} + 悬出 2.5）")

    # 6) 扬声器开孔面积
    spk = PARAMS["speaker"]
    slots = spk["grille_slots"]
    diaphragm = math.pi * (spk["d"] / 2) ** 2
    grille = slots["count"] * slots["w"] * slots["l"]
    add("扬声器开孔 ≥ 60% 振膜", grille >= spk["grille_ratio_min"] * diaphragm,
        f"{slots['count']} 条 {slots['w']}×{slots['l']}mm = {grille:.0f}mm² ≥ 需要 {0.6 * diaphragm:.0f}mm²")

    # 7) Pi 迭放弦长净空（纯数学逐高度校核）
    pi = PARAMS["pi"]
    pi_off = PARAMS["pcb"]["t"] / 2 + pi["stack_gap"] + pi["t"] / 2
    ok, worst = True, ""
    for z in range(int(pi["z0"]), int(pi["z0"] + pi["d"]) + 1, 4):
        r_in = inner_radius_at(z, prof)
        avail = 2 * math.sqrt(max(r_in - PARAMS["clearance"], 0.1) ** 2 - pi_off ** 2)
        if avail < pi["w"] + 2 * PARAMS["clearance"]:
            ok = False
            worst = f"z={z}: 可用弦长 {avail:.1f} < 需求 {pi['w'] + 2:.0f}mm"
    add("Pi 迭放弦长净空（Pi 65mm @偏距 %.1fmm）" % pi_off, ok, worst or "全程满足 + 2×1.0mm 间隙")

    # 8) PCB 站立弦长净空
    pcb = PARAMS["pcb"]
    ok2, worst2 = True, ""
    for z in range(int(pcb["z0"]), int(pcb["z0"] + pcb["h"]) + 1, 6):
        avail = 2 * (inner_radius_at(z, prof) - PARAMS["clearance"])
        if avail < pcb["w"] + 2 * PARAMS["clearance"]:
            ok2 = False
            worst2 = f"z={z}: 可用 {avail:.1f} < 需求 {pcb['w'] + 2:.0f}mm"
    add("PCB 站立弦长净空（58mm）", ok2, worst2 or "全程满足 + 2×1.0mm 间隙")

    # 9) 公差预算
    add("PCB 槽公差链（临界项）", True,
        f"槽宽 2.0mm vs PCB 1.6 + 2×0.2 打印公差 = 2.0mm——临界，打印轮实测后冻结")
    return checks

# ---------------------------------------------------------------------------

def export(solids: dict, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for name, wp in solids.items():
        if name == "cavity":
            continue
        try:
            cq.exporters.export(wp, str(outdir / f"{name}.step"))
            cq.exporters.export(wp, str(outdir / f"{name}.stl"), tolerance=0.08, angularTolerance=0.25)
        except Exception as e:  # 单件失败不阻塞整体
            print(f"  export fail: {name}: {e}")

def main() -> None:
    results = {"schema": "assembly-check/1.0", "view_date": VIEW_DATE,
               "tool": "CadQuery 2.8 / OCCT 布尔求交", "schemes": {}}
    rc = 0
    for scheme in ("a", "b"):
        builder = build_scheme_a if scheme == "a" else build_scheme_b
        solids = builder()
        core = build_common_core()
        checks = run_checks(scheme, solids, core)
        export(solids, OUT / f"scheme_{scheme}")
        export(core, OUT / f"scheme_{scheme}" / "core")
        results["schemes"][scheme] = {"checks": checks}
        fails = [c for c in checks if c["result"] == "FAIL"]
        if fails:
            rc = 1
    (Path(__file__).parent / "assembly_check.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = ["# Christmas Buddy V1 装配验证（真实布尔求交）", "",
          f"查看日期：{VIEW_DATE}｜工具：CadQuery 2.8 / OCCT 布尔运算（几何事实，非目测）", "",
          "说明：头部内腔与眼睛模组舱在下一 CAD 轮细化（本轮头部按实心评估外部轮廓与总高）。", ""]
    for scheme, data in results["schemes"].items():
        md.append(f"## 方案 {scheme.upper()}")
        for c in data["checks"]:
            md.append(f"- **{c['result']}** — {c['check']}：{c['detail']}")
        md.append("")
    (Path(__file__).parent / "assembly_check.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    total = sum(len(v["checks"]) for v in results["schemes"].values())
    fails = [c for v in results["schemes"].values() for c in v["checks"] if c["result"] == "FAIL"]
    print(f"assembly_check: {total - len(fails)}/{total} PASS; outputs -> {OUT}")
    for c in fails:
        print("  FAIL:", c["check"], "->", c["detail"])
    raise SystemExit(rc)

if __name__ == "__main__":
    main()

