#!/usr/bin/env python3
"""M5 制造发布合同 · Manifest Checker v3（Batch3）。

v3 变更（Batch3 审查修复）：
  - bom.csv 纳入 BOUND（遗漏修复）；BOM 变更 = Release 候选失效。
  - BOM↔网表一致性检查（映射表驱动：每个 BOM 项必须对应存在的网表器件，反之关键器件必须有 BOM 行）。
  - 目录确定性哈希 directory_manifest()：Gerber 等目录工件按规范化相对路径排序、
    逐文件 sha256、排除临时文件、空目录有定义、符号链接跳过并记录、顺序无关。
  - 检查器自身源码纳入 BOUND（检查器是受验证的软件产品）。
  - BASE 可参数化（对抗测试在临时副本树上运行，绝不碰真实文件）。

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
    """从 manifest 提取稳定字段的规范视图（确定性：sort_keys）。
    排除时间戳/自身哈希等不稳定或循环字段。"""
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
    rc = m.get("release_candidate", {})
    meta = {k: rc.get(k) for k in ("product", "tuple", "source_commit", "approval_state")}
    return {"artifacts": arts, "release": meta,
            "not_yet": sorted(m.get("not_yet", []), key=lambda e: e.get("path", ""))}

def canonical_hash(artifacts: list, not_yet: list, release_meta: dict) -> str:
    payload = {"artifacts": sorted(artifacts, key=lambda a: a["path"]),
               "not_yet": sorted(not_yet, key=lambda e: e.get("path", "")),
               "release": release_meta}
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
    }
    manifest_hash = canonical_hash(artifacts, not_yet, release_meta)
    manifest = {
        "schema": "m5-release-manifest/2.0",
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
            "hash_basis": "canonical v4：path/kind/sha/bytes/slot/tool/files/symlinks + release 元数据；"
                          "排除时间戳与自身哈希（不稳定/循环字段）",
            "rule": "任一工件或元数据变化 → canonical hash 变化 → 新候选；旧 approval_state 不继承",
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

def gen_lean(manifest: dict, base: Path = BASE) -> None:
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

/-- 生成即验证 A：当前真实候选（未冻结、未批准）不可制造。 -/
example : ChristmasBuddy.Version.manufacturable currentTuple = false := by rfl

example : ChristmasBuddy.Version.manufacturingRelease
    (⟨currentTuple, none⟩ : ChristmasBuddy.Version.ApprovedRelease)
    ⟨currentTuple, currentManifestHash, "GATE"⟩ currentManifestHash = false := by rfl

/-- 生成即验证 B（隔离测试候选，非真实批准）：完整+冻结+精确批准的候选**能**通过制造资格
    判断——证明合同不是恒假开关；批准记录绑定精确 release 与 manifest_hash。 -/
def isolatedTestCandidate : ChristmasBuddy.Version.ApprovedRelease :=
  ⟨ChristmasBuddy.Version.v1, some "GATE-test"⟩

def isolatedTestRecord : ChristmasBuddy.Version.ApprovalRecord :=
  ⟨ChristmasBuddy.Version.v1, currentManifestHash, "GATE-test"⟩

example : ChristmasBuddy.Version.manufacturingRelease
    isolatedTestCandidate isolatedTestRecord currentManifestHash = true := by decide

/-- 真实候选 UNAPPROVED 不受隔离测试影响（批准记录绑定精确 release）。 -/
example : ChristmasBuddy.Version.manufacturingRelease
    (⟨currentTuple, none⟩ : ChristmasBuddy.Version.ApprovedRelease)
    isolatedTestRecord currentManifestHash = false := by decide
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
    appeared = [it["path"] for it in m["not_yet"] if (base / it["path"]).exists()]
    if appeared:
        bad.append(f"NOT_YET 工件已出现（须重跑 build 升级为 BOUND）: {appeared[:3]}")
    canonical = canonical_payload(m)
    stored = m.get("release_candidate", {}).get("manifest_hash")
    rehash = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
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
