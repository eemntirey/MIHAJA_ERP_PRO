

from app import create_app
from app.models.tenant import Tenant
from app.models.utilisateur import Utilisateur

app = create_app()

with app.app_context():

    print("\n========== TENANTS ==========")

    tenants = Tenant.query.all()

    if not tenants:
        print("Aucun tenant trouvé.")
    else:
        for t in tenants:
            print(
                f"ID={t.id} | "
                f"Nom={t.nom} | "
                f"Slug={t.slug} | "
                f"Actif={t.is_active}"
            )

    print("\n========== UTILISATEURS ==========")

    utilisateurs = Utilisateur.query.all()

    if not utilisateurs:
        print("Aucun utilisateur trouvé.")
    else:
        for u in utilisateurs:
            print(
                f"ID={u.id} | "
                f"Email={u.email} | "
                f"Role={u.role} | "
                f"Tenant_ID={u.tenant_id}"
            )

    print("\n========== FIN ==========")
