import sys
import os

# Add forge-os to Python path
forge_os_path = r"C:\Users\Jwmor\Desktop\Projects\vs code\forge-os"
if forge_os_path not in sys.path:
    sys.path.insert(0, forge_os_path)

# Set environment variable
os.environ["PYTHONPATH"] = forge_os_path

# Now run uvicorn
import uvicorn

if __name__ == "__main__":
    print(f"Starting Forge Backend server on http://localhost:8000")
    print(f"Python path includes: {forge_os_path}")

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
