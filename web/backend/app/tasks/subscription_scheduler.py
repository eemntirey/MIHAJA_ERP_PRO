from datetime import datetime, timedelta
from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.services.abonnement_service import AbonnementService
from app.models.subscription_audit import SubscriptionAuditTrail


def run_subscription_expiration_check():
    now = datetime.utcnow()
    abonnements_expired = Abonnement.query.filter(
        Abonnement.statut == StatutAbonnement.ACTIF,
        Abonnement.is_active == True,
        Abonnement.plan == 'pro',
        Abonnement.date_fin < (now - timedelta(days=30))
    ).all()
    results = []
    for abn in abonnements_expired:
        try:
            abn_gratuit, audit = AbonnementService.downgrade_to_free_plan(
                abn.tenant_id, trigger='automatique', user_id=None
            )
            results.append({
                'tenant_id': abn.tenant_id,
                'audit_id': audit.id,
                'status': 'retrograded',
            })
        except Exception as e:
            results.append({
                'tenant_id': abn.tenant_id,
                'status': 'error',
                'message': str(e),
            })
    return results
