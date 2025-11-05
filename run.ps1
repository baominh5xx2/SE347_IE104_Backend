# PowerShell script to run the backend with uv

Write-Host "🚀 Starting AI Assistant Backend with LangGraph..." -ForegroundColor Green
Write-Host ""

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ Created .env file. Please update it with your API keys!" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "❌ .env.example not found!" -ForegroundColor Red
        exit 1
    }
}

# Check if uv is installed
if (-Not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uv is not installed!" -ForegroundColor Red
    Write-Host "📦 Install uv with: irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor Yellow
    exit 1
}

# Sync dependencies
Write-Host "📦 Syncing dependencies..." -ForegroundColor Cyan
uv sync

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to sync dependencies!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Dependencies synced successfully!" -ForegroundColor Green
Write-Host ""

# Run the application
Write-Host "🏃 Running application..." -ForegroundColor Cyan
Write-Host "📡 API will be available at: http://localhost:8000" -ForegroundColor Blue
Write-Host "📚 Docs available at: http://localhost:8000/docs" -ForegroundColor Blue
Write-Host ""

uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
