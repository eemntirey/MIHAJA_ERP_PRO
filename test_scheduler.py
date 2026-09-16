import sys, os
sys.path.insert(0, 'C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend')
os.environ['FLASK_APP'] = 'app'
import dotenv
dotenv.load_dotenv('C:/Users/eemntirey/Desktop/ERP_MM/MIHAJA_ERP_PRO/web/backend/.env')
from app import create_app
app = create_app()
with app.app_context():
    from datetime import datetime, timedelta
    from app import db
    from app.models.abonnement import Abonnement, StatutAbonnement
    from app.models.tenant import Tenant
    from app.tasks.subscription_scheduler import run_subscription_expiration_check
    # Créer un tenant Pro expiré depuis 31 jours
    tenant = Tenant(nom='TestSched2', slug='test-sched2', plan='pro', is_active=True, statut='actif')
    db.session.add(tenant)
    db.session.commit()
    abn = Abonnement(
        tenant_id=tenant.id,
        montant=15000,
        devise='MGA',
        date_debut=datetime.utcnow() - timedelta(days=60),
        date_fin=datetime.utcnow() - timedelta(days=31),
        statut=StatutAbonnement.ACTIF,
        plan='pro',
    )
    db.session.add(abn)
    db.session.commit()
    # Exécuter le scheduler
    results = run_subscription_expiration_check()
    print('SCHEDULER RESULT:', results)
    from app.models.subscription_audit import SubscriptionAuditTrail
    audit = SubscriptionAuditTrail.query.filter_by(tenant_id=tenant.id, declencheur='automatique').first()
    print('AUDIT FOUND:', audit.id if audit else None, audit.nouveau_plan if audit else None)
    # Nettoyer
    db.session.delete(abn)
    if audit:
        db.session.delete(audit)
    db.session.delete(tenant)
    db.session.commit()
