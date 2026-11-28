#!/usr/bin/env python3
"""M5 制造发布合同 · Manifest Checker v6（Batch4.3）：双层哈希 + 动态版本冻结。

v6 变更（PR #37 Review #4727422072：批准记录哈希固定点 + 动态冻结）：
  - **双层哈希模型**（解环）：
      release_hash  = SHA256(canonical(product, tuple, source_commit, artifacts, not_yet))
                      —— 产品发布内容身份；不含 approval_state/approver/approval_records/
                         manifest_hash/release_hash（批准元数据与循环字段一律不入）。
      manifest_hash = SHA256(canonical(release_hash, frozen_registry, approval_state,
                                       approver, approval_records))
                      —— 完整发布清单封套完整性；含 release_hash 值但不含自身，无自引用。
    批准记录绑定 release_hash（内容身份）而非 manifest_hash（封套）——
    旧模型 H=SHA256(Payload(H)) 的固定点不存在了，合法批准可以实际生成与核验。
  - release-spec.json 成为受控版本输入（tuple/frozen_registry/approval_state/approver/
    approval_records）；build 从其读取，不再硬编码空四元组。
    release-spec.json **不**进 ARTIFACT_TABLE（否则批准元数据进入 release_hash 基线，
    固定点回归）；其完整性由 check() 的 spec↔manifest 一致性比对承担。
  - frozen_registry（动态冻结注册表）成为 manifest 字段并经 gen_lean 生成
    currentFrozenRegistry；制造资格要求候选精确在册。
  - check 顺序（任何异常都不静默 PASS）：读真实工件 → 重算 release_hash → 工件/目录哈希 →
    批准记录精确匹配 → 注册表与冻结成员资格 → 重算 manifest_hash → spec 一致性 →
    ReleaseCurrent.lean 数据绑定 → PASS/FAIL。

v3-v5 既有的（保留）：
  - bom.csv 纳入 BOUND；BOM↔网表一致性；目录确定性哈希 directory_manifest()
    （符号链接按完整相对路径排序——PR#36 Review #4727196824）。
  - 批准人身份精确匹配（PR#36 Review #4727196821）；gen_lean 真实数据映射；
    BASE 可参数化（对抗测试在临时副本树上运行，绝不碰真实文件）。

与 Lean 的分工（三层不得混淆）：Lean 证抽象合同与结构一致性（Version.lean）；
本脚本证 SHA256 与真实文件绑定（TESTED 层）；工作台 GATE 负责现实授权。
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

# 文档性登记：两个 canonical payload 均**手工挑选**字段；以下字段不入 release 内容基线
# （frozen_registry/approval_* 属封套基线；manifest_hash 为循环字段永不入任何基线；
#  release_hash 只入封套基线——批准绑定值，不入自身内容基线）。
CANONICAL_EXCLUDE = {"generated_at", "date", "manifest_hash", "hash_basis", "rule", "note",
                     "tuple_state", "schema", "frozen_registry", "approval_state", "approver",
                     "approval_records", "release_hash"}

def _norm_artifacts(m: dict) -> list:
    """工件数组规范化（release_hash 与旧实现共享的确定性规则）：
    artifacts 按完整相对路径排序；目录工件 files/skipped_symlinks 按完整相对路径排序。"""
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
    return arts

def _json_key(v) -> str:
    return json.dumps(v, sort_keys=True, ensure_ascii=False)

def canonical_release_payload(m: dict) -> dict:
    """**Release Content 哈希输入**（双层之一；build/check 共用本唯一实现）。

    覆盖：product、version_tuple、source_commit、artifacts、not_yet。
    **不得包含**：approval_state / approver / approval_records / manifest_hash / release_hash
    （批准元数据不入内容身份——否则批准记录哈希固定点回归，PR#37 Review #4727422072）。
    数组规范化：artifacts/files/skipped_symlinks/not_yet 全按完整相对路径排序。"""
    rc = m.get("release_candidate", {})
    return {"artifacts": _norm_artifacts(m),
            "release": {"product": rc.get("product"), "tuple": rc.get("tuple"),
                        "source_commit": rc.get("source_commit")},
            "not_yet": sorted(m.get("not_yet", []), key=lambda e: e.get("path", ""))}

def release_hash(m: dict) -> str:
    """release_hash = SHA256(canonical_release_payload)——产品发布内容身份。
    工件或四元组变化 → release_hash 变化 → 旧批准失效（批准记录绑定的就是本值）。"""
    return hashlib.sha256(
        json.dumps(canonical_release_payload(m), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

def canonical_manifest_payload(m: dict) -> dict:
    """**Manifest Envelope 哈希输入**（双层之二；build/check 共用本唯一实现）。

    覆盖：release_hash（内容身份的绑定值）、frozen_registry、approval_state、approver、
    approval_records。含 release_hash 值但**不含 manifest_hash 自身**——无自引用/无循环。
    语义无序数组规范化：frozen_registry / approval_records 按其 JSON 规范形式排序。"""
    rc = m.get("release_candidate", {})
    frozen = sorted(rc.get("frozen_registry") or [], key=_json_key)
    records = sorted(rc.get("approval_records") or [], key=_json_key)
    return {"release_hash": rc.get("release_hash"),
            "frozen_registry": frozen,
            "approval_state": rc.get("approval_state"),
            "approver": rc.get("approver"),
            "approval_records": records}

def manifest_hash(m: dict) -> str:
    """manifest_hash = SHA256(canonical_manifest_payload)——完整清单封套完整性。
    release_hash/批准状态/批准人/批准记录/冻结注册表任一变化 → 封套变化（新清单）。"""
    return hashlib.sha256(
        json.dumps(canonical_manifest_payload(m), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

def load_release_spec(base: Path) -> dict:
    """读取受控版本输入 release-spec.json。缺失即异常（版本输入无受控来源，禁止静默默认）。"""
    p = base / "release-spec.json"
    if not p.exists():
        raise FileNotFoundError(f"{p} 缺失——build 拒绝在无受控版本输入时生成候选")
    spec = json.loads(p.read_text(encoding="utf-8"))
    if spec.get("schema") != "release-spec/1.0":
        raise ValueError(f"release-spec.json schema={spec.get('schema')!r} 不受支持（须 release-spec/1.0）")
    for key in ("product", "tuple", "frozen_registry", "approval_state", "approver",
                "approval_records"):
        if key not in spec:
            raise ValueError(f"release-spec.json 缺少受控字段 {key}")
    if spec["approval_state"] not in ("UNAPPROVED", "APPROVED"):
        raise ValueError(f"approval_state={spec['approval_state']!r} 非法（UNAPPROVED/APPROVED）")
    frozen = spec["frozen_registry"]
    seen = set()
    for r in frozen:
        if not (isinstance(r, dict) and all(isinstance(r.get(k), int) for k in
                                            ("pcb", "cad", "fw", "bom"))):
            raise ValueError(f"frozen_registry 条目 {r!r} 非完整四元组（GATE 只能冻结完整发布）")
        k = _json_key(r)
        if k in seen:
            raise ValueError(f"frozen_registry 重复条目 {r!r}")
        seen.add(k)
    if spec["approval_state"] == "APPROVED" and not (
            isinstance(spec.get("approver"), str) and spec["approver"]):
        raise ValueError("APPROVED 需要 approver（非空字符串）")
    return spec

def scan_artifacts(base: Path) -> tuple[list, list]:
    """扫描真实工件（build 与 check 共用同一扫描实现——check 的 release_hash 重算
    必须基于**实时**文件内容，而非 manifest 内存储的哈希）。返回 (artifacts, not_yet)。"""
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
    return artifacts, not_yet

def build(base: Path = BASE) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    spec = load_release_spec(base)  # 受控版本输入（缺失/结构非法即异常，绝不静默默认）
    artifacts, not_yet = scan_artifacts(base)
    # —— 双层哈希（先内容后封套，无自引用）——
    staged = {"artifacts": artifacts, "not_yet": not_yet,
              "release_candidate": {"product": spec["product"], "tuple": spec["tuple"],
                                    "source_commit": git_commit()}}
    rc = staged["release_candidate"]
    hr = release_hash(staged)
    rc["release_hash"] = hr
    rc.update({"frozen_registry": spec["frozen_registry"],
               "approval_state": spec["approval_state"],
               "approver": spec["approver"],
               "approval_records": spec["approval_records"]})
    hm = manifest_hash(staged)
    rc["manifest_hash"] = hm
    manifest = {
        "schema": "m5-release-manifest/3.0",
        "product": spec["product"],
        "date": date.today().isoformat(),
        "generated_at": now,
        "release_candidate": {
            "product": rc["product"],
            "tuple": rc["tuple"],
            "tuple_state": ("由 release-spec.json 受控生成（冻结注册表见 frozen_registry）"
                            if spec["approval_state"] == "APPROVED" else
                            "preresearch（版本由 release-spec.json 控制；冻结须 GATE 门禁人工批准）"),
            "source_commit": rc["source_commit"],
            "release_hash": hr,
            "manifest_hash": hm,
            "approval_state": rc["approval_state"],
            "approver": rc["approver"],
            "approval_records": rc["approval_records"],
            "frozen_registry": rc["frozen_registry"],
            "hash_basis": "双层哈希 v6：release_hash=SHA256(canonical(product,tuple,source_commit,"
                          "artifacts,not_yet))=产品内容身份（批准绑定层）；manifest_hash=SHA256("
                          "canonical(release_hash,frozen_registry,approval_state,approver,"
                          "approval_records))=清单封套完整性。批准元数据不入内容基线、"
                          "manifest_hash 不入任何基线（无自引用/无固定点）；"
                          "全部数组按完整相对路径或语义键规范化；build/check 共用唯一实现",
            "rule": "工件或四元组变化 → release_hash 变 → 旧批准失效；"
                    "批准状态/批准人/批准记录/冻结注册表变化 → manifest_hash 变（release_hash 不变）",
        },
        "artifacts": artifacts,
        "not_yet": not_yet,
        "note": "NOT_YET 工件不携带任何哈希（禁止虚构占位）；OB-1 义务待真实 EDA 工程产出解除。",
    }
    (base / "m5_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    gen_lean(manifest, base)
    print(f"m5_manifest build: {len(artifacts)} BOUND, {len(not_yet)} NOT_YET, "
          f"release_hash={hr[:12]}…, manifest_hash={hm[:12]}…, {rc['approval_state']}")
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
    """批准治理（受信任注册表边界，Batch4.3 更新为双层哈希语义）：
    APPROVED ⇔ 注册表中存在与当前候选**精确一致**（release 四元组 + release_hash +
    批准人三元全等）且批准人非空的记录；UNAPPROVED 则不得有任何批准记录；
    APPROVED 候选还必须精确在冻结注册表中。

    外部信任边界：本函数只校验**记录结构一致性**；现实中批准人的身份与授权真实性
    由工作台 GATE 门禁与受控批准流程负责——脚本与 Lean 都无法验证现实中人的身份。
    （独立函数便于对抗测试做故障注入：禁用后诊断必须消失，否则套件 FAIL。）"""
    errs = []
    records = rc.get("approval_records") or []
    approved = rc.get("approval_state") == "APPROVED"

    def exact(r) -> bool:
        return (isinstance(r, dict)
                and r.get("release") == rc.get("tuple")
                and r.get("releaseHash") == rc.get("release_hash")
                and isinstance(r.get("approver"), str) and r["approver"] != ""
                and r.get("approver") == rc.get("approver"))

    if approved:
        if not any(exact(r) for r in records):
            errs.append("批准状态与批准记录矛盾：APPROVED 但注册表中无与当前候选精确一致的"
                        "批准记录（release+release_hash+approver 三元精确、批准人非空）")
        frozen = rc.get("frozen_registry") or []
        if not any(_json_key(r) == _json_key(rc.get("tuple")) for r in frozen):
            errs.append("冻结注册表缺少候选：APPROVED 但当前四元组不在 frozen_registry 中"
                        "（GATE 须先冻结该版本组合）")
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
    for k, t in (("release", dict), ("releaseHash", str), ("approver", str)):
        if not isinstance(r.get(k), t):
            raise ValueError(f"approval_records 条目结构非法：{r!r}（{k} 须为 {t.__name__}）")
    if not r["approver"]:
        raise ValueError("approval_records 条目 approver 为空——拒绝生成（空标识不是有效批准人）")
    return (f"⟨{_lean_tuple(r['release'])}, {_lean_str(r['releaseHash'])}, "
            f"{_lean_str(r['approver'])}⟩")

# 隔离测试身份（混合版本 PCB=2 CAD=1 FW=3 BOM=2；与生产候选重合时拒绝生成）
MIXED_TEST_TUPLE = {"pcb": 2, "cad": 1, "fw": 3, "bom": 2}

def gen_lean(manifest: dict, base: Path = BASE) -> None:
    """受控转换（Batch4.2 P1-2 + Batch4.3）：manifest → Lean 常量文件。
    currentTuple / currentApproved / currentCandidateApprover / currentRegistry /
    currentFrozenRegistry / currentReleaseHash / currentManifestHash 全部从
    release_candidate 真实生成（不再写死；冻结注册表由 release-spec 经 manifest 受控生成）。

    生成即验证 R1 把制造资格判定与 approval_state 恒等绑定：若数据自相矛盾
    （APPROVED 但注册表无精确记录 / release_hash、冻结注册表、批准人任一不符），
    `by decide` 会证明该断言为假 → 编译失败 → 矛盾数据被拒。生成器只负责忠实投影
    数据，判定正确性由 Lean 独立复核。"""
    rc = manifest["release_candidate"]
    if rc.get("tuple") == MIXED_TEST_TUPLE and rc.get("approver") == "GATE-test":
        raise ValueError("真实候选与隔离测试身份重合（混合版本/GATE-test）——拒绝生成；请更换隔离测试标识")
    frozen = ", ".join(_lean_tuple(r) for r in (rc.get("frozen_registry") or []))
    frozen_lean = "[" + frozen + "]" if frozen else "[]"
    registry = [_lean_record(r) for r in (rc.get("approval_records") or [])]
    registry_lean = "[" + ", ".join(registry) + "]"
    approved = rc.get("approval_state") == "APPROVED"
    approver = rc.get("approver")
    rec_approver = approver if (approved and isinstance(approver, str) and approver) else "GATE"
    tpl = f"""import ChristmasBuddy.Version

