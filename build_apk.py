# -*- coding: utf-8 -*-
"""
build_apk.py — REP Panel 手机版 APK 构建（免 Gradle 手工链路）

流程：
  1. aapt2 compile   资源 -> .flat
  2. aapt2 link      -> APK 骨架 + R.java
  3. javac           Java 源码 -> .class
  4. d8              .class -> classes.dex
  5. zip             把 dex + assets 塞进 APK
  6. zipalign        对齐
  7. apksigner       签名

产物：dist/REA-Panel-Mobile.apk
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))

JDK = r"D:\TOOL\jdk\bin"
BT = r"D:\TOOL\Android\Sdk\build-tools\35.0.0"

PLATFORM_CANDIDATES = [
    r"D:\TOOL\Android\Sdk\platforms\android-34\android.jar",
    r"D:\Android\Sdk\platforms\android-34\android.jar",
]

BUILD = os.path.join(HERE, "build")
DIST = os.path.join(HERE, "dist")


def find_platform() -> str:
    for p in PLATFORM_CANDIDATES:
        if os.path.isfile(p):
            return p
    # 扫描
    for root in (r"D:\TOOL\Android\Sdk\platforms", r"D:\Android\Sdk\platforms"):
        if os.path.isdir(root):
            for d in sorted(os.listdir(root), reverse=True):
                jar = os.path.join(root, d, "android.jar")
                if os.path.isfile(jar):
                    return jar
    raise SystemExit("[错误] 找不到 android.jar")


def run(cmd: list[str], desc: str, cwd: str | None = None, shell: bool = False) -> None:
    print(f"\n>>> {desc}")
    print("    " + " ".join(str(c) for c in cmd)[:160])
    r = subprocess.run(cmd, cwd=cwd, shell=shell,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = r.stdout.decode("utf-8", errors="replace")
    if r.returncode != 0:
        print(out[-4000:])
        raise SystemExit(f"[错误] {desc} 失败 (code={r.returncode})")
    if out.strip():
        tail = "\n".join(out.strip().splitlines()[-6:])
        print("    " + tail.replace("\n", "\n    "))
    print(f"    ✔ {desc}")


def main() -> int:
    platform = find_platform()
    print("=" * 62)
    print("  REA Panel 手机版 — APK 构建")
    print("=" * 62)
    print(f"  JDK      : {JDK}")
    print(f"  Tools    : {BT}")
    print(f"  Platform : {platform}")
    print("=" * 62)

    for exe in ("aapt2.exe", "d8.bat", "zipalign.exe", "apksigner.bat"):
        if not os.path.isfile(os.path.join(BT, exe)):
            raise SystemExit(f"[错误] 缺少 {exe}，检查 {BT}")
    for exe in ("javac.exe", "keytool.exe", "jar.exe"):
        if not os.path.isfile(os.path.join(JDK, exe)):
            raise SystemExit(f"[错误] 缺少 {exe}，检查 {JDK}")

    # 清理
    for d in (BUILD, DIST):
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(BUILD, "gen"), exist_ok=True)
    os.makedirs(os.path.join(BUILD, "obj"), exist_ok=True)
    os.makedirs(os.path.join(BUILD, "dex"), exist_ok=True)
    os.makedirs(DIST, exist_ok=True)

    res_zip = os.path.join(BUILD, "res.zip")
    unsigned = os.path.join(BUILD, "app.unsigned.apk")
    aligned = os.path.join(BUILD, "app.aligned.apk")
    out_apk = os.path.join(DIST, "REA-Panel-Mobile.apk")

    # 1. 编译资源
    run([os.path.join(BT, "aapt2.exe"), "compile",
         "--dir", os.path.join(HERE, "res"), "-o", res_zip],
        "aapt2 compile 资源")

    # 2. 链接资源
    run([os.path.join(BT, "aapt2.exe"), "link",
         "-o", unsigned,
         "-I", platform,
         "--manifest", os.path.join(HERE, "AndroidManifest.xml"),
         "--java", os.path.join(BUILD, "gen"),
         "--min-sdk-version", "24",
         "--target-sdk-version", "34",
         "-A", os.path.join(HERE, "assets"),
         "--auto-add-overlay",
         res_zip],
        "aapt2 link 生成 APK 骨架 + R.java")

    # 3. javac
    srcs = glob.glob(os.path.join(HERE, "src", "**", "*.java"), recursive=True)
    srcs += glob.glob(os.path.join(BUILD, "gen", "**", "*.java"), recursive=True)
    if not srcs:
        raise SystemExit("[错误] 未找到 Java 源文件")
    print(f"\n    发现 {len(srcs)} 个 Java 文件")
    run([os.path.join(JDK, "javac.exe"),
         "-encoding", "UTF-8",
         "-source", "8", "-target", "8",
         "-classpath", platform,
         "-d", os.path.join(BUILD, "obj"),
         "-nowarn",
         *srcs],
        "javac 编译 Java")

    # 4. d8
    classes = glob.glob(os.path.join(BUILD, "obj", "**", "*.class"), recursive=True)
    if not classes:
        raise SystemExit("[错误] javac 未产生 .class")
    print(f"    {len(classes)} 个 .class")
    run([os.path.join(BT, "d8.bat"), "--min-api", "24",
         "--output", os.path.join(BUILD, "dex"),
         "--lib", platform,
         *classes],
        "d8 转换为 dex", shell=True)

    dex = os.path.join(BUILD, "dex", "classes.dex")
    if not os.path.isfile(dex):
        raise SystemExit("[错误] d8 未产生 classes.dex")
    print(f"    classes.dex: {os.path.getsize(dex)} bytes")

    # 5. 把 dex 写回 APK
    run([os.path.join(JDK, "jar.exe"), "uf", unsigned, "-C",
         os.path.join(BUILD, "dex"), "classes.dex"],
        "写入 classes.dex")

    # 校验 assets 是否在包里
    with zipfile.ZipFile(unsigned) as z:
        names = z.namelist()
    has_assets = any(n.startswith("assets/panel/") for n in names)
    print(f"    APK 内条目 {len(names)} 个，assets/panel 存在: {has_assets}")

    # 6. zipalign
    run([os.path.join(BT, "zipalign.exe"), "-f", "4", unsigned, aligned],
        "zipalign 对齐")

    # 7. 签名
    ks = os.path.join(HERE, "debug.keystore")
    if not os.path.isfile(ks):
        run([os.path.join(JDK, "keytool.exe"), "-genkeypair", "-v",
             "-keystore", ks, "-alias", "readebug",
             "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
             "-storepass", "android", "-keypass", "android",
             "-dname", "CN=REA Panel, OU=Dev, O=Local, L=Local, S=Local, C=CN"],
            "生成调试签名库")

    run([os.path.join(BT, "apksigner.bat"), "sign",
         "--ks", ks, "--ks-key-alias", "readebug",
         "--ks-pass", "pass:android", "--key-pass", "pass:android",
         "--out", out_apk, aligned],
        "apksigner 签名", shell=True)

    # 验证
    r = subprocess.run([os.path.join(BT, "apksigner.bat"), "verify", "--print-certs", out_apk],
                       shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    vout = r.stdout.decode("utf-8", errors="replace").strip()
    print("\n>>> 签名校验")
    for line in vout.splitlines():
        if "Signer" in line or "verified" in line.lower():
            print("    " + line.strip())

    size = os.path.getsize(out_apk)
    print("\n" + "=" * 62)
    print(f"  构建完成！")
    print(f"  产物  : {out_apk}")
    print(f"  大小  : {size/1024:.1f} KB ({size} bytes)")
    print(f"  安装  : adb install -r \"{out_apk}\"")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
