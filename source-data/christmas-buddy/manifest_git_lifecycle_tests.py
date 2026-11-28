#!/usr/bin/env python3
"""真实 Git 提交生命周期测试（Batch4.3.1 P0-2）：独立临时 Git 仓库，
不依赖真实仓库的全局 HEAD——验证 source_commit 受控固定的完整生命周期。

流程（对应任务 A–F + 追加负向）：
  0  负向：spec 缺失/非法/不可达 source_commit → build 拒绝（不得静默写 null）
  A  创建候选内容提交 A（临时仓，内容 = 全部受管工件）
  B  将 A 写入 release-spec.source_commit
  C  build → release_hash
  D  GATE 创建绑定该 release_hash 的批准记录（APPROVED）
  E  提交批准元数据 → 提交 B
  F  在 B 上重新 build/check
     预期：source_commit 仍为 A；release_hash 不变；manifest_hash 因批准元数据变化；
           M5.check PASS；Lean 编译 + 公理审计 PASS
  G  source_commit 漂移（改为 B）→ release_hash 改变 → 旧批准失效（治理 FAIL）
  H  提交 C：修改 PCB 工件并提交
     预期：check FAIL（漂移 + release_hash 实时重算）；重建后 source_commit 仍为 A、
           release_hash 改变、旧批准不继承（治理 FAIL）

运行：python3 source-data/christmas-buddy/manifest_git_lifecycle_tests.py
（前置：proof 已 lake build——Lean 编译用真实 .lake 的 LEAN_PATH。）
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

MIXED = {"pcb": 2, "cad": 1, "fw": 3, "bom": 2}
WHITELIST = {"propext", "Classical.choice", "Quot.sound"}
GEN_THEOREMS = [
    "ChristmasBuddy.r1_real_candidate_matches_approval_state",
    "ChristmasBuddy.r2_isolated_registry_cannot_approve_real_candidate",
]

def run_check(tmp: Path) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            M5.check(tmp)
        except SystemExit:
            pass
    return buf.getvalue()

def lean_compile_audit(p: Path) -> tuple[int, str, dict]:
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

def main() -> int:
    ok = True
    results: list[tuple[str, bool]] = []

    def record(name: str, passed: bool) -> None:
        results.append((name, passed))
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    repo = Path(tempfile.mkdtemp(prefix="cbu_gitlc_")) / "repo"

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-c", "user.name=cbu-lifecycle", "-c", "user.email=cbu-lifecycle@test", *args],
            cwd=repo, capture_output=True, text=True, timeout=60)

    def write_spec(spec: dict) -> None:
        (repo / "release-spec.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def load_spec() -> dict:
        return json.loads((repo / "release-spec.json").read_text(encoding="utf-8"))

    def commit_all(msg: str) -> str:
        add = git("add", "-A")  # 一次性临时仓库（非共享工作区），全量暂存安全
        c = git("commit", "-m", msg)
        assert add.returncode == 0 and c.returncode == 0, (add.stderr, c.stderr)
        return git("rev-parse", "HEAD").stdout.strip()

    try:
        # —— 准备：临时仓 + 全部受管工件 + 初始 spec（source_commit 缺失）——
        repo.mkdir(parents=True)
        for row in M5.ARTIFACT_TABLE:
            src = SRC / row[0]
            if src.is_file():
                (repo / row[0]).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, repo / row[0])
        (repo / "manufacturing/gerber").mkdir(parents=True, exist_ok=True)
        (repo / "manufacturing/gerber/top.gbr").write_bytes(b"G04 top v1\n")
        (repo / "manufacturing/gerber/bottom.gbr").write_bytes(b"G04 bottom v1\n")
        spec = json.loads((SRC / "release-spec.json").read_text(encoding="utf-8"))
        spec.pop("source_commit", None)          # 初始缺失（负向 0 用）
        spec["tuple"] = dict(MIXED)
        spec["frozen_registry"] = [dict(MIXED)]
        spec["approval_state"] = "UNAPPROVED"
        spec["approver"] = None
        spec["approval_records"] = []
        write_spec(spec)
        assert git("init", "-b", "main").returncode == 0

        # —— 负向 0：缺失/非法/不可达 source_commit 必须 FAIL ——
        def build_must_reject(tag: str, spec_mut: dict, needle: str) -> None:
            write_spec(spec_mut)
            try:
                M5.build(repo)
                record(f"0-{tag} → build 拒绝", False)
            except (ValueError, FileNotFoundError) as e:
                record(f"0-{tag} → build 拒绝（{str(e)[:36]}…）", needle in str(e))
        build_must_reject("缺失 source_commit", spec, "source_commit")
        bad = dict(spec); bad["source_commit"] = "not-a-sha"
        build_must_reject("非法格式", bad, "非法")
        bad = dict(spec); bad["source_commit"] = "0" * 40
        build_must_reject("不可达提交", bad, "不可达")

        # —— A：候选内容提交 A ——
        sha_a = commit_all("A: candidate content")
        record(f"A 候选内容提交 A = {sha_a[:12]}…", re.fullmatch(r"[0-9a-f]{40}", sha_a) is not None)

        # —— B：将 A 写入 release-spec.source_commit；C：build ——
        spec = load_spec()
        spec["source_commit"] = sha_a
        write_spec(spec)
        man1 = M5.build(repo)
        hr = man1["release_candidate"]["release_hash"]
        hm1 = man1["release_candidate"]["manifest_hash"]
        record(f"B/C source_commit=A 固定入 spec → build：release_hash={hr[:12]}… "
               f"manifest_hash={hm1[:12]}…",
               man1["release_candidate"]["source_commit"] == sha_a)

        # —— D：GATE 批准绑定该 release_hash ——
        spec = load_spec()
        spec["approval_state"] = "APPROVED"
        spec["approver"] = "alice"
        spec["approval_records"] = [{"release": dict(MIXED), "releaseHash": hr,
                                     "approver": "alice"}]
        write_spec(spec)

        # —— E：提交批准元数据 → 提交 B；F：B 上重新 build/check ——
        sha_b = commit_all("B: GATE approval metadata")
        man2 = M5.build(repo)
        rc2 = man2["release_candidate"]
        out = run_check(repo)
        f_ok = (sha_b != sha_a and git("rev-parse", "HEAD").stdout.strip() == sha_b
                and rc2["source_commit"] == sha_a                # source_commit 仍为 A
                and rc2["release_hash"] == hr                    # release_hash 不变
                and rc2["manifest_hash"] != hm1                  # 封套因批准元数据变化
                and "m5_manifest check: PASS" in out)            # check PASS（批准有效）
        record(f"E/F 提交 B={sha_b[:12]}… 后重建：source_commit 仍 A、release_hash 不变、"
               f"manifest_hash 已变、check PASS", f_ok)
        code, err, axioms = lean_compile_audit(repo / "proof/src/ChristmasBuddy/ReleaseCurrent.lean")
        missing = [n for n in GEN_THEOREMS if n not in axioms]
        bad_ax = {n: a for n, a in axioms.items() if any(x not in WHITELIST for x in a)}
        record("F Lean 编译 + 公理审计 PASS（R1 = currentApproved = true，白名单内）",
               code == 0 and not missing and not bad_ax)

        # —— G：source_commit 漂移（改为 B，可达但非候选基准）→ 新候选 + 旧批准失效 ——
        spec = load_spec()
        spec["source_commit"] = sha_b
        write_spec(spec)
        man3 = M5.build(repo)
        rc3 = man3["release_candidate"]
        out3 = run_check(repo)
        g_ok = (rc3["source_commit"] == sha_b and rc3["release_hash"] != hr
                and "批准状态与批准记录" in out3 and "FAIL" in out3)
        record("G source_commit 漂移（A→B）→ release_hash 改变 → 旧批准失效（治理 FAIL）", g_ok)
        spec = load_spec()
        spec["source_commit"] = sha_a                      # 恢复基准 A
        write_spec(spec)
        M5.build(repo)

        # —— H：提交 C 修改 PCB 工件（合法格式的内容变更：追加尾随空行，字节不同）——
        p = repo / "eda/netlist.json"
        p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        sha_c = commit_all("C: pcb artifact change")
        out_stale = run_check(repo)
        stale_ok = ("FAIL" in out_stale and "哈希漂移" in out_stale
                    and "release_hash 不一致" in out_stale)
        record(f"H1 提交 C={sha_c[:12]}…（PCB 工件）→ 旧清单 check FAIL（漂移+release_hash）", stale_ok)
        M5.build(repo)
        rc4 = json.loads((repo / "m5_manifest.json").read_text(encoding="utf-8"))["release_candidate"]
        out4 = run_check(repo)
        h2_ok = (rc4["source_commit"] == sha_a          # 基准仍是 A（内容候选基准不变）
                 and rc4["release_hash"] != hr          # 内容已变 → release_hash 改变
                 and "批准状态与批准记录" in out4 and "FAIL" in out4)  # 旧批准不继承
        record("H2 重建后：source_commit 仍 A、release_hash 已变、旧批准记录失效（治理 FAIL）", h2_ok)

        # —— 双层哈希稳定：失败态可复现 + 恢复后绿色不动点 ——
        hm_a = json.loads((repo / "m5_manifest.json").read_text(encoding="utf-8"))["release_candidate"]["manifest_hash"]
        out_a = run_check(repo)
        M5.build(repo)
        out_b = run_check(repo)
        hm_b = json.loads((repo / "m5_manifest.json").read_text(encoding="utf-8"))["release_candidate"]["manifest_hash"]
        record("I1 失败态不动点：重复 build/check 输出逐字节一致、哈希稳定",
               hm_a == hm_b and out_a == out_b and "FAIL" in out_a)
        spec = load_spec()                               # 恢复合法 UNAPPROVED 态
        spec["approval_state"] = "UNAPPROVED"
        spec["approver"] = None
        spec["approval_records"] = []
        write_spec(spec)
        M5.build(repo)
        r1 = run_check(repo)
        M5.build(repo)
        r2 = run_check(repo)
        record("I2 恢复 UNAPPROVED → 绿色不动点（两次 build/check 均 PASS）",
               "m5_manifest check: PASS" in r1 and "m5_manifest check: PASS" in r2)
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)

    ok = all(r for _, r in results)
    print("\n结果:", "ALL PASS" if ok else "FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
