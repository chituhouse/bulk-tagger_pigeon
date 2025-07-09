@echo off
:: 启动 MiniMax Tagger GUI
if not exist .\.venv (
    echo [错误] 未找到 .venv 目录，请先运行 windows_install.bat 完成安装。
    pause
    exit /b 1
)
call .\.venv\Scripts\activate.bat
python -m minimax_tagger.gui
pause 