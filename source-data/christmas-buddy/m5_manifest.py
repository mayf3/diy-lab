#!/usr/bin/env python3
"""M5 制造发布合同 · Manifest Checker v5（Batch4.2）。

v5 变更（PR #36 两条 Review Finding 修复 + 发布合同收口）：
  - P0-2（#4727196824）：build 与 check **共用唯一** canonical_payload 规范化实现——
    artifacts / files / skipped_symlinks / not_yet / approval_records 全部按完整相对路径排序
    （符号链接不再按 basename 序进入哈希，basename 序 ≠ 完整路径序时 build 后立即 check PASS）。
  - P0-1（#4727196821）：release_candidate 增加 approver（候选宣称批准人）；
    Lean manufacturingRelease 增加 r.approver = some rec.approver 身份精确一致判定。
  - P1-1：批准注册表（approval_records）成为显式合同字段；Lean 判定加入注册表成员资格。
  - P1-2：gen_lean 从 manifest 真实生成 currentTuple/currentApproved/currentCandidateApprover/
    currentRegistry（不再写死）；生成即验证 R1 把制造资格与 approval_state 恒等绑定。
  - check 增加批准治理规则 approval_consistency（APPROVED 必须有精确登记的批准记录）。

v3/v4 既有的（保留）：
  - bom.csv 纳入 BOUND；BOM↔网表一致性检查；目录确定性哈希 directory_manifest()。
  - 检查器自身源码纳入 BOUND；BASE 可参数化（对抗测试在临时副本树上运行，绝不碰真实文件）。

职责（governance MAP 的实现层）：
1. build：扫描设计/制造工件，计算 sha256，生成 m5_manifest.json（release 候选）。
   - 尚不存在的工件（Gerber/PCB 源/固件/制造报告）登记 status=NOT_YET，不写虚构哈希。
   - release_candidate 含版本四元组（pcb/cad/fw/bom）、source_commit、manifest_hash、
     approval_state、approver、approval_records。
   - 任何工件内容或批准元数据变化都会改变 manifest_hash → 旧批准不能静默继承。
2. check：重算并核对（漂移即 FAIL，列出变更文件）+ 批准治理。
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

# 目录工件的临时文件排除规则（确定性：不随枚举顺序变化）
DIR_EXCLUDE = {".DS_Store", "Thumbs.db"}
DIR_EXCLUDE_SUFFIX = (".log", ".tmp", "~", ".bak", ".swp")

def directory_manifest(d: Path, base: Path) -> dict:
    """确定性目录哈希。
    规范：相对路径 POSIX 正斜杠、按 Unicode codepoint 排序、逐文件 sha256、
    排除 DIR_EXCLUDE/后缀与隐藏点文件、空目录 → files=[] + dir_sha256=sha256(b"")、
    符号链接一律跳过并登记（不跟随）、大小写保留不折叠、输入枚举顺序不影响结果。"""
    files, skipped = [], []
    if d.exists():
        for f in sorted(d.rglob("*"), key=lambda q: q.name):
            if f.is_symlink():
                skipped.append(str(f.relative_to(base)).replace("\\", "/"))
                continue
            if not f.is_file():
                continue
            rel = f.relative_to(base).as_posix()
            name = f.name
            if name in DIR_EXCLUDE or name.startswith(".") or name.endswith(DIR_EXCLUDE_SUFFIX):
                continue
            files.append({"path": rel, "bytes": f.stat().st_size, "sha256": sha256(f)})
    files.sort(key=lambda e: e["path"])
    skipped.sort()  # P0-2：按完整相对路径排序（basename 序 ≠ 完整路径序时不一致）
    h = hashlib.sha256()
    for e in files:  # 空列表 → sha256(b"")，有定义
        h.update(e["path"].encode())
        h.update(str(e["bytes"]).encode())
        h.update(e["sha256"].encode())
    return {"files": files, "dir_sha256": h.hexdigest(), "skipped_symlinks": skipped}

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
    ("bom.csv",                                 "采购 BOM",            "采购执行轮",       "bom"),
    ("visual/visual-specs.json",                "视觉约束",            "visual_specs.py", "design"),
    ("tasks/christmas-buddy-v1.tasks.json",     "工程任务书",          "gen_eng_tasks.py","design"),
    ("proof/src/ChristmasBuddy/StateMachine.lean", "M2 状态机证明",    "lean 4.19.0",     "fw"),
    ("proof/src/ChristmasBuddy/Power.lean",     "M1 电源证明",         "lean 4.19.0",     "fw"),
    ("proof/src/ChristmasBuddy/Version.lean",   "M5 发布合同证明",      "lean 4.19.0",     "fw"),
    ("proof/verification.json",                 "Lean 验证回执",       "verify_proof.py", "fw"),
    ("eda/netlist.py",                          "网表检查器源码",       "python3",        "pcb"),
    ("eda/netlist_tests.py",                    "网表负向测试源码",     "python3",        "pcb"),
    ("mech/build_mech.py",                      "机械检查器源码",       "python3",        "cad"),
    ("mech/openings.py",                        "开孔几何检查源码",     "python3",        "cad"),
    ("mech/mech_tests.py",                      "机械负向测试源码",     "python3",        "cad"),
    ("mech/coupon_verify.py",                   "测件验证器源码",       "python3",        "cad"),
    ("mech/coupon_tests.py",                    "测件负向测试源码",     "python3",        "cad"),
    ("m5_manifest.py",                          "Manifest 检查器源码",  "python3",        "bom"),
    # —— 尚不存在的制造工件：显式 NOT_YET ——
    ("eda/project/PCB1_1.epcb2",                "PCB 源文件",          "嘉立创EDA 4.1.x", "pcb"),
    ("manufacturing/gerber/",                   "Gerber 包",           "pcb_ManufactureData", "pcb", "dir"),
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

CANONICAL_EXCLUDE = {"generated_at", "date", "manifest_hash", "hash_basis", "rule", "note",
                     "tuple_state", "schema"}

def canonical_payload(m: dict) -> dict:
    """**唯一**规范化视图（P0-2 #4727196824）：build 与 check 都必须经由本函数取得哈希输入，
    不得各自另实现排序。

    规范化规则（全部确定性）：
    - artifacts 按完整相对路径排序；
    - 目录工件的 files 按完整相对路径排序、skipped_symlinks 按完整相对路径排序；
    - not_yet 按完整相对路径排序；
    - approval_records（语义无序集合）按 (manifest_hash, approver, release) 排序；
    - 排除时间戳（generated_at/date）与循环字段（manifest_hash）等不稳定字段（CANONICAL_EXCLUDE）。
    """
    arts = []
    for a in m.get("artifacts", []):
        e = {k: a.get(k) for k in ("path", "logical_name", "kind", "sha256", "bytes",
                                   "version_slot", "tool", "tool_version", "status")
             if k in a}
        if "files" in a:
            e["files"] = sorted(a["files"], key=lambda f: f["path"])
        if "skipped_symlinks" in a:
            e["skipped_symlinks"] = sorted(a["skipped_symlinks"])
        arts.append(e)
    arts.sort(key=lambda a: a["path"])
    rc = m.get("release_candidate", {})
    meta = {k: rc.get(k) for k in ("product", "tuple", "source_commit", "approval_state",
                                   "approver", "approval_records")}
    records = sorted(meta.get("approval_records") or [],
                     key=lambda r: json.dumps([r.get("manifest_hash"), r.get("approver"),
                                               r.get("release")], sort_keys=True,
                                              ensure_ascii=False))
    meta["approval_records"] = records
    return {"artifacts": arts, "release": meta,
            "not_yet": sorted(m.get("not_yet", []), key=lambda e: e.get("path", ""))}

def canonical_hash(m: dict) -> str:
    """canonical 哈希 = sha256(canonical_payload 规范视图)。
    build（对自建数据）与 check（对读回的 manifest）调用**同一个**函数（P0-2）。"""
    payload = canonical_payload(m)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def build(base: Path = BASE) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    artifacts, not_yet = [], []
    for row in ARTIFACT_TABLE:
        rel, name, tool, slot = row[:4]
        is_dir = len(row) > 4 and row[4] == "dir"
        p = base / rel
        if is_dir and p.exists():
            dm = directory_manifest(p, base)
            artifacts.append({
                "path": rel, "logical_name": name, "kind": "directory",
                "sha256": dm["dir_sha256"], "bytes": sum(e["bytes"] for e in dm["files"]),
                "files": dm["files"], "skipped_symlinks": dm["skipped_symlinks"],
                "version_slot": slot, "tool": tool, "tool_version": tool_version(tool),
                "status": "BOUND",
            })
        elif p.exists():
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
    consistency = bom_netlist_consistency(base)
    if consistency:
        not_yet.append({"path": "BOM_NETLIST_CONSISTENCY", "logical_name": "BOM↔网表一致性",
                        "version_slot": "bom", "status": "FAIL",
                        "errors": consistency})
    artifacts.sort(key=lambda a: a["path"])
    release_meta = {
        "product": "christmas-buddy-v1",
        "tuple": {"pcb": None, "cad": None, "fw": None, "bom": None},
        "source_commit": git_commit(),
        "approval_state": "UNAPPROVED",
        "approver": None,
        "approval_records": [],
    }
    manifest_hash = canonical_hash({"artifacts": artifacts, "not_yet": not_yet,
                                    "release_candidate": release_meta})
    manifest = {
        "schema": "m5-release-manifest/2.1",
        "product": "christmas-buddy-v1",
        "date": date.today().isoformat(),
        "generated_at": now,
        "release_candidate": {
            "product": release_meta["product"],
            "tuple": release_meta["tuple"],
            "tuple_state": "preresearch（四段未冻结——冻结须 GATE 门禁人工批准）",
            "source_commit": release_meta["source_commit"],
            "manifest_hash": manifest_hash,
            "approval_state": "UNAPPROVED",
            "approver": release_meta["approver"],
            "approval_records": release_meta["approval_records"],
            "hash_basis": "canonical v5：path/kind/sha/bytes/slot/tool/files/symlinks + release 元数据"
                          "（含 approver/approval_records）；全部数组按完整相对路径规范化；"
                          "build/check 共用 canonical_payload 唯一实现；排除时间戳与自身哈希",
            "rule": "任一工件或批准元数据变化 → canonical hash 变化 → 新候选；旧批准不继承",
        },
        "artifacts": artifacts,
        "not_yet": not_yet,
        "note": "NOT_YET 工件不携带任何哈希（禁止虚构占位）；OB-1 义务待真实 EDA 工程产出解除。",
    }
    (base / "m5_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    gen_lean(manifest, base)
    print(f"m5_manifest build: {len(artifacts)} BOUND, {len(not_yet)} NOT_YET, "
          f"manifest_hash={manifest_hash[:12]}…")
    return manifest

def bom_netlist_consistency(base: Path) -> list[str]:
    """BOM↔网表一致性：BOM_NETWORK 映射表中每一项必须同时存在于 bom.csv 与网表 devices。"""
    mapping = {  # bom.csv id → netlist refs（一个 BOM 项可覆盖多个器件位号）
        "B01": [], "B02": [], "B03": ["U1"], "B04": ["U2"], "B05": ["U3"],
        "B06": ["U4"], "B08": ["U5"], "B09": ["U6"], "B10": ["Q1"], "B11": ["D1"],
        "B12": ["F1", "F2", "F3"], "B13": ["SW5"], "B14": ["SW1", "SW2", "SW3", "SW4", "SW6"],
        "B15": ["J1"], "B17": ["J4", "J5", "J6", "J7", "J8"], "B18": ["J9"],
    }
    errors = []
    nl_path = base / "eda/netlist.json"
    bom_path = base / "bom.csv"
    if not nl_path.exists() or not bom_path.exists():
        return errors
    try:
        refs = {d["ref"] for d in json.loads(nl_path.read_text(encoding="utf-8"))["devices"]}
    except (json.JSONDecodeError, KeyError) as e:
        return [f"netlist.json 无法解析（工件损坏，按 FAIL 处理）: {e}"]
    bom_ids = set()
    for line in bom_path.read_text(encoding="utf-8").splitlines()[1:]:
        if line.strip():
            bom_ids.add(line.split(",")[0])
    for bom_id, need in mapping.items():
        if bom_id not in bom_ids:
            errors.append(f"BOM 缺行 {bom_id}")
        for ref in need:
            if ref not in refs:
                errors.append(f"BOM {bom_id} 映射的网表器件 {ref} 不存在")
    return errors

def approval_consistency(rc: dict) -> list[str]:
    """批准治理（P1-1 受信任注册表边界）：approval_state 必须与批准记录精确一致。
    APPROVED ⇔ 注册表中存在与当前候选**精确一致**（release 四元组 + manifest_hash +
    批准人三元全等）且批准人非空的记录；UNAPPROVED 则不得有任何批准记录。

    外部信任边界：本函数只校验**记录结构一致性**；现实中批准人的身份与授权真实性
    由工作台 GATE 门禁与受控批准流程负责——脚本与 Lean 都无法验证现实中人的身份。
    （独立函数便于对抗测试做故障注入：禁用后诊断必须消失，否则套件 FAIL。）"""
    errs = []
    records = rc.get("approval_records") or []
    approved = rc.get("approval_state") == "APPROVED"

    def exact(r) -> bool:
        return (isinstance(r, dict)
                and r.get("release") == rc.get("tuple")
                and r.get("manifest_hash") == rc.get("manifest_hash")
                and isinstance(r.get("approver"), str) and r["approver"] != ""
                and r.get("approver") == rc.get("approver"))

    if approved:
        if not any(exact(r) for r in records):
            errs.append("批准状态与批准记录矛盾：APPROVED 但注册表中无与当前候选精确一致的"
                        "批准记录（release+manifest_hash+approver 三元精确、批准人非空）")
    elif records:
        errs.append("批准状态与批准记录矛盾：未 APPROVED 但注册表已有批准记录")
    return errs

def _lean_opt_nat(v) -> str:
    return "none" if v is None else f"some {int(v)}"

def _lean_tuple(t: dict) -> str:
    return "⟨" + ", ".join(_lean_opt_nat(t.get(k)) for k in ("pcb", "cad", "fw", "bom")) + "⟩"

def _lean_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)  # UTF-8 字面量；引号/反斜杠转义与 Lean 兼容

def _lean_record(r: dict) -> str:
    return (f"⟨{_lean_tuple(r['release'])}, {_lean_str(r['manifest_hash'])}, "
            f"{_lean_str(r['approver'])}⟩")

def gen_lean(manifest: dict, base: Path = BASE) -> None:
    """受控转换（P1-2）：manifest → Lean 常量文件。currentTuple / currentApproved /
    currentCandidateApprover / currentRegistry 全部从 release_candidate 真实生成（不再写死）。

    生成即验证 R1 把制造资格判定与 approval_state 恒等绑定：若数据自相矛盾
    （APPROVED 但注册表无精确记录 / release、哈希、批准人任一不符），
    `by decide` 会证明该断言为假 → 编译失败 → 生成被拒。预测与复核分层：生成器
    只负责忠实投影数据，判定正确性由 Lean 独立复核。"""
    rc = manifest["release_candidate"]
    if rc.get("tuple") == {"pcb": 1, "cad": 1, "fw": 1, "bom": 1} and rc.get("approver") == "GATE-test":
        raise ValueError("真实候选与隔离测试身份重合（v1/GATE-test）——拒绝生成；请更换隔离测试标识")
    registry = [_lean_record(r) for r in (rc.get("approval_records") or [])]
    registry_lean = "[" + ", ".join(registry) + "]"
    approved = rc.get("approval_state") == "APPROVED"
    approver = rc.get("approver")
    rec_approver = approver if (approved and isinstance(approver, str) and approver) else "GATE"
    tpl = f"""import ChristmasBuddy.Version

