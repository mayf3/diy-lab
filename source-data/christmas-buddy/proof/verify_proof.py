#!/usr/bin/env python3
"""Lean 证明验证入口（复现 primitives verify_lean.py 的最小约定）。

流程：lake build → lake env lean Axioms.lean（公理审计）→ 写 verification.json。
公理白名单：propext, Classical.choice, Quot.sound；出现 sorryAx 即失败。

运行：python3 source-data/christmas-buddy/proof/verify_proof.py
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

WHITELIST = {"propext", "Classical.choice", "Quot.sound"}

def main() -> None:
    base = Path(__file__).parent
    receipt: dict = {"schema": "lean-verification/1.0", "product": "christmas-buddy-v1",
                     "date": date.today().isoformat(), "toolchain": None, "steps": []}

    toolchain = (base / "lean-toolchain").read_text().strip()
    receipt["toolchain"] = toolchain

    def run(cmd: list[str], label: str) -> tuple[int, str]:
        p = subprocess.run(cmd, cwd=base, capture_output=True, text=True, timeout=600)
        out = p.stdout + p.stderr
        receipt["steps"].append({"step": label, "cmd": " ".join(cmd), "rc": p.returncode})
        return p.returncode, out

    rc_build, _ = run(["lake", "build"], "lake build")
    rc_ax, ax_out = run(["lake", "env", "lean", "Axioms.lean"], "axiom audit")

    theorems = {}
    for m in re.finditer(r"'([^']+)' does not depend on any axioms", ax_out):
        theorems[m.group(1)] = []
    for m in re.finditer(r"'([^']+)' depends on axioms: \[([^\]]*)\]", ax_out):
        theorems[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]

    violations = []
    for thm, ax in theorems.items():
        for a in ax:
            if a not in WHITELIST:
                violations.append(f"{thm}: non-whitelisted axiom {a}")
    if "error" in ax_out.lower() and not theorems:
        violations.append("axiom audit produced no theorem entries")

    receipt["theorems"] = theorems
    receipt["axiom_whitelist"] = sorted(WHITELIST)
    receipt["violations"] = violations
    receipt["result"] = "PASS" if (rc_build == 0 and rc_ax == 0 and not violations) else "FAIL"

    (base / "verification.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    print(f"lean verification: {receipt['result']} — {len(theorems)} theorems, "
          f"{len(violations)} violations")
    for v in violations:
        print("  !", v)
    raise SystemExit(0 if receipt["result"] == "PASS" else 1)

if __name__ == "__main__":
    main()
