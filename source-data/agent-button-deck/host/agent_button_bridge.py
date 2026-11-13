#!/usr/bin/env python3
"""Agent Button Deck: intentionally narrow macOS router for untrusted button events.

G0 needs Python 3.10+ only:
  python3 agent_button_bridge.py --config mappings.example.json --stdin

G1/G2 USB adds optional pyserial:
  python3 agent_button_bridge.py --list-ports
  python3 agent_button_bridge.py --config ~/.config/agent-button-deck/mappings.json --port /dev/cu.YOUR_PORT

Actions are DISABLED by default. Only --enable-actions turns on the
user-reviewed mappings. USB input can never supply command arguments.
No secrets, session identifiers, login or API credentials are stored on MCU.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_ACTION_FIELDS = {
    "open_app": {"type", "bundle_id"},
    "open_url": {"type", "url"},
    "shortcut": {"type", "name"},
    "agent_event": {"type", "route_id", "endpoint"},
}
MAX_EVENT_BYTES = 512


def _key_ok(key: object) -> bool:
    if not isinstance(key, str) or not re.fullmatch(r"K[1-9][0-9]?", key):
        return False
    return 1 <= int(key[1:]) <= 64


def _https_ok(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not any(ord(ch) < 32 for ch in value)
            and (parsed.port is None or 1 <= parsed.port <= 65535)
        )
    except ValueError:
        return False


def _loopback_ok(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 256:
        return False
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == "http"
            and parsed.hostname == "127.0.0.1"
            and parsed.username is None
            and parsed.password is None
            and parsed.port is not None
            and 1 <= parsed.port <= 65535
            and not parsed.query
            and not parsed.fragment
            and re.fullmatch(r"/[A-Za-z0-9/_-]{1,100}", parsed.path) is not None
        )
    except ValueError:
        return False


def validate_config(data: object) -> dict:
    """Reject unsupported action types/fields and dangerous endpoint forms."""
    if (
        not isinstance(data, dict)
        or type(data.get("schema_version")) is not int
        or data["schema_version"] != 1
        or set(data) != {"schema_version", "routes"}
    ):
        raise ValueError("Expected schema_version=1 and routes object")
    routes = data["routes"]
    if not isinstance(routes, dict) or not (1 <= len(routes) <= 64):
        raise ValueError("routes must contain 1..64 key mappings")
    for key, action in routes.items():
        if not _key_ok(key):
            raise ValueError("Invalid key; expected K1..K64")
        if not isinstance(action, dict):
            raise ValueError("Each route must be an object")
        kind = action.get("type")
        if kind not in ALLOWED_ACTION_FIELDS or set(action) != ALLOWED_ACTION_FIELDS[kind]:
            raise ValueError("Unrecognized action type or unsupported fields")
        if kind == "open_url" and not _https_ok(action["url"]):
            raise ValueError("open_url requires a safe HTTPS URL")
        if kind == "open_app" and (
            not isinstance(action["bundle_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9_-]+(?:[.][A-Za-z0-9_-]+)+", action["bundle_id"])
        ):
            raise ValueError("open_app requires a bundle identifier")
        if kind == "shortcut" and (
            not isinstance(action["name"], str)
            or not re.fullmatch(r"[\w][\w .-]{0,79}", action["name"], re.UNICODE)
        ):
            raise ValueError("shortcut requires a simple named macOS Shortcut")
        if kind == "agent_event" and (
            not _loopback_ok(action["endpoint"])
            or not isinstance(action["route_id"], str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", action["route_id"])
        ):
            raise ValueError("agent_event requires a loopback endpoint and simple route_id")
    return data


def load_config(path: str | Path) -> dict:
    return validate_config(json.loads(Path(path).expanduser().read_text(encoding="utf-8")))


def parse_event(raw: str | bytes) -> dict | None:
    """Input is a single line from potentially untrusted USB hardware."""
    if isinstance(raw, bytes):
        if len(raw) > MAX_EVENT_BYTES:
            return None
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_EVENT_BYTES:
        return None
    try:
        event = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if (
        not isinstance(event, dict)
        or set(event) != {"v", "event", "key"}
        or type(event.get("v")) is not int
        or event["v"] != 1
        or event["event"] != "press"
        or not _key_ok(event["key"])
    ):
        return None
    return event


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent localhost adapter from forwarding payload to an external URL."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def execute_action(key: str, action: dict) -> None:
    """No shell=True, no executable supplied by USB, no remote Agent endpoint."""
    kind = action["type"]
    if kind == "agent_event":
        body = json.dumps({
            "source": "agent-button-deck", "v": 1, "event": "press",
            "key": key, "route_id": action["route_id"]
        }, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            action["endpoint"], data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        # Redirects are deliberately prohibited: even a local adapter cannot
        # silently bounce this event to a remote network address.
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=3) as response:
            if not (200 <= response.status < 300):
                raise OSError("Adapter did not acknowledge event")
        return

    if platform.system() != "Darwin":
        raise OSError("Live app/URL/Shortcut actions are macOS-only; use dry-run here")
    if kind == "open_app":
        command = ["open", "-b", action["bundle_id"]]
    elif kind == "open_url":
        command = ["open", action["url"]]
    elif kind == "shortcut":
        command = ["shortcuts", "run", action["name"]]
    else:
        raise ValueError("Unknown action")
    subprocess.run(command, check=True, timeout=30)


def handle_line(raw: str | bytes, config: dict, enable_actions: bool = False) -> bool:
    event = parse_event(raw)
    if event is None:
        print("[IGNORED] invalid protocol event", file=sys.stderr)
        return False
    key = event["key"]
    action = config["routes"].get(key)
    if action is None:
        print(f"[IGNORED] {key}: no configured action")
        return False

    kind = action["type"]
    if not enable_actions:
        print(f"[DRY RUN] {key} -> {kind}")
        return True
    try:
        execute_action(key, action)
    except (OSError, ValueError, subprocess.SubprocessError, urllib.error.URLError) as exc:
        # Avoid printing private URLs or request data in exception messages.
        print(f"[FAILED] {key} -> {kind} ({type(exc).__name__})", file=sys.stderr)
        return False
    print(f"[OK] {key} -> {kind}")
    return True


def _import_serial():
    try:
        import serial
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError("For real USB mode install pyserial into your Python environment") from exc
    return serial, list_ports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stdin", action="store_true", help="read one JSON event per line, no hardware")
    group.add_argument("--port", help="serial port returned by --list-ports")
    group.add_argument("--list-ports", action="store_true", help="show detected serial ports")
    parser.add_argument("--config", help="private JSON button mapping file")
    parser.add_argument("--enable-actions", action="store_true", help="explicitly allow configured live actions")
    args = parser.parse_args(argv)

    if args.list_ports:
        try:
            _, list_ports = _import_serial()
        except RuntimeError as exc:
            parser.error(str(exc))
        for p in list_ports.comports():
            print(f"{p.device} | {p.description}")
        return 0

    if not args.config:
        parser.error("--config is required with --stdin or --port")
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as exc:
        parser.error(f"Invalid config: {type(exc).__name__}")
    if not args.enable_actions:
        print("[SAFE] dry-run only; add --enable-actions after reviewing your local mappings", file=sys.stderr)

    if args.stdin:
        for raw in sys.stdin:
            handle_line(raw, config, args.enable_actions)
        return 0

    try:
        serial, _ = _import_serial()
        with serial.Serial(args.port, baudrate=115200, timeout=1) as conn:
            print(f"[LISTENING] {args.port} @115200")
            while True:
                raw = conn.read_until(b"\n", size=MAX_EVENT_BYTES + 1)
                if raw:
                    handle_line(raw, config, args.enable_actions)
    except KeyboardInterrupt:
        print("\n[STOPPED]")
    except (RuntimeError, OSError) as exc:
        print(f"[FAILED] serial connection: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