/-! AUTO-GENERATED by m5_manifest.py v6 @ {manifest['generated_at']} — 手改无效，重建需重跑脚本。
此文件是 Release 抽象模型（Version.lean）与真实 m5_manifest.json 之间的受控转换层（MAP）。
currentTuple / currentApproved / currentCandidateApprover / currentRegistry /
currentFrozenRegistry / currentReleaseHash / currentManifestHash 全部从 release_candidate
真实数据生成（双层哈希：批准绑定 release_hash，manifest_hash 仅为封套身份，两者不得混用）。
生成即验证 R1 把制造资格判定与 approval_state 恒等绑定：数据矛盾 = 编译失败。
若此文件与 m5_manifest.json 不一致，以 m5_manifest.json 为准并重新生成。 -/

namespace ChristmasBuddy

/-- 当前候选的 **release_hash**（产品内容身份；批准记录绑定本值）。 -/
def currentReleaseHash : String := "{rc['release_hash']}"

/-- 当前候选的 **manifest_hash**（清单封套完整性；与 release_hash 语义不得混用）。 -/
def currentManifestHash : String := "{rc['manifest_hash']}"

/-- 当前候选四元组（release_candidate.tuple 真实生成）。 -/
def currentTuple : ChristmasBuddy.Version.Release := {_lean_tuple(rc['tuple'])}

