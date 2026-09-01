from datetime import datetime, timedelta
from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.models.tenant import Tenant, StatutTenant
from app.security.tenant import get_current_tenant_id
from app.security.plans import apply_plan_to_abonnement, get_plan_duration_days, get_plan_price, is_unlimited
from app.services.papi.payment import resolve_payment_provider


class AbonnementService:

    @classmethod
    def get_active_by_tenant(cls, tenant_id):
        now = datetime.utcnow()
        return Abonnement.query.filter(
            Abonnement.tenant_id == tenant_id,
            Abonnement.statut == StatutAbonnement.ACTIF,
            Abonnement.date_fin > now,
            Abonnement.is_active == True
        ).first()

    @classmethod
    def activate_free_plan(cls, tenant_id, plan='gratuit'):
        tenant = db.session.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant non trouve")

        now = datetime.utcnow()
        duree_jours = get_plan_duration_days(plan)
        if is_unlimited(duree_jours):
            date_fin = now + timedelta(days=365 * 99)  # ~9999 ans = illimité
        else:
            date_fin = now + timedelta(days=duree_jours)

        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=0,
            devise='MGA',
            date_debut=now,
            date_fin=date_fin,
            statut=StatutAbonnement.ACTIF,
            plan=plan,
        )
        apply_plan_to_abonnement(abonnement, plan)
        db.session.add(abonnement)
        db.session.flush()

        tenant.statut = StatutTenant.ACTIF
        tenant.is_active = True
        tenant.plan = plan
        tenant.date_abonnement = now
        db.session.add(tenant)
        db.session.commit()

        return abonnement

    @classmethod
    def create_abonnement(cls, data):
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            tenant_id = get_current_tenant_id()

        if not tenant_id:
            raise ValueError("tenant_id requis")

        plan = data.get('plan', 'starter')

        if plan == 'gratuit':
            return cls.activate_free_plan(tenant_id, plan), None

        duree_jours = get_plan_duration_days(plan)
        now = datetime.utcnow()
        if is_unlimited(duree_jours):
            date_fin = now + timedelta(days=365 * 99)
        else:
            date_fin = now + timedelta(days=duree_jours)

        montant_officiel = get_plan_price(plan)
        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=montant_officiel,
            devise=data.get('devise', 'MGA'),
            date_debut=data.get('date_debut') or now,
            date_fin=data.get('date_fin') or date_fin,
            statut=StatutAbonnement.EN_ATTENTE,
            methode_paiement=data.get('methode_paiement'),
            reference_paiement=data.get('reference_paiement'),
            notes=data.get('notes'),
            plan=plan
        )
        apply_plan_to_abonnement(abonnement, abonnement.plan)
        db.session.add(abonnement)
        db.session.flush()

        provider, payment_method = resolve_payment_provider(data.get('methode_paiement'))

        paiement = Paiement(
            tenant_id=tenant_id,
            subscription_id=abonnement.id,
            montant=montant_officiel,
            devise=data.get('devise', 'MGA'),
            statut=StatutPaiement.EN_ATTENTE,
            type=TypePaiement.ABONNEMENT,
            provider=provider,
            payment_method=payment_method,
            reference=data.get('reference_paiement'),
            notes=data.get('notes'),
        )
        db.session.add(paiement)
        db.session.commit()

        return abonnement, paiement

    @classmethod
    def get_history_by_tenant(cls, tenant_id, page=1, per_page=20):
        query = Abonnement.query.filter_by(tenant_id=tenant_id)
        paginated = query.order_by(Abonnement.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return paginated.items, paginated.total

    @classmethod
    def get_all_subscriptions(cls, tenant_id=None, page=1, per_page=20,
                              statut=None, plan=None):
        query = Abonnement.query.join(Tenant, Abonnement.tenant_id == Tenant.id)
        if tenant_id is not None:
            query = query.filter(Tenant.id == tenant_id)
        if statut:
            query = query.filter(Abonnement.statut == statut)
        if plan:
            query = query.filter(Abonnement.plan == plan)
        query = query.filter(Tenant.is_active == True)
        paginated = query.order_by(Abonnement.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return paginated.items, paginated.total

    @classmethod
    def renew_subscription(cls, abonnement_id):
        abonnement = Abonnement.query.filter_by(id=abonnement_id, is_active=True).first()
        if not abonnement:
            return None

        now = datetime.utcnow()
        if abonnement.date_fin and abonnement.date_fin > now:
            base_date = abonnement.date_fin
        else:
            base_date = now

        duree_jours = get_plan_duration_days(abonnement.plan)
        if is_unlimited(duree_jours):
            date_fin = base_date + timedelta(days=365 * 99)
        else:
            date_fin = base_date + timedelta(days=duree_jours)

        abonnement.date_debut = base_date
        abonnement.date_fin = date_fin
        abonnement.statut = StatutAbonnement.ACTIF
        apply_plan_to_abonnement(abonnement, abonnement.plan)
        abonnement.save()

        provider, payment_method = resolve_payment_provider(abonnement.methode_paiement)

        paiement = Paiement(
            tenant_id=abonnement.tenant_id,
            subscription_id=abonnement.id,
            montant=abonnement.montant or get_plan_price(abonnement.plan),
            devise=abonnement.devise,
            statut=StatutPaiement.EN_ATTENTE,
            type=TypePaiement.ABONNEMENT,
            provider=provider,
            payment_method=payment_method,
            reference=f"Renouvellement {abonnement.id}",
            notes=f"Renouvellement de l'abonnement {abonnement.id}",
        )
        db.session.add(paiement)
        db.session.commit()

        return abonnement, paiement

    @classmethod
    def cancel_subscription(cls, abonnement_id):
        abonnement = Abonnement.query.filter_by(id=abonnement_id, is_active=True).first()
        if not abonnement:
            return None
        abonnement.statut = StatutAbonnement.ANNULE
        abonnement.save()
        return abonnement
