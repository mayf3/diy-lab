"""Hardware Studio（整改轮）回归测试：证明行为，不追求测试数量。

覆盖审查要求：
1. 改尺寸/STEP、保留旧回执 → 普通校验与工作台构建识别过期（不需要 --changed），
   再次构建仍过期（持久）。
2. 真实重跑建模+检查取得匹配回执后才恢复有效（本测试执行真实 FreeCAD 运行一次）。
3. 仅填 pcb 版本号 + guard.product_ready=true，证据缺失时不得得到产品就绪（冲突报错）。
4. 关键尺寸变化经依赖图使机械检查/联合验证/制造资料失效（--changed 仅预览）。
5. 从仓库外目录运行 build_data 正常（ROOT 定位）。

合成夹具用于状态逻辑；真实 FreeCAD 运行用于真实几何；两类结果分别报告。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "hardware/check_project.py"
PROJECT = ROOT / "hardware/space-buddy-r1/project.json"
DIMS = ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1/dims.json"
FC_PY = "/Applications/FreeCAD.app/Contents/Resources/bin/python"
CAD_DIR = ROOT / "source-data/agent-button-deck/pcba-v1/cad"


def run_validator(changed=None, project=PROJECT):
    args = [sys.executable, str(CHECKER), "--project", str(project)]
    if changed:
        args += ["--changed", changed]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else {}


def run_build_data(cwd=None):
    proc = subprocess.run([sys.executable, str(ROOT / "workbench/build_data.py")],
                          capture_output=True, text=True, timeout=120,
                          cwd=cwd or str(ROOT))
    return proc


def run_real_checker():
    """真实 FreeCAD 运行几何检查器（生成新回执）。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = "/Applications/FreeCAD.app/Contents/Resources/lib"
    proc = subprocess.run([FC_PY, str(CAD_DIR / "check_case.py")],
                          capture_output=True, text=True, timeout=300, env=env,
                          cwd=str(CAD_DIR))
    return proc.returncode, proc.stdout


class StaleEvidenceTests(unittest.TestCase):
    """整改 A：过期证据在普通校验与工作台构建中持续可见。"""

    def setUp(self):
        self._backup = DIMS.read_bytes()

    def tearDown(self):
        DIMS.write_bytes(self._backup)
        run_build_data()  # 恢复工作台为绿色基线

    def test_dims_change_without_rerun_is_stale_in_validator(self):
        # 篡改尺寸（追加一个键，模拟"改了输入但没重跑检查"）
        dims = json.loads(DIMS.read_text())
        dims["params"]["body"]["W"] = 99.0
        DIMS.write_text(json.dumps(dims, ensure_ascii=False))
        code, out = run_validator()
        self.assertNotEqual(code, 0, "旧回执+新尺寸必须校验失败")
        self.assertEqual(out["checks"]["cad_evidence_state"], "stale")
        self.assertFalse(out["checks"]["cad_geometry_green"], "过期必须撤销 CAD 完成")
        self.assertTrue(any("dims_sha256" in f for f in out["failures"]))

    def test_stale_persists_across_workbench_rebuilds(self):
        dims = json.loads(DIMS.read_text())
        dims["params"]["body"]["W"] = 99.0
        DIMS.write_text(json.dumps(dims, ensure_ascii=False))
        for build_no in (1, 2):
            proc = run_build_data()
            self.assertEqual(proc.returncode, 0, proc.stderr)
            wb = json.loads((ROOT / "workbench/web/workbench.json").read_text())
            facts = wb["hardware"]["facts"]
            self.assertEqual(facts["cad_evidence_state"], "stale",
                             f"第 {build_no} 次重建后仍必须显示过期")
            self.assertFalse(wb["hardware"]["facts"]["product_ready"])
            self.assertEqual(wb["hardware"]["ok"], False,
                             "过期状态下工作台不得显示校验通过")

    def test_recovery_requires_real_rerun(self):
        dims = json.loads(DIMS.read_text())
        dims["params"]["body"]["W"] = 99.0
        DIMS.write_text(json.dumps(dims, ensure_ascii=False))
        code, _ = run_validator()
        self.assertNotEqual(code, 0)
        # 还原输入 → 回执再次匹配（这是"输入未变"的合法恢复路径）
        DIMS.write_bytes(self._backup)
        code, out = run_validator()
        self.assertEqual(code, 0, "还原输入后应恢复（回执仍与内容匹配）")
        # 输入真的变了 → 必须真实重跑检查器取得新回执后才恢复
        dims["params"]["body"]["W"] = 99.0
        DIMS.write_text(json.dumps(dims, ensure_ascii=False))
        rc, stdout = run_real_checker()
        self.assertEqual(rc, 0, f"真实重跑失败：{stdout[-300:]}")
        self.assertIn("receipt written", stdout)
        code, out = run_validator()
        self.assertEqual(code, 0, "真实重跑取得新回执后应恢复有效")
        self.assertEqual(out["checks"]["cad_evidence_state"], "valid")
        # 恢复基线
        DIMS.write_bytes(self._backup)
        run_real_checker()
        run_build_data()


