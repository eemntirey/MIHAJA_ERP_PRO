import sqlite3
c = sqlite3.connect('instance/erp.db')
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("TABLES:", tables)
print("notifications exists:", 'notifications' in tables)