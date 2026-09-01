import sqlite3

db_path = r'C:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO\web\backend\erp.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

import sys
sys.path.insert(0, r'C:\Users\eemntirey\Desktop\ERP_MM\MIHAJA_ERP_PRO\web\backend')

from app.models.utilisateur import Utilisateur
from app.models.abonnement import Abonnement
from app.models.tenant import Tenant
from app.models.paiement import Paiement
from app.models.role_permission import RoleModel, Permission

models = [Utilisateur, Abonnement, Tenant, Paiement, RoleModel, Permission]

for model in models:
    table_name = model.__tablename__
    if table_name not in tables:
        print(f'Table {table_name} MISSING in DB')
        continue
    
    cursor.execute(f'PRAGMA table_info({table_name})')
    db_cols = set(row[1] for row in cursor.fetchall())
    model_cols = set(c.name for c in model.__table__.columns)
    
    missing = model_cols - db_cols
    extra = db_cols - model_cols
    if missing or extra:
        print(f'\n{table_name}:')
        if missing:
            print(f'  Missing: {missing}')
        if extra:
            print(f'  Extra: {extra}')

conn.close()