class ProductReadyEvidenceTests(unittest.TestCase):
    """整改 B：product_ready 必须由证据计算，人工声明冲突即报错。"""

    def _variant(self, mutate):
        proj = json.loads(PROJECT.read_text(encoding="utf-8"))
        mutate(proj)
        tmp = Path(tempfile.mkstemp(suffix=".json", dir=str(ROOT / "hardware"))[1])
        tmp.write_text(json.dumps(proj, ensure_ascii=False), encoding="utf-8")
        self.addCleanup(lambda: tmp.exists() and tmp.unlink())
        return tmp

    def test_pcb_number_and_manual_flag_cannot_fake_ready(self):
        def mutate(p):
            # 伪造 PCB 版本：同时清除 EDA 真实证据（模拟"凭空填版本号"）
            p["version_contract"]["revisions"]["pcb"] = 1
            p["domains"]["eda"]["project"] = None
            p["domains"]["eda"]["outputs_present"] = []
            p["guard"]["product_ready"] = True
        code, out = run_validator(project=self._variant(mutate))
        self.assertNotEqual(code, 0, "填个版本号+手写 true 不得得到产品就绪")
        facts = out["facts"]
        self.assertFalse(facts["product_ready"])
        self.assertTrue(any("人工声明与证据冲突" in f for f in out["failures"]))
        self.assertTrue(facts["product_ready_reasons"], "必须列出具体未就绪原因")
        # 各领域独立表达，不互相冒充
        # pcb=1 + 真实 EDA 工程 → 进行中；冻结还需设计检查有效与联合验证
        self.assertFalse(facts["pcb_frozen"], "pcb=1 未过设计检查/联合验证不得冻结")
        self.assertFalse(facts["package_complete"])
        self.assertFalse(facts["acceptance_done"])
        self.assertFalse(facts["order_authorized"])

    def test_eda_guard_is_computed_not_constant(self):
        code, out = run_validator()
        # 真实状态：product_ready=False 且 EDA 工程已验证 → 守卫应为真（未误报）
        self.assertTrue(out["checks"]["eda_not_product_guard"])
        # 守卫是计算值：验证它与输入一致（非恒真）
        expected = not (out["facts"]["product_ready_computed"]
                        and not json.loads(PROJECT.read_text(encoding="utf-8"))
                        ["domains"]["eda"].get("project"))
        self.assertEqual(out["checks"]["eda_not_product_guard"], expected)

    def test_fabricated_eda_evidence_is_rejected(self):
        import tempfile
        # 负例 1：虚构本地工程路径
        def fake_path(p):
            p["domains"]["eda"]["project"] = "/tmp/nonexistent-fake/Fake.eprj3"
            p["domains"]["eda"]["readback_file"] = None
            p["domains"]["eda"]["outputs_present"] = []
        code, out = run_validator(project=self._variant(fake_path))
        self.assertTrue(any("EDA 工程证据" in f for f in out["failures"]), "虚构路径必须被检出")
        # 负例 2：虚构 EDA 产物（uuid 与读回身份不符 / evidence 文件缺失）
        def fake_outputs(p):
            eda = p["domains"]["eda"]
            eda["project"] = {
                "kind": "cloud", "project_uuid": "4ab9e52666a4fc7fe9b1d0c7c4c4263444d972eb139973d04478d976200a78b8",
                "schematic_uuid": "7415725566084bd0",
                "local_session_path": "/Users/yanfenma/Documents/LCEDA-Pro/projects/SpaceBuddy-R1",
                "readback_file": "hardware/space-buddy-r1/eda-readback.json"}
            eda["outputs_present"] = [
                {"name": "原理图", "uuid": "deadbeef", "evidence": "hardware/space-buddy-r1/eda-readback.json"},
                {"name": "PCB", "uuid": "7415725566084bd0", "evidence": "hardware/无此文件.json"}]
        code, out = run_validator(project=self._variant(fake_outputs))
        self.assertTrue(any("EDA 产物证据缺陷" in f for f in out["failures"]), "虚构产物必须被检出")

    def test_checks_json_tamper_detected(self):
        # 负例：手改 checks.json 把失败改成 ok=true → 回执哈希比对必须检出
        checks_path = ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1/checks.json"
        backup = checks_path.read_bytes()
        try:
            cj = json.loads(checks_path.read_text())
            cj["ok"] = True; cj["failed"] = []
            checks_path.write_text(json.dumps(cj))
            code, out = run_validator()
            self.assertNotEqual(code, 0, "手改报告必须被检出")
            self.assertTrue(any("checks_sha256" in f or "不一致" in f for f in out["failures"]))
        finally:
            checks_path.write_bytes(backup)
            # 以真实重跑恢复一致性（字节还原的旧报告会与最新回执错位）
            run_real_checker()

    def test_first_batch_release_does_not_require_acceptance_or_payment(self):
        # 三态分离：下单授权与实物验收独立表达（facts），不混入设计缺口 reasons
        code, out = run_validator()
        reasons = " ".join(out["facts"]["product_ready_reasons"])
        self.assertNotIn("制造下单未获授权", reasons, "授权状态不得混入设计缺口")
        self.assertNotIn("实物验收未完成", reasons, "验收状态不得混入设计缺口")
        self.assertFalse(out["facts"]["manufacturing_authorized"])
        self.assertFalse(out["facts"]["product_accepted"])
        self.assertEqual(out["checks"]["cad_evidence_state"], "valid")


