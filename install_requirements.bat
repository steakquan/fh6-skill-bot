@echo off
title Install Requirements - Forza Horizon 6 Skill Bot
echo ===================================================
echo   Forza Horizon 6 Skill Bot - 安裝依賴套件
echo ===================================================
echo.
echo   正在安裝所需的 Python 函式庫 (opencv-python, pillow, pywin32)...
echo.
pip install opencv-python pillow pywin32
if errorlevel 1 (
    echo.
    echo   嘗試以 python -m pip 安裝...
    echo.
    python -m pip install opencv-python pillow pywin32
)

echo.
if errorlevel 0 (
    echo ===================================================
    echo   套件安裝完成！您可以點擊 run_bot.bat 開始使用。
    echo ===================================================
) else (
    echo ===================================================
    echo   錯誤：無法完成安裝！
    echo   請確認您的電腦是否已安裝 Python，並已勾選「Add to PATH」。
    echo ===================================================
)
echo.
pause
