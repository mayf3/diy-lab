#!/usr/bin/env python3
"""Software-first 5V Christmas tree controller using WLED's official JSON API.

No custom MCU firmware, soldering, accounts or cloud service. WLED's own web UI
continues autonomous animations after the Mac disconnects. No physical device
has been tested by this project. Only operates on explicitly supplied LAN hosts.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENES_PATH = HERE / "scenes.json"


def local_device_url(value: str) -> str:
    """Reject public hosts, arbitrary URLs, credentials and path injection."""
    value = value.strip()
    if not value:
        raise ValueError("Provide --host <private-IP-or-wled.local> or TREE_WLED_HOST")
    parsed = urllib.parse.urlsplit(value if "://" in value else "http://" + value)
    if parsed.scheme != "http" or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("WLED must be an HTTP LAN host with no path, credentials or query")
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid WLED host")
    if host.endswith(".local"):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*\.local", host):
            raise ValueError("Invalid local hostname")
    else:
        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError("Only private LAN IPs or .local hostnames are permitted") from exc
        if not address.is_private and not address.is_loopback:
            raise ValueError("Public IPs are not permitted")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid port")
    netloc = f"[{host}]" if ":" in host else host
    if parsed.port:
        netloc += f":{parsed.port}"
    return f"http://{netloc}"


def read_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=4) as response:
        return json.load(response)


def send_json(url: str, data: dict) -> object:
    payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=4) as response:
        return json.load(response)


def effect_id(name: str, effects: list) -> int:
    # Effect IDs vary by WLED release/build: never hardcode animation IDs.
    for i, found in enumerate(effects):
        if isinstance(found, str) and found.casefold() == name.casefold():
            return i
    raise ValueError(f"Effect '{name}' is not in this controller's firmware; options: {effects[:30]}")


def scene_payload(scene: dict, effects: list, brightness_ceiling: int) -> dict:
    bri = scene["brightness"]
    if not isinstance(bri, int) or not 0 <= bri <= brightness_ceiling <= 96:
        raise ValueError("Scene brightness exceeds the project's conservative ceiling")
    col = scene["color"]
    if not isinstance(col, list) or len(col) != 3 or any(not isinstance(x,int) or not 0 <= x <= 255 for x in col):
        raise ValueError("Expected one RGB triplet")
    return {
        "on": True, "bri": bri, "transition": 10,
        "seg": [{"id":0, "fx":effect_id(scene["effect"], effects),
                 "col":[col], "sx":int(scene["speed"]), "ix":int(scene["intensity"])}],
    }


def execute(host: str, operation: str, scene_file: Path = SCENES_PATH, dry_run: bool = False) -> dict:
    conf = json.loads(scene_file.read_text(encoding="utf-8"))
    if operation.startswith("K") and operation in conf["button_deck_mapping"]:
        operation = conf["button_deck_mapping"][operation]
    if operation != "off" and operation != "status" and operation not in conf["scenes"]:
        raise ValueError(f"Unknown scene/event {operation}")
    base = local_device_url(host)
    if dry_run:
        # Explicitly no network/physical action in dry-run.
        return {"dry_run":True,"host":base,"operation":operation,
                "scene":conf["scenes"].get(operation),"note":"No network request was sent"}
    if operation == "status":
        state = read_json(base + "/json/si")
        return {"state":state}
    if operation == "off":
        return {"command":{"on":False},"result":send_json(base + "/json/state", {"on":False})}
    effects = read_json(base + "/json/eff")
    if not isinstance(effects, list):
        raise ValueError("Expected WLED /json/eff to return a list")
    body = scene_payload(conf["scenes"][operation], effects, conf["brightness_ceiling"])
    return {"command":body, "result":send_json(base + "/json/state", body)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Control a LAN WLED Christmas tree; default dry-run for safety.")
    ap.add_argument("--host", default=os.getenv("TREE_WLED_HOST", ""), help="e.g. 192.168.1.88 or wled.local")
    ap.add_argument("--live", action="store_true", help="Actually send commands to the WLED device; omit for dry-run")
    ap.add_argument("operation", choices=["status","off","warm","breathe","sparkle","rainbow","night","K1","K2","K3","K4"])
    args = ap.parse_args()
    try:
        print(json.dumps(execute(args.host, args.operation, dry_run=not args.live), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, TimeoutError) as exc:
        print(f"WLED error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
