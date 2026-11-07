@echo off
REM ============================================================
REM  REA Panel 手机版 — 一键构建 APK
REM  手工链路（免 Gradle）：aapt2 -> javac -> d8 -> zipalign -> apksigner
REM  依赖本机：JDK21 / build-tools 35.0.0
REM  产物：dist\REA-Panel-Mobile.apk
REM ============================================================
setlocal enabledelayedexpansion

set JDK=D:\TOOL\jdk\bin
set BT=D:\TOOL\Android\Sdk\build-tools\35.0.0
set PLATFORM=D:\TOOL\Android\Sdk\platforms\android-34\android.jar
set ADB=D:\Android\Sdk\platform-tools\adb.exe

cd /d "%~dp0"

REM --- 找 android.jar（多路径尝试）---
if not exist "%PLATFORM%" (
    for %%P in ("D:\TOOL\Android\Sdk\platforms" "D:\Android\Sdk\platforms") do (
        if exist %%P (
            for /d %%D in (%%P\android-*) do set PLATFORM=%%D\android.jar
        )
    )
)
if not exist "%PLATFORM%" (
    echo [错误] 找不到 android.jar，请检查 Android SDK platforms 目录
    exit /b 1
)
echo 使用 android.jar: %PLATFORM%

REM --- 清理 ---
echo.
echo [1/7] 清理输出目录...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
mkdir build\gen build\obj build\dex dist

REM --- 资源编译 ---
echo.
echo [2/7] aapt2 编译资源...
"%BT%\aapt2.exe" compile --dir res -o build\res.zip
if errorlevel 1 ( echo [错误] aapt2 compile 失败 & exit /b 1 )

echo.
echo [3/7] aapt2 链接资源 + 生成 R.java...
"%BT%\aapt2.exe" link ^
  -o build\app.unsigned.apk ^
  -I "%PLATFORM%" ^
  --manifest AndroidManifest.xml ^
  --java build\gen ^
  --min-sdk-version 24 ^
  --target-sdk-version 34 ^
  -A assets ^
  --auto-add-overlay ^
  build\res.zip
if errorlevel 1 ( echo [错误] aapt2 link 失败 & exit /b 1 )

REM --- 编译 Java ---
echo.
echo [4/7] javac 编译 Java 源码...
dir /s /b src\*.java build\gen\*.java > build\sources.txt
"%JDK%\javac.exe" -encoding UTF-8 -source 17 -target 17 ^
  -bootclasspath "%PLATFORM%" ^
  -classpath "%PLATFORM%" ^
  -d build\obj ^
  @build\sources.txt 2>&1
if errorlevel 1 ( echo [错误] javac 失败 & exit /b 1 )

REM --- dex ---
echo.
echo [5/7] d8 转换 dex...
"%BT%\d8.bat" --min-api 24 --output build\dex ^
  --lib "%PLATFORM%" ^
  (for /r build\obj %%f in (*.class) do @echo "%%f")
if errorlevel 1 ( echo [错误] d8 失败 & exit /b 1 )

REM --- 打包 ---
echo.
echo [6/7] 写入 dex 并打包...
cd build\dex
"%JDK%\jar.exe" uf ..\app.unsigned.apk classes.dex
cd ..\..

REM --- 签名 ---
echo.
echo [7/7] zipalign + 签名...
"%BT%\zipalign.exe" -f 4 build\app.unsigned.apk build\app.aligned.apk
if errorlevel 1 ( echo [错误] zipalign 失败 & exit /b 1 )

if not exist debug.keystore (
    echo     生成调试签名库...
    "%JDK%\keytool.exe" -genkeypair -v -keystore debug.keystore ^
      -alias readebug -keyalg RSA -keysize 2048 -validity 10000 ^
      -storepass android -keypass android ^
      -dname "CN=REA Panel, OU=Dev, O=Local, L=Local, S=Local, C=CN" 2>nul
)

"%BT%\apksigner.bat" sign ^
  --ks debug.keystore --ks-key-alias readebug ^
  --ks-pass pass:android --key-pass pass:android ^
  --out dist\REA-Panel-Mobile.apk ^
  build\app.aligned.apk
if errorlevel 1 ( echo [错误] 签名失败 & exit /b 1 )

echo.
echo 校验签名...
"%BT%\apksigner.bat" verify --print-certs dist\REA-Panel-Mobile.apk | findstr /i "Signer"

echo.
echo ============================================================
echo  构建完成！
echo  产物： %CD%\dist\REA-Panel-Mobile.apk
echo.
echo  安装到设备： "%ADB%" install -r dist\REA-Panel-Mobile.apk
echo ============================================================
endlocal
