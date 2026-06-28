import sqlite3
from datetime import date as _d
conn = sqlite3.connect("soloist.db")
c = conn.cursor()
date = _d.today().isoformat()
total = 0
for table, col in [("checkins", "checkin_date"), ("boyfriend_promises", "promise_date"), ("ledger", "entry_date")]:
    try:
        c.execute(f"DELETE FROM {table} WHERE {col} = ?", (date,))
        total += c.rowcount
    except Exception:
        pass
conn.commit()
conn.close()
print(f"Deleted rows: {total}")

