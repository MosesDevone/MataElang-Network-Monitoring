
import sys
import os

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import User, UserRole

def promote_user(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"[-] User with email {email} not found.")
            return

        user.role = UserRole.HEAD_ADMIN
        db.commit()
        print(f"[+] User {user.username} ({user.email}) has been promoted to HEAD_ADMIN.")
        print("[+] You can now access the User Management menu in the dashboard Sidebar.")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python promote_user.py <email>")
        print("Example: python promote_user.py admin@example.com")
        sys.exit(1)
    
    promote_user(sys.argv[1])
