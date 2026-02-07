#!/bin/bash

# =============================================================================
# Setup Script for Self-Evolving Trading System (macOS/Linux)
# =============================================================================

echo "======================================================================"
echo "🚀 Self-Evolving Trading System - Setup"
echo "======================================================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

echo "✅ Python is installed"
echo ""

# Check Node.js
echo "📋 Checking Node.js..."
node --version

if [ $? -ne 0 ]; then
    echo "❌ Node.js is not installed!"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js is installed"
echo ""

# Check Conda (Optional)
if command -v conda &> /dev/null; then
    echo "✅ Conda found - You can use: conda activate upBit"
    USE_CONDA=1
else
    echo "ℹ️  Conda not found - Using pip venv instead"
    USE_CONDA=0
fi

echo ""

# Create virtual environment (if not using Conda)
if [ $USE_CONDA -eq 0 ]; then
    if [ ! -d "venv" ]; then
        echo "🔨 Creating virtual environment..."
        python3 -m venv venv
        echo "✅ Virtual environment created"
    else
        echo "ℹ️  Virtual environment already exists"
    fi

    echo ""
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
else
    echo "ℹ️  Using Conda environment 'upBit'"
    echo "To activate: conda activate upBit"
fi

echo ""

# Install Backend Dependencies
echo "📦 Installing Backend dependencies..."
pip install --upgrade pip

if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install backend dependencies!"
        exit 1
    fi

    echo "✅ Backend dependencies installed successfully"
else
    echo "⚠️  backend/requirements.txt not found!"
fi

echo ""

# Install Frontend Dependencies
echo "📦 Installing Frontend dependencies..."
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    npm install

    if [ $? -ne 0 ]; then
        echo "❌ Failed to install frontend dependencies!"
        exit 1
    fi

    echo "✅ Frontend dependencies installed successfully"
    cd ..
else
    echo "⚠️  frontend directory not found!"
fi

echo ""

# Create .env file if not exists
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example backend/.env
        echo "✅ .env file created"
        echo "⚠️  IMPORTANT: Please edit backend/.env and add your Upbit API keys!"
        echo ""
        echo "   vim backend/.env"
        echo "   or"
        echo "   nano backend/.env"
    else
        echo "⚠️  .env.example not found!"
    fi
else
    echo "ℹ️  .env file already exists"
fi

echo ""

# Create admin user
echo "👤 Create Admin User"
echo ""
read -p "Do you want to create an admin user now? (y/n): " CREATE_ADMIN

if [ "$CREATE_ADMIN" = "y" ] || [ "$CREATE_ADMIN" = "Y" ]; then
    cd backend
    python3 create_admin.py
    cd ..
fi

echo ""
echo "======================================================================"
echo "✅ Setup Complete!"
echo "======================================================================"
echo ""
echo "📍 Next Steps:"
echo ""
echo "   1. Edit backend/.env file and add your Upbit API keys:"
echo "      $ nano backend/.env"
echo ""
echo "   2. Start development servers:"
echo "      $ ./start_dev.sh"
echo ""
echo "   3. Access the application:"
echo "      Frontend: http://localhost:3000"
echo "      API Docs: http://localhost:8000/docs"
echo ""
echo "======================================================================"
echo "⚠️  Platform: macOS/Linux"
echo "⚠️  Backend: FastAPI (Python)"
echo "⚠️  Frontend: React + TypeScript"
echo "======================================================================"
echo ""
