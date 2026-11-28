#!/usr/bin/env python3
"""Christmas Buddy 全链验证入口（依赖序；任一步 FAIL 即停止）。

用途：CAD/EDA/预算等任何工件修改后，一条命令重跑全部检查（§四：模型修改后自动重新运行检查）。
运行：python3 scripts/verify_all.py [christmas-buddy]
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
SLUG = sys.argv[1] if len(sys.argv) > 1 else "christmas-buddy"
B = ROOT / f"source-data/{SLUG}"
STEPS = [
    ("电源预算", [sys.executable, str(B/"power/power_budget.py")]),
    ("接口表", [sys.executable, str(B/"interfaces/interfaces.py")]),
    ("架构比较", [sys.executable, str(B/"architecture/architecture.py")]),
    ("机械+装配+几何开孔", [sys.executable, str(B/"mech/build_mech.py")]),
    ("机械负向", [sys.executable, str(B/"mech/mech_tests.py")]),
    ("测件正向", [sys.executable, str(B/"mech/coupon_verify.py")]),
    ("测件负向", [sys.executable, str(B/"mech/coupon_tests.py")]),
    ("网表 ERC", [sys.executable, str(B/"eda/netlist.py")]),
    ("网表负向", [sys.executable, str(B/"eda/netlist_tests.py")]),
    ("视觉约束", [sys.executable, str(B/"visual/visual_specs.py")]),
    ("任务书", [sys.executable, str(ROOT/"scripts/gen_eng_tasks.py"), SLUG, "v1"]),
    ("Lean+公理审计", [sys.executable, str(B/"proof/verify_proof.py")]),
    ("M5 重建候选1", [sys.executable, str(B/"m5_manifest.py"), "build"]),
    ("Lean 复验", [sys.executable, str(B/"proof/verify_proof.py")]),
    ("M5 重建候选2（收敛）", [sys.executable, str(B/"m5_manifest.py"), "build"]),
    ("M5 manifest check", [sys.executable, str(B/"m5_manifest.py"), "check"]),
    ("M5 对抗矩阵", [sys.executable, str(B/"manifest_adversarial_tests.py")]),
    ("站点 check.py", [sys.executable, str(ROOT/"scripts/check.py")]),
]
rc = 0
for name, cmd in STEPS:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    tail = (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]
    print(f"[{'PASS' if p.returncode == 0 else 'FAIL'}] {name}: {tail[0][:100]}")
    if p.returncode != 0:
        rc = 1
        break
sys.exit(rc)
