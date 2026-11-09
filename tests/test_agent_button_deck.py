"""Offline tests for Agent Button Deck: no USB device, requests or actions required."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
BRIDGE = ROOT / "source-data/agent-button-deck/host/agent_button_bridge.py"
EXAMPLE = ROOT / "source-data/agent-button-deck/host/mappings.example.json"
spec = importlib.util.spec_from_file_location("agent_button_bridge", BRIDGE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class AgentButtonDeckTests(unittest.TestCase):
    def setUp(self):
        self.config = module.load_config(EXAMPLE)

    def test_example_has_four_distinct_actions(self):
        self.assertEqual(set(self.config["routes"]), {"K1", "K2", "K3", "K4"})
        self.assertEqual(
            [self.config["routes"][f"K{i}"]["type"] for i in range(1, 5)],
            ["open_app", "open_url", "shortcut", "agent_event"]
        )

    def test_valid_events_and_boundaries(self):
        self.assertEqual(
            module.parse_event('{"v":1,"event":"press","key":"K1"}')["key"], "K1"
        )
        self.assertEqual(
            module.parse_event(b'{"v":1,"event":"press","key":"K64"}\n')["key"], "K64"
        )
        for key in ("K0", "K00", "K01", "K65", "K999", "HELLO", "K-1"):
            self.assertIsNone(module.parse_event(json.dumps({
                "v": 1, "event": "press", "key": key
            })), key)
        for raw in ('{}', '{"v":1,"event":"release","key":"K1"}',
                    '{"v":true,"event":"press","key":"K1"}',
                    '{"v":1,"event":"press","key":"K1","command":"rm -rf ~"}',
                    'bad json', b'\xff', "x" * 1024):
            self.assertIsNone(module.parse_event(raw), raw)

    def test_default_dry_run_does_not_execute(self):
        with patch.object(module, "execute_action") as live:
            for i in range(1, 5):
                self.assertTrue(module.handle_line(
                    json.dumps({"v": 1, "event": "press", "key": f"K{i}"}),
                    self.config,
                ))
            live.assert_not_called()

    def test_unknown_event_is_dropped(self):
        with patch.object(module, "execute_action") as live:
            self.assertFalse(module.handle_line(
                '{"v":1,"event":"press","key":"K5"}', self.config,
                enable_actions=True,
            ))
            live.assert_not_called()

    def test_forbidden_action_or_url_cannot_be_configured(self):
        cases = [
            ("K1", {"type": "shell", "command": "date"}),
            ("K2", {"type": "open_url", "url": "file:///etc/passwd"}),
            ("K2", {"type": "open_url", "url": "https://user:pw@example.com"}),
            ("K4", {"type": "agent_event", "route_id": "research",
                    "endpoint": "https://external.example/button"}),
            ("K4", {"type": "agent_event", "route_id": "research",
                    "endpoint": "http://localhost:8765/button"}),
            ("K4", {"type": "agent_event", "route_id": "research",
                    "endpoint": "http://127.0.0.1:8765/button?redirect=https://example.com"}),
        ]
        for key, action in cases:
            changed = copy.deepcopy(self.config)
            changed["routes"][key] = action
            with self.assertRaises(ValueError):
                module.validate_config(changed)

    def test_explicit_enable_controls_execution(self):
        with patch.object(module, "execute_action") as live:
            result = module.handle_line(
                '{"v":1,"event":"press","key":"K1"}', self.config, enable_actions=True
            )
            self.assertTrue(result)
            live.assert_called_once_with("K1", self.config["routes"]["K1"])

    def test_agent_event_payload_contains_only_route_and_key(self):
        class FakeResponse:
            status = 204
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        class FakeOpener:
            def open(self, request, timeout):
                self.request = request
                self.timeout = timeout
                return FakeResponse()

        opener = FakeOpener()
        with patch.object(module.urllib.request, "build_opener", return_value=opener):
            module.execute_action("K4", self.config["routes"]["K4"])
        data = json.loads(opener.request.data)
        self.assertEqual(data, {"source": "agent-button-deck", "v": 1,
                                "event": "press", "key": "K4", "route_id": "research"})
        self.assertEqual(opener.timeout, 3)

    def test_schema_and_loopback_restrictions(self):
        self.assertFalse(module._loopback_ok("http://127.0.0.1:8765/../secret"))
        self.assertFalse(module._loopback_ok("http://127.0.0.1.evil.com:8765/button"))
        self.assertTrue(module._loopback_ok("http://127.0.0.1:8765/button"))
        wrong = copy.deepcopy(self.config)
        wrong["schema_version"] = 2
        with self.assertRaises(ValueError):
            module.validate_config(wrong)


if __name__ == "__main__":
    unittest.main()
