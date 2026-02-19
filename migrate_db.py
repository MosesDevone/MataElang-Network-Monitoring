
import sqlite3

def add_columns():
    db_path = "f:/AIO/MatEl/release/matel.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add avatar_url column if not exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_url VARCHAR")
            print("[+] Added avatar_url column")
        except sqlite3.OperationalError:
            print("[-] avatar_url column already exists or error")

        # Add bio column if not exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN bio VARCHAR")
            print("[+] Added bio column")
        except sqlite3.OperationalError:
            print("[-] bio column already exists or error")
            
        # Add reset_token column if not exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN reset_token VARCHAR")
            print("[+] Added reset_token column")
        except sqlite3.OperationalError:
            print("[-] reset_token column already exists or error")

        conn.commit()
        conn.close()
        print("Database migration completed.")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    add_columns()
