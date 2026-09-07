import sqlite3, os, shutil, sys

db_path = os.path.join('web', 'backend', 'instance', 'erp.db')
bak_path = db_path + '.bak'

if not os.path.exists(bak_path):
    shutil.copy2(db_path, bak_path)
    print("Backed up to", bak_path)
else:
    print("Backup already exists:", bak_path)

conn = sqlite3.connect(db_path)
try:
    rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    print("Before:", rows)
    conn.execute("DELETE FROM alembic_version")
    conn.commit()
    rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    print("After:", rows)
except Exception as e:
    print("alembic_version handling:", e)
    # table may not exist; create empty marker
    conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL); INSERT INTO alembic_version (version_num) VALUES ('')")
    conn.commit()
conn.close()
