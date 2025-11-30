import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent.parent / "aqi.db"

def ensure():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS measurements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT,
        timestamp TEXT,
        aqi INTEGER,
        pm25 REAL,
        pm10 REAL
    )""")
    conn.commit()
    conn.close()

def save_measurement(city, ts_iso, aqi=None, pm25=None, pm10=None):
    ensure()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO measurements(city, timestamp, aqi, pm25, pm10) VALUES (?,?,?,?,?)",
                (city, ts_iso, aqi, pm25, pm10))
    conn.commit()
    conn.close()

def get_top_cities(limit=10):
    ensure()
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT city, MAX(COALESCE(aqi,0)) as aqi FROM measurements GROUP BY city ORDER BY aqi DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"city":r[0], "aqi": r[1]} for r in rows]
