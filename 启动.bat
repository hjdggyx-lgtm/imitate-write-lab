@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   写作训练 - 启动
echo ============================================
echo.

python writing_train_ui.py

if errorlevel 1 (
    echo.
    echo ============================================
    echo   程序异常退出，错误码: %errorlevel%
    echo ============================================
    pause
)