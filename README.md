# REA Tool · 双端逆向工程控制台

REA CLI（v6.5.0，155 个命令）的图形化双端实现。

- 在线介绍页：<https://180lisilence.github.io/rea-tool-myself/>
- 仓库：<https://github.com/180lisilence/rea-tool-myself>

## 分支

| 分支 | 内容 |
|---|---|
| `main` | 项目介绍页 `index.html`（GitHub Pages） |
| `panel` | Windows 原生面板（PyQt6 + PyInstaller），源码与成品 `dist/REA-Panel.exe` |
| `mobile` | Android 手机端（WebView + 局域网 REST/SSE），源码与成品 `dist/REA-Panel-Mobile.apk` |

## 下载

- [REA-Panel.exe（Windows 面板端）](https://github.com/180lisilence/rea-tool-myself/releases/download/v1.0.0/REA-Panel.exe)
- [REA-Panel-Mobile.apk（Android 手机端）](https://github.com/180lisilence/rea-tool-myself/releases/download/v1.0.0/REA-Panel-Mobile.apk)

## 原理速览

PC 端 `REA-Panel.exe` 用 PyQt6 三栏窗口直接 fork 本机 rea 进程：左栏命令索引、中栏由 `--schema` 的 JSON Schema 自动生成参数表单、右栏结果三视图，QThread 异步流式读取 stdout/stderr，PyInstaller 打成单文件 exe。

手机端 `REA-Panel-Mobile.apk` 是一个约 50 KB 的 WebView 壳，加载随包内置的 `assets/panel/` 本地 H5 界面；界面通过 `fetch` / SSE 调电脑上 `app/rea_server.py` 暴露的 REST API（`/api/ping`、`/api/commands`、`/api/schema`、`/api/run`、`/api/stream`），服务绑定 `0.0.0.0:8788`，手机与电脑同一局域网即可。两端共用 `app/rea_backend.py` 调用层。

构建：PC 端 `build.bat` → PyInstaller；手机端 `build_apk.py` → aapt2 compile/link → javac → d8 → jar 写 dex → zipalign → apksigner（免 Gradle 手工链路）。

详细原理、架构图与使用步骤见根目录 `index.html`。
