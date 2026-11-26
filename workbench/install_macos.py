#!/usr/bin/env python3
"""Install this checkout's loopback-only workbench as a user login service."""
from __future__ import annotations

import json
import os
import platform
import plistlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LABEL = 'com.mayf3.hardware-workbench'
PORT = 8135
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if platform.system() != 'Darwin':
        raise SystemExit('This installer is for the user’s Mac only.')
    for relative in ['workbench/serve.py', 'workbench/web/index.html', 'workbench/web/workbench.json']:
        if not (ROOT / relative).is_file():
            raise SystemExit(f'Missing workbench input: {relative}')
    local_home = Path.home()
    state_file = local_home / 'Documents/DIY/eda-toolchain/workbench-state.json'
    log_dir = local_home / 'Library/Logs/MakerLabWorkbench'
    agent_file = local_home / 'Library/LaunchAgents' / f'{LABEL}.plist'
    arguments = [sys.executable, str(ROOT / 'workbench/serve.py'), '--port', str(PORT),
                 '--state-file', str(state_file)]
    if agent_file.exists():
        existing = plistlib.loads(agent_file.read_bytes())
        if existing.get('Label') != LABEL or existing.get('ProgramArguments') != arguments:
            raise SystemExit('An existing workbench service uses different arguments; left unchanged.')
    domain = f'gui/{os.getuid()}'
    running = subprocess.run(['launchctl', 'print', f'{domain}/{LABEL}'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if not running:
        import socket
        with socket.socket() as probe:
            try:
                probe.bind(('127.0.0.1', PORT))
            except OSError:
                raise SystemExit(f'Port {PORT} is already in use; no existing service was changed.')
    log_dir.mkdir(parents=True, exist_ok=True)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    agent_file.parent.mkdir(parents=True, exist_ok=True)
    configuration = {
        'Label': LABEL, 'ProgramArguments': arguments,
        'WorkingDirectory': str(ROOT), 'RunAtLoad': True,
        'KeepAlive': {'SuccessfulExit': False}, 'ThrottleInterval': 10,
        'StandardOutPath': str(log_dir / 'server.log'),
        'StandardErrorPath': str(log_dir / 'server-error.log'),
    }
    agent_file.write_bytes(plistlib.dumps(configuration))
    if not running:
        subprocess.run(['launchctl', 'bootstrap', domain, str(agent_file)], check=True)
    desktop_link = local_home / 'Desktop/硬件工作台.webloc'
    url = f'http://127.0.0.1:{PORT}/'
    if desktop_link.exists():
        try:
            same_link = plistlib.loads(desktop_link.read_bytes()).get('URL') == url
        except Exception:
            same_link = False
        if not same_link:
            desktop_link = local_home / 'Desktop/Maker-Lab-硬件工作台.webloc'
            if desktop_link.exists():
                raise SystemExit('Desktop shortcut name already exists; left unchanged.')
    desktop_link.write_bytes(plistlib.dumps({'URL': url}))
    status = None
    last_error = None
    # This health probe targets this machine's loopback service only.
    # System proxy variables must not send 127.0.0.1 through an external proxy.
    local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        try:
            with local_http.open(url + 'api/status', timeout=10) as response:
                status = json.load(response)
            break
        except (OSError, ValueError, urllib.error.URLError) as error:
            last_error = type(error).__name__
            time.sleep(0.5)
    if status is None:
        raise SystemExit(f'Service configured, but status verification failed: {last_error}; see {log_dir}')
    subprocess.run(['open', url], check=True)
    print(json.dumps({'url': url, 'shortcut': str(desktop_link), 'service': str(agent_file),
                      'status': status}, ensure_ascii=False))


if __name__ == '__main__':
    main()