/-! AUTO-GENERATED by m5_manifest.py v5 @ {manifest['generated_at']} — 手改无效，重建需重跑脚本。
此文件是 Release 抽象模型（Version.lean）与真实 m5_manifest.json 之间的受控转换层（MAP）。
currentTuple / currentApproved / currentCandidateApprover / currentRegistry 全部从
release_candidate 真实数据生成（Batch4.2 P1-2，不再写死）。
生成即验证 R1 把制造资格判定与 approval_state 恒等绑定：数据矛盾 = 编译失败。
若此文件与 m5_manifest.json 不一致，以 m5_manifest.json 为准并重新生成。 -/

namespace ChristmasBuddy

/-- 当前候选发布的 manifest 哈希（真实文件集合的绑定）。 -/
def currentManifestHash : String := "{rc['manifest_hash']}"

/-- 当前候选四元组（release_candidate.tuple 真实生成）。 -/
def currentTuple : ChristmasBuddy.Version.Release := {_lean_tuple(rc['tuple'])}

/-- 当前候选批准状态（approval_state 真实生成）。 -/
def currentApproved : Bool := {str(approved).lower()}

/-- 当前候选宣称的批准人（approver；UNAPPROVED 为 none）。 -/
def currentCandidateApprover : Option String := {_lean_opt_nat(approver) if approver is None else f'some {_lean_str(approver)}'}

