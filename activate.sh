#!/bin/bash
# Activation script for Google Drive Photo Sync development environment

echo "🚀 Activating Google Drive Photo Sync development environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

echo "✅ Development environment ready!"
echo ""
echo "🔧 Available commands:"
echo "  python __main__.py --help          # Show CLI help"
echo "  python -m unittest discover -v     # Run all tests"
echo "  deactivate                         # Exit virtual environment"
echo ""
echo "📝 Before running the sync tool:"
echo "  1. Download credentials.json from Google Cloud Console"
echo "  2. Place it in the project root directory"
echo ""
echo "🎯 Example usage:"
echo "  python __main__.py 1BcDefGhIjKlMnOp --album-name 'My Photos' --verbose"