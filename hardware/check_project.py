#!/usr/bin/env python3
"""Hardware Project 校验器（PR-A/整改轮）。

用法：
  python3 hardware/check_project.py --project hardware/space-buddy-r1/project.json
      常规校验：四元组完整性、产物存在性、CAD 证据回执比对（stale/unknown 撤销完成态）、
      证据计算 product_ready（人工声明与证据冲突即报错）、失效传播预览（--changed）。
      输出 JSON 摘要（供 8135 build_data 消费），校验失败退出码 2。
  --changed dims.keys,dims.usb_ports
      仅作为"影响预览"：列出依赖图下游将被失效的产物；不是失效机制本体。

失效机制（整改 A）：CAD 证据由 check_case.py 写 receipt.json 绑定输入（建模脚本/检查器/dims）
与产物（6 个 STEP）的内容哈希；本脚本每次运行重算当前哈希并逐项比对——
不匹配/缺回执 → cad_status=stale/unknown，撤销「CAD 完成」，重建工作台后仍保持，
只有重跑真实建模+检查生成新回执后恢复。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAD_DIR = ROOT / "source-data/agent-button-deck/pcba-v1/cad"
RENDERS = CAD_DIR / "renders/case-r1"
CLEAR = 0.05


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


_FC_VER_CACHE = None


def freecad_version() -> str:
    """当前 FreeCAD 版本（捆绑 python 探针，结果缓存）。"""
    global _FC_VER_CACHE
    if _FC_VER_CACHE:
        return _FC_VER_CACHE
    import subprocess
    fc_py = "/Applications/FreeCAD.app/Contents/Resources/bin/python"
    env = dict(os.environ)
    env["PYTHONPATH"] = "/Applications/FreeCAD.app/Contents/Resources/lib"
    try:
        r = subprocess.run([fc_py, "-c",
                            "import FreeCAD;print('.'.join(str(v) for v in FreeCAD.Version()[:3]))"],
                           capture_output=True, text=True, timeout=180, env=env)
        _FC_VER_CACHE = r.stdout.strip() or "unknown"
    except Exception:
        _FC_VER_CACHE = "unknown"
    return _FC_VER_CACHE


def cad_evidence_state() -> tuple[str, list[str], dict | None]:
    """返回 (valid|stale|unknown, 差异原因列表, receipt)。"""
    receipt_path = RENDERS / "receipt.json"
    if not receipt_path.is_file():
        return "unknown", ["receipt.json 缺失（未跑过真实几何检查）"], None
    receipt = load(receipt_path)
    diffs: list[str] = []
    # 手改 checks.json（把失败改成 ok）会被哈希比对检出
    try:
        checks_now = load(RENDERS / "checks.json")
        recorded_result = receipt.get("execution_result")
        if recorded_result is not None:
            # 完整比对：ok + 失败清单（手改部分字段也会被检出）
            if bool(checks_now.get("ok")) != bool(recorded_result.get("ok")):
                diffs.append("checks.json 的 ok 与回执 execution_result 不一致（疑似手改报告）")
            if list(checks_now.get("failed", [])) != list(recorded_result.get("failed", [])):
                diffs.append("checks.json 的 failed 清单与回执不一致（疑似手改报告）")
            if list(checks_now.get("failed", [])) != list(receipt.get("checks_failed_list", [])):
                diffs.append("checks.json 的 failed 清单与回执 checks_failed_list 不一致")
        else:
            diffs.append("回执缺少 execution_result")
        fc_now = freecad_version()
        fc_rec = receipt.get("freecad_version")
        if not fc_rec:
            diffs.append("FreeCAD 版本 UNKNOWN（回执未记录）")
        elif fc_rec != fc_now:
            diffs.append(f"FreeCAD 版本与回执不符：当前 {fc_now} / 回执 {fc_rec}")
    except Exception as e:
        diffs.append(f"checks.json 不可读：{e}")
    pairs = [
        ("model_script_sha256", CAD_DIR / "g2-case-r1.py"),
        ("checker_sha256", CAD_DIR / "check_case.py"),
        ("dims_sha256", RENDERS / "dims.json"),
        ("checks_sha256", RENDERS / "checks.json"),
    ]
    for key, path in pairs:
        current = sha256_file(path)
        # checks_sha256 在回执顶层（check_case.py 写入），其余在 inputs
        recorded = (receipt.get("checks_sha256") if key == "checks_sha256"
                    else receipt.get("inputs", {}).get(key))
        if recorded != current:
            diffs.append(f"{key} 与回执不符（{path.name} 已变化）")
    for name in ("body", "base", "cap-a", "cap-b", "cap-c", "cap-d"):
        p = RENDERS / f"case-r1-{name}.step"
        current = sha256_file(p)
        recorded = receipt.get("outputs", {}).get(f"step_sha256::{name}")
        if recorded != current:
            diffs.append(f"step_sha256::{name} 与回执不符（{p.name} 已变化）")
    return ("stale" if diffs else "valid"), diffs, receipt


def validate(project_path: Path, changed: list[str] | None = None) -> dict:
    proj = load(project_path)
    failures: list[str] = []
    checks: dict[str, object] = {}
    facts: dict[str, object] = {}
    reasons: list[str] = []

    revs = proj["version_contract"]["revisions"]

    # 1) 四元组完整性（null/draft 等允许——只要求字段存在且为成套声明）
    for seg in ("pcb", "cad", "fw", "bom"):
        if seg not in revs:
            failures.append(f"version_contract.revisions 缺少段：{seg}")
    checks["quad_complete"] = all(seg in revs for seg in ("pcb", "cad", "fw", "bom"))
    facts["quad"] = {k: revs.get(k) for k in ("pcb", "cad", "fw", "bom")}

    # 2) 产物文件存在性（登记了的就必须在）
    missing = []
    for rel in proj["domains"]["cad"].get("outputs", []):
        if not (ROOT / rel).is_file():
            missing.append(rel)
    for key in ("firmware", "bom"):
        rel = proj["domains"][key].get("entry")
        if rel and not (ROOT / rel).is_file():
            missing.append(rel)
    for rel in proj["domains"]["manufacturing"].get("package_present", []):
        if not (ROOT / rel).is_file():
            missing.append(rel)
    if missing:
        failures.append(f"登记产物文件缺失：{missing}")
    checks["artifacts_present"] = not missing
    facts["missing_files"] = missing

    # 3) CAD 证据：回执比对（不匹配/缺回执 → stale/unknown，撤销完成态）
    cad_state, diffs, _ = cad_evidence_state()
    checks["cad_evidence_state"] = cad_state
    facts["cad_evidence_state"] = cad_state
    facts["cad_evidence_diffs"] = diffs
    if cad_state != "valid":
        failures.append(f"CAD 证据 {cad_state}：" + "；".join(diffs or ["无回执"]))
        checks["cad_geometry_green"] = False
    else:
        cj = load(RENDERS / "checks.json")
        checks["cad_geometry_green"] = bool(cj.get("ok"))
        if not cj.get("ok"):
            failures.append(f"CAD 几何检查未全绿：{cj.get('failed')}")

    # 4) 尺寸确认状态（冻结判定，独立于检查有效性）
    dims = load(RENDERS / "dims.json") if (RENDERS / "dims.json").is_file() else {"sources": {}}
    unconfirmed = [k for k, v in dims.get("sources", {}).items() if v.get("status") != "confirmed-official"]
    facts["dims_confirmed"] = not unconfirmed
    facts["dims_unconfirmed"] = unconfirmed

    # 5) EDA 原生工程与 PCB（真实证据：本地工程路径存在 或 读回身份文件核对）
    eda_dom = proj["domains"]["eda"]
    eda_project = eda_dom.get("project")
    eda_verified = False
    eda_verify_fail = []
    if isinstance(eda_project, dict):
        local_path = (eda_project.get("local_session_path") or "").split("（")[0].strip()
        local_exists = Path(local_path).is_dir()
        rb_path = eda_project.get("readback_file")
        rb = load(ROOT / rb_path) if rb_path and (ROOT / rb_path).is_file() else None
        rb_match = bool(rb) and (
            rb.get("project_uuid") == eda_project.get("project_uuid") and
            rb.get("schematic_uuid") == eda_project.get("schematic_uuid"))
        # 真实性判定：读回身份匹配（编辑器 API 实读）为主；本地落盘为辅（首次保存前可能尚未落盘）
        if rb_path and not rb:
            eda_verify_fail.append(f"读回身份文件不存在：{rb_path}")
        elif rb_path and not rb_match:
            eda_verify_fail.append("读回身份与登记的 uuid 不一致")
        elif not rb_path and not local_exists:
            eda_verify_fail.append(f"既无读回身份文件也无本地工程：{local_path}")
        eda_verified = (bool(rb) and rb_match) or local_exists
    elif isinstance(eda_project, str) and eda_project:
        eda_verify_fail.append(f"本地工程路径不存在：{eda_project}")
    failures.extend(f"EDA 工程证据：{x}" for x in eda_verify_fail)
    checks["eda_project_verified"] = eda_verified and not eda_verify_fail
    eda_outputs = eda_dom.get("outputs_present", [])
    ALLOWED_TYPES = {"schematic", "pcb", "gerber", "bom", "cpl", "pcb_step"}
    # gerber/bom/cpl/pcb_step 必须有 path+digest（真实产物文件），不能用读回身份文件冒充
    PATH_REQUIRED_TYPES = {"gerber", "bom", "cpl", "pcb_step"}
    seen_refs, bad_outputs = set(), []
    pcb_object_uuid = None
    evidence_files_used = {}  # evidence 文件 → 使用它的产物类型集合（防同一文件冒充多种产物）
    for o in eda_outputs:
        name, otype = o.get("name"), o.get("type")
        uuid, digest, ev = o.get("uuid"), o.get("digest"), o.get("evidence")
        opath = o.get("path")
        if (uuid, otype) in seen_refs:
            bad_outputs.append((name, "重复引用同一 uuid+类型"))
        seen_refs.add((uuid, otype))
        if otype not in ALLOWED_TYPES:
            bad_outputs.append((name, f"未知产物类型 {otype}"))
        if not ev or not (ROOT / ev).is_file():
            bad_outputs.append((name, f"证据文件缺失 {ev}"))
            continue
        # 同一证据文件不得承载多种产物类型（读回身份文件只能给 schematic/pcb 各用一次）
        ev_key = str(Path(ev))
        evidence_files_used.setdefault(ev_key, set()).add(otype)
        if len(evidence_files_used[ev_key]) > 2:
            bad_outputs.append((name, f"证据文件 {Path(ev).name} 承载了过多产物类型"))
        # path+digest 严格检查：PATH_REQUIRED_TYPES 缺 path/digest 直接 FAIL
        if otype in PATH_REQUIRED_TYPES:
            if not opath or not digest:
                bad_outputs.append((name, f"{otype} 必须提供真实产物路径和 SHA256 摘要"))
            else:
                pp = ROOT / opath
                if not pp.is_file():
                    bad_outputs.append((name, f"产物真实路径不存在 {opath}"))
                elif sha256_file(pp) != digest:
                    bad_outputs.append((name, f"产物内容摘要不符 {opath}"))
        else:
            # 非强制类型：如果提供了 path+digest 也要校验
            if opath and digest:
                pp = ROOT / opath
                if not pp.is_file():
                    bad_outputs.append((name, f"产物真实路径不存在 {opath}"))
                elif sha256_file(pp) != digest:
                    bad_outputs.append((name, f"产物内容摘要不符 {opath}"))
        ev_text = (ROOT / ev).read_text(encoding="utf-8", errors="ignore")
        if uuid and uuid not in ev_text:
            bad_outputs.append((name, f"证据文件中找不到 uuid {str(uuid)[:12]}"))
        if otype == "schematic" and rb and uuid and uuid != rb.get("schematic_uuid"):
            bad_outputs.append((name, "schematic uuid 与读回身份不符"))
        if otype == "pcb":
            if rb and uuid and uuid != rb.get("pcb_uuid"):
                bad_outputs.append((name, "pcb uuid 与读回身份不符"))
            else:
                pcb_object_uuid = uuid
        if otype not in ("schematic", "pcb") and ev and Path(ev).name == "eda-readback.json":
            bad_outputs.append((name, f"{otype} 产物不得用 EDA 读回身份文件冒充证据"))
    if eda_outputs and bad_outputs:
        failures.append("EDA 产物证据缺陷：" + "；".join(f"{n}:{w}" for n, w in bad_outputs))
    outputs_verified = bool(eda_outputs) and not bad_outputs

    # ── PCB 状态分离（整改：空 PCB 对象 ≠ 完成/冻结）──
    # pcb_object_verified: EDA 工程中有经读回核验的真实 PCB 对象
    # pcb_layout_started: EDA PCB 已有元件或走线（当前无法自动检测，标 False）
    # pcb_design_verified: DRC 全绿 + 联合验证通过（等 PR-B/C 实现）
    # pcb_frozen: 版本数字 + 上述全部
    pcb_object_verified = eda_verified and bool(pcb_object_uuid)
    pcb_layout_started = False   # PR-B DRC 后才可标记
    pcb_design_verified = False  # PR-B ERC+DRC 全绿 + PR-C 联合验证后才可标记
    pcb_frozen = (isinstance(revs.get("pcb"), int)
                  and pcb_object_verified and pcb_design_verified)
    pcb_evidence = eda_verified and outputs_verified and bool(pcb_object_uuid)

    facts["pcb_status"] = ("已冻结（rev %s）" % revs["pcb"]) if pcb_frozen and pcb_evidence else (
        "进行中（原生工程已建立，产物未齐）" if eda_project else "未开始（无 R1 原生 EDA 工程）")
    facts["pcb_frozen"] = pcb_frozen and pcb_evidence
    facts["pcb_object_uuid"] = pcb_object_uuid or None
    facts["pcb_object_verified"] = pcb_object_verified
    facts["pcb_layout_started"] = pcb_layout_started
    facts["pcb_design_verified"] = pcb_design_verified

    # 6) 联合验证 / 制造包 / 授权 / 验收（区分表达，不互相混入）
    joint = proj.get("joint_check", {})
    joint_evidence = joint.get("evidence")
    facts["joint_status"] = ("已验证（%s）" % joint_evidence) if joint_evidence else (
        joint.get("status") or "未开始")
    checks["joint_verified"] = bool(joint_evidence)

    mfg = proj["domains"]["manufacturing"]
    required = mfg.get("package_required", [])
    present = mfg.get("package_present", [])
    missing_pkg = [x for x in required if x not in present]
    facts["package_complete"] = not missing_pkg
    facts["package_missing"] = missing_pkg
    checks["package_complete"] = facts["package_complete"]

    order_authorized = bool(mfg.get("order_authorized"))
    facts["order_authorized"] = order_authorized
    acceptance = proj["domains"].get("acceptance", {})
    acceptance_evidence = acceptance.get("evidence")
    facts["acceptance_done"] = bool(acceptance_evidence)
    checks["acceptance_done"] = bool(acceptance_evidence)

    # 7) 证据计算 product_ready（人工声明不透传）
    #    首次打样放行 = 设计检查有效 + 尺寸全部确认 + 联合验证 + 制造包齐全 + 下单授权；
    #    实物验收完成是最终验收项，不是首次打样前置条件。
    dims_ready = facts["dims_confirmed"]
    design_ok = (cad_state == "valid") and checks["cad_geometry_green"] and dims_ready
    product_ready_computed = bool(
        design_ok and pcb_frozen and pcb_evidence and checks["joint_verified"]
        and facts["package_complete"] and order_authorized and facts["acceptance_done"])
    if not design_ok:
        reasons.append("CAD 设计检查未有效通过" + ("（尺寸存在占位/待实测项：%s）" % ",".join(unconfirmed) if unconfirmed else ""))
    if not pcb_frozen:
        reasons.append("PCB 版本未冻结（需真实 PCB 对象+DRC 全绿+联合验证通过）")
    if not pcb_evidence:
        reasons.append("EDA 原生工程产物不足（原理图/DRC/BOM/CPL/Gerber 等）")
    if not checks["joint_verified"]:
        reasons.append("板壳联合验证未完成")
    if not facts["package_complete"]:
        reasons.append("制造包缺件：%s" % "、".join(missing_pkg))
    # 下单授权与实物验收不再进入设计缺口 reasons（三态分离），由 facts 单独表达
    facts["product_ready_computed"] = product_ready_computed
    facts["product_ready_reasons"] = reasons
    # 三态分离（整改 8）：设计/授权/验收互不冒充
    facts["design_ready"] = bool(design_ok and pcb_frozen and pcb_evidence and checks["joint_verified"])
    facts["manufacturing_authorized"] = order_authorized
    facts["product_accepted"] = bool(acceptance_evidence)

    # 8) 人工声明与证据冲突检查
    guard = proj.get("guard", {})
    manual_ready = guard.get("product_ready")
    if manual_ready is True and not product_ready_computed:
        failures.append("人工声明与证据冲突：guard.product_ready=true 但证据计算为未就绪（原因：%s）"
                        % "；".join(reasons))
    checks["manual_vs_evidence_consistent"] = not (
        manual_ready is True and not product_ready_computed)
    facts["product_ready"] = product_ready_computed

    # 9) EDA≠产品守卫：真实判断（非恒真）
    checks["eda_not_product_guard"] = not (product_ready_computed and not eda_project)
    facts["eda_environment_note"] = proj["domains"]["eda"].get("editor_note", "")

    # 10) 失效传播预览（--changed 仅预览；失效本体由回执比对承担）
    graph = proj.get("dependency_graph", {})
    stale_preview: list[str] = []
    for changed_key in changed or []:
        if changed_key in graph:
            for down in graph[changed_key]["downstream"]:
                stale_preview.append(f"{down} ← {changed_key} 变更 → STALE-需重新验证")
        else:
            failures.append(f"未知变更键：{changed_key}（dependency_graph 无此条目，须先登记）")
    result = {
        "project": proj["product"],
        "ok": not failures,
        "failures": failures,
        "checks": checks,
        "facts": facts,
        "stale_preview": stale_preview,
        "note": "全部状态由本脚本从真实文件与回执计算；--changed 仅为影响预览",
    }
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
