# Start the Forge Backend server with proper Python path

$env:PYTHONPATH = "C:\Users\Jwmor\Desktop\Projects\vs code\forge-os"
Write-Host "Starting Forge Backend server on http://localhost:8000" -ForegroundColor Green
Write-Host "PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Cyan

& .\venv\Scripts\python.exe -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
