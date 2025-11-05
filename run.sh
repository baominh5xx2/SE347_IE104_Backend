#!/bin/bash

# Bash script to run the backend with uv

echo "🚀 Starting AI Assistant Backend with LangGraph..."
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp ".env.example" ".env"
        echo "✅ Created .env file. Please update it with your API keys!"
        echo ""
    else
        echo "❌ .env.example not found!"
        exit 1
    fi
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed!"
    echo "📦 Install uv with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies
echo "📦 Syncing dependencies..."
uv sync

if [ $? -ne 0 ]; then
    echo "❌ Failed to sync dependencies!"
    exit 1
fi

echo "✅ Dependencies synced successfully!"
echo ""

# Run the application
echo "🏃 Running application..."
echo "📡 API will be available at: http://localhost:8000"
echo "📚 Docs available at: http://localhost:8000/docs"
echo ""

uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
