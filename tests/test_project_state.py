#!/usr/bin/env python3
"""Cross-page fact consistency checks: structured fields and their sources.

历史文档允许保留旧状态，但必须标注作废；结构化状态（projects.json）必须与
DOAVR 权威源（source-data/<slug>/workflow.json 的 public_status）一致。
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))
BY_SLUG = {p["slug"]: p for p in PROJECTS}


def workflow(slug: str):
    path = ROOT / "source-data" / slug / "workflow.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


class WorkflowLinkage(unittest.TestCase):
    """projects.json 的状态必须能在 DOAVR 权威源里得到验证。"""

    def test_public_status_matches_projects_json(self):
        for slug, project in BY_SLUG.items():
            data = workflow(slug)
            if data is None:
                continue
            self.assertEqual(
                data.get("public_status"), project["status"],
                f"{slug}: projects.json 状态与 workflow.json public_status 不一致")

    def test_building_or_verified_requires_evidenced_transition(self):
        for slug, project in BY_SLUG.items():
            if project["status"] not in {"building", "verified"}:
                continue
            data = workflow(slug)
            self.assertIsNotNone(
                data, f"{slug}: 标记 {project['status']} 必须先建 workflow.json 权威源")
            history = data.get("status_history") or []
            self.assertTrue(
                any(h.get("to") == project["status"] and h.get("evidence_ref") for h in history),
                f"{slug}: 进入 {project['status']} 的状态史必须带 evidence_ref")

    def test_workflow_public_status_uses_known_states(self):
        allowed = {"planning", "preparing", "building", "verified",
                   "completed-unwritten", "archived"}
        for slug, project in BY_SLUG.items():
            data = workflow(slug)
            if data is None:
                continue
            self.assertIn(data.get("public_status"), allowed,
                          f"{slug}: public_status 超出 projects.json 允许枚举")


class TentPurchaseFacts(unittest.TestCase):
    """圣诞帐篷：采购事实口径（未下单、HelloKitty 已作废、验收未发生）。"""

    def setUp(self):
        self.tent = BY_SLUG["christmas-magic-tent"]
        self.index = (ROOT / "content/projects/christmas-magic-tent/index.md").read_text(encoding="utf-8")
        self.plan = (ROOT / "content/projects/christmas-magic-tent/consolidated-purchase-plan.md").read_text(encoding="utf-8")

    def test_status_is_preparing_not_building(self):
        self.assertEqual(self.tent["status"], "preparing",
                         "帐篷未下单（READY_BUY）：不得标记 building")

    def test_description_claims_purchase_without_arrival_acceptance(self):
        # 2026-11-13 用户确认已购买：描述可以声称已购买，但到货验收仍未发生
        self.assertIn("已购买", self.tent["description"])
        self.assertIn("尺寸待实测", self.tent["description"])
        for word in ("已到货", "验收通过"):
            self.assertNotIn(word, self.tent["description"],
                             "到货验收未发生：不得声称已到货或已通过验收")

    def test_index_header_no_longer_claims_no_purchase_planned(self):
        self.assertNotIn("规划中、明确暂不采购", self.index,
                         "采购决策已冻结：页首过期声明必须移除")

    def test_hellokitty_kept_as_history_but_marked_void(self):
        first = self.index.find("299.52")
        self.assertNotEqual(first, -1, "历史候选应保留可追溯记录")
        window = self.index[max(0, first - 300): first + 400]
        self.assertIn("作废", window, "HelloKitty 历史报价旁必须标注已作废")

    def test_final_sku_and_readiness_in_purchase_plan(self):
        self.assertIn("165cm", self.plan)
        self.assertIn("READY_BUY", self.plan)
        self.assertNotIn("已购买", self.plan)

    def test_budget_field_separates_actual_planned_and_cap(self):
        budget = self.tent["budget"]
        self.assertIn("已确认支出", budget, "预算字段必须写明实际支出口径")
        self.assertIn("上限", budget, "预算字段必须写明总预算上限")
        self.assertNotIn("非真实支出", budget, "旧的单一预算文案应已被三口径取代")

    def test_arrival_checklist_stays_unchecked_until_it_happens(self):
        checklist = (ROOT / "source-data/christmas-magic-tent/arrival-acceptance-checklist.md").read_text(encoding="utf-8")
        self.assertIn("- [ ]", checklist, "到货验收未发生：清单必须保留未勾选状态")
        self.assertNotIn("- [x]", checklist, "到货验收未发生：不得出现已勾选项")


class HeroCta(unittest.TestCase):
    """CTA 承诺必须与项目内容匹配：无可跟做教程前，只承诺「查看进展」。"""

    def test_cta_promises_progress_not_followable_build(self):
        build = (ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
        self.assertIn("查看圣诞帐篷制作进展", build)
        self.assertNotIn("跟做进行中的制作", build)


if __name__ == "__main__":
    unittest.main()
