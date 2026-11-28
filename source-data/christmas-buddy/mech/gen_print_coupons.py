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

def coupon_c1() -> cq.Workplane:
    """PCB 槽公差梯：4 槽，槽宽递增，深 6mm，板厚 4mm。"""
    wp = cq.Workplane("XY").box(60, 12, 4)
    for i, w in enumerate((1.8, 2.0, 2.2, 2.4)):
        slot = cq.Workplane("XY").box(w, 30, 8).translate((10 + i * 12, 0, 2))
        wp = wp.cut(slot)
    return wp.translate((0, 0, 2))

def coupon_c2() -> cq.Workplane:
    """孔径阶梯：4 通孔。"""
    wp = cq.Workplane("XY").box(40, 12, 3)
    for i, d in enumerate((2.0, 2.2, 2.4, 2.6)):
        hole = cq.Solid.makeCylinder(d / 2, 10, Vector(-15 + i * 10, 0, -1), Vector(0, 0, 1))
        wp = wp.cut(cq.Workplane(obj=hole))
    return wp.translate((0, 0, 1.5))

def coupon_c3() -> cq.Workplane:
    """USB-C 开孔试件：13.4×7.4 通孔 + 壁厚 2.8mm（与外壳一致）。"""
    wall = cq.Workplane("XY").box(30, 2.8, 16)
    hole = cq.Workplane("XY").box(13.4, 40, 7.4).translate((0, 0, 4))
    return wall.cut(hole).translate((0, -1.4, 0))

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
