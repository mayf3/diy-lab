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


class ZeroSolderConstraintTests(unittest.TestCase):
    """零焊接核心约束必须贯穿 spec/模型/CAD 任务书/交付方案，防止工序转嫁给用户。"""

    def setUp(self):
        base = ROOT / "source-data/agent-button-deck/pcba-v1"
        self.spec = (base / "space-buddy-r1-spec.md").read_text(encoding="utf-8")
        self.models = (base / "models-r1.md").read_text(encoding="utf-8")
        self.taskbook = (base / "g2-case-cad-taskbook.md").read_text(encoding="utf-8")
        plan_path = base / "factory-delivery-plan.md"
        self.assertTrue(plan_path.is_file(), "factory-delivery-plan.md 缺失")
        self.plan = plan_path.read_text(encoding="utf-8")

    def test_zero_solder_is_propagated_through_all_stages(self):
        self.assertIn("零焊接核心约束", self.spec)
        self.assertIn("G8 否决项", self.spec)
        self.assertIn("零焊接（P0", self.models)
        self.assertIn("免焊接独立复装", self.models)
        self.assertIn("G2-0 主体与底座先行", self.taskbook)
        self.assertIn("零焊接验证（P0）", self.taskbook)

    def test_factory_plan_covers_all_seven_capabilities(self):
        for capability in ("PCB 制板", "SMT 贴片", "MX 机械轴通孔插件焊",
                           "排母/连接器插件焊", "客供特殊元件代焊",
                           "外壳 3D 打印", "不同颜色零件分别制造"):
            self.assertIn(capability, self.plan, f"能力表缺行：{capability}")
        self.assertIn("SMT 能力 ≠ 插件焊接能力", self.plan,
                      "不得把 SMT 能力等同于插件焊接能力")
        self.assertIn("未上架的器件可以邮寄到嘉立创焊接", self.plan,
                      "客供件代焊依据必须引用官方帮助文档")
        self.assertIn("不得转嫁焊接给用户", self.plan)

    def test_real_dimensions_gate_for_openings(self):
        self.assertIn("必须由真实元件尺寸确定", self.taskbook,
                      "键帽孔/轴孔/固定孔/USB 开孔必须由真实元件尺寸确定")


class UserFacingDeliveryTests(unittest.TestCase):
    """用户视角交付物：采购与组装说明必须保持零焊接、不代付、无术语门槛。"""

    def setUp(self):
        base = ROOT / "source-data/agent-button-deck/pcba-v1"
        self.batch1 = (base / "bom-batch1-user.md").read_text(encoding="utf-8")
        self.guide = (base / "assembly-guide-draft.md").read_text(encoding="utf-8")
        self.talk = (base / "jlc-dfm-checklist.md").read_text(encoding="utf-8")

    def test_batch1_has_six_elements_and_no_auto_purchase(self):
        for kw in ("兼容性依据", "替代", "参考链接", "实时价格", "确认"):
            self.assertIn(kw, self.batch1, f"第一批清单缺要素：{kw}")
        for sku in ("Gazzew Boba U4", "ESP32-S3-DevKitC-1-N8R8"):
            self.assertIn(sku, self.batch1, f"第一批清单缺准确 SKU：{sku}")
        self.assertIn("自己下单付款", self.batch1, "必须写明由负责人本人下单付款")
        self.assertIn("U4T 不是静音轴", self.batch1, "型号警示必须保留")

    def test_assembly_guide_is_solder_free(self):
        self.assertIn("全篇没有任何焊接", self.guide)
        for banned in ("焊接步骤", "烙铁", "飞线"):
            self.assertNotIn(banned, self.guide.split("维护")[1] if "维护" in self.guide else self.guide)
        self.assertIn("维护", self.guide)
        self.assertIn("不需要任何焊接工具", self.guide)

    def test_dfm_script_covers_switch_and_materials(self):
        self.assertIn("手插", self.talk)
        self.assertIn("邮寄", self.talk)
        self.assertIn("华秋", self.talk, "外部供应商预案必须留名")


