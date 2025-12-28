#!/bin/bash
# Forge Backend Startup Script (Linux/macOS)
# Sets environment variables and starts the backend server

echo "Starting Forge Backend..."
echo ""

# Set environment variables
export FORGE_DB_PATH=forge.db
export ADMIN_TOKEN=changeme
export FORGE_ENV=development

echo "Environment:"
echo "  FORGE_DB_PATH=$FORGE_DB_PATH"
echo "  ADMIN_TOKEN=$ADMIN_TOKEN"
echo "  FORGE_ENV=$FORGE_ENV"
echo ""

echo "Starting uvicorn on http://localhost:8000..."
python -m uvicorn main:app --reload --port 8000
