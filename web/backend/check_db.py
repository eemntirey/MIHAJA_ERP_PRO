import sqlite3

conn = sqlite3.connect('erp.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f'{len(tables)} tables')
for t in tables:
    print(f'  - {t[0]}')
conn.close()
