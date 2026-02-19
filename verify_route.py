
import sys
import os
import uvicorn
from fastapi import FastAPI

# Add current dir to path to find main.pyd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import app
    print("Successfully imported main.app")
except ImportError as e:
    print(f"Failed to import main: {e}")
    sys.exit(1)

found = False
for route in app.routes:
    if hasattr(route, "path") and route.path == "/api/auth/resend-verification":
        print("FOUND ROUTE: /api/auth/resend-verification")
        found = True
        break

if not found:
    print("ROUTE NOT FOUND: /api/auth/resend-verification")
    print("Available routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f" - {route.path}")
else:
    print("Route verification passed.")
