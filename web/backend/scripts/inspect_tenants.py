from app import create_app, db
from app.models.utilisateur import Utilisateur, Role
from app.models.tenant import Tenant

app = create_app()

with app.app_context():
    print('=== TENANTS ===')
    tenants = Tenant.query.all()
    for t in tenants:
        user_count = Utilisateur.query.filter(
            Utilisateur.tenant_id == t.id,
            Utilisateur.is_active == True,
        ).count()
        print(f"- {t.nom} | {t.slug} | {t.plan} | {t.statut.value} | users={user_count}")

    print('\n=== ADMINS ===')
    admins = Utilisateur.query.filter(Utilisateur.role == Role.ADMIN).all()
    for a in admins:
        print(f"- {a.username} | {a.email}")
