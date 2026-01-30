#!/bin/bash

# =============================================================================
# Quick Start Script for Self-Evolving Trading System
# =============================================================================

echo "======================================================================"
echo "🚀 Self-Evolving Trading System - Quick Start"
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

# Create virtual environment (optional but recommended)
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

echo ""
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies!"
    exit 1
fi

echo "✅ Dependencies installed successfully"
echo ""

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Please edit .env file and add your Bithumb API keys!"
    echo ""
    echo "   vim .env"
    echo "   or"
    echo "   nano .env"
    echo ""
else
    echo "ℹ️  .env file already exists"
fi

echo ""
echo "======================================================================"
echo "✅ Setup Complete!"
echo "======================================================================"
echo ""
echo "📍 Next Steps:"
echo ""
echo "   1. Edit .env file and add your API keys:"
echo "      $ nano .env"
echo ""
echo "   2. Run the dashboard:"
echo "      $ streamlit run app.py"
echo ""
echo "   3. Click 'START' button in the sidebar to begin trading"
echo ""
echo "======================================================================"
echo "⚠️  IMPORTANT: The bot is in DEMO mode by default."
echo "    Edit trading_bot.py to enable real trading (at your own risk!)"
echo "======================================================================"
