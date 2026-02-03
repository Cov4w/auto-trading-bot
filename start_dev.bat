@echo off
setlocal
echo 🚀 Starting Trading Bot Development Environment...

REM Check venv
if not exist venv (
    echo ❌ Virtual environment not found! Please run setup.bat first.
    pause
    exit /b 1
)

echo.
echo [1/2] Starting Backend (FastAPI + Uvicorn)...
echo    - Port: 8000
echo    - Docs: http://localhost:8000/docs
start "Trading Bot Backend" cmd /k "call venv\Scripts\activate && cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to initialize
timeout /t 3 /nobreak >nul

echo.
echo [2/2] Starting Frontend (React + Vite)...
echo    - URL: http://localhost:3000
start "Trading Bot Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ✅ Services started in separate windows!
echo Press any key to exit this launcher (services will keep running).
pause
