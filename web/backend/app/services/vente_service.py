from flask import current_app
from datetime import datetime
from decimal import Decimal
from app import db
from sqlalchemy.orm import joinedload
from app.models.vente import Vente
from app.models.ligne_vente import LigneVente
from app.models.produit import Produit
from app.models.stock import MouvementStock
from app.models.client import Client
from app.security.tenant import get_current_tenant_id
import random
import string

TYPES_GROS = ('grossiste', 'semi_grossiste', 'revendeur')

TYPE_VENTE_VALIDES = ('gros', 'detail')

_NIVEAUX_PRIX = {
    'grossiste': 'prix_grossiste',
    'semi_grossiste': 'prix_demi_gros',
    'revendeur': 'prix_revendeur',
}

_REPLI_GROS = ('prix_revendeur', 'prix_demi_gros', 'prix_grossiste', 'prix_vente_ht')


def derive_type_vente(client_type):
    return 'gros' if client_type in TYPES_GROS else 'detail'


def _prix_field_effectif(type_vente, client_type):
    if type_vente == 'gros':
        return _NIVEAUX_PRIX.get(client_type, 'prix_grossiste')
    return 'prix_vente_ht'


def _resolve_prix_unitaire(produit, prix_field, repli):
    for field in (prix_field,) + tuple(repli):
        value = getattr(produit, field, None)
        if value is not None:
            return Decimal(str(value))
    return Decimal('0')


def _prepare_sale_line(ligne, tenant_id, prix_field, repli):
    """Normalise une ligne de vente et calcule ses montants en Decimal."""
    produit_id = ligne.get('produit_id')
    produit = None
    if produit_id:
        query = Produit.query.filter_by(id=produit_id)
        if tenant_id:
            query = query.filter_by(tenant_id=tenant_id)
        produit = query.first()
        if not produit:
            raise ValueError(f"Produit id={produit_id} introuvable")
    quantite = Decimal(str(ligne.get('quantite', 0)))
    if quantite <= 0:
        raise ValueError("La quantité doit être supérieure à 0")
    prix_unitaire = ligne.get('prix_unitaire')
    if _ajout_prix_automatique(prix_unitaire):
        prix_unitaire = _resolve_prix_unitaire(produit, prix_field, repli)
    prix_unitaire = Decimal(str(prix_unitaire))
    if prix_unitaire < 0:
        raise ValueError("Le prix unitaire ne peut pas être négatif")
    taux_tva = Decimal(str(ligne.get('taux_tva', 20)))
    remise = Decimal(str(ligne.get('remise', 0)))
    if taux_tva < 0:
        raise ValueError("Le taux de TVA ne peut pas être négatif")
    if remise < 0 or remise > 100:
        raise ValueError("La remise doit être comprise entre 0 et 100 %")
    base_ht = quantite * prix_unitaire * (Decimal('1') - remise / Decimal('100'))
    total_ttc = base_ht * (Decimal('1') + taux_tva / Decimal('100'))
    return {
        'produit_id': produit_id, 'quantite': quantite,
        'prix_unitaire': prix_unitaire, 'taux_tva': taux_tva,
        'remise': remise, 'total_ht': base_ht, 'total_ttc': total_ttc,
    }


def _ajout_prix_automatique(value):
    if value is None or value == '':
        return True
    try:
        return Decimal(str(value)) == 0
    except Exception:
        return False


