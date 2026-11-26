#!/usr/bin/env python3
"""Loopback-only Maker Lab workbench. Python standard library; no background agent."""

from __future__ import annotations

import argparse
import ipaddress
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import socket
import subprocess
import sys
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit


MAX_BODY_BYTES = 65536
MAX_NOTE_CHARS = 8000
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
DEFAULT_SKILLS = ("lceda-pro-automation", "pcb-product-delivery")


class WorkbenchError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_json(path: Path, maximum: int = 1048576):
    with path.open("rb") as handle:
        raw = handle.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("JSON file exceeds size limit")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)


def inside(root: Path, relative: str) -> Path:
    """Reject traversal and symlink escapes before any file read or open action."""
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise WorkbenchError(400, "invalid_path", "路径无效。")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts:
        raise WorkbenchError(403, "path_forbidden", "不能访问工作台范围之外的路径。")
    try:
        resolved = (root / path).resolve()
        resolved.relative_to(root.resolve())
    except (ValueError, OSError, RuntimeError):
        raise WorkbenchError(403, "path_forbidden", "不能访问工作台范围之外的路径。") from None
    return resolved


class Workbench:
    def __init__(self, repo_root: Path, state_file: Path, *, doctor_timeout: float = 5.0):
        self.repo_root = repo_root.resolve()
        self.web_root = self.repo_root / "workbench" / "web"
        self.state_file = state_file.expanduser().absolute()
        self.doctor_timeout = doctor_timeout
        self.state_lock = threading.RLock()
        self.probe_lock = threading.Lock()

    def catalog(self):
        try:
            data = read_json(self.web_root / "workbench.json")
            if not isinstance(data, dict):
                raise ValueError("catalog must be an object")
            for group in ("projects", "documents"):
                entries = data.get(group, [])
                if not isinstance(entries, list):
                    raise ValueError("catalog group must be a list")
                ids = set()
                for item in entries:
                    if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                        raise ValueError("catalog item needs an id")
                    if not ID_PATTERN.fullmatch(item["id"]) or item["id"] in ids:
                        raise ValueError("invalid or duplicate id")
                    ids.add(item["id"])
                    if group == "documents" and not isinstance(item.get("path"), str):
                        raise ValueError("document needs a path")
            return data
        except (OSError, ValueError, UnicodeError):
            raise WorkbenchError(500, "catalog_unavailable", "无法读取工作台项目数据，请检查 workbench.json。") from None

    def project(self, project_id):
        if not isinstance(project_id, str):
            raise WorkbenchError(400, "invalid_project", "请选择有效的项目。")
        item = next((p for p in self.catalog().get("projects", []) if p["id"] == project_id), None)
        if item is None:
            raise WorkbenchError(404, "unknown_project", "项目不在当前工作台清单中。")
        return item

    def environment(self):
        try:
            data = read_json(self.repo_root / "docs" / "eda" / "environment-status.json", 65536)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError, UnicodeError):
            return {}

    def application(self, evidence):
        raw = evidence.get("application")
        if not isinstance(raw, str):
            return None, None
        app = Path(raw).expanduser()
        if not app.is_absolute() or app.suffix != ".app" or not app.is_dir():
            return None, None
        info_file = app / "Contents" / "Info.plist"
        if not info_file.is_file():
            return None, None
        try:
            with info_file.open("rb") as handle:
                name = plistlib.load(handle).get("CFBundleExecutable")
            if not isinstance(name, str) or Path(name).name != name or name in (".", ".."):
                return app, None
            binary = (app / "Contents" / "MacOS" / name).resolve()
            binary.relative_to(app.resolve())
            if binary.is_file() and os.access(binary, os.X_OK):
                return app, binary
        except (OSError, ValueError, plistlib.InvalidFileException):
            pass
        return app, None

    @staticmethod
    def installed_skill(skill_id):
        home = Path.home()
        roots = (home / ".codex/skills", home / ".agents/skills", home / ".claude/skills")
        candidates = []
        for root in roots:
            candidates.append(root / skill_id / "SKILL.md")
            for directory in (root, root / "remote-skills"):
                if directory.is_dir():
                    candidates.extend(directory.glob("skill-*/SKILL.md"))
        expected = re.compile(r"(?m)^name:\s*['\"]?" + re.escape(skill_id) + r"['\"]?\s*$")
        for path in candidates:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    prefix = handle.read(8192)
                if prefix.startswith("---") and expected.search(prefix.split("---", 2)[1]):
                    return True
            except (OSError, UnicodeError, IndexError):
                continue
        return False

    def status(self):
        with self.probe_lock:
            evidence = self.environment()
            app, binary = self.application(evidence)
            cli_available = binary is not None and evidence.get("cli_help") == "passed"
            bridge = {"state": "unavailable", "detail": "尚未在当前电脑找到已核验的 EDA 命令行。"}
            if cli_available:
                try:
                    result = subprocess.run(
                        [str(binary), "doctor"], capture_output=True, text=True,
                        timeout=self.doctor_timeout, check=False,
                    )
                    response = json.loads(result.stdout, object_pairs_hook=unique_object)
                    if not isinstance(response, dict) or result.returncode != 0 or response.get("ok") is not True:
                        error = response.get("error", {}) if isinstance(response, dict) else {}
                        code = error.get("code", "") if isinstance(error, dict) else ""
                        code = code if isinstance(code, str) and re.fullmatch(r"[A-Z0-9_:-]{1,64}", code) else "PROBE_FAILED"
                        bridge = {"state": "error", "detail": f"doctor 返回错误（{code}）；连接状态未确认。"}
                    else:
                        value = response.get("value")
                        if not isinstance(value, dict) or not isinstance(value.get("connected"), bool):
                            bridge = {"state": "error", "detail": "doctor 响应缺少明确的连接状态。"}
                        elif value.get("versionMatch") is False:
                            bridge = {"state": "error", "detail": "命令行与运行中的桥接版本不一致。"}
                        elif value["connected"]:
                            bridge = {"state": "connected", "detail": "本机桥接已连接；这不代表已激活或编辑器任务已通过。"}
                        else:
                            bridge = {"state": "disconnected", "detail": "doctor 已运行，当前未连接到编辑器桥接。"}
                except subprocess.TimeoutExpired:
                    bridge = {"state": "timeout", "detail": f"doctor 在 {self.doctor_timeout:g} 秒内没有完成；未创建编辑器会话。"}
                except (ValueError, UnicodeError):
                    bridge = {"state": "error", "detail": "doctor 没有返回可验证的 JSON 结果。"}
                except OSError:
                    cli_available = False
                    bridge = {"state": "error", "detail": "当前电脑无法执行已记录的 EDA 命令行。"}
            recorded_state = str(evidence.get("state", ""))
            pending = ("activation" in recorded_state and ("pending" in recorded_state or "blocked" in recorded_state)) or evidence.get("editor_round_trip") == "blocked_by_first_activation"
            activation = {
                "state": "pending" if pending else "unverified",
                "detail": "安装记录显示仍待本人完成官方激活；本次只检查桥接连接。" if pending else "本接口不读取激活文件，也不依据桥接连接推断激活结果。",
            }
            skill_ids = evidence.get("skills", list(DEFAULT_SKILLS))
            if not isinstance(skill_ids, list):
                skill_ids = list(DEFAULT_SKILLS)
            skill_ids = [s for s in skill_ids if isinstance(s, str) and ID_PATTERN.fullmatch(s)]
            return {
                "mode": "local", "checked_at": utc_now(), "app_installed": app is not None,
                "cli_available": cli_available,
                "skills": [{"id": s, "installed": self.installed_skill(s)} for s in skill_ids],
                "bridge": bridge, "activation": activation,
                "editor_round_trip": "passed" if evidence.get("editor_round_trip") == "passed" and not pending and bridge["state"] == "connected" else "pending",
            }

    def _state(self):
        if self.state_file.is_symlink():
            raise WorkbenchError(500, "notes_unavailable", "备注文件是符号链接，未读取或覆盖。")
        if not self.state_file.exists():
            return {"version": 1, "notes": {}}
        try:
            state = read_json(self.state_file, 4194304)
            if not isinstance(state, dict) or not isinstance(state.get("notes"), dict):
                raise ValueError("invalid notes state")
            for key, item in state["notes"].items():
                if not isinstance(key, str) or not isinstance(item, dict):
                    raise ValueError("invalid note")
                if not isinstance(item.get("text"), str) or len(item["text"]) > MAX_NOTE_CHARS or not isinstance(item.get("updated_at"), str):
                    raise ValueError("invalid note contents")
            return state
        except (OSError, ValueError, UnicodeError):
            raise WorkbenchError(500, "notes_unavailable", "备注文件无法读取或格式异常；原文件已保留。") from None

    def notes(self):
        with self.state_lock:
            allowed = {item["id"] for item in self.catalog().get("projects", [])}
            return {"notes": {key: value for key, value in self._state()["notes"].items() if key in allowed}}

    def save_note(self, body):
        if set(body) != {"project_id", "text"}:
            raise WorkbenchError(400, "invalid_note", "备注请求只接受 project_id 和 text。")
        self.project(body["project_id"])
        text = body["text"]
        if not isinstance(text, str) or len(text) > MAX_NOTE_CHARS:
            raise WorkbenchError(400, "invalid_note", "备注须为文字，最多 8000 个字符。")
        try:
            text.encode("utf-8")
        except UnicodeError:
            raise WorkbenchError(400, "invalid_note", "备注包含无效的文字编码。") from None
        with self.state_lock:
            state = self._state()
            state["notes"][body["project_id"]] = {"text": text, "updated_at": utc_now()}
            temporary = None
            try:
                self.state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.state_file.parent, prefix=".workbench-state-", suffix=".tmp", delete=False) as handle:
                    temporary = Path(handle.name)
                    json.dump(state, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temporary, 0o600)
                os.replace(temporary, self.state_file)
            except OSError:
                raise WorkbenchError(500, "notes_save_failed", "备注未能保存到电脑；请保留输入内容后重试。") from None
            finally:
                if temporary is not None and temporary.exists():
                    try:
                        temporary.unlink()
                    except OSError:
                        pass
            return self.notes()

    def action(self, body):
        if set(body) - {"action", "project_id"} or body.get("action") not in ("open_eda", "open_project"):
            raise WorkbenchError(400, "invalid_action", "工作台只支持打开 EDA 或已知项目文件夹。")
        action = body["action"]
        if action == "open_eda":
            if "project_id" in body:
                raise WorkbenchError(400, "invalid_action", "打开 EDA 不接受项目参数。")
        else:
            project = self.project(body.get("project_id"))
            target = inside(self.repo_root, project.get("workspace"))
        if sys.platform != "darwin":
            raise WorkbenchError(501, "platform_unsupported", "打开本机应用和项目文件夹仅在 Mac 工作台提供。")
        if action == "open_eda":
            app, _ = self.application(self.environment())
            if app is None:
                raise WorkbenchError(409, "app_unavailable", "当前电脑没有找到记录中的 EDA 应用。")
            command = ["/usr/bin/open", "-a", str(app)]
        else:
            if not target.is_dir():
                raise WorkbenchError(404, "workspace_unavailable", "项目文件夹尚未创建或当前不可用。")
            command = ["/usr/bin/open", str(target)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise WorkbenchError(500, "open_failed", "未能完成打开请求，请在 Mac 上检查。") from None
        if result.returncode != 0:
            raise WorkbenchError(500, "open_failed", "macOS 没有接受打开请求，请在 Mac 上检查。")
        return {"ok": True, "action": action, "detail": "已向 Mac 发送打开请求。"}

    def document(self, key):
        item = next((d for d in self.catalog().get("documents", []) if d["id"] == key), None)
        if item is None:
            raise WorkbenchError(404, "unknown_document", "文档不在工作台清单中。")
        path = inside(self.repo_root, item["path"])
        if not path.is_file():
            raise WorkbenchError(404, "document_unavailable", "文档当前不可用。")
        return path, str(item.get("name") or path.name)


class WorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, app):
        self.app = app
        address = (loopback_host(address[0]), address[1])
        if ":" in address[0]:
            self.address_family = socket.AF_INET6
        super().__init__(address, WorkbenchHandler)
        bound_host, port = self.server_address[:2]
        hosts = {bound_host, "localhost"}
        self.allowed_hosts = {f"[{h}]:{port}" if ":" in h else f"{h}:{port}" for h in hosts}
        if port == 80:
            self.allowed_hosts.update(hosts)