/-- 当前冻结注册表（release_candidate.frozen_registry 受控生成；生产当前为空）。 -/
def currentFrozenRegistry : List ChristmasBuddy.Version.Release := {frozen_lean}

/-- 当前候选批准状态（approval_state 真实生成）。 -/
def currentApproved : Bool := {str(approved).lower()}

/-- 当前候选宣称的批准人（approver；UNAPPROVED 为 none）。 -/
def currentCandidateApprover : Option String := {_lean_opt_nat(approver) if approver is None else f'some {_lean_str(approver)}'}

/-- 受信任批准注册表（release_candidate.approval_records 受控生成；生产当前为空）。 -/
def currentRegistry : List ChristmasBuddy.Version.ApprovalRecord := {registry_lean}

/-- 生成即验证 R1：真实候选 × 真实冻结注册表 × 真实批准注册表的制造资格
    **恒等于** approval_state（批准绑定 **release_hash**）。
    APPROVED 而记录不精确匹配（批准人身份 / release / release_hash / 冻结注册表 /
    批准注册表任一不符）→ 判定 false ≠ true → 编译失败。 -/
theorem r1_real_candidate_matches_approval_state :
    ChristmasBuddy.Version.manufacturingReleaseIn currentFrozenRegistry currentRegistry
      currentReleaseHash
      (⟨currentTuple, currentCandidateApprover⟩ : ChristmasBuddy.Version.ApprovedRelease)
      ⟨currentTuple, currentReleaseHash, {_lean_str(rec_approver)}⟩
    = currentApproved := by decide

