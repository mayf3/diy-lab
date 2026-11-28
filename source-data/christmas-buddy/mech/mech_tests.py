#!/usr/bin/env python3
"""CAD 几何检查负向测试（P0-4 要求）：

- 删除扬声器格栅开孔 → 格栅贯穿/面积检查必须 FAIL
- 删除 USB-C 开孔 → USB 贯穿检查必须 FAIL
- 格栅缩窄（1.0mm）→ 贯穿检查必须 FAIL（2.2mm 探针无法通过）

证明检查器验证的是**导出 STEP 的真实几何**，不是设计参数的自说自话。

运行：python3 source-data/christmas-buddy/mech/mech_tests.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import cadquery as cq

sys.path.insert(0, str(Path(__file__).parent))
import build_mech as BM      # noqa: E402
from openings import geometry_checks  # noqa: E402

def run_variant(mode: str, tag: str) -> list[dict]:
    out = Path(tempfile.mkdtemp(prefix=f"cbu_neg_{tag}_"))
    solids = BM.build_scheme_a(mode=mode)
    BM.export(solids, out)
    checks, _unknowns = geometry_checks("a", out)
    shutil.rmtree(out, ignore_errors=True)
    return checks

def get(checks, key):
    return next((c for c in checks if key in c["check"]), None)

def main() -> None:
    ok = True
    print("=== CAD 几何检查负向测试（方案 A 变体）===")

    full = run_variant("full", "full")
    c = get(full, "格栅 16 槽全部贯穿")
    print(f"  [{'PASS' if c and c['result'] == 'PASS' else 'FAIL'}] 正常模型：格栅贯穿 PASS")
    ok = ok and c is not None and c["result"] == "PASS"

    none_checks = run_variant("none", "none")
    c1 = get(none_checks, "格栅 16 槽全部贯穿")
    c2 = get(none_checks, "USB-C 开孔贯穿")
    ok1 = c1 is not None and c1["result"] == "FAIL"
    ok2 = c2 is not None and c2["result"] == "FAIL"
    print(f"  [{'PASS' if ok1 else 'FAIL'}] 删除格栅 → 格栅贯穿 FAIL（{c1['detail'][:60] if c1 else '无输出'}）")
    print(f"  [{'PASS' if ok2 else 'FAIL'}] 删除 USB 开孔 → USB 贯穿 FAIL（{c2['detail'][:60] if c2 else '无输出'}）")
    ok = ok and ok1 and ok2

    shrunk = run_variant("shrunk", "shrunk")
    c3 = get(shrunk, "格栅 16 槽全部贯穿")
    ok3 = c3 is not None and c3["result"] == "FAIL"
    print(f"  [{'PASS' if ok3 else 'FAIL'}] 格栅缩窄 1.0mm → 贯穿 FAIL（{c3['detail'][:60] if c3 else '无输出'}）")
    ok = ok and ok3

    # UNKNOWN 注册必须存在（未建模项不得冒充 PASS）
    import json
    ac = json.loads((Path(__file__).parent / "assembly_check.json").read_text(encoding="utf-8"))
    unknowns = ac["schemes"]["a"].get("unknowns", [])
    ok4 = len(unknowns) >= 5
    print(f"  [{'PASS' if ok4 else 'FAIL'}] UNKNOWN 注册表存在（{len(unknowns)} 项未建模功能如实登记）")
    ok = ok and ok4

    print("\n结果:", "ALL PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
