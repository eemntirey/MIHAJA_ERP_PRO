from datetime import datetime, timedelta
from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.services.abonnement_service import AbonnementService
from app.models.subscription_audit import SubscriptionAuditTrail
from app.services.notification_service import create_notification


def run_subscription_reminders():
    now = datetime.utcnow()
    abonnements_grace = Abonnement.query.filter(
        Abonnement.statut == StatutAbonnement.ACTIF,
        Abonnement.is_active == True,
        Abonnement.plan == 'pro',
        Abonnement.date_fin <= now + timedelta(days=30),
    ).all()
    results = []
    for abn in abonnements_grace:
        try:
            from app.models.tenant import Tenant
            tenant = db.session.get(Tenant, abn.tenant_id)
            if tenant:
                from app.models.notification import Notification
                last_notif = Notification.query.filter(
                    Notification.tenant_id == abn.tenant_id,
                    Notification.type == 'subscription_reminder',
                    Notification.is_active == True,
                ).order_by(Notification.created_at.desc()).first()
                if last_notif:
                    days_since = (now - last_notif.created_at).days
                    if days_since < 3:
                        continue  # Moins de 3 jours écoulés
                days_left = max(0, (abn.date_fin - now).days) if abn.date_fin > now else 0
                create_notification(
                    tenant_id=abn.tenant_id,
                    title='Rappel abonnement : période de grâce',
                    message=f"Période de grâce en cours : il vous reste {days_left} jours pour régler votre abonnement. Après ce délai, le compte passera au plan Gratuit.",
                    notif_type='subscription_reminder',
                    link='/subscriptions',
                    commit=True,
                )
                results.append({'tenant_id': abn.tenant_id, 'status': 'reminder_sent'})
        except Exception as e:
            results.append({'tenant_id': abn.tenant_id, 'status': 'error', 'message': str(e)})
    return results


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
            abn_gratuit, audit = AbonnementService.downgrade_to_gratuit_plan(
                abn.tenant_id, trigger='automatique', user_id=None, target_plan='gratuit'
            )
            results.append({
                'tenant_id': abn.tenant_id,
                'audit_id': audit.id,
                'status': 'retrograded',
                'nouveau_plan': 'gratuit',
            })
        except Exception as e:
            results.append({
                'tenant_id': abn.tenant_id,
                'status': 'error',
                'message': str(e),
            })
    return results
