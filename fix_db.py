import sqlite3
import asyncio
import aiohttp
import sys
import os

# Add current directory to path to import net_tools if needed, though we implement simpler here
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DB_FILE = "./sql_app.db"

def migrate_db():
    print("--- Checking Database Schema ---")
    
    # Helper to connect to DB even if name varies
    db_path = DB_FILE
    if not os.path.exists(db_path):
        # Try finding it
        files = [f for f in os.listdir('.') if f.endswith('.db')]
        if files:
            db_path = files[0]
            print(f"Found database: {db_path}")
        else:
            print(f"Database file {DB_FILE} not found. Starting fresh? (Skip migration)")
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check columns in monitors table
    cursor.execute("PRAGMA table_info(monitors)")
    columns = [info[1] for info in cursor.fetchall()]
    
    tasks = [
        ("latitude", "FLOAT"),
        ("longitude", "FLOAT"),
        ("country", "VARCHAR"),
        ("city", "VARCHAR")
    ]
    
    for col, dtype in tasks:
        if col not in columns:
            print(f"Adding missing column: {col}...")
            try:
                cursor.execute(f"ALTER TABLE monitors ADD COLUMN {col} {dtype}")
                print(f"[OK] Added {col}")
            except Exception as e:
                print(f"[ERR] Failed to add {col}: {e}")
        else:
            print(f"[OK] Column {col} exists")
            
    conn.commit()
    conn.close()
    print("--- Schema Check Complete ---\n")

async def resolve_ip(target):
    import socket
    from urllib.parse import urlparse
    try:
        # Clean target if it's a URL
        hostname = target
        if "://" in target:
            try:
                parsed = urlparse(target)
                hostname = parsed.hostname or target
            except:
                pass
        
        # Resolve domain to IP first
        try:
            ip_address = socket.gethostbyname(hostname)
        except:
            ip_address = hostname
            
        url = f"http://ip-api.com/json/{ip_address}?fields=status,country,city,lat,lon,query"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data
                    else:
                        return None
    except Exception as e:
        print(f"Error checking {target}: {e}")
    return None

async def backfill_geoip():
    # Helper to connect to DB even if name varies
    db_path = DB_FILE
    if not os.path.exists(db_path):
        # Try finding it
        files = [f for f in os.listdir('.') if f.endswith('.db')]
        if files:
            db_path = files[0]
            print(f"Found database: {db_path}")
        else:
            print("No database found.")
            return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get monitors
    try:
        # First ensure columns exist or this query fails
        cursor.execute("SELECT id, name, target FROM monitors WHERE latitude IS NULL OR latitude = 0")
        monitors = cursor.fetchall()
    except Exception as e:
        print(f"Error querying monitors (Columns might be missing? Run migration first): {e}")
        conn.close()
        return
    
    if not monitors:
        print("No monitors need GeoIP update.")
        conn.close()
        return

    print(f"Found {len(monitors)} monitors to update...")
    
    for row in monitors:
        m_id, name, target = row
        print(f"Resolving location for {name} ({target})...")
        data = await resolve_ip(target)
        
        if data:
            lat = data.get('lat')
            lon = data.get('lon')
            country = data.get('country')
            city = data.get('city')
            
            print(f"  -> Found: {city}, {country} ({lat}, {lon})")
            
            cursor.execute(
                "UPDATE monitors SET latitude=?, longitude=?, country=?, city=? WHERE id=?",
                (lat, lon, country, city, m_id)
            )
        else:
            print("  -> Failed or Private IP (No public location)")
            
    conn.commit()
    conn.close()
    print("--- Backfill Complete ---")

if __name__ == "__main__":
    migrate_db()
    # Run async logic
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(backfill_geoip())
    except Exception as e:
        print(f"Async Error: {e}")
