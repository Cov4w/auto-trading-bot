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

REM 2. Node.js Check
call node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is not installed or not in PATH!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo ✅ Node.js found

REM 3. Conda Check (Optional)
where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Conda found - You can use: conda activate upBit
    set USE_CONDA=1
) else (
    echo ℹ️  Conda not found - Using pip venv instead
    set USE_CONDA=0
)

REM 4. Virtual Environment
if %USE_CONDA%==0 (
    if not exist venv (
        echo 🔨 Creating virtual environment...
        python -m venv venv
    ) else (
        echo ℹ️  Virtual environment already exists
    )
    echo 🔄 Activating virtual environment...
    call venv\Scripts\activate
) else (
    echo ℹ️  Using Conda environment 'upBit'
    echo To activate: conda activate upBit
)

REM 5. Install Backend Dependencies
echo 📦 Installing Backend dependencies...
python -m pip install --upgrade pip
if exist backend\requirements.txt (
    pip install -r backend\requirements.txt
    echo ✅ Backend dependencies installed
) else (
    echo ⚠️  backend\requirements.txt not found!
)

REM 6. Install Frontend Dependencies
echo 📦 Installing Frontend dependencies...
if exist frontend\package.json (
    cd frontend
    call npm install
    if %errorlevel% equ 0 (
        echo ✅ Frontend dependencies installed
    )
    cd ..
) else (
    echo ⚠️  frontend directory not found!
)

REM 7. Create .env
if not exist backend\.env (
    echo 📝 Creating .env file from template...
    if exist .env.example (
        copy .env.example backend\.env
        echo ✅ .env file created
        echo ⚠️  IMPORTANT: Edit backend\.env and add your Upbit API keys!
    ) else (
        echo ⚠️  .env.example not found!
    )
) else (
    echo ℹ️  .env file already exists
)

REM 8. Create admin user
echo.
echo 👤 Create Admin User
echo.
set /p CREATE_ADMIN="Do you want to create an admin user now? (y/n): "
if /i "%CREATE_ADMIN%"=="y" (
    cd backend
    python create_admin.py
    cd ..
)

echo.
echo ======================================================================
echo ✅ Setup Complete!
echo ======================================================================
echo.
echo 📍 Next Steps:
echo.
echo   1. Edit backend\.env file and add your Upbit API keys
echo.
echo   2. Start development servers:
echo      start_dev.bat
echo.
echo   3. Access the application:
echo      Frontend: http://localhost:3000
echo      API Docs: http://localhost:8000/docs
echo.
echo ======================================================================
echo ⚠️  Platform: Windows
echo ⚠️  Backend: FastAPI (Python)
echo ⚠️  Frontend: React + TypeScript
echo ======================================================================
echo.
pause
