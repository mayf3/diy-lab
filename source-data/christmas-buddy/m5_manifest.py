#!/usr/bin/env python3
"""M5 制造发布合同 · Manifest Checker v2（P1 升级）。

职责（governance MAP 的实现层）：
1. build：扫描设计/制造工件，计算 sha256，生成 m5_manifest.json（release 候选）。
   - 尚不存在的工件（Gerber/PCB 源/固件/制造报告）登记 status=NOT_YET，不写虚构哈希。
   - release_candidate 含版本四元组（pcb/cad/fw/bom）、source_commit、manifest_hash、approval_state。
   - 任何工件内容变化都会改变 manifest_hash → 旧批准不能静默继承（须重建候选并重新走门禁）。
2. check：重算并核对（漂移即 FAIL，列出变更文件）。
3. build 内置 gen-lean：从 manifest 受控生成 proof/src/ChristmasBuddy/ReleaseCurrent.lean，
   使 Lean 定理作用在**真实数据**上（与 checker 共用同一版本语义）。

与 Lean 的分工：Lean 证抽象发布合同（Version.lean）；本脚本证真实文件绑定（TESTED 层）。
不得声称「Lean 编译通过 = 制造文件通过」。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
LEAN_OUT = BASE / "proof/src/ChristmasBuddy/ReleaseCurrent.lean"

# (相对路径, 逻辑名, 工具, 版本槽)  version_slot: pcb/cad/fw/bom/design
ARTIFACT_TABLE = [
    ("power/budget.json",                       "电源预算",            "power_budget.py", "design"),
    ("interfaces/interfaces.json",              "接口定义",            "interfaces.py",   "design"),
    ("architecture/architecture.json",          "架构比较",            "architecture.py", "design"),
    ("mech/mech_params.json",                   "机械参数",            "params.py",       "cad"),
    ("mech/assembly_check.json",                "装配检查",            "build_mech.py",   "cad"),
    ("eda/netlist.json",                        "网表",                "netlist.py",      "pcb"),
    ("eda/erc_report.md",                       "ERC 报告",            "netlist.py",      "pcb"),
    ("eda/environment-status.json",             "EDA 环境证据",        "人工登记",         "pcb"),
    ("visual/visual-specs.json",                "视觉约束",            "visual_specs.py", "design"),
    ("tasks/christmas-buddy-v1.tasks.json",     "工程任务书",          "gen_eng_tasks.py","design"),
    ("proof/src/ChristmasBuddy/StateMachine.lean", "M2 状态机证明",    "lean 4.19.0",     "fw"),
    ("proof/src/ChristmasBuddy/Power.lean",     "M1 电源证明",         "lean 4.19.0",     "fw"),
    ("proof/src/ChristmasBuddy/Version.lean",   "M5 发布合同证明",      "lean 4.19.0",     "fw"),
    ("proof/verification.json",                 "Lean 验证回执",       "verify_proof.py", "fw"),
    # —— 尚不存在的制造工件：显式 NOT_YET ——
    ("eda/project/PCB1_1.epcb2",                "PCB 源文件",          "嘉立创EDA 4.1.x", "pcb"),
    ("manufacturing/gerber/",                   "Gerber 包",           "pcb_ManufactureData", "pcb"),
    ("manufacturing/bom.xlsx",                  "贴片 BOM",            "sch_ManufactureData", "bom"),
    ("manufacturing/cpl.xlsx",                  "坐标文件",            "pcb_ManufactureData", "pcb"),
    ("manufacturing/pcb.step",                  "PCB STEP",            "pcb_ManufactureData", "cad"),
    ("manufacturing/drc-report.json",           "DRC 报告",            "pcb_Drc.check",   "pcb"),
    ("manufacturing/dfm-report.json",           "DFM 报告",            "嘉立创下单系统",   "pcb"),
    ("firmware/esp32/main.bin",                 "ESP32 固件",          "esp-idf",         "fw"),
    ("firmware/pi/service.tar.gz",              "Pi 服务包",           "Python 3",        "fw"),
    ("mech/outputs/print-coupon/test-report.json", "试打印公差报告",    "卡尺+人",         "cad"),
]

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
                              text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None

def tool_version(tool: str) -> str:
    if tool.startswith("lean"):
        return "leanprover/lean4:v4.19.0"
    return tool  # 工具版本随工件自身登记；未实测版本如实保留工具名

def build() -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    artifacts, not_yet = [], []
    for rel, name, tool, slot in ARTIFACT_TABLE:
        p = BASE / rel
        if p.exists():
            artifacts.append({
                "path": rel, "logical_name": name, "sha256": sha256(p),
                "bytes": p.stat().st_size, "version_slot": slot,
                "tool": tool, "tool_version": tool_version(tool),
                "status": "BOUND",
            })
        else:
            not_yet.append({
                "path": rel, "logical_name": name, "version_slot": slot,
                "status": "NOT_YET", "sha256": None,
            })
    artifacts.sort(key=lambda a: a["path"])
    manifest_hash_src = json.dumps([a["sha256"] for a in artifacts], sort_keys=True)
    manifest_hash = hashlib.sha256(manifest_hash_src.encode()).hexdigest()
    manifest = {
        "schema": "m5-release-manifest/2.0",
        "product": "christmas-buddy-v1",
        "date": date.today().isoformat(),
        "generated_at": now,
        "release_candidate": {
            "product": "christmas-buddy-v1",
            "tuple": {"pcb": None, "cad": None, "fw": None, "bom": None},
            "tuple_state": "preresearch（四段未冻结——冻结须 GATE 门禁人工批准）",
            "source_commit": git_commit(),
            "manifest_hash": manifest_hash,
            "approval_state": "UNAPPROVED",
            "rule": "任一工件变化 → manifest_hash 变化 → 产生新候选；旧 approval_state 不继承",
        },
        "artifacts": artifacts,
        "not_yet": not_yet,
        "note": "NOT_YET 工件不携带任何哈希（禁止虚构占位）；OB-1 义务待真实 EDA 工程产出解除。",
    }
    (BASE / "m5_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    gen_lean(manifest)
    print(f"m5_manifest build: {len(artifacts)} BOUND, {len(not_yet)} NOT_YET, "
          f"manifest_hash={manifest_hash[:12]}…")
    return manifest

def gen_lean(manifest: dict) -> None:
    """受控转换：manifest → Lean 常量文件（checker 与 Lean 同一版本语义）。"""
    rc = manifest["release_candidate"]
    tpl = f"""import ChristmasBuddy.Version

