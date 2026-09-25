from datetime import datetime
from decimal import Decimal
from app import db
from app.models.commande_achat import CommandeAchat, ReceptionAchat
from app.models.ligne_achat import LigneAchat
from app.models.produit import Produit
from app.models.stock import MouvementStock
from app.security.tenant import get_current_tenant_id
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

def _gen_reference(prefix, id_val=None):
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    suffix = f'-{id_val}' if id_val else ''
    return f'{prefix}-{ts}{suffix}'

class CommandeAchatService:
    model = CommandeAchat

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('ACH')
        
        for date_field in ('date_livraison_prevue', 'date_reception', 'date_commande'):
            if date_field in data and isinstance(data[date_field], str):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field].replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    pass
        
        lignes_data = data.pop('lignes', [])
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.flush()
        total_ht = Decimal('0')
        total_ttc = Decimal('0')
        for ligne in lignes_data:
            ligne['commande_achat_id'] = instance.id
            if tenant_id:
                ligne['tenant_id'] = tenant_id
            ligne_obj = LigneAchat(**ligne)
            db.session.add(ligne_obj)
            taux_tva = Decimal(str(ligne.get('taux_tva', 20) or 0))
            total_ht += Decimal(str(ligne_obj.total_ht or 0))
            total_ttc += Decimal(str(ligne_obj.total_ht or 0)) * (Decimal('1') + taux_tva / Decimal('100'))
        instance.total_ht = total_ht
        instance.total_ttc = total_ttc
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        lignes_data = data.pop('lignes', None)
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        if lignes_data is not None:
            LigneAchat.query.filter_by(commande_achat_id=id, is_active=True).update({'is_active': False})
            total_ht = 0
            total_ttc = 0
            for ligne in lignes_data:
                ligne['commande_achat_id'] = id
                ligne['tenant_id'] = instance.tenant_id
                ligne_obj = LigneAchat(**ligne)
                db.session.add(ligne_obj)
                taux_tva = Decimal(str(ligne.get('taux_tva', 20) or 0))
                total_ht += Decimal(str(ligne_obj.total_ht or 0))
                total_ttc += Decimal(str(ligne_obj.total_ht or 0)) * (Decimal('1') + taux_tva / Decimal('100'))
            instance.total_ht = total_ht
            instance.total_ttc = total_ttc
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return True

class ReceptionAchatService:
    model = ReceptionAchat

    @classmethod
    def _get_tenant_filter(cls, query):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            query = query.filter(cls.model.tenant_id == tenant_id)
        return query

    @classmethod
    def get_all(cls, page=1, per_page=20, filters=None, order_by=None):
        query = cls.model.query.filter_by(is_active=True)
        query = cls._get_tenant_filter(query)
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(cls.model, key):
                    query = query.filter_by(**{key: value})
        if order_by:
            query = query.order_by(order_by)
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated.items, paginated.total

    @classmethod
    def get_by_id(cls, id):
        query = cls.model.query.filter_by(id=id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("tenant_id est obligatoire pour cette ressource")

        data = dict(data or {})
        commande_id = data.get('commande_achat_id')
        if not commande_id:
            raise ValueError("commande_achat_id est requis")

        commande = CommandeAchat.query.filter_by(
            id=commande_id, tenant_id=tenant_id, is_active=True
        ).first()
        if not commande:
            raise ValueError("Commande d'achat introuvable")

        lines = LigneAchat.query.filter_by(
            commande_achat_id=commande.id,
            tenant_id=tenant_id,
            is_active=True,
        ).all()
        produit_id = data.pop('produit_id', None)
        if produit_id is not None:
            try:
                produit_id = int(produit_id)
            except (TypeError, ValueError):
                raise ValueError("produit_id doit être un entier")
            line = next((row for row in lines if row.produit_id == produit_id), None)
            if not line:
                raise ValueError("Le produit ne fait pas partie de la commande")
        elif len(lines) == 1:
            line = lines[0]
            produit_id = line.produit_id
        elif len(lines) > 1:
            raise ValueError(
                "Cette commande contient plusieurs produits : produit_id est requis pour la réception"
            )
        else:
            raise ValueError("La commande ne contient aucune ligne de produit")

        try:
            quantite_recue = Decimal(str(data.get('quantite_recue')))
        except (TypeError, ValueError):
            raise ValueError("quantite_recue invalide")
        if quantite_recue <= 0:
            raise ValueError("La quantité reçue doit être supérieure à 0")

        quantite_commandee = Decimal(str(line.quantite or 0))
        existing_received = db.session.query(
            db.func.coalesce(db.func.sum(cls.model.quantite_recue), 0)
        ).filter(
            cls.model.commande_achat_id == commande.id,
            cls.model.produit_id == produit_id,
            cls.model.is_active.is_(True),
            cls.model.tenant_id == tenant_id,
        ).scalar() or 0
        remaining = quantite_commandee - Decimal(str(existing_received))
        if quantite_recue > remaining:
            raise ValueError(
                f"Quantité reçue trop élevée : reste {remaining}"
            )

        produit = Produit.query.filter_by(
            id=produit_id, tenant_id=tenant_id, is_active=True
        ).with_for_update().first()
        if not produit:
            raise ValueError("Produit introuvable")

        stock_avant = Decimal(str(produit.quantite_stock or 0))
        produit.quantite_stock = stock_avant + quantite_recue
        db.session.add(MouvementStock(
            produit_id=produit.id,
            type_mouvement='entree',
            quantite=quantite_recue,
            stock_avant=stock_avant,
            stock_apres=produit.quantite_stock,
            raison=f'Réception achat {data.get("reference") or commande.reference}',
            reference=data.get('reference') or commande.reference,
            tenant_id=tenant_id,
        ))

        data['tenant_id'] = tenant_id
        data['produit_id'] = produit_id
        data['quantite_recue'] = quantite_recue
        data['quantite_commandee'] = quantite_commandee
        data['ecart'] = quantite_recue - quantite_commandee
        if not data.get('reference'):
            data['reference'] = _gen_reference('REC')

        instance = cls.model(**data)
        db.session.add(instance)

        total_received = Decimal(str(existing_received)) + quantite_recue
        if total_received >= quantite_commandee:
            commande.statut = 'recue'
        else:
            commande.statut = 'partiellement_recue'

        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Erreur d'intégrité: {str(e.orig)}")
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return True
