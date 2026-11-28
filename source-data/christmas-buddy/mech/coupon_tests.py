#!/usr/bin/env python3
"""测件几何验证器负向测试（Batch3 P0-1/P0-2 要求）：

C1: 槽移出边界 → R2 FAIL；槽切穿底板 → R3 FAIL
C2: 盲孔 → R4 FAIL；孔径缩小 → R4 FAIL；删孔 → R4 FAIL
C3: 开孔缩窄 → R6 FAIL

运行：python3 source-data/christmas-buddy/mech/coupon_tests.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import coupon_verify as CV     # noqa: E402
import gen_print_coupons as GC  # noqa: E402

def run(builder, variant, verifier, expect_key, expect_result="FAIL"):
    wp = CV.build_export_reimport(builder, variant, f"neg_{variant}")
    checks = verifier(wp)
    c = next((c for c in checks if expect_key in c["check"]), None)
    if c is None:
        return False, "规则未输出"
    return c["result"] == expect_result, f"{c['check']} → {c['result']}（{c['detail'][:50]}）"

def main() -> None:
    ok = True
    print("=== 测件负向测试 ===")
    cases = [
        ("C1 槽移出边界 → R2 FAIL", GC.coupon_c1, "outside", CV.verify_c1, "R2 槽位存在 x=-21"),
        ("C1 槽切穿底板 → R3 FAIL", GC.coupon_c1, "through", CV.verify_c1, "R3 底板完整"),
        ("C2 盲孔 → R4 FAIL", GC.coupon_c2, "blind", CV.verify_c2, "R4 孔贯穿 x=-15"),
        ("C2 孔径缩小 → R4 FAIL", GC.coupon_c2, "shrunk", CV.verify_c2, "R4 孔贯穿 x=-15"),
        ("C2 删除一孔 → R4 FAIL（量规不受阻即无孔）", GC.coupon_c2, "missing", CV.verify_c2, "R4 孔贯穿 x=15"),
        ("C3 开孔缩窄 → R6 FAIL", GC.coupon_c3, "shrunk", CV.verify_c3, "R6 插头包络"),
    ]
    for name, builder, variant, verifier, key in cases:
        passed, detail = run(builder, variant, verifier, key)
        print(f"  [{'PASS' if passed else 'FAIL'}] {name} — {detail}")
        ok = ok and passed
    print("\n结果:", "ALL PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
