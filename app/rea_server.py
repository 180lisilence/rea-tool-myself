# -*- coding: utf-8 -*-
"""
rea_server.py — 电脑端 HTTP 服务，把 rea CLI 暴露成 REST API 供手机访问

端点：
  GET  /api/ping                    健康检查
  GET  /api/env                     环境信息
  GET  /api/commands                全部命令索引（153 条）
  GET  /api/schema?cmd=<name>       单命令 JSON Schema
  POST /api/run                     {"args": ["analyze","path"]} 执行命令
  GET  /api/stream?cmd=...&args=... 流式执行（SSE）

仅用标准库，便于独立打包或直接在 Python 下运行。
默认绑定 0.0.0.0:8788，手机与电脑需在同一局域网。
"""

from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 兼容直接运行与包内导入
try:
    from . import rea_backend as rb
except ImportError:  # noqa: BLE001
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import rea_backend as rb

DEFAULT_PORT = 8788
TOKEN = ""  # 可选：设置后手机端需带 X-REA-TOKEN 头

_env: rb.ReaEnv | None = None
_env_lock = threading.Lock()
_schema_cache: dict[str, dict] = {}


def get_env() -> rb.ReaEnv:
    global _env
    with _env_lock:
        if _env is None:
            _env = rb.resolve_rea()
        return _env


def lan_ips() -> list[str]:
    """列出本机局域网 IPv4 地址，方便用户知道该在手机填什么。"""
    ips: list[str] = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:  # noqa: BLE001
        pass
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:  # noqa: BLE001
        pass
    return ips


class Handler(BaseHTTPRequestHandler):
    server_version = "REA-Server/1.0"
    protocol_version = "HTTP/1.1"

    # ---- 工具 -------------------------------------------------------------

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-REA-TOKEN")

    def _json(self, obj, code: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text: str, code: int = 200, ctype: str = "text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _check_token(self) -> bool:
        if not TOKEN:
            return True
        return self.headers.get("X-REA-TOKEN", "") == TOKEN

    def log_message(self, fmt, *args):  # noqa: D102
        ts = time.strftime("%H:%M:%S")
        sys.stderr.write(f"[{ts}] {self.address_string()} {fmt % args}\n")

    # ---- 路由 -------------------------------------------------------------

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if not self._check_token():
            self._json({"error": "token 无效"}, 403)
            return

        try:
            if path == "/api/ping":
                self._json({"ok": True, "server": "REA-Server", "time": time.time()})

            elif path == "/api/env":
                env = get_env()
                self._json({
                    "ok": True,
                    "kind": env.kind,
                    "cmd": env.cmd,
                    "baseArgs": env.base_args,
                    "lan": lan_ips(),
                    "port": self.server.server_address[1],
                })

            elif path == "/api/commands":
                cmds = rb.list_commands(get_env())
                self._json({"ok": True, "count": len(cmds), "commands": cmds})

            elif path == "/api/schema":
                cmd = (qs.get("cmd") or [""])[0]
                if not cmd:
                    self._json({"error": "缺少 cmd 参数"}, 400)
                    return
                if cmd not in _schema_cache:
                    _schema_cache[cmd] = rb.get_schema(get_env(), cmd)
                self._json({"ok": True, "command": cmd, "schema": _schema_cache[cmd]})

            elif path == "/api/stream":
                self._stream(qs)

            elif path in ("/", "/index.html"):
                self._text("REA Server 运行中。API: /api/ping /api/env /api/commands "
                           "/api/schema?cmd= /api/run")

            else:
                self._json({"error": "未知端点", "path": path}, 404)

        except Exception as e:  # noqa: BLE001
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if not self._check_token():
            self._json({"error": "token 无效"}, 403)
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:  # noqa: BLE001
            self._json({"error": f"请求体解析失败: {e}"}, 400)
            return

        try:
            if path == "/api/run":
                args = payload.get("args") or []
                if not isinstance(args, list) or not args:
                    self._json({"error": "args 必须是非空数组"}, 400)
                    return
                cwd = payload.get("cwd")
                t0 = time.time()
                res = rb.run_stream(get_env(), [str(a) for a in args], cwd=cwd)
                res["ms"] = int((time.time() - t0) * 1000)
                res["ok"] = True
                self._json(res)
            else:
                self._json({"error": "未知端点", "path": path}, 404)
        except Exception as e:  # noqa: BLE001
            self._json({"error": f"{type(e).__name__}: {e}", "ok": False}, 500)

    # ---- SSE 流式 ---------------------------------------------------------

    def _stream(self, qs):
        cmd = (qs.get("cmd") or [""])[0]
        args = qs.get("arg") or []
        if not cmd:
            self._json({"error": "缺少 cmd 参数"}, 400)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()

        def emit(event: str, data):
            try:
                chunk = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
            except Exception:  # noqa: BLE001
                pass

        buffer: list[str] = []

        def on_out(text: str):
            buffer.append(text)
            emit("chunk", {"text": text})

        res = rb.run_stream(get_env(), [cmd, *args], on_output=on_out)
        emit("done", {"code": res.get("code", -1), "stdout": res.get("stdout", ""),
                      "stderr": res.get("stderr", ""), "error": res.get("error")})


def serve(port: int = DEFAULT_PORT, host: str = "0.0.0.0"):
    env = get_env()
    print("=" * 62)
    print("  REA Server — 手机端后端服务")
    print("=" * 62)
    print(f"  rea 环境   : {env.kind}  ({env.describe()})")
    print(f"  监听地址   : http://{host}:{port}")
    for ip in lan_ips():
        print(f"  手机填这个 : http://{ip}:{port}")
    print("=" * 62)
    print("  Ctrl+C 停止")
    print()

    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="REA 手机端后端服务")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--token", default="", help="可选访问令牌")
    args = ap.parse_args()
    TOKEN = args.token
    serve(args.port, args.host)
