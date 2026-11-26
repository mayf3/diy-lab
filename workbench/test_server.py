"""Risk-focused HTTP and persistence tests; no EDA installation is required."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import serve


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.repo = self.base / "lab"
        self.web = self.repo / "workbench/web"
        self.web.mkdir(parents=True)
        (self.web / "index.html").write_text("<h1>Hardware workbench</h1>", encoding="utf-8")
        (self.web / "empty").mkdir()
        (self.repo / "source-data/button-deck").mkdir(parents=True)
        (self.repo / "source-data/recorder").mkdir(parents=True)
        (self.repo / "docs/eda").mkdir(parents=True)
        (self.repo / "docs/eda/README.md").write_text("# Local design evidence\n", encoding="utf-8")
        self.catalog = {
            "projects": [
                {"id": "button-deck", "workspace": "source-data/button-deck"},
                {"id": "recorder", "workspace": "source-data/recorder"},
            ],
            "documents": [{"id": "guide", "path": "docs/eda/README.md", "name": "设计记录.md"}],
        }
        self.write_catalog()
        self.bundle = self.base / "嘉立创EDA(专业版).app"
        (self.bundle / "Contents/MacOS").mkdir(parents=True)
        with (self.bundle / "Contents/Info.plist").open("wb") as handle:
            plistlib.dump({"CFBundleExecutable": "LCEDA-Pro"}, handle)
        self.binary = self.bundle / "Contents/MacOS/LCEDA-Pro"
        self.calls = self.base / "doctor-calls.json"
        self.write_doctor({"ok": True, "value": {"connected": True, "versionMatch": True}})
        self.evidence = {
            "state": "installed_pending_official_activation",
            "application": str(self.bundle), "cli_help": "passed", "doctor_connected": True,
            "editor_round_trip": "blocked_by_first_activation", "skills": [],
        }
        self.write_evidence()
        self.state = self.base / "private/workbench-state.json"
        self.app = serve.Workbench(self.repo, self.state, doctor_timeout=0.5)
        self.server = serve.WorkbenchServer(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = f"127.0.0.1:{self.server.server_port}"
        self.origin = "http://" + self.host

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def write_catalog(self):
        (self.web / "workbench.json").write_text(json.dumps(self.catalog), encoding="utf-8")

    def write_evidence(self):
        (self.repo / "docs/eda/environment-status.json").write_text(json.dumps(self.evidence), encoding="utf-8")

    def write_doctor(self, output=None, *, raw=None, delay=0):
        source = (
            f"#!{sys.executable}\n"
            "import json, sys, time\n"
            f"open({str(self.calls)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
            f"time.sleep({delay!r})\n"
            f"print({(raw if raw is not None else json.dumps(output))!r})\n"
        )
        self.binary.write_text(source, encoding="utf-8")
        self.binary.chmod(0o700)

    def request(self, method, path, body=None, headers=None, *, marked=True):
        supplied = {"Host": self.host}
        if method == "POST" and marked:
            supplied.update({"Origin": self.origin, "Content-Type": "application/json", "X-Workbench-Request": "1"})
        supplied.update(headers or {})
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=True).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.request(method, path, body=body, headers=supplied)
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    def post(self, path, body, **kwargs):
        status, _, data = self.request("POST", path, body, **kwargs)
        return status, json.loads(data)

    def test_loopback_only(self):
        for host in ("0.0.0.0", "::", "192.168.1.10", "example.com", "127.0.0.1.evil"):
            with self.subTest(host=host), self.assertRaises(argparse.ArgumentTypeError):
                serve.loopback_host(host)
        with self.assertRaises(argparse.ArgumentTypeError):
            serve.WorkbenchServer(("0.0.0.0", 0), self.app)
        self.assertEqual(serve.loopback_host("localhost"), "127.0.0.1")
        self.assertEqual(serve.loopback_host("::1"), "::1")

    def test_static_files_without_directory_listing(self):
        status, headers, data = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Hardware workbench", data)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertEqual(self.request("GET", "/empty/")[0], 404)
        self.assertEqual(self.request("GET", "/workbench.json")[0], 200)

    def test_path_traversal_and_static_symlink_escape(self):
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt", "/%2e%2e%5csecret.txt"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path)[0], 403)
        (self.web / "leak.md").symlink_to(self.repo / "docs/eda/README.md")
        self.assertEqual(self.request("GET", "/leak.md")[0], 403)

    def test_documents_are_allowlisted_and_cannot_escape(self):
        status, headers, data = self.request("GET", "/documents/guide")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("sandbox", headers["Content-Security-Policy"])
        self.assertIn(b"Local design evidence", data)
        self.assertEqual(self.request("GET", "/documents/docs/eda/README.md")[0], 404)
        outside = self.base / "private.txt"
        outside.write_text("private marker", encoding="utf-8")
        (self.repo / "docs/escape.txt").symlink_to(outside)
        self.catalog["documents"].append({"id": "escape", "path": "docs/escape.txt"})
        self.write_catalog()
        status, _, data = self.request("GET", "/documents/escape")
        self.assertEqual(status, 403)
        self.assertNotIn(b"private marker", data)

    def test_invalid_host_and_origin_are_rejected_before_probe(self):
        for headers in ({"Host": "evil.example"}, {"Host": self.host + ".evil"}, {"Origin": "https://evil.example"}, {"Origin": "http://127.0.0.1:1"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("GET", "/api/status", headers=headers)[0], 403)
        self.assertFalse(self.calls.exists())

    def test_duplicate_host_is_rejected(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        connection.putrequest("GET", "/", skip_host=True)
        connection.putheader("Host", self.host)
        connection.putheader("Host", "evil.example")
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        connection.close()

    def test_post_requires_origin_marker_and_json(self):
        body = {"project_id": "button-deck", "text": "hello"}
        self.assertEqual(self.post("/api/notes", body, marked=False)[0], 403)
        self.assertEqual(self.post("/api/notes", body, headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.post("/api/notes", body, headers={"X-Workbench-Request": "0"})[0], 403)
        self.assertEqual(self.post("/api/notes", body, headers={"Content-Type": "text/plain"})[0], 415)
        self.assertFalse(self.state.exists())

    def test_body_and_note_limits_and_invalid_json(self):
        status, _ = self.post("/api/notes", b"", headers={"Content-Length": str(serve.MAX_BODY_BYTES + 1)})
        self.assertEqual(status, 413)
        self.assertEqual(self.post("/api/notes", {"project_id": "button-deck", "text": "a" * 8001})[0], 400)
        self.assertEqual(self.post("/api/notes", {"project_id": "unknown", "text": "x"})[0], 404)
        self.assertEqual(self.post("/api/notes", {"project_id": "button-deck", "text": "\ud800"})[0], 400)
        self.assertEqual(self.post("/api/notes", b'{"project_id":"button-deck","text":"one","text":"two"}')[0], 400)
        self.assertEqual(self.post("/api/notes", b'[]')[0], 400)

    def test_notes_persist_and_get_reads_disk(self):
        note = "优先做成品\n无需手焊 🔌"
        status, body = self.post("/api/notes", {"project_id": "button-deck", "text": note})
        self.assertEqual(status, 200)
        self.assertEqual(body["notes"]["button-deck"]["text"], note)
        saved = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(saved["notes"]["button-deck"]["text"], note)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        status, _, raw = self.request("GET", "/api/notes")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), body)
        self.assertIn("updated_at", body["notes"]["button-deck"])

    def test_concurrent_notes_do_not_lose_other_projects(self):
        def save(project):
            return self.post("/api/notes", {"project_id": project, "text": project})[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(save, ("button-deck", "recorder"))), [200, 200])
        self.assertEqual(set(json.loads(self.state.read_text())["notes"]), {"button-deck", "recorder"})

    def test_failed_atomic_replace_keeps_previous_note(self):
        self.assertEqual(self.post("/api/notes", {"project_id": "button-deck", "text": "old"})[0], 200)
        with patch.object(serve.os, "replace", side_effect=OSError("disk failure")):
            status, result = self.post("/api/notes", {"project_id": "button-deck", "text": "new"})
        self.assertEqual(status, 500)
        self.assertEqual(result["error"]["code"], "notes_save_failed")
        self.assertEqual(json.loads(self.state.read_text())["notes"]["button-deck"]["text"], "old")
        self.assertEqual(list(self.state.parent.glob(".workbench-state-*.tmp")), [])

    def test_corrupt_or_symlinked_state_is_not_reset_or_read(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("broken notes", encoding="utf-8")
        self.assertEqual(self.request("GET", "/api/notes")[0], 500)
        self.assertEqual(self.post("/api/notes", {"project_id": "button-deck", "text": "new"})[0], 500)
        self.assertEqual(self.state.read_text(), "broken notes")
        self.state.unlink()
        private = self.base / "activation.txt"
        private.write_text("private-activation-marker", encoding="utf-8")
        self.state.symlink_to(private)
        status, _, data = self.request("GET", "/api/notes")
        self.assertEqual(status, 500)
        self.assertNotIn(b"private-activation-marker", data)

    def test_actions_use_only_catalog_and_exact_argv(self):
        with patch.object(serve.sys, "platform", "darwin"), patch.object(serve.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            self.assertEqual(self.post("/api/actions", {"action": "shell", "command": "touch bad"})[0], 400)
            self.assertEqual(self.post("/api/actions", {"action": "open_project", "project_id": "button-deck", "path": "/tmp"})[0], 400)
            self.assertEqual(self.post("/api/actions", {"action": "open_project", "project_id": "unknown"})[0], 404)
            self.assertEqual(run.call_count, 0)
            self.assertEqual(self.post("/api/actions", {"action": "open_project", "project_id": "button-deck"})[0], 200)
            self.assertEqual(run.call_args.args[0], ["/usr/bin/open", str((self.repo / "source-data/button-deck").resolve())])
            self.assertNotIn("shell", run.call_args.kwargs)
            self.assertEqual(self.post("/api/actions", {"action": "open_eda"})[0], 200)
            self.assertEqual(run.call_args.args[0], ["/usr/bin/open", "-a", str(self.bundle)])
        self.catalog["projects"][0]["workspace"] = "../../"
        self.write_catalog()
        self.assertEqual(self.post("/api/actions", {"action": "open_project", "project_id": "button-deck"})[0], 403)

    def test_actions_report_linux_and_open_failure(self):
        with patch.object(serve.sys, "platform", "linux"):
            self.assertEqual(self.post("/api/actions", {"action": "open_eda"})[0], 501)
            self.assertEqual(self.post("/api/actions", {"action": "open_project", "project_id": "button-deck"})[0], 501)
        with patch.object(serve.sys, "platform", "darwin"), patch.object(serve.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "failed")):
            self.assertEqual(self.post("/api/actions", {"action": "open_eda"})[0], 500)

    @unittest.skipIf(os.name == "nt", "fixture CLI uses a POSIX executable")
    def test_live_doctor_does_not_claim_activation_or_read_license(self):
        (self.bundle / "lceda-pro-activation.txt").write_text("private-activation-marker", encoding="utf-8")
        status, _, raw = self.request("GET", "/api/status")
        body = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertTrue(body["app_installed"])
        self.assertTrue(body["cli_available"])
        self.assertEqual(body["bridge"]["state"], "connected")
        self.assertEqual(body["activation"]["state"], "pending")
        self.assertEqual(body["editor_round_trip"], "pending")
        self.assertEqual(json.loads(self.calls.read_text()), ["doctor"])
        self.assertNotIn(str(self.base).encode(), raw)
        self.assertNotIn(b"private-activation-marker", raw)

    @unittest.skipIf(os.name == "nt", "fixture CLI uses a POSIX executable")
    def test_live_probe_overrides_stale_receipt_and_checks_files(self):
        self.write_doctor({"ok": True, "value": {"connected": False}})
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertEqual(body["bridge"]["state"], "disconnected")
        self.binary.unlink()
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertTrue(body["app_installed"])
        self.assertFalse(body["cli_available"])
        self.assertEqual(body["bridge"]["state"], "unavailable")

    @unittest.skipIf(os.name == "nt", "fixture CLI uses a POSIX executable")
    def test_round_trip_needs_explicit_evidence_and_connected_probe(self):
        self.evidence.update({"state": "installed", "editor_round_trip": "passed"})
        self.write_evidence()
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertEqual(body["activation"]["state"], "unverified")
        # 新合同：历史 passed 记录缺少激活验收与时间戳证据时，实时状态降级为 pending
        self.assertEqual(body["editor_round_trip"], "pending")
        self.assertFalse(body["ready"])
        self.write_doctor({"ok": True, "value": {"connected": False}})
        self.assertEqual(json.loads(self.request("GET", "/api/status")[2])["editor_round_trip"], "pending")

    @unittest.skipIf(os.name == "nt", "fixture CLI uses a POSIX executable")
    def test_verified_activation_and_round_trip_show_ready(self):
        self.evidence.update({
            "state": "activated_editor_round_trip_passed",
            "activation_accepted_at": "2026-11-26T12:16:00+08:00",
            "editor_round_trip": "passed",
            "editor_round_trip_passed_at": "2026-11-26T14:08:00+08:00",
        })
        self.write_evidence()
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertEqual(body["activation"]["state"], "verified")
        self.assertEqual(body["activation"]["accepted_at"], "2026-11-26T12:16:00+08:00")
        self.assertEqual(body["editor_round_trip"], "passed")
        self.assertEqual(body["editor_round_trip_evidence_at"], "2026-11-26T14:08:00+08:00")
        self.assertTrue(body["ready"])
        self.assertEqual(body["ready_blockers"], [])
        self.write_doctor({"ok": True, "value": {"connected": False}})
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertEqual(body["editor_round_trip"], "pending")
        self.assertFalse(body["ready"])
        self.assertIn("编辑器桥接已连接", body["ready_blockers"])
        self.write_doctor({"ok": True, "value": {"connected": True, "versionMatch": False}})
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertEqual(body["bridge"]["state"], "error")
        self.assertEqual(body["editor_round_trip"], "pending")
        self.assertFalse(body["ready"])

    @unittest.skipIf(os.name == "nt", "fixture CLI uses a POSIX executable")
    def test_activation_ui_evidence_without_round_trip_stays_unverified(self):
        self.evidence.update({
            "state": "activated",
            "activation_accepted_at": "2026-11-26T12:16:00+08:00",
        })
        self.write_evidence()
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertEqual(body["activation"]["state"], "unverified")
        self.assertIn("工程读写", body["activation"]["detail"])
        self.assertEqual(body["editor_round_trip"], "pending")
        self.assertFalse(body["ready"])
        self.assertIn("官方激活已验收", body["ready_blockers"])

    @unittest.skipIf(os.name == "nt", "fixture CLI uses a POSIX executable")
    def test_round_trip_claim_without_timestamp_is_not_accepted(self):
        self.evidence.update({
            "state": "activated_editor_round_trip_passed",
            "activation_accepted_at": "2026-11-26T12:16:00+08:00",
            "editor_round_trip": "passed",
        })
        self.write_evidence()
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertEqual(body["editor_round_trip"], "pending")
        self.assertEqual(body["activation"]["state"], "unverified")
        self.assertFalse(body["ready"])

    @unittest.skipIf(os.name == "nt", "fixture CLI uses a POSIX executable")
    def test_probe_failures_are_bounded_and_structured(self):
        self.write_doctor(raw="not json")
        self.assertEqual(json.loads(self.request("GET", "/api/status")[2])["bridge"]["state"], "error")
        self.write_doctor({"ok": False, "error": {"code": "EXECUTION_ERROR", "message": "/Users/private/path"}})
        raw = self.request("GET", "/api/status")[2]
        self.assertIn(b"EXECUTION_ERROR", raw)
        self.assertNotIn(b"/Users/private", raw)
        self.app.doctor_timeout = 0.6
        self.write_doctor({"ok": True, "value": {"connected": True}}, delay=3)
        started = time.monotonic()
        body = json.loads(self.request("GET", "/api/status")[2])
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertEqual(body["bridge"]["state"], "timeout")
        self.assertEqual(body["editor_round_trip"], "pending")


if __name__ == "__main__":
    unittest.main()
