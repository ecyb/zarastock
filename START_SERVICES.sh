#!/bin/bash
# Quick start script for Zara Stock Checker

echo "🚀 Starting Zara Stock Checker Services"
echo "========================================"
echo ""

# Check if Docker is running
if docker info > /dev/null 2>&1; then
    echo "✅ Docker is running"
    echo "Starting services with Docker Compose..."
    docker compose up -d
    echo ""
    echo "✅ Services started!"
    echo "View logs: docker compose logs -f"
    echo "Stop services: docker compose down"
else
    echo "❌ Docker is not running"
    echo ""
    echo "Please start Docker Desktop first, then run:"
    echo "  docker compose up -d"
    echo ""
    echo "Or run manually in two terminals:"
    echo "  Terminal 1: python telegram_bot.py"
    echo "  Terminal 2: python run_and_notify.py"
fi

