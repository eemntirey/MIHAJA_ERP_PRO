import sqlite3
conn = sqlite3.connect(r'C:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO\erp.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'platform_config%'")
print('Tables:', [r[0] for r in c.fetchall()])
# Renommer la table
try:
    c.execute("ALTER TABLE platform_config RENAME TO platform_configs")
    conn.commit()
    print('Table renommée en platform_configs')
except Exception as e:
    print('Erreur lors du renommage:', e)
