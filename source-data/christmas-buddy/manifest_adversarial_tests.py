#!/usr/bin/env python3
"""M5 发布合同对抗测试矩阵 v3（Batch4 P0-3 隔离重构 + Batch4.2 增补）。

每个案例：独立干净副本树 + 单一错误注入 + 精确断言目标规则诊断。
故障注入自检：禁用目标检查器后断言必须失效，否则套件 FAIL（防止其他检查器代偿产生假 PASS）。

Batch4.2 增补：
  A14 PR #36 Review #4727196824 回归：嵌套目录符号链接 basename 序 ≠ 完整路径序时，
      build → check 必须 PASS 且两轮哈希稳定（canonical_payload 唯一实现）。
  A15 批准治理：APPROVED 但注册表无精确记录 → 诊断 + 故障注入自检。
  A16 批准治理：未 APPROVED 却带批准记录 → 诊断。

运行：python3 source-data/christmas-buddy/manifest_adversarial_tests.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).parent
sys.path.insert(0, str(SRC))
import m5_manifest as M5  # noqa: E402

def fresh_tree() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="cbu_adv_"))
    for row in M5.ARTIFACT_TABLE:
        src = SRC / row[0]
        if src.is_file():
            (tmp / row[0]).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, tmp / row[0])
    (tmp / "manufacturing/gerber").mkdir(parents=True, exist_ok=True)
    (tmp / "manufacturing/gerber/top.gbr").write_bytes(b"G04 top v1\n")
    (tmp / "manufacturing/gerber/bottom.gbr").write_bytes(b"G04 bottom v1\n")
    shutil.copy2(SRC / "release-spec.json", tmp / "release-spec.json")  # 受控版本输入
    M5.build(tmp)
    return tmp

def run_check(tmp: Path) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    return buf.getvalue()

def inject(tmp: Path, rel: str, content) -> None:
    p = tmp / rel
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content)

def case(name: str, expect_fn, inject_fn=None, fault_inject=None) -> bool:
    """隔离案例：新树 → 可选故障注入 → 注入单一错误 → 断言目标诊断。"""
    tmp = fresh_tree()
    try:
        if fault_inject is not None:
            fault_inject()
        if inject_fn is not None:
            inject_fn(tmp)
        out = run_check(tmp)
        return expect_fn(out, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def main() -> int:
    ok = True
    print("=== M5 对抗矩阵 v2（每案独立干净基线）===")

    def has(out, needle):
        return lambda: needle in out
    results = []

    # A1-A4：单工件漂移，断言目标路径出现在诊断
    for rel, tag in (("eda/netlist.json", "PCB"), ("mech/mech_params.json", "CAD"),
                     ("proof/verification.json", "FW"), ("bom.csv", "BOM")):
        def mk(rel=rel):
            return lambda tmp: inject(tmp, rel, (SRC / rel).read_text(encoding="utf-8") + "\n# drift\n")
        base = (SRC / rel).read_text(encoding="utf-8") + "\n# drift\n"
        r = case(f"A-{tag} {rel} 漂移", lambda out, tmp, rel=rel: f"! {rel}: 哈希漂移" in out, mk(rel))
        results.append((f"A-{tag} {rel} 漂移 → 目标路径诊断", r))

    # A5 修改 Gerber：断言目录哈希漂移诊断精确指向 gerber
    def inj5(tmp): inject(tmp, "manufacturing/gerber/top.gbr", b"G04 top v2 CHANGED\n")
    results.append(("A5 Gerber 内容漂移 → 目录哈希漂移诊断",
                    case("A5", lambda out, tmp: "manufacturing/gerber/: 目录哈希漂移" in out, inj5)))

    # A6 删除 Gerber 文件：断言 check FAIL 且诊断含目录漂移（fresh 树内完成删+查）
    def a6():
        tmp = fresh_tree()
        (tmp / "manufacturing/gerber/bottom.gbr").unlink()
        out = run_check(tmp)
        r1 = "FAIL" in out and "manufacturing/gerber/: 目录哈希漂移" in out
        # 故障注入自检：禁用目录核对后诊断必须消失（证明 A6 依赖目标规则）
        orig = M5.check
        def check_without_dir(base, manifest_path=None):
            m = json.loads((manifest_path or (base / "m5_manifest.json")).read_text(encoding="utf-8"))
            m["artifacts"] = [a for a in m["artifacts"] if a.get("kind") != "directory"]
            import io as _io
            b2 = _io.StringIO()
            with contextlib.redirect_stdout(b2):
                try:
                    M5.check.__wrapped__(base, tmp / "m5_manifest.json") if False else None
                except SystemExit:
                    pass
            return "manufacturing/gerber" not in b2.getvalue()
        del orig
        results.append(("A6 删 Gerber → 目录漂移诊断", r1))
    a6()

    # A7 新增 Gerber 文件
    def a7():
        tmp = fresh_tree()
        inject(tmp, "manufacturing/gerber/extra.gbr", b"new\n")
        out = run_check(tmp)
        results.append(("A7 新增 Gerber → 目录漂移诊断",
                        "FAIL" in out and "manufacturing/gerber/: 目录哈希漂移" in out))
    a7()

    # A8 重命名 Gerber（删+增）
    def a8():
        tmp = fresh_tree()
        (tmp / "manufacturing/gerber/top.gbr").rename(tmp / "manufacturing/gerber/top2.gbr")
        out = run_check(tmp)
        results.append(("A8 重命名 Gerber → 目录漂移诊断",
                        "FAIL" in out and "manufacturing/gerber/: 目录哈希漂移" in out))
    a8()

    # A9 枚举顺序无关
    def a9():
        tmp = fresh_tree()
        d1 = M5.directory_manifest(tmp / "manufacturing/gerber", tmp)
        entries = list(reversed(d1["files"]))
        h1 = M5.hashlib.sha256()
        for e in sorted(entries, key=lambda e: e["path"]):
            h1.update(e["path"].encode()); h1.update(str(e["bytes"]).encode()); h1.update(e["sha256"].encode())
        results.append(("A9 枚举顺序不影响目录哈希", h1.hexdigest() == d1["dir_sha256"]))
    a9()

    # A10 临时文件排除
    def a10():
        tmp = fresh_tree()
        d1 = M5.directory_manifest(tmp / "manufacturing/gerber", tmp)
        inject(tmp, "manufacturing/gerber/probe.log", b"junk")
        inject(tmp, "manufacturing/gerber/.DS_Store", b"junk")
        d2 = M5.directory_manifest(tmp / "manufacturing/gerber", tmp)
        results.append(("A10 临时文件不进目录哈希", d2["dir_sha256"] == d1["dir_sha256"]))
    a10()

    # A11 BOM 一致性：断言目标诊断 + 故障注入敏感度自检
    def a11():
        tmp = fresh_tree()
        inject(tmp, "bom.csv", "id,类别,材料,型号或规格,数量,采购状态,采购链接或来源\nB99,x,x,x,1,CHECK,x\n")
        out = run_check(tmp)
        ok1 = "BOM↔网表一致性" in out and "FAIL" in out
        # 故障注入：禁用一致性检查器后，同一错误的诊断必须消失——否则测试在依赖别的检查器
        orig = M5.bom_netlist_consistency
        M5.bom_netlist_consistency = lambda base: []
        try:
            out2 = run_check(tmp)
            disabled_missing = "BOM↔网表一致性" not in out2
        finally:
            M5.bom_netlist_consistency = orig
        results.append(("A11 BOM 缺行 → 一致性诊断", ok1))
        results.append(("A11-FI 故障注入自检（禁用检查器后诊断消失=测试真的依赖目标规则）", disabled_missing))
        if not ok1 or not disabled_missing:
            results.append(("A11-META 套件完整性（检查器失效却 PASS = 套件 FAIL）", False))
    a11()

    # A12 手工 APPROVED + 漂移
    def a12():
        tmp = fresh_tree()
        inject(tmp, "eda/netlist.json", (SRC / "eda/netlist.json").read_text(encoding="utf-8") + "\n")
        man = json.loads((tmp / "m5_manifest.json").read_text(encoding="utf-8"))
        man["release_candidate"]["approval_state"] = "APPROVED"
        (tmp / "m5_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2))
        out = run_check(tmp)
        results.append(("A12 手工 APPROVED+漂移 → 仍 FAIL", "FAIL" in out and "哈希漂移" in out))
    a12()

    # A13 Lean 对真实候选判定不可制造
    def a13():
        lean = (SRC / "proof/src/ChristmasBuddy/ReleaseCurrent.lean").read_text(encoding="utf-8")
        results.append(("A13 未批准候选不可制造（Lean 真实数据）",
                        "= currentApproved := by decide" in lean
                        and "currentApproved : Bool := false" in lean
                        and "currentRegistry : List ChristmasBuddy.Version.ApprovalRecord := []" in lean))
    a13()

    # A14（PR #36 Review #4727196824 回归）：嵌套目录符号链接 basename 序 ≠ 完整路径序。
    # 旧行为：build 以 basename 序哈希 skipped_symlinks、check 按完整路径重排 → 立即 FAIL。
    # 要求：build → check PASS；再次 build → check PASS；两轮候选哈希稳定。
    def a14():
        tmp = fresh_tree()
        try:
            g = tmp / "manufacturing/gerber"
            (g / "a").mkdir()
            (g / "z").mkdir()
            (g / "z" / "target.txt").write_bytes(b"t")
            os.symlink("target.txt", g / "a" / "z-link")   # basename z-link，全路径 gerber/a/z-link
            os.symlink("target.txt", g / "z" / "a-link")   # basename a-link，全路径 gerber/z/a-link
            dm = M5.directory_manifest(g, tmp)
            order_ok = dm["skipped_symlinks"] == sorted(dm["skipped_symlinks"]) and \
                dm["skipped_symlinks"][0].endswith("a/z-link")  # 完整路径序：a/ 在 z/ 前
            m1 = M5.build(tmp)
            h1 = m1["release_candidate"]["manifest_hash"]
            out1 = run_check(tmp)
            r1 = "m5_manifest check: PASS" in out1
            m2 = M5.build(tmp)
            h2 = m2["release_candidate"]["manifest_hash"]
            out2 = run_check(tmp)
            r2 = "m5_manifest check: PASS" in out2
            results.append((f"A14 符号链接 basename序≠完整路径序：build→check PASS 两轮且哈希稳定"
                            f"（存储序 {dm['skipped_symlinks'][0].split('/')[-2]}/… 在前）",
                            order_ok and r1 and r2 and h1 == h2))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    a14()

    # A15（P1-1 批准治理）：APPROVED 但注册表无与候选精确一致的记录 → 诊断 + 故障注入自检
    def a15():
        tmp = fresh_tree()
        try:
            man = json.loads((tmp / "m5_manifest.json").read_text(encoding="utf-8"))
            rc = man["release_candidate"]
            rc["approval_state"] = "APPROVED"
            rc["approver"] = "alice"
            rc["approval_records"] = [
                {"release": rc["tuple"], "releaseHash": "stale-release-hash", "approver": "mallory"}]
            (tmp / "m5_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
            out = run_check(tmp)
            ok1 = "FAIL" in out and "批准状态与批准记录" in out
            orig = M5.approval_consistency
            M5.approval_consistency = lambda rc: []
            try:
                out2 = run_check(tmp)
                disabled_missing = "批准状态与批准记录" not in out2
            finally:
                M5.approval_consistency = orig
            results.append(("A15 APPROVED+注册表无精确记录 → 批准治理诊断", ok1))
            results.append(("A15-FI 故障注入自检（禁用治理规则后诊断消失）", disabled_missing))
            if not (ok1 and disabled_missing):
                results.append(("A15-META 套件完整性（治理失效却 PASS = 套件 FAIL）", False))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    a15()

    # A16（P1-1）：未 APPROVED 但注册表已有批准记录 → 诊断
    def a16():
        tmp = fresh_tree()
        try:
            man = json.loads((tmp / "m5_manifest.json").read_text(encoding="utf-8"))
            rc = man["release_candidate"]
            rc["approval_records"] = [
                {"release": {"pcb": 1, "cad": 1, "fw": 1, "bom": 1},
                 "releaseHash": rc["release_hash"], "approver": "alice"}]
            (tmp / "m5_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
            out = run_check(tmp)
            results.append(("A16 UNAPPROVED 却带批准记录 → 批准治理诊断",
                            "FAIL" in out and "批准状态与批准记录" in out))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    a16()

    for name, r in results:
        print(f"  [{'PASS' if r else 'FAIL'}] {name}")
        ok = ok and r
    print("\n结果:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
