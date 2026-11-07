# -*- coding: utf-8 -*-
"""
rea_backend.py — REA CLI 调用层

职责：
  * 定位 rea 可执行环境（托管 node + rea.mjs，回退 npm .cmd）
  * 拉取命令索引（rea --help）
  * 拉取单命令 JSON Schema（rea <cmd> --schema --format json）
  * 执行命令（QThread 中流式读取 stdout/stderr）

不依赖任何第三方库，仅用标准库，保证 PyInstaller 打包零意外。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Iterable

# ---- 常量：本机已知路径（打包后仍优先用托管 node，可移植性靠回退链） ----

MANAGED_NODE_CANDIDATES = [
    r"C:\Users\19513\.workbuddy\binaries\node\versions\22.22.2-3\node.exe",
]

REA_MJS_CANDIDATES = [
    r"C:\Users\19513\AppData\Roaming\npm\node_modules\rea-agents\scripts\rea.mjs",
]

REA_CMD_CANDIDATES = [
    r"C:\Users\19513\AppData\Roaming\npm\rea.cmd",
]

# 命令输出可能很大，给足缓冲
_MAX_CAPTURE = 64 * 1024 * 1024


@dataclass
class ReaEnv:
    """解析后的 rea 执行环境"""

    cmd: str
    base_args: list[str] = field(default_factory=list)
    kind: str = "bare"  # node+mjs | cmd | bare

    def describe(self) -> str:
        return f"{self.cmd} {' '.join(self.base_args)}".strip()

    def argv(self, args: Iterable[str]) -> list[str]:
        return [self.cmd, *self.base_args, *args]


def resolve_rea() -> ReaEnv:
    """按优先级定位 rea 执行环境。"""
    node = next((p for p in MANAGED_NODE_CANDIDATES if os.path.isfile(p)), None)
    mjs = next((p for p in REA_MJS_CANDIDATES if os.path.isfile(p)), None)
    if node and mjs:
        return ReaEnv(cmd=node, base_args=[mjs], kind="node+mjs")

    for c in REA_CMD_CANDIDATES:
        if os.path.isfile(c):
            return ReaEnv(cmd=c, base_args=[], kind="cmd")

    which = shutil.which("rea")
    if which:
        return ReaEnv(cmd=which, base_args=[], kind="bare")

    # 最后兜底：交给 PATH（可能失败，由调用方报错）
    return ReaEnv(cmd="rea", base_args=[], kind="bare")


# ---- 命令索引 --------------------------------------------------------------

_CMD_LINE = re.compile(r"^ {2}([a-z0-9][a-z0-9-]*)\s{2,}(.*)$")


def list_commands(env: ReaEnv, timeout: int = 90) -> list[dict]:
    """解析 `rea --help`，返回 [{name, summary}]。"""
    out = _capture(env, ["--help"], timeout=timeout)
    cmds: list[dict] = []
    in_commands = False
    for line in out.splitlines():
        if re.match(r"^\s*Commands:\s*$", line):
            in_commands = True
            continue
        if in_commands and not line.strip():
            in_commands = False
            continue
        if not in_commands:
            continue
        m = _CMD_LINE.match(line)
        if m:
            cmds.append({"name": m.group(1), "summary": m.group(2).strip()})
    return cmds


def get_schema(env: ReaEnv, command: str, timeout: int = 60) -> dict:
    """拉取单命令 JSON Schema。失败时返回 {'error': '...'}"""
    try:
        out = _capture(env, [command, "--schema", "--format", "json"], timeout=timeout)
        return json.loads(out)
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def _capture(env: ReaEnv, args: list[str], timeout: int = 120) -> str:
    """同步执行并捕获合并输出。"""
    proc = subprocess.run(
        env.argv(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        creationflags=_no_window(),
    )
    return proc.stdout.decode("utf-8", errors="replace")


def _no_window() -> int:
    """Windows 下隐藏黑框"""
    if sys.platform == "win32":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return 0


# ---- 异步执行（供 Qt 线程调用） --------------------------------------------


def run_stream(
    env: ReaEnv,
    args: list[str],
    on_output: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    cwd: str | None = None,
) -> dict:
    """
    流式执行命令。每读到一段输出就调用 on_output(text)。
    返回 {'code': int, 'stdout': str, 'stderr': str, 'error': str|None}

    注意：rea 把日志写 stderr、结构化结果写 stdout，两者都需要保留，
    这里按“合并顺序”回传但在返回值里分开存放（若可区分）。
    """
    try:
        proc = subprocess.Popen(
            env.argv(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd if cwd and os.path.isdir(cwd) else None,
            creationflags=_no_window(),
            bufsize=0,
        )
    except Exception as e:  # noqa: BLE001
        return {"code": -1, "stdout": "", "stderr": "", "error": f"{type(e).__name__}: {e}"}

    import threading

    out_chunks: list[str] = []
    err_chunks: list[str] = []

    def pump(stream, sink):
        try:
            for raw in iter(stream.readline, b""):
                if should_stop and should_stop():
                    break
                text = raw.decode("utf-8", errors="replace")
                sink.append(text)
                if on_output:
                    on_output(text)
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                stream.close()
            except Exception:  # noqa: BLE001
                pass

    t1 = threading.Thread(target=pump, args=(proc.stdout, out_chunks), daemon=True)
    t2 = threading.Thread(target=pump, args=(proc.stderr, err_chunks), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    code = proc.wait()
    return {
        "code": code,
        "stdout": "".join(out_chunks),
        "stderr": "".join(err_chunks),
        "error": None,
    }
