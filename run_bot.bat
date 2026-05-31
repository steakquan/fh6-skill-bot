@echo off
cd /d "%~dp0"

:: Define user local Python 3.12 path dynamically
set LOCAL_PYTHON="%LocalAppData%\Programs\Python\Python312\pythonw.exe"

if exist %LOCAL_PYTHON% (
    start "" %LOCAL_PYTHON% gui.py
) else (
    :: Fallback to default pythonw in system PATH
    start "" pythonw gui.py
)
