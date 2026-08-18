from app import create_app, db
from app.models.tenant import Tenant

app = create_app()

with app.app_context():
    tenants = Tenant.query.all()
    for t in tenants:
        print(t.id, t.slug, t.is_active, t.statut)
