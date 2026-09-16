from flask import current_app
from datetime import datetime
from decimal import Decimal
from app import db
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


def _ajout_prix_automatique(value):
    if value is None or value == '':
        return True
    try:
        return Decimal(str(value)) == 0
    except Exception:
        return False


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
    client_type = client.type.value if client and client.type else 'particulier'

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

    total_ht = 0
    total_ttc = 0
    stock_errors = []
    for ligne in lignes_data:
        quantite = Decimal(str(ligne.get('quantite', 0)))
        prix_unitaire = ligne.get('prix_unitaire')
        if _ajout_prix_automatique(prix_unitaire):
            produit_reference = None
            produit_id = ligne.get('produit_id')
            if produit_id:
                produit_query = Produit.query.filter_by(id=produit_id)
                if tenant_id:
                    produit_query = produit_query.filter_by(tenant_id=tenant_id)
                produit_reference = produit_query.first()
            ligne['prix_unitaire'] = prix_unitaire = (
                float(_resolve_prix_unitaire(produit_reference, prix_field, repli))
                if produit_reference else 0
            )
        prix_unitaire = Decimal(str(prix_unitaire))
        taux_tva = Decimal(str(ligne.get('taux_tva', 20)))
        remise = Decimal(str(ligne.get('remise', 0)))
        base_ht = quantite * prix_unitaire * (1 - remise / 100)
        total_ht += base_ht
        total_ttc += base_ht * (1 + taux_tva / 100)

    data['total_ht'] = total_ht
    data['total_ttc'] = total_ttc
    facture_auto = data.pop('facture_auto', None) or data.pop('confirmer_facture', None)
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