def get_sales_summary(debut=None, fin=None, limit=None):
    """Liste les ventes avec filtres SQL et relations préchargées."""
    tenant_id = get_current_tenant_id()
    query = Vente.query.options(
        joinedload(Vente.client),
        joinedload(Vente.commercial),
    ).filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    if debut is not None:
        query = query.filter(Vente.date >= debut)
    if fin is not None:
        query = query.filter(Vente.date < fin)
    query = query.order_by(Vente.created_at.desc())
    if limit is not None:
        try:
            safe_limit = min(max(int(limit), 1), 500)
            query = query.limit(safe_limit)
        except (TypeError, ValueError):
            pass
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def update(id, data):
    data = dict(data or {})
    sale = get_by_id(id)
    if not sale:
        return None

    if 'date' in data and isinstance(data['date'], str):
        raw_date = data['date']
        try:
            data['date'] = datetime.strptime(raw_date, '%Y-%m-%d')
        except ValueError:
            try:
                data['date'] = datetime.fromisoformat(raw_date)
            except ValueError:
                raise ValueError("Format de date invalide (attendu YYYY-MM-DD)")

    tenant_id = sale.tenant_id or get_current_tenant_id()
    active_invoice = sale.factures.filter_by(is_active=True).first()

    for key in ('total_ht','total_ttc','lignes_vente','tenant_id','id','created_at',
                'updated_at','created_by','updated_by','is_active'):
        data.pop(key, None)

    lignes_presentes = 'lignes' in data
    lignes_data = data.pop('lignes', None)

    if active_invoice and lignes_presentes:
        raise ValueError("Impossible de modifier les lignes d'une vente déjà facturée")
    if active_invoice and any(k in data for k in ('client_id', 'type_vente')):
        raise ValueError("Impossible de modifier le client ou le type d'une vente déjà facturée")

    if lignes_presentes:
        if not isinstance(lignes_data, list) or not lignes_data:
            raise ValueError("Au moins une ligne de vente est requise")

        client_id = data.get('client_id', sale.client_id)
        client_query = Client.query.filter_by(id=client_id)
        if tenant_id:
            client_query = client_query.filter_by(tenant_id=tenant_id)
        client = client_query.first()
        if not client:
            raise ValueError("Client introuvable")

        client_type = getattr(client.type, 'value', client.type) if client.type else 'particulier'
        type_vente = data.get('type_vente', sale.type_vente or derive_type_vente(client_type))
        if type_vente not in TYPE_VENTE_VALIDES:
            raise ValueError("type_vente invalide. Attendu: gros ou detail")
        prix_field = _prix_field_effectif(type_vente, client_type)
        repli = _REPLI_GROS if type_vente == 'gros' else ('prix_vente_ht',)
        prepared = [_prepare_sale_line(row, tenant_id, prix_field, repli) for row in lignes_data]

        old_rows = LigneVente.query.filter_by(
            vente_id=sale.id, tenant_id=tenant_id, is_active=True
        ).all()
        old_by_product = {}
        for row in old_rows:
            old_by_product[row.produit_id] = (
                old_by_product.get(row.produit_id, Decimal('0'))
                + Decimal(str(row.quantite or 0))
            )
        new_by_product = {}
        for row in prepared:
            if row['produit_id']:
                new_by_product[row['produit_id']] = (
                    new_by_product.get(row['produit_id'], Decimal('0')) + row['quantite']
                )

        product_ids = sorted(set(old_by_product) | set(new_by_product))
        if product_ids:
            product_query = Produit.query.filter(Produit.id.in_(product_ids))
            if tenant_id:
                product_query = product_query.filter_by(tenant_id=tenant_id)
            products = {p.id: p for p in product_query.with_for_update().all()}
            for produit_id in product_ids:
                produit = products.get(produit_id)
                if not produit:
                    raise ValueError(f"Produit id={produit_id} introuvable")
                delta = new_by_product.get(produit_id, Decimal('0')) - old_by_product.get(produit_id, Decimal('0'))
                if delta == 0:
                    continue
                stock_avant = Decimal(str(produit.quantite_stock or 0))
                if delta > 0:
                    if stock_avant < delta:
                        raise ValueError(f"Stock insuffisant pour {produit.nom}. Disponible: {stock_avant}")
                    produit.quantite_stock = stock_avant - delta
                    mouvement_type, mouvement_qty = 'sortie', delta
                else:
                    mouvement_qty = -delta
                    produit.quantite_stock = stock_avant + mouvement_qty
                    mouvement_type = 'entree'
                db.session.add(MouvementStock(
                    produit_id=produit.id, type_mouvement=mouvement_type,
                    quantite=mouvement_qty, stock_avant=stock_avant,
                    stock_apres=produit.quantite_stock,
                    raison=f'Modification vente {sale.reference}',
                    reference=sale.reference, tenant_id=tenant_id,
                ))

        for row in old_rows:
            row.is_active = False

        sale.client_id = client_id
        sale.type_vente = type_vente
        sale.total_ht = sum((row['total_ht'] for row in prepared), Decimal('0'))
        sale.total_ttc = sum((row['total_ttc'] for row in prepared), Decimal('0'))

        for row in prepared:
            db.session.add(LigneVente(
                vente_id=sale.id, tenant_id=tenant_id, produit_id=row['produit_id'],
                quantite=row['quantite'], prix_unitaire_ht=row['prix_unitaire'],
                taux_tva=row['taux_tva'], remise=row['remise'],
            ))

    for key, value in data.items():
        if hasattr(sale, key):
            setattr(sale, key, value)

    db.session.commit()
    db.session.refresh(sale)
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

    if data.get('client_passager') in (True, 'true', 'True', 1, '1'):
        passager = get_or_create_passager_client()
        data['client_id'] = passager.id
    elif not data.get('client_id'):
        raise ValueError("Le client est requis")
    data.pop('client_passager', None)

    client = None
    if data.get('client_id'):
        client_query = Client.query.filter_by(id=data['client_id'])
        if tenant_id:
            client_query = client_query.filter_by(tenant_id=tenant_id)
        client = client_query.first()
    client_type = getattr(client.type, 'value', client.type) if client and client.type else 'particulier'

    type_vente = data.get('type_vente')
    if not type_vente:
        type_vente = derive_type_vente(client_type)
    if type_vente not in TYPE_VENTE_VALIDES:
        raise ValueError("type_vente invalide. Attendu: gros ou detail")
    data['type_vente'] = type_vente

    prix_field = _prix_field_effectif(type_vente, client_type)
    repli = _REPLI_GROS if type_vente == 'gros' else ('prix_vente_ht',)

    if 'date' in data and isinstance(data['date'], str):
        try:
            data['date'] = datetime.strptime(data['date'], '%Y-%m-%d')
        except ValueError:
            try:
                data['date'] = datetime.fromisoformat(data['date'])
            except ValueError:
                raise ValueError("Format de date invalide (attendu YYYY-MM-DD)")

    total_ht = Decimal('0')
    total_ttc = Decimal('0')
    prepared_lines = []
    for prepared in prepared_lines:
        produit_id = prepared['produit_id']
        quantite = prepared['quantite']
        mapped_ligne = {
            'vente_id': sale.id, 'tenant_id': sale.tenant_id,
            'produit_id': produit_id, 'quantite': quantite,
            'prix_unitaire_ht': prepared['prix_unitaire'],
            'taux_tva': prepared['taux_tva'],
            'remise': prepared['remise'],
        }
        db.session.add(LigneVente(**mapped_ligne))
        if produit_id:
            produit_query = Produit.query.filter_by(id=produit_id)
            if tenant_id:
                produit_query = produit_query.filter_by(tenant_id=tenant_id)
            produit = produit_query.with_for_update().first()
            if not produit:
                raise ValueError(f"Produit id={produit_id} introuvable")
            try:
                qty_decimal = prepared['quantite']
                if produit.quantite_stock < qty_decimal:
                    raise ValueError(f"Stock insuffisant. Disponible: {produit.quantite_stock}")
                stock_avant = Decimal(str(produit.quantite_stock or 0))
                produit.quantite_stock -= qty_decimal
                db.session.add(MouvementStock(
                    produit_id=produit.id, type_mouvement='sortie',
                    quantite=qty_decimal, stock_avant=stock_avant,
                    stock_apres=produit.quantite_stock,
                    raison=f'Vente {sale.reference}',
                    reference=sale.reference, tenant_id=produit.tenant_id,
                ))
            except ValueError as e:
                stock_errors.append(str(e))
    if stock_errors:
        db.session.rollback()
        raise ValueError("; ".join(stock_errors))
    # Confirmation de facture auto : chemin UNIQUE issue_invoice (P0 #2),
    # dans la MEME transaction que la vente et le stock. Si la facturation
    # echoue (conflit, reference), tout est annule : plus jamais de vente
    # creee avec une facture silencieusement absente.
    if facture_auto:
        from app.services.facturation_service import issue_invoice
        issue_invoice({'vente_id': sale.id}, _commit=False)
    db.session.commit()
    return sale


