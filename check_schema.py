
import sqlite3

def check_db():
    conn = sqlite3.connect("f:/AIO/MatEl/release/matel.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print("Columns in users table:", columns)
    conn.close()

if __name__ == "__main__":
    check_db()
