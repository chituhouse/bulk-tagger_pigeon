@echo off
:: MiniMax Tagger CLI 快速启动脚本
if "%1"=="" (
    echo 用法: run_cli.bat <图片目录> [prompt]
    echo.
    echo 示例: run_cli.bat images "Generate detailed English prompts"
    pause
    exit /b 1
)
if not exist .\.venv (
    echo [错误] 未找到 .venv 目录，请先运行 windows_install.bat 完成安装。
    pause
    exit /b 1
)
call .\.venv\Scripts\activate.bat
set PROMPT_TEXT=%2
if "%PROMPT_TEXT%"=="" set PROMPT_TEXT=Generate detailed English prompts
python -m minimax_tagger %1 --prompt "%PROMPT_TEXT%"
pause 