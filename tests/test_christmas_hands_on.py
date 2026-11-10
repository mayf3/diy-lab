import base64
import io
import json
import unittest
import zipfile
from pathlib import Path
from scripts.build_christmas_hands_on import build, TARGET, ROOT

SOURCE = ROOT / "source-data/christmas-magic-tent/workflow.json"


class ChristmasHandsOnTest(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(SOURCE.read_text(encoding="utf-8"))
        payload = build()
        self.doc = json.loads(payload.partition("export const COURSE = ")[-1].removesuffix(";\n"))
        self.lessons = self.doc["lessons"]

    def test_three_lessons_nineteen_actions(self):
        self.assertEqual([x["action_ref"] for x in self.lessons], ["A02", "A03", "A04"])
        self.assertEqual([len(x["steps"]) for x in self.lessons], [5, 6, 8])
        self.assertEqual(sum(len(x["steps"]) for x in self.lessons), 19)

    def test_each_step_has_action_acceptance_and_stop(self):
        for lesson in self.lessons:
            for step in lesson["steps"]:
                for key in ("title", "do", "expected", "stop", "check", "caption", "scene"):
                    self.assertTrue(step.get(key), (lesson["id"], step["id"], key))

    def test_firmware_zips_contain_ide_correct_structure(self):
        expected_names = [
            {"FirstBlink/FirstBlink.ino"},
            {"ButtonLamp/ButtonLamp.ino"},
            {"ChristmasStar/ChristmasStar.ino", "ChristmasStar/controller.h"},
        ]
        for lesson, expected in zip(self.lessons, expected_names):
            buf = io.BytesIO(base64.b64decode(lesson["bundle_b64"]))
            with zipfile.ZipFile(buf) as z:
                names = set(z.namelist())
                self.assertTrue(expected.issubset(names))
                self.assertIn("README-开始之前.txt", names)
                for name in expected:
                    content = z.read(name).decode("utf-8")
                    self.assertIn("void ", content) if name.endswith(".ino") else self.assertIn("#ifndef ", content)

    def test_generated_course_deterministic(self):
        self.assertEqual(TARGET.read_text(encoding="utf-8"), build())
        self.assertEqual(self.doc["notice"], self.source["tutorial_notice"])

    def test_real_hardware_is_not_marked_complete(self):
        self.assertTrue(all(task["status"] == "planned" for task in self.source["tasks"]))
        self.assertIn("不是", self.doc["notice"])

if __name__ == "__main__":
    unittest.main()
