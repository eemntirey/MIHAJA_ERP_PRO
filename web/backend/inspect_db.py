import sqlite3

db = sqlite3.connect(r'instance\erp.db')
cur = db.cursor()
tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print('tables:', sorted(tabs))
print('has alembic_version:', 'alembic_version' in tabs)
if 'alembic_version' in tabs:
    print('alembic_version rows:', cur.execute('SELECT * FROM alembic_version').fetchall())
try:
    cols = [r[1] for r in cur.execute('PRAGMA table_info(ventes)')]
    print('ventes cols:', cols)
except Exception as e:
    print('ventes err', e)
cur.close()
