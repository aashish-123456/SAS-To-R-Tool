@echo off
echo ========================================
echo SAS to R Automation Platform
echo Quick Start Script for Windows
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed!
    echo Please install from: https://nodejs.org
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed!
    echo Please install from: https://python.org
    pause
    exit /b 1
)

echo Node.js and Python are installed.
echo.

echo ========================================
echo Starting Frontend Server...
echo ========================================
cd frontend
start "Frontend Server" cmd /k "npm install && npm run dev"
cd ..

echo.
echo Waiting 5 seconds before starting backend...
timeout /t 5 /nobreak

echo ========================================
echo Starting Backend Server...
echo ========================================
cd backend
start "Backend Server" cmd /k "python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python main.py"
cd ..

echo.
echo ========================================
echo Both servers are starting!
echo ========================================
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo.
echo The application will open in your browser shortly...
timeout /t 10 /nobreak
start http://localhost:5173

echo.
echo Press any key to stop all servers...
pause

REM Close both server windows
taskkill /FI "WindowTitle eq Frontend Server*" /F
taskkill /FI "WindowTitle eq Backend Server*" /F

echo.
echo Servers stopped.
pause
