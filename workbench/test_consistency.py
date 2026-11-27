"""Button Deck R1 数据一致性检查（自动防漂移）。

审阅意见（2026-11-27）要求增加自动一致性检查，防止旧串口路线数据回流：
- catalog.json 的 button-deck 现行产物不得把旧串口固件/bridge 当作当前产物，
  也不得在现行描述中出现“115200 串口”这类已被 R1 否定的运行口径；
- productization/projects.json 的 constraint 必须确认原生 USB HID 路线；
- R1 正式视觉基准资产（concept-r1.png）必须存在且被 allowlist 引用；
- environment-status.json 必须保持激活与读写往返的验收链完整。

本文件是数据一致性单测，不访问网络、不读取激活材料。
运行：python3 -m unittest discover -s workbench -p 'test_*.py' -v
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(relpath):
    return json.loads((ROOT / relpath).read_text(encoding="utf-8"))


class ButtonDeckR1ConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("workbench/catalog.json")
        self.projects = load("source-data/productization/projects.json")
        self.env = load("docs/eda/environment-status.json")
        self.button = next(
            (p for p in self.projects["projects"] if p["id"] == "agent-button-deck"), None)
        self.button_catalog = self.catalog["projects"]["agent-button-deck"]
        # artifacts 在 catalog 条目里；productization 条目没有该字段
        self.artifacts = {a["name"]: a for a in self.button_catalog["artifacts"]}

    def test_native_usb_route_is_confirmed_in_project_record(self):
        self.assertIn("HID", self.button["constraint"])
        self.assertIn("OTG", self.button["constraint"])
        self.assertNotIn("需要重新评估", self.button["constraint"])

    def test_current_artifacts_do_not_claim_serial_runtime(self):
        for name, artifact in self.artifacts.items():
            if "旧串口" in name or "基线" in name:
                continue  # 明确标注的历史基线允许保留
            detail = artifact.get("detail", "")
            self.assertNotIn(
                "115200", detail,
                f"现行产物 {name} 的描述引用了已被 R1 否定的串口运行口径")
            self.assertNotIn(
                "常驻 bridge", detail.replace("不依赖常驻 bridge", ""),
                f"现行产物 {name} 的描述不得宣称依赖常驻 bridge")

    def test_old_serial_firmware_is_not_presented_as_current(self):
        stale_names = [n for n in self.artifacts if "现有按键固件" in n]
        for name in stale_names:
            self.fail(f"旧串口固件仍以原名出现在现行产物清单：{name}（应标注为基线/历史对照）")
        baseline = [n for n in self.artifacts if "旧串口固件" in n]
        if baseline:
            artifact = self.artifacts[baseline[0]]
            self.assertEqual(artifact.get("status"), "hold",
                             "基线固件即使保留，也必须是 hold 状态而非现行产物")

    def test_r1_revision_doc_exists_and_declares_hid(self):
        doc = ROOT / "source-data/agent-button-deck/pcba-v1/revision-r1-usb-hid.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("F13", text)
        self.assertIn("原生 USB", text)
        self.assertIn("HID", text)

    def test_interface_contract_declares_r1_route_and_maintenance_scope(self):
        text = (ROOT / "source-data/agent-button-deck/pcba-v1/interface-contract.md").read_text(encoding="utf-8")
        self.assertIn("R1 路线声明", text)
        self.assertIn("降级为烧录/维护附录", text)
        self.assertIn("OTG", text)

    def test_official_visual_baseline_is_space_buddy(self):
        png = ROOT / "source-data/agent-button-deck/pcba-v1/renders/concept-r1.png"
        self.assertTrue(png.is_file() and png.stat().st_size > 10000,
                        "R1 正式视觉基准 PNG 缺失或过小")
        html = (ROOT / "source-data/agent-button-deck/pcba-v1/renders/concept-r1.html").read_text(encoding="utf-8")
        self.assertIn("Space Buddy Deck R1", html)
        self.assertIn("视觉方向已冻结", html)
        self.assertIn("工程尺寸未冻结", html)
        self.assertIn("制造未冻结", html)

    def test_environment_record_keeps_activation_and_round_trip_chain(self):
        self.assertEqual(self.env.get("editor_round_trip"), "passed")
        self.assertTrue(self.env.get("activation_accepted_at"))
        self.assertTrue(self.env.get("editor_round_trip_passed_at"))
        evidence = self.env.get("editor_round_trip_evidence", {})
        self.assertEqual(evidence.get("readback_schematic_marker_found"), True)
        self.assertEqual(evidence.get("readback_pcb_marker_found"), True)

    def test_freeze_states_are_explicit_in_visual_baseline(self):
        html = (ROOT / "source-data/agent-button-deck/pcba-v1/renders/concept-r1.html").read_text(encoding="utf-8")
        for state in ("视觉方向已冻结", "工程尺寸未冻结", "制造未冻结"):
            self.assertIn(state, html,
                          f"三态冻结口径缺失：{state}")


class GeneratedWorkbenchConsistencyTests(unittest.TestCase):
    """生成文件必须与上游数据一致（workbench.json 由 build_data.py 生成）。"""

    def test_generated_workbench_matches_upstream(self):
        catalog = load("workbench/catalog.json")
        generated = load("workbench/web/workbench.json")
        button = next(
            (p for p in generated["projects"] if p["id"] == "agent-button-deck"), None)
        self.assertIsNotNone(button, "生成数据缺少 agent-button-deck")
        upstream = catalog["projects"]["agent-button-deck"]
        self.assertEqual(button["tagline"], upstream["tagline"])
        self.assertEqual(button["stages"], upstream["stages"])
        generated_names = [a["name"] for a in button["artifacts"]]
        for name in ("R1 概念效果图", "HID 固件草稿", "R1 设计修订记录"):
            self.assertIn(name, generated_names,
                          f"生成数据缺少 R1 产物：{name}")


if __name__ == "__main__":
    unittest.main()


class StatusBlockTests(unittest.TestCase):
    """工作台必须显示：版本/G 阶段/负责人/最近完成/下一项/阻断/需决策/各域状态。"""

    def setUp(self):
        self.catalog = load("workbench/catalog.json")
        self.button = self.catalog["projects"]["agent-button-deck"]
        self.generated = load("workbench/web/workbench.json")
        self.gen_button = next(
            (p for p in self.generated["projects"] if p["id"] == "agent-button-deck"), None)

    def test_status_block_fields_complete(self):
        sb = self.button.get("status_block")
        self.assertIsInstance(sb, dict, "button-deck 缺少 status_block")
        for field in ("version", "g_stage", "owner", "last_completed",
                      "next_work", "blockers", "needs_user_decision",
                      "freeze", "domain_status"):
            self.assertIn(field, sb, f"status_block 缺少字段：{field}")
        self.assertIn("visual", sb["freeze"])
        self.assertIn("dimensions", sb["freeze"])
        self.assertIn("manufacturing", sb["freeze"])

    def test_status_block_flows_to_generated_data(self):
        self.assertIsNotNone(self.gen_button)
        self.assertEqual(self.gen_button.get("status_block"),
                         self.button.get("status_block"))

    def test_eda_ready_is_not_design_ready(self):
        sb = self.button["status_block"]
        self.assertFalse(sb["product_ready"],
                         "EDA/设计数据不得把产品标为已就绪")
        self.assertIn("EDA ready", sb["product_ready_note"])