class WorkbenchHandler(BaseHTTPRequestHandler):
    server_version = "MakerLabWorkbench"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def log_message(self, format, *args):
        # Do not log note text, license material, or request headers.
        pass

    def guard(self, post=False):
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or hosts[0].lower() not in self.server.allowed_hosts:
            raise WorkbenchError(403, "invalid_host", "只允许通过本机工作台地址访问。")
        origins = self.headers.get_all("Origin", [])
        expected = "http://" + hosts[0].lower()
        if len(origins) > 1 or (origins and origins[0].lower() != expected) or (post and not origins):
            raise WorkbenchError(403, "invalid_origin", "请求来源与工作台地址不一致。")
        if self.headers.get("Sec-Fetch-Site", "") == "cross-site":
            raise WorkbenchError(403, "cross_site_request", "不接受外部网站发来的操作。")
        if post:
            if self.headers.get_all("X-Workbench-Request", []) != ["1"]:
                raise WorkbenchError(403, "missing_request_header", "缺少工作台操作标记。")
            types = self.headers.get_all("Content-Type", [])
            if len(types) != 1 or types[0].split(";", 1)[0].strip().lower() != "application/json":
                raise WorkbenchError(415, "invalid_content_type", "操作请求必须使用 application/json。")

    def route(self):
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
            raise WorkbenchError(400, "invalid_url", "请求地址无效。")
        try:
            path = unquote(parsed.path, errors="strict")
        except UnicodeError:
            raise WorkbenchError(400, "invalid_url", "请求地址编码无效。") from None
        if "\\" in path or "\x00" in path or ".." in PurePosixPath(path).parts:
            raise WorkbenchError(403, "path_forbidden", "不接受目录越界请求。")
        return path

    def common_headers(self, *, document=False):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "sandbox; default-src 'none'; frame-ancestors 'none'" if document else "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

    def send_json(self, status, payload, *, head=False):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.common_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def fail(self, error, *, head=False):
        self.send_json(error.status, {"error": {"code": error.code, "message": error.message}}, head=head)

    def file_response(self, path, *, document=False, name=None, head=False):
        try:
            data = path.read_bytes()
        except OSError:
            raise WorkbenchError(404, "file_unavailable", "文件当前不可用。") from None
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        textual = path.suffix.lower() in (".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".toml", ".log") or kind.startswith("text/")
        if document:
            kind = "text/plain; charset=utf-8" if textual else "application/octet-stream"
        self.send_response(200)
        self.common_headers(document=document)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        if document:
            disposition = "inline" if textual else "attachment"
            suffix = path.suffix if re.fullmatch(r"\.[A-Za-z0-9]+", path.suffix) else ""
            self.send_header("Content-Disposition", f"{disposition}; filename=\"document{suffix}\"; filename*=UTF-8''{quote(name or path.name, safe='')}")
        self.end_headers()
        if not head:
            self.wfile.write(data)

    def get(self, *, head=False):
        try:
            self.guard()
            path = self.route()
            if path == "/api/status" and not head:
                self.send_json(200, self.server.app.status())
            elif path == "/api/notes" and not head:
                self.send_json(200, self.server.app.notes())
            elif path.startswith("/api/"):
                raise WorkbenchError(404, "unknown_endpoint", "接口不存在。")
            elif path.startswith("/documents/"):
                key = path[len("/documents/"):]
                if not ID_PATTERN.fullmatch(key):
                    raise WorkbenchError(404, "unknown_document", "文档不在工作台清单中。")
                file, name = self.server.app.document(key)
                self.file_response(file, document=True, name=name, head=head)
            else:
                file = inside(self.server.app.web_root, "index.html" if path == "/" else path.lstrip("/"))
                if not file.is_file():
                    raise WorkbenchError(404, "file_unavailable", "页面或文件不存在。")
                self.file_response(file, head=head)
        except WorkbenchError as error:
            self.fail(error, head=head)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self.get()

    def do_HEAD(self):
        self.get(head=True)

    def do_POST(self):
        try:
            self.guard(post=True)
            path = self.route()
            if path not in ("/api/notes", "/api/actions"):
                raise WorkbenchError(404, "unknown_endpoint", "接口不存在。")
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
                raise WorkbenchError(400, "invalid_body_length", "请求长度无效。")
            try:
                length = int(lengths[0])
            except ValueError:
                raise WorkbenchError(400, "invalid_body_length", "请求长度无效。") from None
            if length < 0 or length > MAX_BODY_BYTES:
                raise WorkbenchError(413, "body_too_large", "请求内容过长。")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise WorkbenchError(400, "incomplete_body", "请求内容不完整。")
            try:
                body = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
            except (ValueError, UnicodeError):
                raise WorkbenchError(400, "invalid_json", "请求内容不是有效 JSON。") from None
            if not isinstance(body, dict):
                raise WorkbenchError(400, "invalid_json", "请求内容须为 JSON 对象。")
            result = self.server.app.save_note(body) if path == "/api/notes" else self.server.app.action(body)
            self.send_json(200, result)
        except WorkbenchError as error:
            self.fail(error)
        except socket.timeout:
            self.fail(WorkbenchError(408, "request_timeout", "请求内容接收超时。"))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        self.fail(WorkbenchError(405, "method_not_allowed", "不提供跨站访问。"))


def loopback_host(value):
    if value == "localhost":
        return "127.0.0.1"
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise argparse.ArgumentTypeError("host 只能是 localhost 或回环 IP 地址") from None
    if not address.is_loopback:
        raise argparse.ArgumentTypeError("工作台只能监听回环地址，不能开放局域网或公网")
    return str(address)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", type=loopback_host, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8135)
    parser.add_argument("--state-file", type=Path, default=Path.home() / "Documents/DIY/eda-toolchain/workbench-state.json")
    parser.add_argument("--check", action="store_true", help="检查文件、配置与实际 doctor，不启动 HTTP 服务")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("port 必须在 0–65535 范围内")
    app = Workbench(Path(__file__).resolve().parent.parent, args.state_file)
    try:
        app.catalog()
        if not (app.web_root / "index.html").is_file():
            raise WorkbenchError(500, "web_unavailable", "缺少工作台首页。")
        status = app.status()
        if args.check:
            print(json.dumps({"ok": True, "status": status}, ensure_ascii=False, indent=2))
            return 0
        server = WorkbenchServer((args.host, args.port), app)
    except (WorkbenchError, OSError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    host = f"[{args.host}]" if ":" in args.host else args.host
    print(f"Maker Lab workbench: http://{host}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
