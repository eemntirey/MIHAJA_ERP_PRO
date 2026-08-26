import sqlite3, os
db = sqlite3.connect(os.path.join('web', 'backend', 'instance', 'erp.db'))
cur = db.execute("SELECT alembic_version FROM alembic_version")
print("alembic_version:", cur.fetchall())
rows = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
print("tables:", len(rows))
for r in rows:
    print("  ", r[0])
    cnt = db.execute(f"SELECT COUNT(*) FROM '{r[0]}'").fetchone()[0]
    print(f"     rows={cnt}")