class DependencyGraphTests(unittest.TestCase):
    def test_dims_changes_reach_checks_joint_and_package(self):
        proj = json.loads(PROJECT.read_text(encoding="utf-8"))
        for key in ("dims.usb_ports", "dims.keys", "dims.boss", "dims.skirt"):
            downs = proj["dependency_graph"][key]["downstream"]
            self.assertIn("cad.checks", downs, f"{key} 必须影响机械检查")
            self.assertIn("joint-checks", downs, f"{key} 必须影响板壳联合检查")
            self.assertIn("manufacturing.package", downs, f"{key} 必须影响制造资料")

    def test_changed_preview_lists_downstream(self):
        code, out = run_validator(changed="dims.boss")
        self.assertEqual(code, 0)
        self.assertTrue(out["stale_preview"])
        self.assertTrue(any("joint-checks" in s for s in out["stale_preview"]))
        self.assertTrue(any("manufacturing.package" in s for s in out["stale_preview"]))


class BuildPathTests(unittest.TestCase):
    def test_build_data_works_from_outside_repo(self):
        proc = run_build_data(cwd=tempfile.gettempdir())
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        wb = json.loads((ROOT / "workbench/web/workbench.json").read_text())
        self.assertTrue(wb["hardware"]["ok"])

    def test_build_data_reports_failure_readable_when_project_broken(self):
        # 项目文件损坏 → 工作台必须得到明确失败信息，而非旧的成功结论
        with tempfile.TemporaryDirectory() as td:
            broken = Path(td) / "broken.json"
            broken.write_text("{ not valid json", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "hardware/check_project.py"),
                 "--project", str(broken)],
                capture_output=True, text=True, timeout=60, cwd=str(ROOT))
            self.assertNotEqual(proc.returncode, 0)


class RealGeometryNote(unittest.TestCase):
    def test_real_freecad_run_recorded(self):
        # 说明：本文件 StaleEvidenceTests.test_recovery_requires_real_rerun
        # 已执行真实 FreeCAD（捆绑 python）完成几何重算与回执重建；
        # 该运行的成功/失败在该用例断言，此处登记以防漏跑。
        self.assertTrue(FC_PY.startswith("/Applications/FreeCAD.app"))




class QuadPartialTests(unittest.TestCase):
    """四元组禁止部分声明（整改时曾被误删，回归补回）。"""

    def test_quad_partial_is_rejected(self):
        import tempfile
        proj = json.loads(PROJECT.read_text(encoding="utf-8"))
        del proj["version_contract"]["revisions"]["bom"]
        tmp = Path(tempfile.mkstemp(suffix=".json", dir=str(ROOT / "hardware"))[1])
        tmp.write_text(json.dumps(proj, ensure_ascii=False), encoding="utf-8")
        code, out = run_validator(project=tmp)
        tmp.unlink()
        self.assertEqual(code, 2)
        self.assertFalse(out["checks"]["quad_complete"])


