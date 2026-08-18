from datetime import datetime, timedelta
from app import db
from app.models.abonnement import Abonnement, StatutAbonnement
from app.models.paiement import Paiement, StatutPaiement, TypePaiement
from app.security.tenant import get_current_tenant_id


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
    def create_abonnement(cls, data):
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            tenant_id = get_current_tenant_id()

        if not tenant_id:
            raise ValueError("tenant_id requis")

        abonnement = Abonnement(
            tenant_id=tenant_id,
            montant=data.get('montant'),
            devise=data.get('devise', 'MGA'),
            date_debut=data.get('date_debut') or datetime.utcnow(),
            date_fin=data.get('date_fin') or (datetime.utcnow() + timedelta(days=30)),
            statut=StatutAbonnement.EN_ATTENTE,
            methode_paiement=data.get('methode_paiement'),
            reference_paiement=data.get('reference_paiement'),
            notes=data.get('notes'),
            plan=data.get('plan', 'starter')
        )
        db.session.add(abonnement)
        db.session.flush()

        paiement = Paiement(
            tenant_id=tenant_id,
            montant=data.get('montant'),
            devise=data.get('devise', 'MGA'),
            statut=StatutPaiement.EN_ATTENTE,
            type=TypePaiement.ABONNEMENT,
            reference=data.get('reference_paiement'),
            notes=data.get('notes'),
            date_paiement=datetime.utcnow()
        )
        db.session.add(paiement)
        db.session.commit()

        return abonnement, paiement

    @classmethod
    def get_history_by_tenant(cls, tenant_id, page=1, per_page=20):
        query = Abonnement.query.filter_by(tenant_id=tenant_id, is_active=True)
        paginated = query.order_by(Abonnement.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return paginated.items, paginated.total

    @classmethod
    def get_all_subscriptions(cls, tenant_id=None, page=1, per_page=20):
        query = Abonnement.query.filter_by(is_active=True)
        if tenant_id is not None:
            query = query.filter_by(tenant_id=tenant_id)
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

        abonnement.date_debut = base_date
        abonnement.date_fin = base_date + timedelta(days=30)
        abonnement.statut = StatutAbonnement.ACTIF
        abonnement.save()

        paiement = Paiement(
            tenant_id=abonnement.tenant_id,
            montant=abonnement.montant,
            devise=abonnement.devise,
            statut=StatutPaiement.EN_ATTENTE,
            type=TypePaiement.ABONNEMENT,
            reference=f"Renouvellement {abonnement.id}",
            notes=f"Renouvellement de l'abonnement {abonnement.id}",
            date_paiement=now
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