/-! AUTO-GENERATED by m5_manifest.py v2 @ {manifest['generated_at']} — 手改无效，重建需重跑脚本。
此文件是 Release 抽象模型（Version.lean）与真实 manifest 之间的受控转换层（MAP）。
若此文件与 m5_manifest.json 不一致，以 m5_manifest.json 为准并重新生成。 -/

/-- 当前候选发布的 manifest 哈希（真实文件集合的绑定）。 -/
def currentManifestHash : String := "{rc['manifest_hash']}"

/-- 当前候选四元组：本阶段四段全部未冻结（preresearch）。 -/
def currentTuple : ChristmasBuddy.Version.Release := ⟨none, none, none, none⟩

/-- 当前候选批准状态：UNAPPROVED（未走 GATE 门禁）。 -/
def currentApproved : Bool := false

/-- 生成即验证：当前候选（未冻结、未批准）不可制造——由合同定理直接给出。 -/
example : ChristmasBuddy.Version.manufacturable currentTuple = false := by rfl
"""
    LEAN_OUT.parent.mkdir(parents=True, exist_ok=True)
    LEAN_OUT.write_text(tpl + "\n", encoding="utf-8")

def load() -> dict:
    return json.loads((BASE / "m5_manifest.json").read_text(encoding="utf-8"))

def check() -> None:
    m = load()
    bad = []
    for it in m["artifacts"]:
        p = BASE / it["path"]
        if not p.exists():
            bad.append(f"{it['path']}: 已登记工件丢失")
        elif sha256(p) != it["sha256"]:
            bad.append(f"{it['path']}: 哈希漂移（→ 新 release 候选，须重建 + 重新门禁）")
    appeared = [it["path"] for it in m["not_yet"] if (BASE / it["path"]).exists()]
    if appeared:
        bad.append(f"NOT_YET 工件已出现（须重跑 build 升级为 BOUND）: {appeared[:3]}")
    if LEAN_OUT.exists():
        lean = LEAN_OUT.read_text(encoding="utf-8")
        want = m["release_candidate"]["manifest_hash"]
        if f'"{want}"' not in lean:
            bad.append("ReleaseCurrent.lean 与 manifest_hash 不一致（须重新 gen-lean）")
        if m["release_candidate"]["approval_state"] != "UNAPPROVED" and "currentApproved : Bool := false" in lean:
            bad.append("approval_state 已变更但 Lean 常量未更新")
    else:
        bad.append("ReleaseCurrent.lean 缺失（须重跑 build 生成）")
    if bad:
        print("m5_manifest check: FAIL")
        for b in bad:
            print("  !", b)
        sys.exit(1)
    print(f"m5_manifest check: PASS — {len(m['artifacts'])} BOUND / {len(m['not_yet'])} NOT_YET，"
          f"候选 {m['release_candidate']['manifest_hash'][:12]}… {m['release_candidate']['approval_state']}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    (build if mode == "build" else check)()
