"""
DeployGuard Launcher
Run this script to start the local Flask backend and frontend server.
Command: python run.py
"""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import create_app

if __name__ == "__main__":
    app = create_app()
    host = app.config.get("HOST", "127.0.0.1")
    port = app.config.get("PORT", 5000)
    print("=" * 60)
    print(" DeployGuard MVP Platform")
    print(f" Web UI & Dashboard: http://{host}:{port}/")
    print(f" API Health Check:   http://{host}:{port}/api/health")
    print("=" * 60)
    app.run(host=host, port=port, debug=True)
