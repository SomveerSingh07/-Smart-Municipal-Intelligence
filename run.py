import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

def main():
    print("=" * 65)
    print(" Smart Municipal Complaint Intelligence Platform")
    print("=" * 65)
    
    # Change working directory to backend
    os.chdir(BACKEND_DIR)
    
    # Check if dependencies installed
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
    except ImportError:
        print("[*] Installing required backend dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    print("\n[+] Starting FastAPI server with AI, GIS, RAG, and Web UI...")
    print("[+] Citizen Portal & Admin Dashboard: http://localhost:8000")
    print("[+] Interactive Swagger API Docs:      http://localhost:8000/docs")
    print("[+] OpenAPI JSON Specification:       http://localhost:8000/api/v1/openapi.json\n")

    try:
        import uvicorn
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=str(BACKEND_DIR))
    except KeyboardInterrupt:
        print("\n[*] Server shutdown gracefully.")

if __name__ == "__main__":
    main()
