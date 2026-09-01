import sqlite3
from datetime import datetime, timedelta

# Connect to the database
conn = sqlite3.connect('erp.db')
cursor = conn.cursor()

# Check if the tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables: {tables}")

# Check if the tenants table exists
if 'tenants' in tables:
    cursor.execute("SELECT id, nom, plan FROM tenants")
    tenants = cursor.fetchall()
    print(f"\nTenants: {len(tenants)}")
    for t in tenants:
        print(f"  ID={t[0]}, Nom={t[1]}, Plan={t[2]}")

    # Check if the abonnements table exists
    if 'abonnements' in tables:
        cursor.execute("SELECT id, tenant_id, statut, date_fin, is_active, modules FROM abonnements")
        abonnements = cursor.fetchall()
        print(f"\nAbonnements: {len(abonnements)}")
        for a in abonnements:
            print(f"  ID={a[0]}, Tenant={a[1]}, Statut={a[2]}, Date_fin={a[3]}, Is_active={a[4]}, Modules={a[5]}")

        # Update all abonnements to be active with a future date_fin
        new_date_fin = (datetime.utcnow() + timedelta(days=365)).isoformat()
        cursor.execute("""
            UPDATE abonnements
            SET statut = 'actif',
                date_debut = ?,
                date_fin = ?,
                is_active = 1,
                modules = 'dashboard,produits,clients,ventes,factures,paiements,catalogue,stocks,rh,documents,comptabilite,livraison,ia,achats'
            WHERE statut != 'actif' OR date_fin < ? OR is_active != 1
        """, (datetime.utcnow().isoformat(), new_date_fin, datetime.utcnow().isoformat()))

        print(f"\nUpdated {cursor.rowcount} abonnements")

        # Verify the updates
        cursor.execute("SELECT id, tenant_id, statut, date_fin, is_active, modules FROM abonnements")
        abonnements = cursor.fetchall()
        print(f"\nAbonnements after update: {len(abonnements)}")
        for a in abonnements:
            print(f"  ID={a[0]}, Tenant={a[1]}, Statut={a[2]}, Date_fin={a[3]}, Is_active={a[4]}, Modules={a[5]}")
    else:
        print("Abonnements table does not exist")
else:
    print("Tenants table does not exist")

conn.commit()
conn.close()
print("\nDone!")