/-! ### 隔离测试合同（静态；不触及任何真实批准，只使用隔离标识 GATE-test/OTHER） -/

/-- 隔离混合版本候选（PCB=2 CAD=1 FW=3 BOM=2）：证明各组件版本可独立演进，
    不把所有组件限定为同一版本号。 -/
def mixedTestRelease : ChristmasBuddy.Version.Release := ⟨some 2, some 1, some 3, some 2⟩

/-- 隔离测试记录：绑定混合版本与当前候选的 release_hash、批准人 GATE-test。 -/
def isolatedTestRecord : ChristmasBuddy.Version.ApprovalRecord :=
  ⟨mixedTestRelease, currentReleaseHash, "GATE-test"⟩

/-- 第二条隔离记录（批准人 OTHER）：注册表同时含两条，失败可归因到具体检查项。 -/
def isolatedTestRecordOther : ChristmasBuddy.Version.ApprovalRecord :=
  ⟨mixedTestRelease, currentReleaseHash, "OTHER"⟩

/-- 隔离冻结注册表（非生产注册表；仅存在于本生成文件）。 -/
def isolatedFrozenRegistry : List ChristmasBuddy.Version.Release := [mixedTestRelease]

/-- 隔离批准注册表（非生产注册表；仅存在于本生成文件）。 -/
def isolatedTestRegistry : List ChristmasBuddy.Version.ApprovalRecord :=
  [isolatedTestRecord, isolatedTestRecordOther]

