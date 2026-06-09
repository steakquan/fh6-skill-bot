@echo off
title Forza Horizon 6 Skill Bot
cd /d "%~dp0"

:: 1. Search for a Python executable that has the required libraries
set SELECTED_PYTHON=
set SELECTED_PYTHONW=

:: A. Check system python in PATH
python -c "import cv2, PIL, win32gui" >nul 2>nul
if %errorlevel% equ 0 (
    set SELECTED_PYTHON=python
    set SELECTED_PYTHONW=pythonw
    goto :python_ready
)

:: B. Check local Python 3.12
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" -c "import cv2, PIL, win32gui" >nul 2>nul
    if %errorlevel% equ 0 (
        set SELECTED_PYTHON="%LocalAppData%\Programs\Python\Python312\python.exe"
        set SELECTED_PYTHONW="%LocalAppData%\Programs\Python\Python312\pythonw.exe"
        goto :python_ready
    )
)

:: C. Check local Python 3.13
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    "%LocalAppData%\Programs\Python\Python313\python.exe" -c "import cv2, PIL, win32gui" >nul 2>nul
    if %errorlevel% equ 0 (
        set SELECTED_PYTHON="%LocalAppData%\Programs\Python\Python313\python.exe"
        set SELECTED_PYTHONW="%LocalAppData%\Programs\Python\Python313\pythonw.exe"
        goto :python_ready
    )
)

:: D. Check local Python 3.14 (pythoncore)
if exist "%LocalAppData%\Python\pythoncore-3.14-64\python.exe" (
    "%LocalAppData%\Python\pythoncore-3.14-64\python.exe" -c "import cv2, PIL, win32gui" >nul 2>nul
    if %errorlevel% equ 0 (
        set SELECTED_PYTHON="%LocalAppData%\Python\pythoncore-3.14-64\python.exe"
        set SELECTED_PYTHONW="%LocalAppData%\Python\pythoncore-3.14-64\pythonw.exe"
        goto :python_ready
    )
)

:: 2. If no Python with libraries found, pick any available Python fallback to show the error
python --version >nul 2>nul
if %errorlevel% equ 0 (
    set SELECTED_PYTHON=python
    set SELECTED_PYTHONW=pythonw
    goto :show_dependency_error
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set SELECTED_PYTHON="%LocalAppData%\Programs\Python\Python312\python.exe"
    set SELECTED_PYTHONW="%LocalAppData%\Programs\Python\Python312\pythonw.exe"
    goto :show_dependency_error
)

if exist "%LocalAppData%\Python\pythoncore-3.14-64\python.exe" (
    set SELECTED_PYTHON="%LocalAppData%\Python\pythoncore-3.14-64\python.exe"
    set SELECTED_PYTHONW="%LocalAppData%\Python\pythoncore-3.14-64\pythonw.exe"
    goto :show_dependency_error
)

:: 3. No Python found at all
echo ===================================================
echo [錯誤 / ERROR] 系統找不到 Python 執行檔！
echo.
echo 1. 請確認您的電腦已安裝 Python 3.12 或以上版本。
echo 2. 安裝時務必勾選「Add Python to PATH」選項。
echo ===================================================
pause
exit /b 1

:show_dependency_error
echo ===================================================
echo [警告 / WARNING] 偵測到遺失必要的 Python 套件！
echo 正在使用主控台模式啟動以顯示詳細錯誤訊息：
echo ---------------------------------------------------
%SELECTED_PYTHON% gui.py
echo ---------------------------------------------------
echo.
echo 請執行 'install_requirements.bat' 以安裝所有必要套件。
echo ===================================================
pause
exit /b 1

:python_ready
:: 4. Run the GUI silently using pythonw
echo 正在啟動小助手...
start "" %SELECTED_PYTHONW% gui.py
exit /b 0
