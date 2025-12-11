@echo off
echo Starting Forge Console Backend...
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies if needed
echo Checking dependencies...
pip install -q -r requirements.txt

REM Start the server
echo.
echo ========================================
echo Backend running at: http://localhost:8000
echo API docs at: http://localhost:8000/api/docs
echo Press CTRL+C to stop
echo ========================================
echo.

uvicorn src.main:app --reload --port 8000
