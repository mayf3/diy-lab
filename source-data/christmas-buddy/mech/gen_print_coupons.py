#!/usr/bin/env python3
"""试打印测件生成器（§六：几何检查不能替代打印验证）。

生成 3 个公差试件（打印+测量由人执行，Agent 不替代实物验证）：
  C1 PCB 槽公差梯：槽宽 1.8/2.0/2.2/2.4mm（PCB 名义 1.6mm + 公差余量）
  C2 孔径阶梯：Ø2.0/2.2/2.4/2.6mm（自攻螺钉/声孔/定位销）
  C3 USB-C 插头试件：开孔 13.4×7.4 + 插入深度台阶（对应后壳开孔）

输出：mech/outputs/print-coupon/*.stl + measurement-record.csv（测量记录表）
打印参数建议：P1S 0.4 喷嘴，0.2mm 层高，4 壁圈，±45° 交叉填充。
0.2mm 公差保持 ASSUMPTION（OB-2）：实测前不得改标 VERIFIED。

运行：python3 source-data/christmas-buddy/mech/gen_print_coupons.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import cadquery as cq
from cadquery import Vector

OUT = Path(__file__).parent / "outputs/print-coupon"

# C1/C2/C3 修复（Batch3 审查）：槽位全部位于块内、保留 4mm 连续底板、孔真正贯穿。
C1_SLOTS = [(x, w) for x, w in zip((-21.0, -7.0, 7.0, 21.0), (1.8, 2.0, 2.2, 2.4))]
C1 = {"block": (60.0, 24.0, 10.0), "slot_len": 16.0, "slot_depth": 6.0, "floor": 4.0}
C2_HOLES = [(x, d) for x, d in zip((-15.0, -5.0, 5.0, 15.0), (2.0, 2.2, 2.4, 2.6))]
C2 = {"block": (40.0, 12.0, 3.0)}
C3 = {"block": (30.0, 2.8, 16.0), "opening": (13.4, 7.4)}

def coupon_c1(mode: str = "full") -> cq.Workplane:
    """PCB 槽公差梯：4 槽全部在块内，槽深 6mm（不切穿 4mm 底板）。mode 供负向测试。"""
    bw, bd, bh = C1["block"]
    wp = cq.Workplane("XY").box(bw, bd, bh).translate((0, 0, bh / 2))   # z 0..10
    for i, (x, w) in enumerate(C1_SLOTS):
        xx = x
        if mode == "outside":            # 负向：第一槽移出边界
            xx = x + (bw / 2 + 10 if i == 0 else 0)
        depth = C1["slot_depth"] if mode != "through" else bh + 2   # 负向：切穿
        length = C1["slot_len"] if mode != "oversize_len" else bd + 20
        slot = cq.Workplane("XY").box(w, length, depth).translate(
            (xx, 0, bh - depth / 2))                                   # 顶部开槽 depth=6，底板 4mm 完整
        wp = wp.cut(slot)
    return wp

def coupon_c2(mode: str = "full") -> cq.Workplane:
    """孔径阶梯：4 通孔，切割体越出实体两端保证贯穿。"""
    bw, bd, bh = C2["block"]
    wp = cq.Workplane("XY").box(bw, bd, bh).translate((0, 0, bh / 2))   # z 0..3
    holes = C2_HOLES if mode != "missing" else C2_HOLES[:3]
    for i, (x, d) in enumerate(holes):
        dd = d if mode != "shrunk" else d * 0.55
        z0 = -1.5 if mode != "blind" else bh - 1.0   # 全程低于块底=真贯穿；盲孔从顶刻 1mm
        depth = bh + 3.0 if mode != "blind" else 1.0
        hole = cq.Solid.makeCylinder(dd / 2, depth, Vector(x, 0, z0), Vector(0, 0, 1))
        wp = wp.cut(cq.Workplane(obj=hole))
    return wp

def coupon_c3(mode: str = "full") -> cq.Workplane:
    """USB-C 开孔试件：13.4×7.4 径向通孔（壁 2.8mm）。"""
    bw, bt, bh = C3["block"]
    ow, oh = C3["opening"]
    wall = cq.Workplane("XY").box(bw, bt, bh)
    hole = cq.Workplane("XY").box(ow, 40, oh).translate((0, 0, bh / 2))
    wp = wall.cut(hole)
    if mode == "shrunk":
        hole2 = cq.Workplane("XY").box(ow - 4, 40, oh - 2).translate((0, 0, bh / 2))
        wp = cq.Workplane("XY").box(bw, bt, bh).cut(hole2)
    return wp

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, wp in (("C1-pcb-slot", coupon_c1()),
                     ("C2-hole-gauge", coupon_c2()),
                     ("C3-usb-opening", coupon_c3())):
        cq.exporters.export(wp, str(OUT / f"{name}.stl"), tolerance=0.05, angularTolerance=0.2)
        cq.exporters.export(wp, str(OUT / f"{name}.step"))
    rows = [
        ["试件", "特征", "CAD 标称(mm)", "切片尺寸(mm)", "实物测量(mm)", "误差(mm)", "装配结果", "测量人/日期"],
        ["C1-pcb-slot", "槽1", "1.80", "", "", "", "", ""],
        ["C1-pcb-slot", "槽2", "2.00", "", "", "", "", ""],
        ["C1-pcb-slot", "槽3", "2.20", "", "", "", "", ""],
        ["C1-pcb-slot", "槽4", "2.40", "", "", "", "", ""],
        ["C2-hole-gauge", "孔1", "2.00", "", "", "", "", ""],
        ["C2-hole-gauge", "孔2", "2.20", "", "", "", "", ""],
        ["C2-hole-gauge", "孔3", "2.40", "", "", "", "", ""],
        ["C2-hole-gauge", "孔4", "2.60", "", "", "", "", ""],
        ["C3-usb-opening", "开孔宽", "13.40", "", "", "", "", ""],
        ["C3-usb-opening", "开孔高", "7.40", "", "", "", "", ""],
        ["C3-usb-opening", "USB-C 插头插入", "通过/不通过", "", "", "", "", ""],
    ]
    with open(OUT / "measurement-record.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    (OUT / "README.md").write_text(
        "# 试打印测件（T-MEC 试打印任务的输入）\n\n"
        "- 人执行：打印 3 件 → 卡尺测量 → 填 measurement-record.csv → 回填 params.py 的"
        " print_tolerance_xy（当前 0.2 = ASSUMPTION，实测后才能改，OB-2 义务）。\n"
        "- 验收：至少一个槽宽档位能无应力插入 1.6mm PCB 片；USB-C 插头能插入 C3。\n"
        "- 未测量前：装配检查中的公差结论保持「临界，打印轮实测后冻结」表述，禁止改标 PASS/VERIFIED。\n",
        encoding="utf-8")
    print(f"print coupons: 3 STL/STEP + measurement-record.csv -> {OUT}")

if __name__ == "__main__":
    main()
