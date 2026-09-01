from flask import current_app
from datetime import datetime
from decimal import Decimal
from app import db
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.produit import Produit
from app.models.stock import MouvementStock
from app.security.tenant import get_current_tenant_id
import random
import string


def get_sales_summary():
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def update(id, data):
    sale = get_by_id(id)
    if not sale:
        return None
    if 'date' in data and isinstance(data['date'], str):
        data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
    for key, value in data.items():
        if hasattr(sale, key) and key not in ('id', 'tenant_id', 'created_at'):
            setattr(sale, key, value)
    db.session.commit()
    return sale


def delete(id):
    sale = get_by_id(id)
    if not sale:
        return None
    sale.delete()
    return sale


def create_with_lignes(data):
    tenant_id = get_current_tenant_id()
    lignes_data = data.pop('lignes', [])
    if tenant_id:
        data['tenant_id'] = tenant_id

    if not data.get('reference'):
        prefix = 'VENT'
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = ''.join(random.choices(string.digits, k=4))
        data['reference'] = f"{prefix}-{timestamp}-{random_part}"
        # Collision avoidance via uniqueness check on reference (tenant scope).
        # We commit-flush the vente a bit later so two concurrent creations
        # will see each other's reference as taken via the DB unique index.
        attempts = 0
        while Vente.query.filter_by(reference=data['reference']).first():
            attempts += 1
            if attempts > 10:
                raise ValueError("Impossible de generer une reference unique")
            random_part = ''.join(random.choices(string.digits, k=4))
            data['reference'] = f"{prefix}-{timestamp}-{random_part}"

    if not data.get('client_id'):
        raise ValueError("Le client est requis")

    if 'date' in data and isinstance(data['date'], str):
        try:
            data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            try:
                data['date'] = datetime.fromisoformat(data['date'])
            except ValueError:
                raise ValueError("Format de date invalide (attendu YYYY-MM-DD)")

    total_ht = 0
    total_ttc = 0
    stock_errors = []
    for ligne in lignes_data:
        quantite = Decimal(str(ligne.get('quantite', 0)))
        prix_unitaire = Decimal(str(ligne.get('prix_unitaire', 0)))
        taux_tva = Decimal(str(ligne.get('taux_tva', 20)))
        remise = Decimal(str(ligne.get('remise', 0)))
        base_ht = quantite * prix_unitaire * (1 - remise / 100)
        total_ht += base_ht
        total_ttc += base_ht * (1 + taux_tva / 100)

    data['total_ht'] = total_ht
    data['total_ttc'] = total_ttc
    sale = Vente(**data)
    db.session.add(sale)
    db.session.flush()
    for ligne in lignes_data:
        produit_id = ligne.get('produit_id')
        quantite = ligne.get('quantite')
        mapped_ligne = {
            'vente_id': sale.id,
            'tenant_id': sale.tenant_id,
            'produit_id': produit_id,
            'quantite': quantite,
            'prix_unitaire_ht': ligne.get('prix_unitaire'),
            'taux_tva': ligne.get('taux_tva'),
        }
        ligne_vente = LigneVente(**mapped_ligne)
        db.session.add(ligne_vente)
        if produit_id and quantite is not None:
            qty = float(quantite)
            if qty > 0:
                tenant_id = sale.tenant_id
                # Verrouillage optimiste de la ligne produit pour eviter les
                # races conditions (deux ventes concurrentes decrémentant
                # le stock en parallele). Sur SQLite (mode dev/test),
                # with_for_update est ignore : on compense par un SELECT
                # immediat et le check de stock dans la meme transaction.
                produit_query = Produit.query.filter_by(id=produit_id)
                if tenant_id:
                    produit_query = produit_query.filter_by(tenant_id=tenant_id)
                produit = produit_query.with_for_update().first()
                if produit:
                    try:
                        qty_decimal = Decimal(str(qty))
                        if produit.quantite_stock < qty_decimal:
                            raise ValueError(f"Stock insuffisant. Disponible: {produit.quantite_stock}")
                        stock_avant = Decimal(str(produit.quantite_stock or 0))
                        produit.quantite_stock -= qty_decimal
                        stock_apres = Decimal(str(produit.quantite_stock or 0))
                        mouvement = MouvementStock(
                            produit_id=produit.id,
                            type_mouvement='sortie',
                            quantite=qty_decimal,
                            stock_avant=stock_avant,
                            stock_apres=stock_apres,
                            raison=f'Vente {sale.reference}',
                            reference=sale.reference,
                            tenant_id=produit.tenant_id,
                        )
                        db.session.add(mouvement)
                    except ValueError as e:
                        stock_errors.append(str(e))
    if stock_errors:
        db.session.rollback()
        raise ValueError("; ".join(stock_errors))
    db.session.commit()
    return sale


def get_by_client(client_id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(client_id=client_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_stats():
    try:
        tenant_id = get_current_tenant_id()
        query = Vente.query.filter_by(is_active=True)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        ventes = query.all()
        count = len(ventes)
        total = sum(float(v.total_ttc) for v in ventes if v.total_ttc is not None)
        average = total / count if count > 0 else 0
        by_status = {}
        for vente in ventes:
            statut = vente.statut
            if statut not in by_status:
                by_status[statut] = {'count': 0, 'total': 0.0}
            by_status[statut]['count'] += 1
            try:
                by_status[statut]['total'] += float(vente.total_ttc) if vente.total_ttc is not None else 0.0
            except (ValueError, TypeError):
                pass
        return {
            'total': total,
            'count': count,
            'average': average,
            'by_status': by_status
        }
    except Exception as e:
        current_app.logger.exception('Error in get_stats')
        return {
            'total': 0,
            'count': 0,
            'average': 0,
            'by_status': {}
        }
