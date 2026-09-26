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
    def _validate_tenant_references(cls, tenant_id, fournisseur_id=None, lignes=None):
        """Empêche toute commande d'achat de référencer un autre tenant."""
        if fournisseur_id is not None:
            from app.models.fournisseur import Fournisseur
            fournisseur = Fournisseur.query.filter_by(
                id=fournisseur_id,
                tenant_id=tenant_id,
                is_active=True,
            ).first()
            if not fournisseur:
                raise ValueError("Fournisseur introuvable pour ce tenant")

        for ligne in lignes or []:
            produit_id = ligne.get('produit_id')
            if produit_id is None:
                raise ValueError("produit_id est requis pour chaque ligne")
            try:
                produit_id = int(produit_id)
            except (TypeError, ValueError):
                raise ValueError("produit_id doit être un entier")
            produit = Produit.query.filter_by(
                id=produit_id,
                tenant_id=tenant_id,
                is_active=True,
            ).first()
            if not produit:
                raise ValueError(f"Produit id={produit_id} introuvable pour ce tenant")

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
        data['tenant_id'] = tenant_id
        if not data.get('reference'):
            data['reference'] = _gen_reference('ACH')

        lignes_data = data.get('lignes', [])
        if not isinstance(lignes_data, list):
            raise ValueError("lignes doit être une liste")
        cls._validate_tenant_references(
            tenant_id,
            data.get('fournisseur_id'),
            lignes_data,
        )

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
        if lignes_data is not None and not isinstance(lignes_data, list):
            raise ValueError("lignes doit être une liste")
        tenant_id = instance.tenant_id
        if 'fournisseur_id' in data:
            try:
                fournisseur_id = int(data.get('fournisseur_id'))
            except (TypeError, ValueError):
                raise ValueError("fournisseur_id doit être un entier")
            cls._validate_tenant_references(tenant_id, fournisseur_id, None)
        if lignes_data is not None:
            cls._validate_tenant_references(tenant_id, None, lignes_data)
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at'):
                setattr(instance, key, value)
        if lignes_data is not None:
            active_receptions = ReceptionAchat.query.filter_by(
                commande_achat_id=id, tenant_id=instance.tenant_id, is_active=True
            ).count()
            if active_receptions:
                raise ValueError(
                    "Impossible de modifier les lignes d'une commande ayant déjà des réceptions"
                )
            LigneAchat.query.filter_by(commande_achat_id=id, is_active=True).update({'is_active': False})
            total_ht = Decimal('0')
            total_ttc = Decimal('0')
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
        if ReceptionAchat.query.filter_by(
            commande_achat_id=id, tenant_id=instance.tenant_id, is_active=True
        ).count():
            raise ValueError("Impossible de supprimer une commande ayant des réceptions")
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

        cls._refresh_commande_status(commande)

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
    def _refresh_commande_status(cls, commande):
        lines = LigneAchat.query.filter_by(
            commande_achat_id=commande.id,
            tenant_id=commande.tenant_id,
            is_active=True,
        ).all()
        if not lines:
            return
        received_rows = db.session.query(
            cls.model.produit_id,
            db.func.coalesce(db.func.sum(cls.model.quantite_recue), 0),
        ).filter(
            cls.model.commande_achat_id == commande.id,
            cls.model.tenant_id == commande.tenant_id,
            cls.model.is_active.is_(True),
        ).group_by(cls.model.produit_id).all()
        received = {pid: Decimal(str(qty or 0)) for pid, qty in received_rows}
        complete = all(
            received.get(line.produit_id, Decimal('0')) >= Decimal(str(line.quantite or 0))
            for line in lines
        )
        any_received = any(received.get(line.produit_id, Decimal('0')) > 0 for line in lines)
        if complete:
            commande.statut = 'recue'
        elif any_received:
            commande.statut = 'partiellement_recue'

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        data = dict(data or {})
        if any(key in data for key in ('commande_achat_id', 'produit_id', 'quantite_commandee')):
            raise ValueError("Le rattachement produit/commande d'une réception est immutable")

        if 'quantite_recue' in data:
            try:
                new_qty = Decimal(str(data['quantite_recue']))
            except (TypeError, ValueError):
                raise ValueError("quantite_recue invalide")
            if new_qty <= 0:
                raise ValueError("La quantité reçue doit être supérieure à 0")

            commande = instance.commande_achat
            line = LigneAchat.query.filter_by(
                commande_achat_id=commande.id,
                produit_id=instance.produit_id,
                tenant_id=instance.tenant_id,
                is_active=True,
            ).first()
            if not line:
                raise ValueError("La ligne d'achat liée à la réception est introuvable")

            deja_recu = db.session.query(
                db.func.coalesce(db.func.sum(cls.model.quantite_recue), 0)
            ).filter(
                cls.model.commande_achat_id == commande.id,
                cls.model.produit_id == instance.produit_id,
                cls.model.tenant_id == instance.tenant_id,
                cls.model.is_active.is_(True),
                cls.model.id != instance.id,
            ).scalar() or 0
            max_qty = Decimal(str(line.quantite or 0)) - Decimal(str(deja_recu))
            if new_qty > max_qty:
                raise ValueError(f"Quantité reçue trop élevée : reste {max_qty}")

            produit = Produit.query.filter_by(
                id=instance.produit_id,
                tenant_id=instance.tenant_id,
                is_active=True,
            ).with_for_update().first()
            if not produit:
                raise ValueError("Produit introuvable")

            old_qty = Decimal(str(instance.quantite_recue or 0))
            delta = new_qty - old_qty
            stock_avant = Decimal(str(produit.quantite_stock or 0))
            if delta < 0 and stock_avant < -delta:
                raise ValueError("Stock insuffisant pour réduire cette réception")
            produit.quantite_stock = stock_avant + delta

            if delta != 0:
                db.session.add(MouvementStock(
                    produit_id=produit.id,
                    type_mouvement='entree' if delta > 0 else 'sortie',
                    quantite=abs(delta),
                    stock_avant=stock_avant,
                    stock_apres=produit.quantite_stock,
                    raison=f'Correction réception {instance.reference}',
                    reference=instance.reference,
                    tenant_id=instance.tenant_id,
                ))

            instance.quantite_recue = new_qty
            instance.ecart = new_qty - Decimal(str(instance.quantite_commandee or 0))

        for key, value in data.items():
            if key in ('quantite_recue', 'commande_achat_id', 'produit_id', 'quantite_commandee'):
                continue
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at', 'is_active'):
                setattr(instance, key, value)

        cls._refresh_commande_status(instance.commande_achat)
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

        produit = Produit.query.filter_by(
            id=instance.produit_id,
            tenant_id=instance.tenant_id,
            is_active=True,
        ).with_for_update().first()
        if not produit:
            raise ValueError("Produit introuvable")

        qty = Decimal(str(instance.quantite_recue or 0))
        stock_avant = Decimal(str(produit.quantite_stock or 0))
        if stock_avant < qty:
            raise ValueError(
                "Impossible d'annuler la réception : le stock disponible est inférieur à la quantité reçue"
            )
        produit.quantite_stock = stock_avant - qty
        db.session.add(MouvementStock(
            produit_id=produit.id,
            type_mouvement='sortie',
            quantite=qty,
            stock_avant=stock_avant,
            stock_apres=produit.quantite_stock,
            raison=f'Annulation réception {instance.reference}',
            reference=instance.reference,
            tenant_id=instance.tenant_id,
        ))
        commande = instance.commande_achat
        instance.is_active = False
        cls._refresh_commande_status(commande)
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise ValueError(f"Erreur de base de données: {str(e)}")
        return True

