#!/usr/bin/env python3
"""M5→Lean 受控生成 + 双层哈希批准全链测试（Batch4.3）。

**正向必须同时满足 Python Checker 与 Lean**（PR#37 Review #4727422072 指出旧 B 案例
只做 Lean 编译、未跑 M5.check——本版修正为完整链路）：

  隔离测试 Manifest → 生成 release_hash → 创建绑定 release_hash 的批准记录
  → 计算 manifest_hash → 生成 ReleaseCurrent.lean → M5.check → Lean 编译 → 公理审计。

负向案例（每个独立临时目录，单一变异）：
  N1 批准记录绑定旧 release_hash      → 治理 FAIL + Lean 编译 FAIL
  N2 修改 PCB 工件（netlist.json）    → 漂移 + release_hash 实时重算 FAIL（Python 层职责）
  N3 修改 BOM（bom.csv）              → 漂移 + release_hash 实时重算 FAIL（Python 层职责）
  N4 修改批准人（alice→bob）          → 治理 FAIL + Lean 编译 FAIL
  N5 修改四元组                       → 治理 FAIL（旧批准不继承）+ Lean 编译 FAIL
  N6 删除批准记录（保持 APPROVED）    → 治理 FAIL + Lean 编译 FAIL
  N7 伪造 manifest_hash（手改清单）   → 封套重算 FAIL（Python 层职责）
  N8 修改批准状态（APPROVED→UNAPPROVED 留记录）→ 治理 FAIL（Lean 自洽，编译通过）

FI 故障注入：禁用 approval_consistency 后治理诊断必须消失（否则套件 FAIL）。
守卫：真实生产候选保持 UNAPPROVED（本套件绝不写真实 m5_manifest.json / release-spec.json /
ReleaseCurrent.lean）。

运行：python3 source-data/christmas-buddy/manifest_lean_gen_tests.py
（前置：proof 已 lake build——Version.olean 需为最新，A 案例编译即校验。）
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).parent
PROOF = SRC / "proof"
sys.path.insert(0, str(SRC))
import m5_manifest as M5  # noqa: E402

MIXED = {"pcb": 2, "cad": 1, "fw": 3, "bom": 2}   # 混合版本：各组件独立演进
WHITELIST = {"propext", "Classical.choice", "Quot.sound"}
GEN_THEOREMS = [
    "ChristmasBuddy.r1_real_candidate_matches_approval_state",
    "ChristmasBuddy.r2_isolated_registry_cannot_approve_real_candidate",
    "ChristmasBuddy.reg_mixed_exact_match",
    "ChristmasBuddy.reg_mixed_approver_mismatch",
    "ChristmasBuddy.reg_mixed_empty_approver",
    "ChristmasBuddy.reg_mixed_stale_release_hash",
    "ChristmasBuddy.reg_mixed_not_frozen",
    "ChristmasBuddy.reg_mixed_empty_frozen",
    "ChristmasBuddy.reg_mixed_unregistered",
    "ChristmasBuddy.reg_pcb_bump_invalidates",
    "ChristmasBuddy.reg_cad_bump_invalidates",
    "ChristmasBuddy.reg_fw_bump_invalidates",
    "ChristmasBuddy.reg_bom_bump_invalidates",
]

def fresh_tree() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="cbu_leangen_"))
    for row in M5.ARTIFACT_TABLE:
        src = SRC / row[0]
        if src.is_file():
            (tmp / row[0]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp / row[0])
    (tmp / "manufacturing/gerber").mkdir(parents=True, exist_ok=True)
    (tmp / "manufacturing/gerber/top.gbr").write_bytes(b"G04 top v1\n")
    (tmp / "manufacturing/gerber/bottom.gbr").write_bytes(b"G04 bottom v1\n")
    shutil.copy2(SRC / "release-spec.json", tmp / "release-spec.json")
    return tmp

def gen_file(tmp: Path) -> Path:
    return tmp / "proof/src/ChristmasBuddy/ReleaseCurrent.lean"

def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def write_spec(tmp: Path, spec: dict) -> None:
    (tmp / "release-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")

def lean_compile(p: Path, with_audit: bool = False) -> tuple[int, str, dict]:
    """lake env lean 编译；with_audit 时在文件副本上追加 #print axioms 并解析公理依赖。"""
    target = p
    if with_audit:
        target = p.parent / "ReleaseCurrentAudit.lean"
        target.write_text(p.read_text(encoding="utf-8")
                          + "\n" + "\n".join(f"#print axioms {n}" for n in GEN_THEOREMS) + "\n",
                          encoding="utf-8")
    r = subprocess.run(["lake", "env", "lean", str(target)], cwd=PROOF,
                       capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    axioms = {}
    for m in re.finditer(r"'([^']+)' does not depend on any axioms", out):
        axioms[m.group(1)] = []
    for m in re.finditer(r"'([^']+)' depends on axioms: \[([^\]]*)\]", out):
        axioms[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]
    return r.returncode, out, axioms

def run_check(tmp: Path) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    return buf.getvalue()

def make_approved(tmp: Path) -> str:
    """合法批准全流程（正向基线）：定版 → build 取 release_hash → GATE 批准绑定 → 重建。"""
    spec = load_json(tmp / "release-spec.json")
    spec["tuple"] = dict(MIXED)
    spec["frozen_registry"] = [dict(MIXED)]
    write_spec(tmp, spec)
    man = M5.build(tmp)
    hr = man["release_candidate"]["release_hash"]
    spec = load_json(tmp / "release-spec.json")
    spec["approval_state"] = "APPROVED"
    spec["approver"] = "alice"
    spec["approval_records"] = [{"release": dict(MIXED), "releaseHash": hr, "approver": "alice"}]
    write_spec(tmp, spec)
    man2 = M5.build(tmp)
    assert man2["release_candidate"]["release_hash"] == hr, "同一内容重建 release_hash 必须不变"
    return hr

def main() -> int:
    ok = True
    results: list[tuple[str, bool]] = []

    def record(name: str, passed: bool) -> None:
        results.append((name, passed))

    # —— A：真实 Manifest 数据基线（四元组空 / UNAPPROVED / 双空注册表）——
    def case_a() -> None:
        tmp = fresh_tree()
        try:
            M5.build(tmp)
            rc = load_json(tmp / "m5_manifest.json")["release_candidate"]
            data_ok = (rc["tuple"] == {"pcb": None, "cad": None, "fw": None, "bom": None}
                       and rc["approval_state"] == "UNAPPROVED" and rc["approval_records"] == []
                       and rc["frozen_registry"] == []
                       and rc["release_hash"] != rc["manifest_hash"])
            lean = gen_file(tmp).read_text(encoding="utf-8")
            content_ok = ("⟨none, none, none, none⟩" in lean
                          and "currentApproved : Bool := false" in lean
                          and "currentFrozenRegistry : List ChristmasBuddy.Version.Release := []" in lean
                          and "currentRegistry : List ChristmasBuddy.Version.ApprovalRecord := []" in lean
                          and "= currentApproved := by decide" in lean)
            out = run_check(tmp)
            check_ok = "m5_manifest check: PASS" in out
            code, err, _ = lean_compile(gen_file(tmp))
            record("A 真实 Manifest：四元组空+UNAPPROVED+双哈希分离 → check PASS + 编译通过",
                   data_ok and content_ok and check_ok and code == 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    case_a()

    # —— POS-B：合法批准完整链（spec → release_hash → 批准记录 → manifest_hash → 生成 →
    #     M5.check → Lean 编译 → 公理审计）——
    def case_pos_b() -> None:
        tmp = fresh_tree()
        try:
            hr = make_approved(tmp)
            out = run_check(tmp)
            check_ok = "m5_manifest check: PASS" in out and "FAIL" not in out
            rc = load_json(tmp / "m5_manifest.json")["release_candidate"]
            bound_ok = (rc["approval_records"][0]["releaseHash"] == hr
                        and rc["release_hash"] == hr
                        and rc["approval_state"] == "APPROVED")
            lean = gen_file(tmp).read_text(encoding="utf-8")
            lean_ok = ("⟨some 2, some 1, some 3, some 2⟩" in lean
                       and "currentApproved : Bool := true" in lean
                       and 'some "alice"' in lean
                       and "currentFrozenRegistry : List ChristmasBuddy.Version.Release := [⟨some 2, some 1, some 3, some 2⟩]" in lean)
            code, err, axioms = lean_compile(gen_file(tmp), with_audit=True)
            missing = [n for n in GEN_THEOREMS if n not in axioms]
            bad_ax = {n: a for n, a in axioms.items()
                      if any(x not in WHITELIST for x in a)}
            record("POS-B 合法批准完整链：M5.check PASS + Lean 编译 PASS + 公理审计白名单 PASS"
                   + ("" if not missing else f"（审计缺条目 {len(missing)}）"),
                   check_ok and bound_ok and lean_ok and code == 0 and not missing and not bad_ax)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    case_pos_b()

    # —— 负向公共骨架：从合法批准态出发，单一变异 → check 必 FAIL（精确诊断）+
    #     Lean 编译按层级预期（lean_fail=True 的案例必须编译失败）——
    def neg(tag: str, mutate, gov_needle: str, lean_fail: bool, extra_needle: str | None = None):
        tmp = fresh_tree()
        try:
            make_approved(tmp)
            mutate(tmp)
            out = run_check(tmp)
            check_fail = "m5_manifest check: FAIL" in out
            gov_ok = gov_needle in out
            extra_ok = extra_needle is None or extra_needle in out
            code, err, _ = lean_compile(gen_file(tmp))
            lean_ok = (code != 0) == lean_fail
            record(f"{tag} → check FAIL（{gov_needle[:14]}…）+ 编译{'失败' if lean_fail else '通过（Python 层职责）'}",
                   check_fail and gov_ok and extra_ok and lean_ok)
            return tmp
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise

    def n1(tmp):
        spec = load_json(tmp / "release-spec.json")
        spec["approval_records"][0]["releaseHash"] = "stale-release-hash"  # 绑旧 release_hash
        write_spec(tmp, spec)
        M5.build(tmp)

    def n2(tmp):  # 修改 PCB 工件
        p = tmp / "eda/netlist.json"
        p.write_text(p.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")

    def n3(tmp):  # 修改 BOM
        p = tmp / "bom.csv"
        p.write_text(p.read_text(encoding="utf-8") + "\nB99,漂移,x,x,1,CHECK,x\n", encoding="utf-8")

    def n4(tmp):  # 修改批准人（记录仍绑 alice）
        spec = load_json(tmp / "release-spec.json")
        spec["approver"] = "bob"
        write_spec(tmp, spec)
        M5.build(tmp)

    def n5(tmp):  # 修改四元组（旧批准不继承）
        spec = load_json(tmp / "release-spec.json")
        spec["tuple"] = {"pcb": 3, "cad": 1, "fw": 3, "bom": 2}
        write_spec(tmp, spec)
        M5.build(tmp)

    def n6(tmp):  # 删除批准记录（保持 APPROVED）
        spec = load_json(tmp / "release-spec.json")
        spec["approval_records"] = []
        write_spec(tmp, spec)
        M5.build(tmp)

    def n7(tmp):  # 伪造 manifest_hash（手改自动生成清单）
        man_path = tmp / "m5_manifest.json"
        man = load_json(man_path)
        man["release_candidate"]["manifest_hash"] = "f" * 64
        man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def n8(tmp):  # 修改批准状态（保持批准记录）
        spec = load_json(tmp / "release-spec.json")
        spec["approval_state"] = "UNAPPROVED"
        spec["approver"] = None
        write_spec(tmp, spec)
        M5.build(tmp)

    gov = "批准状态与批准记录"
    keep = [neg("N1 批准记录绑定旧 release_hash", n1, gov, lean_fail=True),
            neg("N2 修改 PCB 工件", n2, "哈希漂移", lean_fail=False, extra_needle="release_hash 不一致"),
            neg("N3 修改 BOM", n3, "哈希漂移", lean_fail=False, extra_needle="release_hash 不一致"),
            neg("N4 修改批准人（alice→bob）", n4, gov, lean_fail=True),
            neg("N5 修改四元组（旧批准不继承）", n5, gov, lean_fail=True,
                extra_needle="冻结注册表缺少候选"),
            neg("N6 删除批准记录", n6, gov, lean_fail=True),
            neg("N7 伪造 manifest_hash", n7, "manifest_hash 不一致", lean_fail=False),
            neg("N8 修改批准状态（留批准记录）", n8, gov, lean_fail=False)]
    for t in keep:
        shutil.rmtree(t, ignore_errors=True)

    # —— FI：故障注入——禁用治理规则后 N1/N4/N5/N6/N8 的治理诊断必须消失 ——
    def case_fi() -> None:
        trees = {}
        muts = {"N1": n1, "N4": n4, "N5": n5, "N6": n6, "N8": n8}
        try:
            for tag, mut in muts.items():
                t = fresh_tree()
                make_approved(t)
                mut(t)
                trees[tag] = t
            orig = M5.approval_consistency
            M5.approval_consistency = lambda rc: []
            try:
                outs = {tag: run_check(t) for tag, t in trees.items()}
            finally:
                M5.approval_consistency = orig
            gone = all("批准状态与批准记录" not in o for o in outs.values())
            record("FI 故障注入自检（禁用 approval_consistency 后治理诊断消失）", gone)
        finally:
            for t in trees.values():
                shutil.rmtree(t, ignore_errors=True)
    case_fi()

    # —— 双层哈希无循环依赖（结构性验证）：release_hash 不含批准元数据 ——
    def case_no_cycle() -> None:
        tmp = fresh_tree()
        try:
            hr = make_approved(tmp)
            rc = load_json(tmp / "m5_manifest.json")["release_candidate"]
            # 变更批准元数据 → manifest_hash 必变、release_hash 必不变
            spec = load_json(tmp / "release-spec.json")
            spec["approval_records"][0]["approver"] = "mallory"
            write_spec(tmp, spec)
            man2 = M5.build(tmp)
            rc2 = man2["release_candidate"]
            record("解环 批准元数据变化 → manifest_hash 参与变化而 release_hash 稳定（无自引用）",
                   rc2["release_hash"] == hr and rc2["manifest_hash"] != rc["manifest_hash"]
                   and rc["manifest_hash"] not in json.dumps(M5.canonical_manifest_payload(rc2))
                   and M5.release_hash({"artifacts": [], "not_yet": [],
                                        "release_candidate": {"product": "p", "tuple": {},
                                                              "source_commit": None}})
                   == M5.release_hash({"artifacts": [], "not_yet": [],
                                       "release_candidate": {"product": "p", "tuple": {},
                                                             "source_commit": None,
                                                             "approval_state": "APPROVED",
                                                             "approver": "x",
                                                             "approval_records": [{"a": 1}]}}))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    case_no_cycle()

    # —— 守卫：真实树未被触碰 ——
    def case_real_guard() -> None:
        rc = load_json(SRC / "m5_manifest.json")["release_candidate"]
        spec = load_json(SRC / "release-spec.json")
        record("守卫 真实生产候选保持 UNAPPROVED（测试未写真实树）",
               rc["approval_state"] == "UNAPPROVED" and rc["approval_records"] == []
               and spec["approval_state"] == "UNAPPROVED")
    case_real_guard()

    for name, r in results:
        print(f"  [{'PASS' if r else 'FAIL'}] {name}")
        ok = ok and r
    print("\n结果:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
