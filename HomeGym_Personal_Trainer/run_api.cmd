@echo off
setlocal

cd /d "%~dp0"

if exist "runtime312\Scripts\python.exe" (
    "runtime312\Scripts\python.exe" run_api.py
    goto :eof
)

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" run_api.py
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 run_api.py
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python run_api.py
    goto :eof
)

echo No Python interpreter found. Install Python 3.12+ and run:
echo   pip install -r requirements.txt
exit /b 1
