#!/bin/bash

# PubMed MCP Server Setup Script
# This script creates a virtual environment and installs dependencies

set -e

echo "🔬 Setting up PubMed MCP Server..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies directly
echo "📚 Installing MCP CLI..."
pip install "mcp[cli]>=1.4.0"

echo "📚 Installing requests..."
pip install "requests>=2.31.0"

echo "📚 Installing python-dotenv..."
pip install "python-dotenv>=1.0.0"

echo "📚 Installing typing-extensions..."
pip install "typing-extensions>=4.0.0"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. (Optional) Configure your API key:"
echo "   cp .env.example .env"
echo "   # Edit .env with your NCBI API key and email"
echo ""
echo "3. Run the MCP server:"
echo "   python server.py"
echo ""
echo "4. To deactivate the virtual environment later:"
echo "   deactivate"