class CaseViewerAssetTests(unittest.TestCase):
    """G2-0 外壳查看器三件套必须存在且互相引用（防生成产物漂移）。"""

    def test_viewer_files_exist_and_reference_each_other(self):
        web = ROOT / "workbench/web"
        html = web / "case-r1-viewer.html"
        js = web / "case-r1-viewer.js"
        data = web / "case-r1-viewer-data.js"
        for f in (html, js, data):
            self.assertTrue(f.is_file(), f"缺少 {f.name}")
        text = html.read_text(encoding="utf-8")
        self.assertIn("case-r1-viewer-data.js", text)
        self.assertIn("case-r1-viewer.js", text)
        self.assertGreater(data.stat().st_size, 100_000, "网格数据过小，疑似生成失败")
        self.assertIn("CASE_DATA", data.read_text(encoding="utf-8")[:200])

    def test_case_model_and_placeholders_exist(self):
        out = ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1"
        for name in ("case-r1-body", "case-r1-base", "case-r1-cap-a",
                     "case-r1-cap-b", "case-r1-cap-c", "case-r1-cap-d"):
            self.assertTrue((out / f"{name}.step").is_file(), f"缺少 {name}.step")
            self.assertTrue((out / f"{name}.stl").is_file(), f"缺少 {name}.stl")
        dims = json.loads((out / "dims.json").read_text(encoding="utf-8"))
        self.assertIn("不得标 Manufacturable", dims["rule"], "占位模型必须声明禁止标 Manufacturable")

    def test_dimension_sources_are_typed_and_honest(self):
        out = ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1"
        dims = json.loads((out / "dims.json").read_text(encoding="utf-8"))["sources"]
        # 三态分级 + 页码/测量方式/冻结状态登记
        for key, d in dims.items():
            self.assertIn(d["status"], ("confirmed-official", "awaiting-measure", "placeholder"),
                          f"{key} 的状态必须是三态之一")
            for field in ("doc", "measure", "freeze"):
                self.assertIn(field, d, f"{key} 缺少 {field} 登记")
        # 官方标注 vs 图纸估读 vs 占位 三类必须区分
        self.assertEqual(dims["board_outline"]["source"], "official-doc")
        self.assertIn("62.74", dims["board_outline"]["value"])
        self.assertEqual(dims["usb_zone_8mm"]["source"], "official-doc")
        self.assertIn("不可与 62.74 相加", dims["usb_zone_8mm"]["value"],
                      "8.00mm 的含义必须显式声明，禁止直接相加成总长")
        self.assertIn("≈70.7", dims["board_envelope"]["value"])
        self.assertEqual(dims["board_envelope"]["source"], "official-drawing-read",
                         "整板包络是估读综合，不得标 official-doc")
        self.assertEqual(dims["usb_types"]["source"], "official-doc")
        self.assertIn("J2", dims["usb_types"]["value"])
        self.assertIn("J4", dims["usb_types"]["value"])
        self.assertEqual(dims["usb_ports"]["source"], "official-drawing-read",
                         "中心距是图纸估读")
        self.assertEqual(dims["keys"]["status"], "awaiting-measure", "键帽机构等样轴实测")
        self.assertEqual(dims["boss"]["status"], "placeholder", "PCB 螺柱等 G4 板框")

    def test_geometry_checks_all_green(self):
        out = ROOT / "source-data/agent-button-deck/pcba-v1/cad/renders/case-r1"
        checks = json.loads((out / "checks.json").read_text(encoding="utf-8"))
        self.assertTrue(checks["ok"], f"几何检查未全绿：{checks['failed']}")
        for key in ("body_base_interference_vol", "body_caps_interference_vol",
                    "base_caps_interference_vol"):
            self.assertEqual(checks["checks"][key], 0, f"{key} 必须为零干涉")
        # 双开口必须是真实几何结论（截面分段+中心距+贯穿），不是参数复读
        self.assertTrue(checks["checks"]["rear_wall_two_openings"], "背壁截面必须有两个分离开口")
        self.assertTrue(checks["checks"]["usb_two_openings_geometric"])
        self.assertEqual(checks["measured"]["usb_center_distance"], 12.5)
        self.assertEqual(checks["measured"]["usb_opening_widths"], [11.2, 11.2])
        self.assertTrue(checks["checks"]["usb_holes_through_wall"], "开孔必须贯穿背壁")
        self.assertTrue(checks["checks"]["usb_plug_envelope_passes"], "插头包络必须可通过")
        self.assertTrue(checks["checks"]["usb_envelope_vs_base_clear"], "包络不得撞底座裙壁")
        self.assertTrue(checks["checks"]["assembly_body_in_base"], "主体必须完整落入底座开口")
        self.assertIn("check_case.py", checks.get("note", ""), "checks 必须声明由 STEP 重算")

    def test_checker_negative_selftest_is_documented_and_runnable(self):
        checker = (ROOT / "source-data/agent-button-deck/pcba-v1/cad/check_case.py")
        text = checker.read_text(encoding="utf-8")
        self.assertIn("G2_OUT", text, "检查器必须支持环境变量指定产物目录")
        self.assertIn("self_test", text, "检查器必须内置负向自检")
        self.assertIn("neg_boss_corner_collision_detected", text)
        self.assertIn("neg_small_pocket_detected", text)
        run_doc = (ROOT / "source-data/agent-button-deck/pcba-v1/cad/g2-case-r1.py").read_text(encoding="utf-8")
        # 运行方式必须写进脚本头注释（freecadcmd 对部分目录静默不执行，用捆绑 python 直跑）
        self.assertIn("PYTHONPATH", run_doc + text, "运行方式文档必须存在")


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


