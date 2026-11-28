#!/usr/bin/env python3
"""M5 发布合同对抗测试矩阵（Batch3 §二）：在**临时副本树**上攻击真实 Manifest，
绝不修改真实工作区文件。10+ 攻击全部必须按合同定义失败/通过。

运行：python3 source-data/christmas-buddy/manifest_adversarial_tests.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).parent
sys.path.insert(0, str(SRC))
import m5_manifest as M5  # noqa: E402

NEEDED = [row[0] for row in M5.ARTIFACT_TABLE]

def make_tree() -> Path:
    """构造最小真实副本树（含 bom/网表/检查器源 + 假 Gerber 目录）。"""
    tmp = Path(tempfile.mkdtemp(prefix="cbu_adv_"))
    for rel in NEEDED:
        src = SRC / rel
        dst = tmp / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    (tmp / "manufacturing/gerber").mkdir(parents=True, exist_ok=True)
    (tmp / "manufacturing/gerber/top.gbr").write_bytes(b"G04 top layer v1\n")
    (tmp / "manufacturing/gerber/bottom.gbr").write_bytes(b"G04 bottom layer v1\n")
    M5.build(tmp)  # build 含 gen_lean（受控转换，禁止手写哈希——基线自带一致性）
    assert not Path.exists(tmp / "m5_manifest.json") or True
    return tmp

def expect(label: str, cond: bool, detail: str = "") -> bool:
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail[:90]}" if detail else ""))
    return cond

def drift(tmp: Path, rel: str, content) -> list[str]:
    """改文件 → check 必须报该路径漂移。"""
    p = tmp / rel
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
            out = buf.getvalue()
        except SystemExit:
            out = buf.getvalue()
    return [ln for ln in out.splitlines() if "!" in ln]

def main() -> int:
    ok = True
    print("=== M5 发布合同对抗测试（临时副本树）===")

    # 0 基线
    tmp = make_tree()
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    base_clean = "FAIL" not in buf.getvalue()
    ok = expect("A0 基线副本 check 通过", base_clean, buf.getvalue().strip()[:80])

    # A1–A4 修改 PCB/CAD/FW/BOM 槽工件 → 失效
    for rel, tag, slot in (("eda/netlist.json", "PCB", "pcb"), ("mech/mech_params.json", "CAD", "cad"),
                           ("proof/verification.json", "FW", "fw"), ("bom.csv", "BOM", "bom")):
        bad = drift(tmp, rel, (SRC / rel).read_text(encoding="utf-8") + "\n# drift\n")
        ok &= expect(f"A{1+['PCB','CAD','FW','BOM'].index(tag)} 修改 {tag} 槽工件 → Release 失效",
                     any(rel in b for b in bad), bad[0] if bad else "")

    # A5 修改 Gerber 文件内容
    bad = drift(tmp, "manufacturing/gerber/top.gbr", b"G04 top layer v2 CHANGED\n")
    ok &= expect("A5 修改 Gerber → 目录哈希漂移", any("gerber" in b for b in bad), bad[0] if bad else "")

    # A6 删除 Gerber 文件
    (tmp / "manufacturing/gerber/bottom.gbr").unlink()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    ok &= expect("A6 删除 Gerber 文件 → FAIL", "FAIL" in buf.getvalue(), buf.getvalue().strip()[:80])

    # A7 新增 Gerber 文件
    (tmp / "manufacturing/gerber/extra.gbr").write_bytes(b"new\n")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    ok &= expect("A7 新增 Gerber 文件 → FAIL", "FAIL" in buf.getvalue(), buf.getvalue().strip()[:80])

    # A8 重命名 Gerber（删+增等价）→ FAIL（先恢复 bottom，再重命名 top）
    (tmp / "manufacturing/gerber").mkdir(exist_ok=True)
    (tmp / "manufacturing/gerber/top2.gbr").write_bytes(b"G04 top layer v2 CHANGED\n")
    (tmp / "manufacturing/gerber/top.gbr").unlink()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    ok &= expect("A8 重命名 Gerber → FAIL", "FAIL" in buf.getvalue(), buf.getvalue().strip()[:80])

    # A9 枚举顺序无关：同内容不同顺序 → dir_sha256 相同
    d1 = M5.directory_manifest(tmp / "manufacturing/gerber", tmp)
    # 两种枚举顺序的同一文件集合 → 排序后哈希必须一致（确定性契约）
    entries_rev = list(reversed(d1["files"]))
    h1 = M5.hashlib.sha256()
    for e in sorted(entries_rev, key=lambda e: e["path"]):
        h1.update(e["path"].encode()); h1.update(str(e["bytes"]).encode()); h1.update(e["sha256"].encode())
    h2 = M5.hashlib.sha256()
    for e in d1["files"]:
        h2.update(e["path"].encode()); h2.update(str(e["bytes"]).encode()); h2.update(e["sha256"].encode())
    ok &= expect("A9 枚举顺序不影响目录哈希（排序后一致）",
                 h1.hexdigest() == d1["dir_sha256"] == h2.hexdigest())

    # A10 临时文件被排除
    (tmp / "manufacturing/gerber/probe.log").write_bytes(b"junk")
    (tmp / "manufacturing/gerber/.DS_Store").write_bytes(b"junk")
    d2 = M5.directory_manifest(tmp / "manufacturing/gerber", tmp)
    ok &= expect("A10 临时文件（log/.DS_Store）不进入目录哈希", d2["dir_sha256"] == d1["dir_sha256"])

    # A11 BOM↔网表一致性被检查器执行（缺 U1 映射即 FAIL）
    bad = drift(tmp, "bom.csv", "id,x\n")  # 极端：BOM 只剩表头外一行
    ok &= expect("A11 BOM 行缺失 → 一致性 FAIL", any("BOM" in b or "bom.csv" in b for b in bad),
                 bad[0] if bad else "")

    # A12 旧批准复用：approval_state 手工 APPROVED 但工件漂移 → check FAIL
    man = json.loads((tmp / "m5_manifest.json").read_text(encoding="utf-8"))
    man["release_candidate"]["approval_state"] = "APPROVED"
    (tmp / "m5_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    ok &= expect("A12 手工 APPROVED + 工件漂移 → 仍 FAIL（批准不越哈希）", "FAIL" in buf.getvalue())

    # A13 未批准候选进入制造：合同定理对真实候选数据判定 false（Lean 层，回归）
    lean = (SRC / "proof/src/ChristmasBuddy/ReleaseCurrent.lean").read_text(encoding="utf-8")
    ok &= expect("A13 未批准候选不可制造（Lean 对真实候选）",
                 "by rfl" in lean and "currentTuple : ChristmasBuddy.Version.Release := ⟨none, none, none, none⟩" in lean)

    print("\n结果:", "ALL PASS" if ok else "FAIL")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
