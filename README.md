# REA Panel — 逆向工程控制台

REA CLI（v6.5.0，155 个命令）的图形面板。PyQt6 原生窗口，打包为单文件 exe。

## 为什么不用 Electron

本机 `E:\pythonpath\python.exe` 已内置 **PyQt6 6.11.0 + PyInstaller 6.22.3**。
Electron 每做一个项目要重下 100MB+ Chromium，国内网络常年失败；
本方案依赖装在 Python 全局，**新项目零安装、无需联网**。

## 快速开始

```bash
# 直接运行（开发）
E:\pythonpath\python.exe main.py

# 打包 exe
build.bat            # 或见下方完整命令
```

产物：`dist\REA-Panel.exe`（约 37 MB，单文件，双击即用）

## 打包命令

```bash
E:\pythonpath\python.exe -m PyInstaller --clean --noconfirm ^
  --name REA-Panel --windowed --onefile ^
  --icon assets/icon.ico --add-data "assets;assets" ^
  --hidden-import PyQt6.QtCore --hidden-import PyQt6.QtGui --hidden-import PyQt6.QtWidgets ^
  --exclude-module PyQt6.QtWebEngineCore --exclude-module PyQt6.QtWebEngineWidgets ^
  --exclude-module PyQt6.QtWebEngineQuick --exclude-module tkinter ^
  --exclude-module matplotlib --exclude-module numpy --exclude-module pandas ^
  --exclude-module PIL --exclude-module setuptools ^
  main.py
```

`--exclude-module PyQt6.QtWebEngine*` 必加，否则体积从 37MB 涨到 150MB。

## 功能

| 区域 | 说明 |
|---|---|
| 左栏 | 153 个命令，按 7 个类别分组（总览 / JS-Electron / Android-ADB / 原生-二进制 / 浏览器 / 比对 / 其他），支持搜索 |
| 中栏 | **由 JSON Schema 自动生成参数表单** —— enum→下拉、bool→复选、array→JSON 输入、路径→带「浏览…」按钮 |
| 右栏 | 结果三视图：JSON 折叠树 / 原始文本 / 图片预览（自动识别输出中的 PNG 路径） |
| 底部 | 运行日志 + 退出码 + 耗时 |

快捷键：`Ctrl+F` 搜索命令 · `Ctrl+Enter` / `F5` 运行 · `Esc` 清空搜索

## 架构

```
main.py                  入口
app/
  rea_backend.py         REA 调用层（进程地位、命令索引、schema、流式执行）
  schema_form.py         JSON Schema → Qt 控件（自动表单）
  result_view.py         结果三视图（JSON 树 / 文本 / 图片）
  theme.py               深色 QSS
  main_window.py         主窗口（三栏布局 + QThread 异步）
assets/
  icon.ico               应用图标（7 尺寸，代码生成）
build.bat                一键打包
_probe/                  开发期验证脚本（gen_icon.py / smoke_test.py / snap_real.py）
```

## 执行环境解析

按优先级自动定位 rea：

1. 托管 node + `rea.mjs`：`C:\Users\19513\.workbuddy\binaries\node\versions\22.22.2-3\node.exe` + `...\npm\node_modules\rea-agents\scripts\rea.mjs`
2. npm 全局 `rea.cmd`
3. PATH 上的 `rea`

## 已知限制

- REA 的四个分析引擎（Ghidra / IDA / jadx / Hopper）**尚未配置**，`rea doctor` 会报 `missing_analysis_engine`。面板本身可正常调用不需引擎的命令（如 `doctor`、`compare-*`、`address-to-file-offset`）。
- 开发期截图若用 `QT_QPA_PLATFORM=offscreen`，中文字体会变方框（Qt offscreen 字体库为空），真实窗口模式正常。
