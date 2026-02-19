import uvicorn
import os
import sys

# Ensure this directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# This import will load the compiled main.pyd/so module
# instead of the main.py source file if the .py file is removed.
# When distributed, you should remove the original .py files.
try:
    from main import app
except ImportError as e:
    print("Error: Could not import 'main'. The application might not be built correctly.")
    print("Make sure you see 'main.pyd' (Windows) or 'main.so' (Linux/Mac) in this directory.")
    print(f"Details: {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("===========================================")
    print("   MataElang OS [Encrypted Distribution]   ")
    print("   Running in Protected Mode               ")
    print("===========================================")
    print("Available Routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f" - {route.path}")
            if route.path == "/api/auth/resend-verification":
                print("   [!!!] DEBUG: RESEND VERIFICATION ROUTE FOUND!")
    print("===========================================")
    uvicorn.run(app, host="0.0.0.0", port=8000)
