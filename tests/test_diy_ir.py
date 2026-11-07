#!/usr/bin/env python3
"""No extra dependency; lightweight contract regression tests."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("render_diy_ir", ROOT / "scripts/render_diy_ir.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
PATH = ROOT / "source-data/hachimodock/workflow.json"
ROBOT_PATH = ROOT / "source-data/robot-lab-draw-tree/workflow.json"
ROBOT_DATA = json.loads(ROBOT_PATH.read_text(encoding="utf-8"))
DATA = json.loads(PATH.read_text(encoding="utf-8"))

class TestDiyIR(unittest.TestCase):
    def test_current_hachimo_workflow_valid(self):
        self.assertEqual(mod.validate(DATA, PATH), [])

    def test_two_views_are_synced(self):
        self.assertEqual((ROOT/"content/projects/hachimodock/human-track.md").read_text(encoding="utf-8"), mod.md_human(DATA))
        self.assertEqual((ROOT/"content/projects/hachimodock/agent-track.md").read_text(encoding="utf-8"), mod.md_agent(DATA))

    def test_no_printer_brand_assumption(self):
        routes = json.dumps(DATA["resource_routes"], ensure_ascii=False)
        self.assertIn("没有打印机", routes)
        self.assertIn("代打印", routes)
        self.assertTrue(any("打印" in r["question"] for r in DATA["resource_routes"]))

    def test_cannot_use_undocumented_actor(self):
        bad = copy.deepcopy(DATA)
        bad["tasks"][0]["actor"] = "magic-auto"
        self.assertTrue(mod.validate(bad, PATH))

    def test_cannot_bypass_physical_test_with_agent_claim(self):
        bad = copy.deepcopy(DATA)
        bad["tasks"][0]["actor"] = "agent"
        bad["tasks"][0]["verify"]["type"] = "physical-measurement"
        self.assertTrue(any("pure Agent step" in item for item in mod.validate(bad, PATH)))

    def test_detect_bad_dependency(self):
        bad = copy.deepcopy(DATA)
        bad["tasks"][1]["requires"] = ["A10"]
        self.assertTrue(any("dependencies" in item for item in mod.validate(bad, PATH)))

    def test_no_unproven_observed_claim(self):
        bad = copy.deepcopy(DATA)
        bad["tasks"][0]["verify"]["status"] = "observed"
        self.assertTrue(any("evidence_ref" in item for item in mod.validate(bad, PATH)))

    def test_status_labels_keep_planned_separate(self):
        self.assertTrue(all(t["status"] == "planned" and t["verify"]["status"] == "planned" for t in DATA["tasks"]))

class TestRobotDiyIR(unittest.TestCase):
    def test_robot_workflow_schema_is_valid(self):
        self.assertEqual(mod.validate(ROBOT_DATA, ROBOT_PATH), [])

    def test_robot_human_and_agent_views_are_generated(self):
        slug = "robot-lab-draw-tree"
        target = ROOT / "content/projects" / slug
        self.assertEqual((target / "human-track.md").read_text(encoding="utf-8"), mod.md_human(ROBOT_DATA))
        self.assertEqual((target / "agent-track.md").read_text(encoding="utf-8"), mod.md_agent(ROBOT_DATA))

    def test_no_required_printer_brand_and_offline_route(self):
        routes = json.dumps(ROBOT_DATA["resource_routes"], ensure_ascii=False)
        self.assertIn("代打印", routes)
        self.assertIn("先只做离线样例", routes)
        self.assertTrue(any(r["id"] == "workspace" for r in ROBOT_DATA["resource_routes"]))

    def test_explicit_payment_and_physical_gates(self):
        tasks = ROBOT_DATA["tasks"]
        self.assertTrue(any(t["verify"]["type"] == "human-approval" for t in tasks))
        self.assertTrue(any(t["verify"]["type"] == "device-log" for t in tasks))
        self.assertTrue(any(t["verify"]["type"] == "physical-measurement" for t in tasks))
        self.assertTrue(any(t["actor"] == "agent" and t["verify"]["type"] == "simulation" for t in tasks))
        self.assertTrue(all(t["status"] == "planned" and t["verify"]["status"] == "planned" for t in tasks))
        self.assertFalse(any(t["actor"] == "agent" and t["verify"]["type"].startswith("physical") for t in tasks))

    def test_tasks_link_into_existing_deep_tutorial(self):
        for t in ROBOT_DATA["tasks"]:
            relative = t["deep"].removeprefix("/").rstrip("/")
            self.assertTrue((ROOT / "content" / (relative + ".md")).is_file(), t["id"])


if __name__ == "__main__":
    unittest.main()