/-- 受信任批准注册表（release_candidate.approval_records 受控生成；生产当前为空）。 -/
def currentRegistry : List ChristmasBuddy.Version.ApprovalRecord := {registry_lean}

/-- 生成即验证 R1：真实候选 × 真实注册表的制造资格 **恒等于** approval_state。
    APPROVED 而记录不精确匹配（批准人身份 / release / manifest_hash / 注册表成员任一不符）
    → 判定 false ≠ true → 编译失败。 -/
theorem r1_real_candidate_matches_approval_state :
    ChristmasBuddy.Version.manufacturingReleaseIn currentRegistry
      (⟨currentTuple, currentCandidateApprover⟩ : ChristmasBuddy.Version.ApprovedRelease)
      ⟨currentTuple, currentManifestHash, {_lean_str(rec_approver)}⟩ currentManifestHash
    = currentApproved := by decide

/-! ### 隔离测试合同（静态；不触及任何真实批准，只使用隔离标识 GATE-test/OTHER） -/

/-- 隔离测试记录：绑定当前候选哈希、v1 冻结版、批准人 GATE-test。 -/
def isolatedTestRecord : ChristmasBuddy.Version.ApprovalRecord :=
  ⟨ChristmasBuddy.Version.v1, currentManifestHash, "GATE-test"⟩

