@echo off
echo Starting Forge Backend server on http://localhost:8000
set PYTHONPATH=C:\Users\Jwmor\Desktop\Projects\vs code\forge-os
.\venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