/-- 混合版本正向：完整 + 冻结 + 批准人精确一致 + release_hash 精确一致 + 已注册
    → 可制造（合法批准完整通过；组件版本独立演进）。 -/
theorem reg_mixed_exact_match :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedFrozenRegistry isolatedTestRegistry
      currentReleaseHash
      (⟨mixedTestRelease, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = true := by decide

/-- 批准人身份不符（GATE-test vs OTHER，OTHER 已注册）→ 不可制造。 -/
theorem reg_mixed_approver_mismatch :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedFrozenRegistry isolatedTestRegistry
      currentReleaseHash
      (⟨mixedTestRelease, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecordOther = false := by decide

/-- 空字符串批准人不可制造（记录自含注册、字段精确匹配，仅批准人为空）。 -/
theorem reg_mixed_empty_approver :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedFrozenRegistry
      [⟨mixedTestRelease, currentReleaseHash, ""⟩] currentReleaseHash
      (⟨mixedTestRelease, some ""⟩ : ChristmasBuddy.Version.ApprovedRelease)
      ⟨mixedTestRelease, currentReleaseHash, ""⟩ = false := by decide

/-- 批准记录绑定**旧 release_hash** → 不可制造（双层哈希：内容已变，旧批准失效）。 -/
theorem reg_mixed_stale_release_hash :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedFrozenRegistry
      [⟨mixedTestRelease, "stale-release-hash", "GATE-test"⟩] currentReleaseHash
      (⟨mixedTestRelease, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      ⟨mixedTestRelease, "stale-release-hash", "GATE-test"⟩ = false := by decide

/-- 冻结注册表缺少候选（注册表只有 v1，候选是混合版本）→ 不可制造。 -/
theorem reg_mixed_not_frozen :
    ChristmasBuddy.Version.manufacturingReleaseIn [ChristmasBuddy.Version.v1]
      isolatedTestRegistry currentReleaseHash
      (⟨mixedTestRelease, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

/-- 冻结注册表为空（生产现状）→ 任何候选都不可制造。 -/
theorem reg_mixed_empty_frozen :
    ChristmasBuddy.Version.manufacturingReleaseIn [] isolatedTestRegistry
      currentReleaseHash
      (⟨mixedTestRelease, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

/-- 字段全部正确但批准记录未在注册表 → 不可制造。 -/
theorem reg_mixed_unregistered :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedFrozenRegistry
      [isolatedTestRecordOther] currentReleaseHash
      (⟨mixedTestRelease, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

/-- PCB 版本变化（2→3）：新版本已冻结，但旧批准记录仍绑定旧版本 → 不可制造。 -/
theorem reg_pcb_bump_invalidates :
    ChristmasBuddy.Version.manufacturingReleaseIn
      [mixedTestRelease, ⟨some 3, some 1, some 3, some 2⟩] isolatedTestRegistry
      currentReleaseHash
      (⟨⟨some 3, some 1, some 3, some 2⟩, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

/-- CAD 版本变化（1→2）：旧批准记录仍绑定旧版本 → 不可制造。 -/
theorem reg_cad_bump_invalidates :
    ChristmasBuddy.Version.manufacturingReleaseIn
      [mixedTestRelease, ⟨some 2, some 2, some 3, some 2⟩] isolatedTestRegistry
      currentReleaseHash
      (⟨⟨some 2, some 2, some 3, some 2⟩, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

/-- FW 版本变化（3→4）：旧批准记录仍绑定旧版本 → 不可制造。 -/
theorem reg_fw_bump_invalidates :
    ChristmasBuddy.Version.manufacturingReleaseIn
      [mixedTestRelease, ⟨some 2, some 1, some 4, some 2⟩] isolatedTestRegistry
      currentReleaseHash
      (⟨⟨some 2, some 1, some 4, some 2⟩, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

/-- BOM 版本变化（2→3）：旧批准记录仍绑定旧版本 → 不可制造。 -/
theorem reg_bom_bump_invalidates :
    ChristmasBuddy.Version.manufacturingReleaseIn
      [mixedTestRelease, ⟨some 2, some 1, some 3, some 3⟩] isolatedTestRegistry
      currentReleaseHash
      (⟨⟨some 2, some 1, some 3, some 3⟩, some "GATE-test"⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

/-- 生成即验证 R2：隔离测试注册表不得让真实候选取得制造资格（身份隔离守卫）。 -/
theorem r2_isolated_registry_cannot_approve_real_candidate :
    ChristmasBuddy.Version.manufacturingReleaseIn isolatedFrozenRegistry isolatedTestRegistry
      currentReleaseHash
      (⟨currentTuple, currentCandidateApprover⟩ : ChristmasBuddy.Version.ApprovedRelease)
      isolatedTestRecord = false := by decide

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

    def fmt12(v) -> str:
        return (v if isinstance(v, str) else "None")[:12]

    # 1/3. 真实工件层：逐工件哈希 + 目录哈希
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
    # 2. release_hash 独立重算（内容身份）：基于**实时扫描**的工件 + manifest 四元组，
    #    与批准元数据无关——双层解耦的核对点；文件漂移在此聚合暴露。
    rc = m.get("release_candidate", {})
    live_arts, live_ny = scan_artifacts(base)
    live_staged = {"artifacts": live_arts, "not_yet": live_ny,
                   "release_candidate": {"product": rc.get("product"),
                                         "tuple": rc.get("tuple"),
                                         "source_commit": rc.get("source_commit")}}
    stored_rh = rc.get("release_hash")
    recomputed_rh = release_hash(live_staged)
    if stored_rh != recomputed_rh:
        bad.append(f"release_hash 不一致：登记 {fmt12(stored_rh)}… ≠ 实时重算 {recomputed_rh[:12]}…"
                   "（内容或四元组已变 → 旧批准失效，须重建并重新 GATE）")
    # 4/5. 批准记录精确匹配 + 注册表/冻结成员资格
    for e in bom_netlist_consistency(base):
        bad.append(f"BOM↔网表一致性: {e}")
    for e in approval_consistency(rc):
        bad.append(f"批准治理: {e}")
    appeared = [it["path"] for it in m["not_yet"] if (base / it["path"]).exists()]
    if appeared:
        bad.append(f"NOT_YET 工件已出现（须重跑 build 升级为 BOUND）: {appeared[:3]}")
    # 6. manifest_hash（封套）独立重算
    stored_hm = rc.get("manifest_hash")
    recomputed_hm = manifest_hash(m)
    if stored_hm != recomputed_hm:
        bad.append(f"manifest_hash 不一致：登记 {fmt12(stored_hm)}… ≠ 重算 {recomputed_hm[:12]}…"
                   "（封套被篡改或字段漂移）")
    # release-spec 一致性：受控输入 ↔ 生成清单（禁止手改 Manifest 伪造冻结版本）
    try:
        spec = load_release_spec(base)
        diffs = [k for k in ("product", "tuple", "approval_state", "approver",
                             "approval_records", "frozen_registry")
                 if _json_key(spec.get(k)) != _json_key(rc.get(k))]
        if diffs:
            bad.append(f"release-spec 不一致（{', '.join(diffs)}）——受控版本输入已变，须重新 build")
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        bad.append(f"release-spec 不可用: {e}")
    # 7. ReleaseCurrent.lean 数据绑定
    lean_out = base / "proof/src/ChristmasBuddy/ReleaseCurrent.lean"
    if lean_out.exists():
        lean = lean_out.read_text(encoding="utf-8")
        if f'"{recomputed_rh}"' not in lean:
            bad.append("ReleaseCurrent.lean 与 release_hash 不一致（须重新 gen-lean）")
        if f'"{recomputed_hm}"' not in lean:
            bad.append("ReleaseCurrent.lean 与 manifest_hash 不一致（须重新 gen-lean）")
        if rc.get("approval_state") != "UNAPPROVED" and "currentApproved : Bool := false" in lean:
            bad.append("approval_state 已变更但 Lean 常量未更新")
    else:
        bad.append("ReleaseCurrent.lean 缺失（须重跑 build 生成）")
    # 8. 结论
    if bad:
        print("m5_manifest check: FAIL")
        for b in bad:
            print("  !", b)
        sys.exit(1)
    print(f"m5_manifest check: PASS — {len(m['artifacts'])} BOUND / {len(m['not_yet'])} NOT_YET，"
          f"release_hash={recomputed_rh[:12]}… manifest_hash={recomputed_hm[:12]}… "
          f"{rc.get('approval_state')}")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    (build if mode == "build" else check)()