/-- 第二条隔离记录（批准人 OTHER）：注册表同时含两条，失败可归因到具体检查项。 -/
def isolatedTestRecordOther : ChristmasBuddy.Version.ApprovalRecord :=
  ⟨ChristmasBuddy.Version.v1, currentManifestHash, "OTHER"⟩

/-- 隔离测试注册表（非生产注册表；仅存在于本生成文件）。 -/
def isolatedTestRegistry : List ChristmasBuddy.Version.ApprovalRecord :=
  [isolatedTestRecord, isolatedTestRecordOther]

/-- P0-1 案例 A（正向）：候选批准人 = 记录批准人 = GATE-test，记录已注册 → 可制造。 -/
theorem reg_caseA_approver_exact_match :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedTestRegistry
      (⟨ChristmasBuddy.Version.v1, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord currentManifestHash = true := by decide

/-- P0-1 案例 B（负向）：候选批准人 GATE-test ≠ 记录批准人 OTHER → 不可制造。
    （OTHER 记录也在注册表中——失败只能归因于批准人身份精确匹配检查。） -/
theorem reg_caseB_approver_identity_mismatch :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedTestRegistry
      (⟨ChristmasBuddy.Version.v1, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecordOther currentManifestHash = false := by decide

/-- 空字符串批准人不可制造（记录自含注册、字段精确匹配，仅批准人为空）。 -/
theorem reg_caseC_empty_approver :
    ChristmasBuddy.Version.manufacturingReleaseIn
      [⟨ChristmasBuddy.Version.v1, currentManifestHash, ""⟩]
      (⟨ChristmasBuddy.Version.v1, some ""⟩ : ChristmasBuddy.Version.ApprovedRelease)
      ⟨ChristmasBuddy.Version.v1, currentManifestHash, ""⟩ currentManifestHash = false := by decide

/-- P1-1 案例 3：记录已注册（自含注册表）但 manifest_hash 与当前候选不符 → 不可制造。 -/
theorem reg_case3_hash_mismatch :
    ChristmasBuddy.Version.manufacturingReleaseIn
      [⟨ChristmasBuddy.Version.v1, "stale-hash", "GATE-test"⟩]
      (⟨ChristmasBuddy.Version.v1, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      ⟨ChristmasBuddy.Version.v1, "stale-hash", "GATE-test"⟩ currentManifestHash = false := by decide

/-- P1-1 案例 4：记录已注册但绑定不同 release → 不可制造（旧批准不越版本）。 -/
theorem reg_case4_release_mismatch :
    ChristmasBuddy.Version.manufacturingReleaseIn
      [⟨⟨some 2, some 1, some 1, some 1⟩, currentManifestHash, "GATE-test"⟩]
      (⟨ChristmasBuddy.Version.v1, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      ⟨⟨some 2, some 1, some 1, some 1⟩, currentManifestHash, "GATE-test"⟩ currentManifestHash
    = false := by decide

/-- P1-1 案例 5：字段全部正确但批准记录未在注册表 → 不可制造。 -/
theorem reg_case5_record_unregistered :
    ChristmasBuddy.Version.manufacturingReleaseIn [isolatedTestRecordOther]
      (⟨ChristmasBuddy.Version.v1, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord currentManifestHash = false := by decide

/-- P1-1 案例 6：注册表为空（生产现状）→ 任何候选都不可制造。 -/
theorem reg_case6_empty_registry :
    ChristmasBuddy.Version.manufacturingReleaseIn []
      (⟨ChristmasBuddy.Version.v1, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord currentManifestHash = false := by decide

/-- 生成即验证 R2：隔离测试注册表不得让真实候选取得制造资格（身份隔离守卫）。 -/
theorem r2_isolated_registry_cannot_approve_real_candidate :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedTestRegistry
      (⟨currentTuple, currentCandidateApprover⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord currentManifestHash = false := by decide

end ChristmasBuddy
"""
    out = base / "proof/src/ChristmasBuddy/ReleaseCurrent.lean"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(tpl + "\n", encoding="utf-8")

def load() -> dict:
    return json.loads((BASE / "m5_manifest.json").read_text(encoding="utf-8"))

def check(base: Path = BASE, manifest_path: Path | None = None) -> None:
    m = json.loads((manifest_path or (base / "m5_manifest.json")).read_text(encoding="utf-8"))
    bad = []
    for it in m["artifacts"]:
        p = base / it["path"]
        if it.get("kind") == "directory":
            if not p.exists():
                bad.append(f"{it['path']}: 目录工件丢失")
            else:
                cur = directory_manifest(p, base)["dir_sha256"]
                if cur != it["sha256"]:
                    bad.append(f"{it['path']}: 目录哈希漂移（→ 新候选）")
            continue
        if not p.exists():
            bad.append(f"{it['path']}: 已登记工件丢失")
        elif sha256(p) != it["sha256"]:
            bad.append(f"{it['path']}: 哈希漂移（→ 新 release 候选，须重建 + 重新门禁）")
    for e in bom_netlist_consistency(base):
        bad.append(f"BOM↔网表一致性: {e}")
    for e in approval_consistency(m.get("release_candidate", {})):
        bad.append(f"批准治理: {e}")
    appeared = [it["path"] for it in m["not_yet"] if (base / it["path"]).exists()]
    if appeared:
        bad.append(f"NOT_YET 工件已出现（须重跑 build 升级为 BOUND）: {appeared[:3]}")
    stored = m.get("release_candidate", {}).get("manifest_hash")
    rehash = canonical_hash(m)  # P0-2：与 build 共用同一 canonical_payload/canonical_hash
    if stored != rehash:
        bad.append(f"canonical hash 不一致：manifest 登记 {stored[:12]}… ≠ 独立重算 {rehash[:12]}…"
                   "（候选被篡改或 hash_basis 字段漂移）")
    lean_out = base / "proof/src/ChristmasBuddy/ReleaseCurrent.lean"
    if lean_out.exists():
        lean = lean_out.read_text(encoding="utf-8")
        want = rehash
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