class ReferenceStudiesTests(unittest.TestCase):
    """参考工程研究区：只登记来源/许可/模式，不得把第三方文件登记为本地资产。"""

    def setUp(self):
        catalog = load("workbench/catalog.json")
        self.catalog = catalog
        self.studies = catalog["projects"]["agent-button-deck"].get("reference_studies")
        generated = load("workbench/web/workbench.json")
        gen_button = next(
            (p for p in generated["projects"] if p["id"] == "agent-button-deck"), None)
        self.gen_studies = gen_button.get("reference_studies") if gen_button else None

    def _study(self):
        self.assertIsInstance(self.studies, list, "button-deck 缺少 reference_studies 区")
        study = next((s for s in self.studies if "HachimoDock" in s["name"]), None)
        self.assertIsNotNone(study, "HachimoDock 参考研究未登记")
        return study

    def test_hachimodock_study_registered_with_license_and_boundary(self):
        study = self._study()
        for field in ("url", "license", "study_doc", "completeness",
                      "patterns", "tasks", "open_questions", "boundary"):
            self.assertIn(field, study, f"参考研究缺少字段：{field}")
        self.assertIn("SDFL-PPO", study["license"], "MakerWorld 仅限平台打印边界必须记录")
        self.assertIn("非商业", study["license"], "仓库非商业许可边界必须记录")

    def test_completeness_is_four_state_and_honest(self):
        completeness = self._study()["completeness"]
        self.assertIsInstance(completeness, dict, "完成度必须是四态结构")
        expected = {
            "来源与许可审计": "完成",
            "六方面资料研究": "完成",
            "原始 PCB/EDA/STEP 工程直接审查": "未完成",
            "实物制造复现": "未完成",
        }
        self.assertEqual(completeness, expected,
                         "完成度四态口径漂移：未下载的工程文件与未复现的实物不得标为完成")

    def test_study_doc_is_in_documents_allowlist(self):
        study = self._study()
        allowlisted = [d for d in self.catalog["documents"]
                       if d.get("path") == study["study_doc"]]
        self.assertTrue(allowlisted,
                        "study_doc 必须登记进 documents allowlist 才能成为文档链接")
        self.assertEqual(allowlisted[0]["id"], "hachimodock-study")
        self.assertTrue((ROOT / study["study_doc"]).is_file(),
                        "allowlist 指向的研究文档实际不存在")

    def test_g1_decision_items_match_confirmed_preferences(self):
        decisions = " | ".join(
            self.catalog["projects"]["agent-button-deck"]["status_block"]["decision_items"])
        self.assertNotIn("手感", decisions, "tactile-light+quiet 已确认，不得再列为待决策")
        self.assertNotIn("机构定档", decisions, "按键机构偏好已确认，不得再列为待决策")
        self.assertIn("键帽四色打印路线", decisions, "四色打印路线保留为 G2 前待决策")
        self.assertIn("F13", decisions)
        blockers = " | ".join(
            self.catalog["projects"]["agent-button-deck"]["status_block"]["blockers"])
        self.assertIn("样轴", blockers, "轴体 SKU 等待样轴验证，应登记为阻断")

    def test_tasks_map_to_g2_g4_g6_without_new_gates(self):
        tasks = " | ".join(self._study()["tasks"])
        for gate in ("G2-", "G4-", "G6-"):
            self.assertIn(gate, tasks, f"缺少 {gate} 显式任务映射")

    def test_study_doc_exists_and_declares_no_copy_rule(self):
        doc = ROOT / "source-data/agent-button-deck/pcba-v1/reference-studies/hachimodock-study.md"
        self.assertTrue(doc.is_file(), "hachimodock-study.md 缺失")
        text = doc.read_text(encoding="utf-8")
        self.assertIn("SHA256", text)
        self.assertIn("不复制", text)
        self.assertIn("四列", text)
        self.assertIn("完成度四态", text)

    def test_reference_studies_flow_to_generated_data(self):
        self.assertEqual(self.gen_studies, self.studies,
                         "reference_studies 未透传到生成的 workbench.json")

    def test_no_third_party_files_committed_into_repo(self):
        ref_dir = ROOT / "source-data/agent-button-deck/pcba-v1/reference-studies"
        allowed_ext = {".md"}
        for f in ref_dir.iterdir():
            self.assertIn(f.suffix, allowed_ext,
                          f"参考研究目录出现非文档文件 {f.name}（不得复制第三方工程文件）")

