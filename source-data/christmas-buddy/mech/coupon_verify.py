#!/usr/bin/env python3
"""测件几何验证器（Batch3 P0-1/P0-2）：在**导出 STEP 重导入**上验证测件真实几何。

检查规则（每条都有负向案例，见 coupon_tests.py）：
  R1 实体连通性：重导入后恰为 1 个 solid（断裂=FAIL）
  R2 C1 槽位存在且在界：标称位置的槽针（宽-0.3）沿深度方向可穿过槽腔
  R3 C1 底板完整：底板中心探针（跨整块底面）必须撞到材料（=底板未被切穿）
  R4 C2 孔贯穿：标称孔位上、直径-0.2 的销针从顶贯穿到底（体积 0）
  R5 C2 孔径上限：直径+0.5 的过量规不得通过（孔未超差）
  R6 C3 开孔贯穿：插头包络 12×6 探针贯穿壁体

六层证据分级（不得混用）：参数 → CAD 构造 → STEP 几何（本文件）→ STL → 切片 → 实物。

运行：python3 source-data/christmas-buddy/mech/coupon_verify.py [--variant C1|C1-through|C1-outside|C2|C2-blind|C2-shrunk|C2-missing|C3|C3-shrunk]
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import cadquery as cq
from cadquery import Vector

sys.path.insert(0, str(Path(__file__).parent))
import gen_print_coupons as GC  # noqa: E402

def reimport_volume(part: cq.Workplane, probe: cq.Shape) -> float:
    """探针与重导入实体的交集体积；OCCT 空结果异常按「异常不静默」上抛策略处理：
    这里显式区分——Empty结果(0)才是合法的「无材料」。"""
    if isinstance(probe, cq.Workplane):
        probe = probe.val()
    inter = part.intersect(cq.Workplane(obj=probe))
    return inter.val().Volume() if inter.vals() else 0.0

def solid_count(wp: cq.Workplane) -> int:
    return len(wp.solids().vals())

def verify_c1(wp: cq.Workplane) -> list[dict]:
    checks = []
    def add(key, ok, detail):
        checks.append({"check": key, "result": "PASS" if ok else "FAIL", "detail": detail,
                       "basis": "STEP-geometry(coupon)"})
    n = solid_count(wp)
    add("R1 连通性（1 solid）", n == 1, f"solids={n}")
    bh = GC.C1["block"][2]
    for (x, w) in GC.C1_SLOTS:
        pin = cq.Solid.makeBox(w - 0.3, GC.C1["slot_len"] - 1, GC.C1["slot_depth"] + 3,
                               Vector(x - (w - 0.3) / 2, -(GC.C1["slot_len"] - 1) / 2,
                                      bh - GC.C1["slot_depth"]))
        v = reimport_volume(wp, pin)
        add(f"R2 槽位存在 x={x} w={w}", v <= 1e-6, f"槽针干涉 {v:.3f}mm³")
    # R3（Batch4 P0-2）：按每槽实际宽度逐槽计算三维体积期望（含 10% 测量容差）。
    # 审查反例：最宽槽期望 107.1mm³，旧统一阈值 45.9mm³ 会让半切底板误 PASS。
    floor_ok = True
    bad = []
    for (x, w) in GC.C1_SLOTS:
        probe_w = w - 0.3
        probe_len = GC.C1["slot_len"] - 1
        probe_h = GC.C1["floor"] - 0.6
        nominal = probe_w * probe_len * probe_h          # 期望体积 = 探针几何体积
        probe = cq.Solid.makeBox(probe_w, probe_len, probe_h,
                                 Vector(x - probe_w / 2, -probe_len / 2, 0.3))
        v = reimport_volume(wp, probe)
        if v < nominal * 0.9 or v > nominal * 1.02:
            floor_ok = False
            bad.append(f"x={x}(w={w}): {v:.1f} vs 期望 {nominal:.1f}mm³")
    add("R3 底板完整（逐槽位三维体积，按槽宽独立阈值）", floor_ok,
        "每槽底板体积=探针体积（全实心）" if floor_ok else f"底板异常：{bad[:3]}")
    return checks

def verify_c2(wp: cq.Workplane) -> list[dict]:
    checks = []
    def add(key, ok, detail):
        checks.append({"check": key, "result": "PASS" if ok else "FAIL", "detail": detail,
                       "basis": "STEP-geometry(coupon)"})
    n = solid_count(wp)
    add("R1 连通性（1 solid）", n == 1, f"solids={n}")
    bh = GC.C2["block"][2]
    for (x, d) in GC.C2_HOLES:
        pin = cq.Solid.makeCylinder(d / 2 - 0.1, bh + 4, Vector(x, 0, -2), Vector(0, 0, 1))
        v = reimport_volume(wp, pin)
        add(f"R4 孔贯穿 x={x} Ø{d}（销针通过）", v <= 1e-6, f"销针干涉 {v:.3f}mm³")
        gauge = cq.Solid.makeCylinder(d / 2 + 0.25, bh + 4, Vector(x, 0, -2), Vector(0, 0, 1))
        v2 = reimport_volume(wp, gauge)
        add(f"R5 孔径未超差 x={x} Ø{d}（+0.5 量规受阻）", v2 > 1e-6, f"量规受阻体积 {v2:.3f}mm³")
    return checks

def verify_c3(wp: cq.Workplane) -> list[dict]:
    checks = []
    def add(key, ok, detail):
        checks.append({"check": key, "result": "PASS" if ok else "FAIL", "detail": detail,
                       "basis": "STEP-geometry(coupon)"})
    n = solid_count(wp)
    add("R1 连通性（1 solid）", n == 1, f"solids={n}")
    # 封闭孔验证：孔中心 z=0，四周保留实体
    plug = cq.Solid.makeBox(12.0, 20.0, 6.0, Vector(-6.0, -10.0, -3.0))
    v = reimport_volume(wp, plug)
    add("R6 插头包络贯穿（12×6 通过封闭孔）", v <= 1e-6, f"包络干涉 {v:.3f}mm³")
    # R7 孔四周实体保留：孔中心上下各偏移 ±(oh/2+1.5) 的探针必须撞到材料
    oh = GC.C3["opening"][1]
    for tag, dz in (("孔上方", oh / 2 + 1.5), ("孔下方", -(oh / 2 + 1.5))):
        guard = cq.Solid.makeBox(12.0, 20.0, 1.0, Vector(-6.0, -10.0, dz - 0.5))
        v2 = reimport_volume(wp, guard)
        nominal = 12.0 * GC.C3["block"][1] * 1.0      # 12×壁厚×1mm 探针全实心
        add(f"R7 孔{tag}实体保留（封闭孔，非缺口）", v2 >= nominal * 0.9,
            f"实体 {v2:.1f}mm³ ≥ 期望 {nominal:.1f}mm³")
    return checks

# ---- 正向链：构建 → 导出 STEP → 重导入 → 验证 ----

def build_export_reimport(builder, variant: str, tag: str) -> cq.Workplane:
    tmp = Path(tempfile.mkdtemp(prefix=f"cbu_coupon_{tag}_"))
    wp = builder(variant)
    cq.exporters.export(wp, str(tmp / "coupon.step"))
    out = cq.importers.importStep(str(tmp / "coupon.step"))
    return out

def main() -> None:
    ok = True
    print("=== 测件正向验证（导出 STEP 重导入）===")
    for name, builder, verifier in (("C1", GC.coupon_c1, verify_c1),
                                    ("C2", GC.coupon_c2, verify_c2),
                                    ("C3", GC.coupon_c3, verify_c3)):
        wp = build_export_reimport(builder, "full", name)
        checks = verifier(wp)
        fails = [c for c in checks if c["result"] == "FAIL"]
        print(f"  {name}: {len(checks)-len(fails)}/{len(checks)} PASS")
        for c in fails:
            print("    FAIL:", c["check"], "->", c["detail"])
        ok = ok and not fails
    print("结果:", "ALL PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
