#!/usr/bin/env python3
"""Guard the published G0 video sample without requiring Pillow or FFmpeg in CI."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("video_from_storyboard", ROOT/"scripts/video_from_storyboard.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SRC = ROOT/"source-data/christmas-magic-tent/video/g0-storyboard.json"


class TestVideoStoryboard(unittest.TestCase):
    def setUp(self):
        self.data = mod.load_and_check(SRC)

    def test_evidence_is_digital_only(self):
        self.assertEqual(self.data["kind"], "digital-simulation")
        self.assertIn("不是实物", self.data["display_notice"])
        self.assertEqual(len(self.data["scenes"]), 8)

    def test_every_visual_exists_with_no_external_asset(self):
        for scene in self.data["scenes"]:
            self.assertTrue((ROOT/scene["visual"]).is_file())
            self.assertTrue((ROOT/scene["evidence_ref"]).is_file())
            self.assertTrue(scene["action_ref"])
            self.assertTrue(scene["evidence"])

    def test_rejects_traversal(self):
        bad = copy.deepcopy(self.data)
        bad["scenes"][0]["visual"] = "../../private/secrets.png"
        tmp = SRC.parent/"_temporary_invalid_video.json"
        try:
            tmp.write_text(json.dumps(bad),encoding="utf-8")
            with self.assertRaises(AssertionError):
                mod.load_and_check(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    def test_rejects_unmarked_simulation(self):
        bad = copy.deepcopy(self.data)
        bad["display_notice"] = "就是一段真实的装配视频"
        tmp = SRC.parent/"_temporary_invalid_video.json"
        try:
            tmp.write_text(json.dumps(bad,ensure_ascii=False),encoding="utf-8")
            with self.assertRaises(AssertionError):
                mod.load_and_check(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    def test_caption_timing_reproducible(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"caption.srt"
            spans = mod.write_srt(self.data,path)
            self.assertEqual(len(spans),8)
            self.assertEqual(spans[0]["start_s"],0)
            self.assertGreater(spans[-1]["end_s"],50)
            self.assertIn("数字模拟",path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()