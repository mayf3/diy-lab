#!/usr/bin/env python3
"""M5 制造模型 · 设计→工件哈希追溯（TESTED 层证据，非 Lean 证明范围）。

记录 Christmas Buddy 全部设计工件的 sha256 与版本四元组状态。
 Lean（Version.lean）只证结构规则；本脚本负责实际绑定与核对。

模式：
  python3 m5_manifest.py build   # 重新计算清单（覆盖 m5_manifest.json）
  python3 m5_manifest.py check   # 校验当前文件与清单一致（退出码 0/1）
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).parent
ARTIFACTS = [
    "power/budget.json",
    "interfaces/interfaces.json",
    "architecture/architecture.json",
    "mech/mech_params.json",
    "mech/assembly_check.json",
    "eda/netlist.json",
    "bom.csv",
    "eda/environment-status.json",
    "visual/visual-specs.json",
    "tasks/christmas-buddy-v1.tasks.json",
    "proof/src/ChristmasBuddy/StateMachine.lean",
    "proof/src/ChristmasBuddy/Power.lean",
    "proof/src/ChristmasBuddy/Version.lean",
    "proof/verification.json",
]

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
                              text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None

def load() -> dict:
    return json.loads((BASE / "m5_manifest.json").read_text(encoding="utf-8"))

def build() -> None:
    items = []
    for rel in ARTIFACTS:
        p = BASE / rel
        if not p.exists():
            print(f"  MISSING: {rel}")
            sys.exit(1)
        items.append({"path": rel, "sha256": sha256(p), "bytes": p.stat().st_size})
    manifest = {
        "schema": "m5-manifest/1.0",
        "product": "christmas-buddy-v1",
        "date": date.today().isoformat(),
        "version_tuple": {"pcb": None, "cad": None, "fw": None, "bom": None,
                          "state": "preresearch（全部未冻结，符合 Version.lean 的 preresearch 定义）"},
        "git_commit": git_commit(),
        "note": "OB-1：pcb 槽冻结前不存在 Gerber/坐标/BOM 制造文件——本清单只绑定设计工件。",
        "artifacts": items,
    }
    (BASE / "m5_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    print(f"m5_manifest build: {len(items)} artifacts")

def check() -> None:
    m = load()
    bad = []
    for it in m["artifacts"]:
        p = BASE / it["path"]
        if not p.exists():
            bad.append(f"{it['path']}: 文件丢失")
        elif sha256(p) != it["sha256"]:
            bad.append(f"{it['path']}: 哈希漂移（文件已改，需重新 build）")
    if bad:
        print("m5_manifest check: FAIL")
        for b in bad:
            print("  !", b)
        sys.exit(1)
    print(f"m5_manifest check: PASS — {len(m['artifacts'])} artifacts 与清单一致")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    (build if mode == "build" else check)()