def get_or_create_passager_client():
    """Retourne (ou cree) le client passager du tenant courant.

    Un seul client passager par tenant. Le code est deterministe
    (PASSAGER-<tenant_id>) pour rester idempotent. En cas de course
    concurrente, on retombe sur une lecture apres rollback.
    """
    from app.models.client import Client
    from sqlalchemy.exc import IntegrityError
    tenant_id = get_current_tenant_id()
    code = f"PASSAGER-{tenant_id}" if tenant_id else "PASSAGER"
    query = Client.query.filter_by(code=code)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    existing = query.first()
    if existing:
        return existing
    client = Client(
        code=code,
        nom='Passager',
        prenom='Client',
        type='particulier',
        secteur='autre',
        est_actif=True,
    )
    if tenant_id:
        client.tenant_id = tenant_id
    db.session.add(client)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        existing = query.first()
        if existing:
            return existing
        raise
    return client


def get_by_client(client_id):
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(client_id=client_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_stats():
    tenant_id = get_current_tenant_id()
    filters = [Vente.is_active.is_(True)]
    if tenant_id:
        filters.append(Vente.tenant_id == tenant_id)

    total, count, average = db.session.query(
        db.func.coalesce(db.func.sum(Vente.total_ttc), 0),
        db.func.count(Vente.id),
        db.func.coalesce(db.func.avg(Vente.total_ttc), 0),
    ).filter(*filters).one()

    rows = db.session.query(
        Vente.statut,
        db.func.count(Vente.id),
        db.func.coalesce(db.func.sum(Vente.total_ttc), 0),
    ).filter(*filters).group_by(Vente.statut).all()

    return {
        'total': float(total or 0),
        'count': int(count or 0),
        'average': float(average or 0),
        'by_status': {
            statut: {'count': int(cnt), 'total': float(amount or 0)}
            for statut, cnt, amount in rows
        },
    }
