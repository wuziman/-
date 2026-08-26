@echo off
REM ============================================================
REM  Quant platform - one-time dependency installer
REM  Keep this file ASCII-only: cmd parses .bat files in the
REM  ANSI codepage, so UTF-8 Chinese text breaks line parsing.
REM ============================================================
cd /d "%~dp0"

echo [1/2] Installing backend dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Backend dependency install FAILED.
    pause
    exit /b 1
)
echo Backend dependencies OK.

echo.
echo [2/2] Installing frontend dependencies...
cd ../frontend
call npm install
if %errorlevel% neq 0 (
    echo Frontend dependency install FAILED.
    pause
    exit /b 1
)
echo Frontend dependencies OK.

echo.
echo ==================================================
echo  All dependencies installed.
echo  Run start.bat to launch the services.
echo ==================================================
echo.
pause