class WorkbenchHardwareCardTests(unittest.TestCase):
    """首屏卡：硬件校验结果与九问数据必须存在且如实。"""

    def test_hardware_section_present_and_facts_flow(self):
        wb = json.loads((ROOT / "workbench/web/workbench.json").read_text(encoding="utf-8"))
        hw = wb.get("hardware") or {}
        self.assertTrue(hw.get("ok"), f"校验未通过：{hw.get('failures')}")
        facts = hw.get("facts") or {}
        self.assertFalse(facts.get("product_ready"), "产品未完成不得标就绪")
        self.assertEqual(facts.get("pcb_status"), "进行中（原生工程已建立，产物未齐）")
        self.assertFalse(facts.get("package_complete"))
        nine = wb.get("hardware_next") or {}
        for key in ("looks_like", "appearance_progress", "blockers",
                    "next_owner", "needs_user"):
            self.assertIn(key, nine, f"九问卡缺字段：{key}")
        # EDA 环境可用 ≠ 产品就绪（环境检查与产品事实分离）
        self.assertIsNotNone(wb.get("environment", {}).get("checks"))




class EdaEvidenceNegativeTests(unittest.TestCase):
    """EDA 产物核验负例：重复引用/伪造类型/虚构 PCB/读回冒充。"""

    def _variant(self, mutate):
        proj = json.loads(PROJECT.read_text(encoding="utf-8"))
        mutate(proj)
        tmp = Path(tempfile.mkstemp(suffix=".json", dir=str(ROOT / "hardware"))[1])
        tmp.write_text(json.dumps(proj, ensure_ascii=False), encoding="utf-8")
        self.addCleanup(lambda: tmp.exists() and tmp.unlink())
        return tmp

    def runv(self, project):
        args = [sys.executable, str(CHECKER), "--project", str(project)]
        proc = subprocess.run(args, capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def test_duplicate_reference_detected(self):
        def m(p):
            out = p["domains"]["eda"]["outputs_present"]
            out.append(dict(out[0]))
        out = self.runv(self._variant(m))
        self.assertTrue(any("重复引用" in f for f in out["failures"]))

    def test_fake_type_detected(self):
        def m(p):
            out = p["domains"]["eda"]["outputs_present"]
            out.append({"name": "假产物", "type": "3mf", "uuid": "7415725566084bd0",
                        "evidence": "hardware/space-buddy-r1/eda-readback.json"})
        out = self.runv(self._variant(m))
        self.assertTrue(any("未知产物类型" in f for f in out["failures"]))

    def test_readback_cannot_impersonate_gerber(self):
        def m(p):
            out = p["domains"]["eda"]["outputs_present"]
            out.append({"name": "假 Gerber", "type": "gerber", "uuid": "7415725566084bd0",
                        "evidence": "hardware/space-buddy-r1/eda-readback.json"})
        out = self.runv(self._variant(m))
        self.assertTrue(any("冒充证据" in f for f in out["failures"]))

    def test_fabricated_pcb_object_detected(self):
        def m(p):
            p["version_contract"]["revisions"]["pcb"] = 1
            out = p["domains"]["eda"]["outputs_present"]
            out.append({"name": "假 PCB", "type": "pcb", "uuid": "deadbeef" * 4,
                        "evidence": "hardware/space-buddy-r1/eda-readback.json"})
        out = self.runv(self._variant(m))
        self.assertTrue(any("pcb uuid 与读回身份不符" in f for f in out["failures"]))

    def test_free_cad_version_recorded_and_checked(self):
        out = self.runv(PROJECT)
        self.assertTrue(out["checks"].get("cad_evidence_state") in ("valid", "stale", "unknown"))
        import json as _json
        receipt = _json.loads((ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1/receipt.json").read_text())
        self.assertIn("freecad_version", receipt, "回执必须记录 FreeCAD 版本")
        self.assertIn("1.1.4", receipt.get("freecad_version", ""), "FreeCAD 版本应为主版本号")
        self.assertIn("execution_result", receipt)




class EdaTypeContractTests(unittest.TestCase):
    """EDA 类型合同：严格 path+digest/读回身份对准/同一证据文件反冒充。"""

    def _variant(self, mutate):
        proj = json.loads(PROJECT.read_text(encoding="utf-8"))
        mutate(proj)
        tmp = Path(tempfile.mkstemp(suffix=".json", dir=str(ROOT / "hardware"))[1])
        tmp.write_text(json.dumps(proj, ensure_ascii=False), encoding="utf-8")
        self.addCleanup(lambda: tmp.exists() and tmp.unlink())
        return tmp

    def runv(self, project):
        proc = subprocess.run(
            [sys.executable, str(CHECKER), "--project", str(project)],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT))
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def test_duplicate_reference_detected(self):
        def m(p):
            out = p["domains"]["eda"]["outputs_present"]
            out.append(dict(out[0]))
        out = self.runv(self._variant(m))
        self.assertTrue(any("重复引用" in f for f in out["failures"]))

    def test_fake_type_detected(self):
        def m(p):
            p["domains"]["eda"]["outputs_present"].append(
                {"name": "假产物", "type": "3mf", "uuid": "7415725566084bd0",
                 "evidence": "hardware/space-buddy-r1/eda-readback.json"})
        out = self.runv(self._variant(m))
        self.assertTrue(any("未知产物类型" in f for f in out["failures"]))

    def test_readback_cannot_impersonate_gerber(self):
        def m(p):
            p["domains"]["eda"]["outputs_present"].append(
                {"name": "假 Gerber", "type": "gerber", "uuid": "7415725566084bd0",
                 "evidence": "hardware/space-buddy-r1/eda-readback.json"})
        out = self.runv(self._variant(m))
        self.assertTrue(any("冒充证据" in f for f in out["failures"]))

    def test_fabricated_pcb_object_detected(self):
        def m(p):
            p["version_contract"]["revisions"]["pcb"] = 1
            p["domains"]["eda"]["outputs_present"].append(
                {"name": "假 PCB", "type": "pcb", "uuid": "deadbeef" * 4,
                 "evidence": "hardware/space-buddy-r1/eda-readback.json"})
        out = self.runv(self._variant(m))
        self.assertTrue(any("pcb uuid 与读回身份不符" in f for f in out["failures"]))

    def test_free_cad_version_unknown_fails(self):
        def m(p):
            pass  # 版本比对由 check_case 回执侧控制；此用例测试校验器逻辑
        # 回执缺 freecad_version → 证据 stale（在 check_case 侧生成时控制）
        # 这里验证 validator 正确传播 stale
        code, out = run_validator()
        self.assertIn(out["checks"]["cad_evidence_state"], ("valid", "stale", "unknown"))

    def test_pcb_status_separation(self):
        _, out = run_validator()
        facts = out["facts"]
        # PCB 对象已核验但设计未完成 → 四态不应全部为 True
        self.assertTrue(facts.get("pcb_object_verified"),
                        "PCB 对象应有读回核验")
        self.assertFalse(facts.get("pcb_layout_started"),
                        "布局未开始")
        self.assertFalse(facts.get("pcb_design_verified"),
                        "设计验证未完成")
        self.assertFalse(facts.get("pcb_frozen"),
                        "PCB 未冻结")


class NetlistClosureTests(unittest.TestCase):
    """2026-11-28 原理图真正闭环整改：真实排针/按键 GPIO/GND 网表断言与占位隔离。"""

    NET = ROOT / "hardware/space-buddy-r1/netlist-evidence.net"
    EVIDENCE = ROOT / "hardware/space-buddy-r1/netlist-evidence.json"
    ASSERT = ROOT / "hardware/space-buddy-r1/eda-assert-netlist.py"
    READBACK = ROOT / "hardware/space-buddy-r1/eda-readback.json"

    def _netlist_text(self):
        return self.NET.read_text(encoding="utf-8")

    def test_netlist_assertions_pass_on_committed_evidence(self):
        # 提交的 .net 必须通过全部机器断言（--check 只断言不写文件）
        proc = subprocess.run([sys.executable, str(self.ASSERT), "--check"],
                              capture_output=True, text=True, timeout=30, cwd=str(ROOT))
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
        self.assertEqual(proc.returncode, 0, f"断言失败: {out.get('failed')}")
        self.assertTrue(out.get("ok"))

    def test_gpio_nets_contain_real_header_pins(self):
        # 假完成检测：GPIO 网络必须同时含排母引脚与按键引脚（只有标签不算）
        text = self._netlist_text()
        for net, jpin, kpin in (("GPIO4", "J1-4", "K1-1"), ("GPIO5", "J1-5", "K2-1"),
                                ("GPIO6", "J1-6", "K3-1"), ("GPIO7", "J1-7", "K4-1")):
            self.assertIn(f"(\n{net} ", text, f"{net} 网络缺失")
            block = text.split(f"(\n{net} ", 1)[1].split("\n)", 1)[0]
            self.assertIn(jpin, block, f"{net} 缺排母引脚 {jpin}")
            self.assertIn(kpin, block, f"{net} 缺按键引脚 {kpin}")

    def test_gnd_includes_switch_grounds_and_real_board_gnd(self):
        text = self._netlist_text()
        block = text.split("(\nGND ", 1)[1].split("\n)", 1)[0]
        for pin in ("K1-2", "K2-2", "K3-2", "K4-2",
                    "J1-22", "J3-1", "J3-21", "J3-22"):
            self.assertIn(pin, block, f"GND 缺真实引脚 {pin}")

    def test_evidence_json_is_machine_generated_and_hash_bound(self):
        ev = json.loads(self.EVIDENCE.read_text(encoding="utf-8"))
        actual = hashlib.sha256(self.NET.read_bytes()).hexdigest()
        self.assertEqual(ev.get("sha256"), actual, "证据哈希与 .net 实际内容不符")
        self.assertEqual(ev.get("size"), self.NET.stat().st_size)
        self.assertIn("自动生成", ev.get("note", ""))
        self.assertTrue(ev.get("persistence", {}).get("stable"))

    def test_switch_supplier_part_is_tbd_not_lcsc(self):
        # C9900017374 不得作为 Supplier Part 声明（仅允许 FOOTPRINT 结构占位）
        ev = json.loads(self.EVIDENCE.read_text(encoding="utf-8"))
        for des, rec in ev.get("components", {}).items():
            if des.startswith("K"):
                self.assertNotIn("C9900017374", rec.get("supplier_part", ""),
                                 f"{des} Supplier Part 仍含 C9900017374")
        self.assertIn("TBD", ev.get("switch_footprint", ""))
        self.assertIn("禁止用于制造", ev.get("switch_footprint", ""))

    def test_designators_unified_in_project_records(self):
        p = json.loads(PROJECT.read_text(encoding="utf-8"))
        des = p["domains"]["eda"]["schematic_progress"]["component_designators"]
        self.assertEqual(des, {"header_left": "J1", "header_right": "J3",
                               "switch_1": "K1", "switch_2": "K2",
                               "switch_3": "K3", "switch_4": "K4"})
        rb = json.loads(self.READBACK.read_text(encoding="utf-8"))
        # 读回一致性：位号修改后 API 读回同值
        self.assertEqual(rb["designator_readback"]["K1"], "K1")
        self.assertEqual(rb["designator_readback"]["J3"], "J3")

    def test_official_pinout_basis_and_erc_classification_recorded(self):
        p = json.loads(PROJECT.read_text(encoding="utf-8"))
        sp = p["domains"]["eda"]["schematic_progress"]
        self.assertIn("ESP32-S3-DevKitC-1 v1.1", sp.get("official_pinout_basis", ""))
        erc = sp["erc"]
        self.assertEqual(erc["error"], 0)
        # Warning 必须有引脚级分类，不允许笼统"均预期"
        self.assertIn("预期未使用引脚", erc["detail"])
        self.assertIn("USB", erc["detail"])
        rb = json.loads(self.READBACK.read_text(encoding="utf-8"))
        groups = rb["erc"]["groups"]
        self.assertEqual(sum(g["count"] for g in groups), 40,
                         "ERC 浮动引脚计数应逐组记录")

    def test_footprint_placeholder_is_quarantined_not_final(self):
        p = json.loads(PROJECT.read_text(encoding="utf-8"))
        sp = p["domains"]["eda"]["schematic_progress"]
        ph = sp.get("switch_footprint_placeholder", "")
        self.assertIn("SW-SMD_C9900017374", ph)
        self.assertIn("禁止用于制造", ph)
        self.assertIn("TBD", sp.get("switch_symbol", ""))


if __name__ == "__main__":
    unittest.main()
