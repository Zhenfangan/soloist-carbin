import sqlite3
for db in ["app_data.db", "soloist.db"]:
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("SELECT checkin_date, period, status FROM checkins WHERE checkin_date = '2026-06-15'")
        rows = c.fetchall()
        print(db, "->", rows)
        conn.close()
    except Exception as e:
        print(db, "error:", e)
