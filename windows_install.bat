@echo off
:: MiniMax Tagger Windows 一键安装脚本
echo ===== MiniMax Tagger 安装向导 =====

:: 检查 Python 是否存在
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python。请先从 https://www.python.org/downloads/windows/ 安装 Python 3.10 及以上版本，并勾选 “Add Python to PATH”。
    pause
    exit /b 1
)

:: 创建并激活虚拟环境
echo [1/4] 创建虚拟环境 .venv ...
python -m venv .venv
call .\.venv\Scripts\activate.bat

:: 升级 pip
python -m pip install --upgrade pip

:: 安装依赖
echo [2/4] 安装依赖，请稍候...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败，请检查网络或重试。
    pause
    exit /b 1
)

:: 创建桌面快捷方式
echo [3/4] 正在创建桌面快捷方式...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$W = New-Object -ComObject WScript.Shell; ^
     $Desk = $W.SpecialFolders['Desktop']; ^
     $Lnk = $W.CreateShortcut($Desk + '\\MiniMax Tagger.lnk'); ^
     $Lnk.TargetPath = '%~dp0run_gui.bat'; ^
     $Lnk.IconLocation = '%~dp0resources\\minimax_tagger.ico'; ^
     $Lnk.WorkingDirectory = '%~dp0'; ^
     $Lnk.Save()"

echo 已在桌面创建 "MiniMax Tagger" 图标，双击即可启动！

:: 完成安装并启动 GUI
echo [4/4] 启动图形界面...
python -m minimax_tagger.gui

echo 程序已退出。如需再次启动，请双击桌面图标或 run_gui.bat
pause 