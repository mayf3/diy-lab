#!/usr/bin/env python3
"""M5→Lean 受控生成测试（Batch4.2 P1-2）：gen_lean 从 Manifest 真实生成，不再写死。

所有案例在**临时目录**执行（fresh 副本树 + 单一数据变异）；真实生产候选始终保持
UNAPPROVED，本套件绝不写真实 m5_manifest.json / ReleaseCurrent.lean。

案例：
  A  真实 Manifest：四元组空 + UNAPPROVED + 注册表空 → 生成不可制造断言，Lean 编译通过
  B  测试 Manifest：四元组 some 1×4（=v1 冻结）、APPROVED、批准记录精确登记
     → 生成可制造断言（R1 = true），Lean 编译通过（合同不是恒假开关）
  C  批准人不同：候选宣称 alice，注册表记录为 mallory → R1 判定 false ≠ true → 编译失败
     （Lean 拒绝矛盾数据）+ check 批准治理诊断
  D  批准记录未登记：字段正确但 registry 无此记录 → 编译失败 + 治理诊断
  E  修改四元组（pcb 1→2）：旧批准不继承 → 编译失败 + 治理诊断
  FI 故障注入：禁用 approval_consistency 后 C/D/E 的治理诊断必须消失
     （否则套件在依赖其他检查器 → FAIL）

运行：python3 source-data/christmas-buddy/manifest_lean_gen_tests.py
（前置：proof 已 lake build——Version.olean 需为最新，套件 A 案例编译即校验。）
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).parent
PROOF = SRC / "proof"
sys.path.insert(0, str(SRC))
import m5_manifest as M5  # noqa: E402

EMPTY_TUPLE = {"pcb": None, "cad": None, "fw": None, "bom": None}
V1_TUPLE = {"pcb": 1, "cad": 1, "fw": 1, "bom": 1}

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
    M5.build(tmp)
    return tmp

def gen_file(tmp: Path) -> Path:
    return tmp / "proof/src/ChristmasBuddy/ReleaseCurrent.lean"

def load_manifest(tmp: Path) -> dict:
    return json.loads((tmp / "m5_manifest.json").read_text(encoding="utf-8"))

def mutate_and_gen(tmp: Path, mut) -> None:
    man = load_manifest(tmp)
    mut(man["release_candidate"])
    (tmp / "m5_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    M5.gen_lean(man, tmp)

def lean_compile(p: Path) -> tuple[int, str]:
    r = subprocess.run(["lake", "env", "lean", str(p)], cwd=PROOF,
                       capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr

def check_output(tmp: Path) -> str:
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    return buf.getvalue()

def main() -> int:
    ok = True
    results: list[tuple[str, bool]] = []
    print("=== M5→Lean 受控生成测试（临时目录隔离，真实候选不受影响）===")

    def record(name: str, passed: bool, detail: str = "") -> None:
        results.append((name, passed))
        if detail:
            results[-1] = (f"{name}（{detail}）", passed)

    # —— A：真实 Manifest 数据基线（四元组空 / UNAPPROVED / 注册表空）——
    def case_a() -> None:
        tmp = fresh_tree()
        try:
            rc = load_manifest(tmp)["release_candidate"]
            data_ok = (rc["tuple"] == EMPTY_TUPLE and rc["approval_state"] == "UNAPPROVED"
                       and rc["approver"] is None and rc["approval_records"] == [])
            lean = gen_file(tmp).read_text(encoding="utf-8")
            content_ok = ("⟨none, none, none, none⟩" in lean
                          and "currentApproved : Bool := false" in lean
                          and 'currentCandidateApprover : Option String := none' in lean
                          and "currentRegistry : List ChristmasBuddy.Version.ApprovalRecord := []"
                          in lean
                          and "= currentApproved := by decide" in lean)
            code, err = lean_compile(gen_file(tmp))
            record("A 真实 Manifest：四元组空+UNAPPROVED → 生成不可制造断言且 Lean 编译通过",
                   data_ok and content_ok and code == 0,
                   "" if code == 0 else err[-200:])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    case_a()

    # —— B：完整+冻结+精确批准登记 → 可制造（正向，非恒假开关）——
    def approve_exactly(rc, approver="alice") -> None:
        rc["tuple"] = dict(V1_TUPLE)
        rc["approval_state"] = "APPROVED"
        rc["approver"] = approver
        rc["approval_records"] = [{"release": dict(V1_TUPLE),
                                   "manifest_hash": rc["manifest_hash"],
                                   "approver": approver}]
    def case_b() -> None:
        tmp = fresh_tree()
        try:
            mutate_and_gen(tmp, lambda rc: approve_exactly(rc))
            lean = gen_file(tmp).read_text(encoding="utf-8")
            content_ok = ("⟨some 1, some 1, some 1, some 1⟩" in lean
                          and "currentApproved : Bool := true" in lean
                          and 'some "alice"' in lean
                          and '⟨⟨some 1, some 1, some 1, some 1⟩,' in lean)
            code, err = lean_compile(gen_file(tmp))
            record("B 测试 Manifest：完整+冻结+批准记录精确登记 → 生成可制造断言且编译通过",
                   content_ok and code == 0, "" if code == 0 else err[-200:])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    case_b()

    def case_cde(tag: str, mut, expect_compile_ok: bool) -> Path:
        """C/D/E 公共骨架：编译必须失败（Lean 拒绝矛盾数据）+ 治理诊断在位。返回树供 FI 复用。"""
        tmp = fresh_tree()
        mutate_and_gen(tmp, mut)
        code, err = lean_compile(gen_file(tmp))
        compile_ok = code == 0
        out = check_output(tmp)
        gov = "批准状态与批准记录" in out and "FAIL" in out
        record(f"{tag} → 编译{'通过' if compile_ok else '失败（Lean 拒绝矛盾数据）'}"
               f" + 治理诊断{'在位' if gov else '缺失'}",
               compile_ok == expect_compile_ok and gov,
               "" if gov else out[-200:])
        return tmp

    # —— C：批准人不同（候选 alice / 注册记录 mallory）——
    tmp_c = None
    def mut_c(rc) -> None:
        rc["tuple"] = dict(V1_TUPLE)
        rc["approval_state"] = "APPROVED"
        rc["approver"] = "alice"
        rc["approval_records"] = [{"release": dict(V1_TUPLE),
                                   "manifest_hash": rc["manifest_hash"],
                                   "approver": "mallory"}]
    tmp_c = case_cde("C 批准人不同（alice vs mallory 已登记）", mut_c, expect_compile_ok=False)

    # —— D：批准记录未登记（字段正确但 registry 为空）——
    def mut_d(rc) -> None:
        rc["tuple"] = dict(V1_TUPLE)
        rc["approval_state"] = "APPROVED"
        rc["approver"] = "alice"
        rc["approval_records"] = []
    tmp_d = case_cde("D 批准记录未登记", mut_d, expect_compile_ok=False)

    # —— E：修改四元组版本，旧批准不继承（记录绑定 pcb=1，候选改为 pcb=2）——
    def mut_e(rc) -> None:
        rc["tuple"] = {"pcb": 2, "cad": 1, "fw": 1, "bom": 1}
        rc["approval_state"] = "APPROVED"
        rc["approver"] = "alice"
        rc["approval_records"] = [{"release": dict(V1_TUPLE),
                                   "manifest_hash": rc["manifest_hash"],
                                   "approver": "alice"}]
    tmp_e = case_cde("E 修改四元组（旧批准不继承）", mut_e, expect_compile_ok=False)

    # —— FI：故障注入——禁用治理规则后 C/D/E 诊断必须消失（证明测试依赖目标规则）——
    def case_fi() -> None:
        orig = M5.approval_consistency
        M5.approval_consistency = lambda rc: []
        try:
            outs = {t: check_output(t) for t in (tmp_c, tmp_d, tmp_e)}
        finally:
            M5.approval_consistency = orig
        gone = all("批准状态与批准记录" not in o for o in outs.values())
        record("FI 故障注入自检（禁用 approval_consistency 后 C/D/E 治理诊断消失）", gone)
    case_fi()
    for t in (tmp_c, tmp_d, tmp_e):
        shutil.rmtree(t, ignore_errors=True)

    # —— 真实树未被触碰（守卫）——
    def case_real_guard() -> None:
        man = json.loads((SRC / "m5_manifest.json").read_text(encoding="utf-8"))
        rc = man["release_candidate"]
        record("守卫 真实生产候选保持 UNAPPROVED（测试未写入真实树）",
               rc["approval_state"] == "UNAPPROVED" and rc["approval_records"] == [])
    case_real_guard()

    for name, r in results:
        print(f"  [{'PASS' if r else 'FAIL'}] {name}")
        ok = ok and r
    print("\n结果:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
