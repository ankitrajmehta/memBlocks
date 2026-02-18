#!/bin/bash
# Start the memBlocks FastAPI backend

echo "🚀 Starting memBlocks FastAPI Backend..."
echo ""

# Check if services are running
echo "Checking Docker services..."
docker-compose ps

echo ""
echo "Starting API server on http://localhost:80001"
echo "Documentation: http://localhost:80001/docs"
echo ""

# Run the backend
cd "$(dirname "$0")/.."
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 80001