class ComponentRegistryTests(unittest.TestCase):
    """实物尺寸统一登记表必须存在且区分来源等级；DFM 话术必须具体到 SKU。"""

    def setUp(self):
        base = ROOT / "source-data/agent-button-deck/pcba-v1"
        self.registry = (base / "component-dimensions-registry.md").read_text(encoding="utf-8")
        self.dfm = (base / "jlc-dfm-checklist.md").read_text(encoding="utf-8")
        self.batch1 = (base / "bom-batch1-user.md").read_text(encoding="utf-8")

    def test_registry_covers_all_components_with_graded_sources(self):
        for comp in ("ESP32-S3-DevKitC-1", "机械轴", "排母", "PCB 载板"):
            self.assertIn(comp, self.registry, f"登记表缺部件：{comp}")
        for level in ("官方文档", "官方图纸估读", "标准推算", "实物测量", "待定"):
            self.assertIn(level, self.registry, f"登记表缺来源等级：{level}")
        self.assertIn("不能改标为「实物测量」", self.registry,
                      "估读与实测的边界必须显式声明")

    def test_dfm_inquiry_names_specific_switch_not_generic(self):
        self.assertIn("Boba U4", self.dfm, "DFM 询问必须点名具体轴体候选")
        self.assertIn("15.6×15.6", self.dfm, "DFM 询问必须给出轴体外廓")
        self.assertIn("不能仅凭", self.dfm, "通用插件声明不构成轴体代焊证据")
        self.assertIn("手插 + 后焊", self.dfm)

    def test_batch1_marks_unverified_items_honestly(self):
        self.assertIn("待核对", self.batch1, "未抓到实时价格的项必须标待核对")
        self.assertIn("预焊排针照片", self.batch1, "预焊排针必须要求照片核对")
        self.assertIn("U4T 不是静音轴", self.batch1)


if __name__ == "__main__":
    unittest.main()
