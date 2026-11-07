@echo off
REM ============================================================
REM  REA Panel 一键打包脚本
REM  用法：双击本文件，或在命令行执行 build.bat
REM  产物：dist\REA-Panel.exe
REM
REM  依赖：E:\pythonpath\python.exe 内已装 PyQt6 + PyInstaller
REM        无需 npm install，无需联网
REM ============================================================
setlocal

set PY=E:\pythonpath\python.exe
cd /d "%~dp0"

echo.
echo [1/3] 语法检查...
"%PY%" -m py_compile main.py app\__init__.py app\rea_backend.py app\schema_form.py app\result_view.py app\theme.py app\main_window.py
if errorlevel 1 (
    echo      语法错误，终止。
    exit /b 1
)
echo      通过。

echo.
echo [2/3] 生成图标（若缺失）...
if not exist "assets\icon.ico" (
    "%PY%" _probe\gen_icon.py
) else (
    echo      assets\icon.ico 已存在，跳过。
)

echo.
echo [3/3] 打包 exe（约 30 秒）...
"%PY%" -m PyInstaller --clean --noconfirm ^
  --name REA-Panel ^
  --windowed ^
  --onefile ^
  --icon assets/icon.ico ^
  --add-data "assets;assets" ^
  --hidden-import PyQt6.QtCore ^
  --hidden-import PyQt6.QtGui ^
  --hidden-import PyQt6.QtWidgets ^
  --exclude-module PyQt6.QtWebEngineCore ^
  --exclude-module PyQt6.QtWebEngineWidgets ^
  --exclude-module PyQt6.QtWebEngineQuick ^
  --exclude-module tkinter ^
  --exclude-module matplotlib ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  --exclude-module PIL ^
  --exclude-module setuptools ^
  main.py
if errorlevel 1 (
    echo      打包失败。
    exit /b 1
)

echo.
echo ============================================================
echo  完成！产物： %CD%\dist\REA-Panel.exe
echo ============================================================
endlocal
