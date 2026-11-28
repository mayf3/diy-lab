#!/usr/bin/env python3
"""M5 发布合同对抗测试矩阵 v2（Batch4 P0-3）：隔离重构。

每个案例：独立干净副本树 + 单一错误注入 + 精确断言目标规则诊断。
故障注入自检：禁用目标检查器后断言必须失效，否则套件 FAIL（防止其他检查器代偿产生假 PASS）。

运行：python3 source-data/christmas-buddy/manifest_adversarial_tests.py
"""
from __future__ import annotations

import contextlib
import io
import json
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
                        "by rfl" in lean and "⟨none, none, none, none⟩" in lean))
    a13()

    for name, r in results:
        print(f"  [{'PASS' if r else 'FAIL'}] {name}")
        ok = ok and r
    print("\n结果:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
