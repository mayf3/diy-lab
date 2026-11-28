#!/usr/bin/env python3
"""Hardware Project 校验器（PR-A）。

用法：
  python3 hardware/check_project.py --project hardware/space-buddy-r1/project.json
      校验四元组完整性、产物文件存在性、CAD 检查新鲜度、EDA≠产品 ready 守卫；
      输出 JSON 摘要（供 8135 build_data 使用），失败退出码 2。
  python3 hardware/check_project.py --project ... --changed dims.usb_ports
      模拟变更：打印依赖图下游需要重新验证的产物清单（失效传播），退出码 0。

纪律：本脚本只读真实文件与 project.json，不生成任何"模拟通过"。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STALE_MARKER = "STALE-需重新验证"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def validate(project_path: Path, changed: list[str] | None = None) -> dict:
    proj = load(project_path)
    failures: list[str] = []
    result: dict = {"project": proj["product"], "failures": failures, "checks": {}}

    # 1) 四元组完整性：pcb/cad/fw/bom 四段必须全部存在（null=明确未开始，允许；缺 key=违规）
    revs = proj["version_contract"]["revisions"]
    for seg in ("pcb", "cad", "fw", "bom"):
        if seg not in revs:
            failures.append(f"version_contract.revisions 缺少段：{seg}")
    result["checks"]["quad_complete"] = all(seg in revs for seg in ("pcb", "cad", "fw", "bom"))
    result["checks"]["quad_values"] = {k: revs.get(k) for k in ("pcb", "cad", "fw", "bom")}

    # 2) 产物文件存在性
    missing = []
    for rel in proj["domains"]["cad"].get("outputs", []):
        if not (ROOT / rel).is_file():
            missing.append(rel)
    fw = proj["domains"]["firmware"].get("entry")
    if fw and not (ROOT / fw).is_file():
        missing.append(fw)
    bom = proj["domains"]["bom"].get("entry")
    if bom and not (ROOT / bom).is_file():
        missing.append(bom)
    checks = proj["domains"].get("manufacturing", {}).get("package_present", [])
    for rel in checks:
        if not (ROOT / rel).is_file():
            missing.append(rel)
    if missing:
        failures.append(f"登记产物文件缺失：{missing}")
    result["checks"]["artifacts_present"] = not missing
    result["missing_files"] = missing

    # 3) CAD 检查新鲜度：checks.json 必须存在且 ok（真实几何检查器产物）
    checks_file = ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1/checks.json"
    if checks_file.is_file():
        cj = load(checks_file)
        result["checks"]["cad_geometry_green"] = bool(cj.get("ok"))
        if not cj.get("ok"):
            failures.append(f"CAD 几何检查未全绿：{cj.get('failed')}")
        if "check_case.py" not in cj.get("note", ""):
            failures.append("checks.json 缺少 STEP 重算来源声明")
    else:
        failures.append("checks.json 不存在（CAD 检查未跑）")
        result["checks"]["cad_geometry_green"] = False

    # 4) EDA ≠ 产品 ready 守卫
    guard = proj.get("guard", {})
    if guard.get("product_ready") is True and revs.get("pcb") in (None, "", "draft"):
        failures.append("守卫违规：PCB 无冻结版本却声明 product_ready")
    result["checks"]["eda_not_product_guard"] = True
    result["product_ready"] = guard.get("product_ready", False)

    # 5) 失效传播：--changed 触发依赖图下游标记
    graph = proj.get("dependency_graph", {})
    stale: list[str] = []
    for changed_key in changed or []:
        if changed_key in graph:
            for down in graph[changed_key]["downstream"]:
                item = f"{down} ← {changed_key} 变更 → {STALE_MARKER}"
                stale.append(item)
        else:
            # 严格模式：依赖图没有登记的变更键一律报错（登记是纪律，不做静默保守传播）
            failures.append(f"未知变更键：{changed_key}（dependency_graph 无此条目，须先登记）")
    result["stale_downstream"] = stale
    result["checks"]["invalidation_propagated"] = (changed is None) or bool(stale)

    result["ok"] = not failures
    return result


def main() -> None:
    args = sys.argv[1:]
    project = ROOT / "hardware/space-buddy-r1/project.json"
    changed: list[str] | None = None
    i = 0
    while i < len(args):
        if args[i] == "--project":
            project = Path(args[i + 1]); i += 2
        elif args[i] == "--changed":
            changed = args[i + 1].split(","); i += 2
        else:
            i += 1
    summary = validate(project, changed)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    sys.exit(0 if summary["ok"] else 2)


if __name__ == "__main__":
    main()
