@echo off
REM Forge Backend Startup Script (Windows)
REM Sets environment variables and starts the backend server

echo Starting Forge Backend...
echo.

REM Set environment variables
set FORGE_DB_PATH=forge.db
set ADMIN_TOKEN=changeme
set FORGE_ENV=development

echo Environment:
echo   FORGE_DB_PATH=%FORGE_DB_PATH%
echo   ADMIN_TOKEN=%ADMIN_TOKEN%
echo   FORGE_ENV=%FORGE_ENV%
echo.

echo Starting uvicorn on http://localhost:8000...
python -m uvicorn main:app --reload --port 8000
