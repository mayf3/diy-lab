import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
SCRIPT=ROOT/"source-data/christmas-magic-tent/tree-v1/tree_wled.py"
spec=importlib.util.spec_from_file_location("tree_wled", SCRIPT)
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)

class TestWLED(unittest.TestCase):
    def test_printable_geometry_artifacts_are_locked(self):
        base = SCRIPT.parent / "generated"
        report = json.loads((base / "geometry-report.json").read_text(encoding="utf-8"))
        for name in ("tree_panel_top_slot", "tree_panel_bottom_slot", "tree_cross_base"):
            self.assertTrue((base / (name + ".stl")).is_file())
            self.assertTrue((base / (name + ".step")).is_file())
            bounds = report[name]["extents_mm"]
            self.assertLess(max(bounds), 245)
            self.assertGreater(report[name]["approx_solid_volume_cm3"], 0)
        self.assertEqual(report["parameters"]["height_mm"], 235)
        self.assertEqual(report["parameters"]["width_mm"], 192)
        self.assertEqual(report["design_notes"]["clearance_mm"], 0.5)

    def test_network_is_disabled_by_default(self):
        with patch.object(module, "read_json", side_effect=AssertionError("network")), patch.object(module, "send_json", side_effect=AssertionError("network")):
            s=module.execute("192.168.1.10","K1",dry_run=True)
            self.assertEqual(s["operation"],"warm")
            self.assertTrue(s["dry_run"])

    def test_supported_local_and_public_rejected(self):
        self.assertEqual(module.local_device_url("wled.local"),"http://wled.local")
        self.assertEqual(module.local_device_url("http://192.168.1.10:81"),"http://192.168.1.10:81")
        for s in ["https://wled.local","https://example.com","8.8.8.8","example.com","http://wled.local/other","http://name:secret@wled.local"]:
            with self.subTest(host=s), self.assertRaises(ValueError):
                module.local_device_url(s)

    def test_effect_ids_dynamic(self):
        ids=["Solid","Breathe","Twinkle","Rainbow"]
        s=json.loads(module.SCENES_PATH.read_text())
        for name,scene in s["scenes"].items():
            p=module.scene_payload(scene,ids,s["brightness_ceiling"])
            self.assertLessEqual(p["bri"],88)
            self.assertEqual(p["seg"][0]["fx"],ids.index(scene["effect"]))
        with self.assertRaises(ValueError):
            module.effect_id("NonExistent",ids)

    def test_button_events_map_to_scenes(self):
        for key,expected in [("K1","warm"),("K2","sparkle"),("K3","rainbow"),("K4","off")]:
            with self.subTest(key=key):
                self.assertEqual(module.execute("192.168.0.8",key,dry_run=True)["operation"],expected)

    def test_live_request_is_json_api_only(self):
        with patch.object(module,"read_json",return_value=["Solid","Breathe","Twinkle","Rainbow"]),patch.object(module,"send_json",return_value={"ok":True}) as sender:
            result=module.execute("192.168.1.2","sparkle",dry_run=False)
            self.assertEqual(result["command"]["seg"][0]["fx"],2)
            self.assertEqual(sender.call_args.args[0],"http://192.168.1.2/json/state")
        with patch.object(module,"send_json",return_value={"ok":True}) as sender:
            module.execute("192.168.1.2","K4",dry_run=False)
            self.assertEqual(sender.call_args.args[1],{"on":False})

if __name__=="__main__":unittest.main()
