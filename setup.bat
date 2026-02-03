@echo off
setlocal
echo ======================================================================
echo 🚀 Self-Evolving Trading System - Setup (Windows)
echo ======================================================================

REM 1. Python Check
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH!
    pause
    exit /b 1
)
echo ✅ Python found

REM 2. Virtual Environment
if not exist venv (
    echo 🔨 Creating virtual environment...
    python -m venv venv
) else (
    echo ℹ️  Virtual environment already exists
)

REM 3. Install Backend Dependencies
echo 📦 Installing Backend dependencies...
call venv\Scripts\activate
python -m pip install --upgrade pip
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo ⚠️  requirements.txt not found!
)

REM 4. Install Frontend Dependencies
echo 📦 Installing Frontend dependencies...
if exist frontend\package.json (
    cd frontend
    call npm install
    cd ..
) else (
    echo ⚠️  frontend directory not found!
)

REM 5. Create .env
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env
    echo ⚠️  IMPORTANT: Please edit .env file and add your API keys!
) else (
    echo ℹ️  .env file already exists
)

echo.
echo ======================================================================
echo ✅ Setup Complete!
echo ======================================================================
echo.
echo Next Steps:
echo 1. Edit .env file with your key
echo 2. Run start_dev.bat
echo.
pause
