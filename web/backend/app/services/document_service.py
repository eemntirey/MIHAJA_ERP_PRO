from app import db
from app.models.modele_document import ModeleDocument
from app.models.document_genere import DocumentGenere
from app.models.vente import Vente
from app.models.facture import Facture
from app.security.tenant import get_current_tenant_id
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import html as _html


def _format_mga(value) -> str:
    """Formate un montant MGA avec séparation des milliers par espace (ex. 149 600)."""
    if value is None:
        return '0'
    try:
        nombre = round(float(value))
    except (TypeError, ValueError):
        return str(value)
    return f'{nombre:,}'.replace(',', ' ')


def _client_label(client) -> str:
    """Nom complet du client : prénom + nom, sinon raison sociale."""
    if client is None:
        return ''
    prenom = (client.prenom or '').strip()
    nom = (client.nom or '').strip()
    label = f'{prenom} {nom}'.strip()
    if label:
        return label
    return (client.raison_sociale or '').strip()


def _build_donnees_document(vente, reference, overrides=None) -> Dict[str, Any]:
    """Construit le jeu de données d'un document depuis une vente (source de vérité).

    Retourne à la fois les valeurs d'affichage (totaux formatés en MGA) et les
    lignes brutes ``items`` (numériques) utilisées par le moteur PDF.
    """
    overrides = overrides or {}
    client = vente.client

    items: List[Dict[str, Any]] = []
    lignes_html: List[str] = []
    for ligne in vente.lignes_vente.all():
        produit_nom = (ligne.produit.nom if ligne.produit else None) or ''
        item = {
            'produit_nom': produit_nom,
            'quantite': float(ligne.quantite or 0),
            'prix_unitaire_ht': float(ligne.prix_unitaire_ht or 0),
            'taux_tva': float(ligne.taux_tva or 0),
            'total_ht': float(ligne.total_ht or 0),
            'total_ttc': float(ligne.total_ttc or 0),
        }
        items.append(item)
        lignes_html.append(
            '<tr>'
            f'<td>{_html.escape(produit_nom)}</td>'
            f'<td>{item["quantite"]}</td>'
            f'<td>{item["prix_unitaire_ht"]:.2f}</td>'
            f'<td>{_format_mga(item["total_ht"])}</td>'
            '</tr>'
        )

    total_ht = float(vente.total_ht or 0)
    total_ttc = float(vente.total_ttc or 0)
    montant_tva = total_ttc - total_ht
    taux_tva = items[0].get('taux_tva', 10.0) if items else 10.0

    donnees = {
        'client_nom': _client_label(client),
        'client_adresse': (client.adresse_facturation if client else None) or '',
        'client_ville': (client.ville_facturation if client else None) or '',
        'client_code_postal': (client.code_postal_facturation if client else None) or '',
        'client_pays': (client.pays_facturation if client else None) or 'Madagascar',
        'client_email': (client.email if client else None) or '',
        'devise': 'MGA',
        'reference': reference,
        'date_emission': vente.date.strftime('%d/%m/%Y') if vente.date else '',
        'date_echeance': '',
        'items': items,
        'lignes': '\n'.join(lignes_html),
        'sous_total': _format_mga(total_ht),
        'remise': 0.0,
        'montant_tva': _format_mga(montant_tva),
        'taux_tva': taux_tva,
        'total_ht': total_ht,
        'total_ttc': _format_mga(total_ttc),
    }
    donnees.update(overrides or {})
    return donnees


def build_donnees_from_vente(vente, overrides=None) -> Dict[str, Any]:
    """Données document dérivées d'une vente (client, lignes, totaux en MGA)."""
    return _build_donnees_document(
        vente, reference=vente.reference, overrides=overrides
    )


def build_donnees_from_facture(facture, overrides=None) -> Dict[str, Any]:
    """Données document dérivées d'une facture (base = vente sous-jacente).

    La référence du document reprend celle de la facture.
    """
    overrides = dict(overrides or {})
    reference = overrides.get('reference', facture.reference)
    return _build_donnees_document(
        facture.vente, reference=reference, overrides=overrides
    )


def resolve_document_context(data) -> Dict[str, Any]:
    """Résout le contexte de génération d'un document depuis une entité métier.

    Args:
        data: ``{'entite_type': 'vente'|'facture', 'entite_id': int, 'overrides': optional dict}``.

    Returns:
        ``{'type_document', 'reference', 'donnees'}``. La référence privilégie la
        facture émise pour la vente si elle existe.

    Raises:
        ValueError: entité inconnue ou type non pris en charge.
    """
    data = data or {}
    entite_type = data.get('entite_type')
    entite_id = data.get('entite_id')
    overrides = data.get('overrides') or {}

    if entite_type == 'vente':
        vente = db.session.get(Vente, entite_id)
        if vente is None:
            raise ValueError(f'Vente introuvable (id={entite_id})')
        facture = Facture.query.filter_by(vente_id=vente.id).order_by(Facture.id.asc()).first()
        if facture is not None:
            return {
                'type_document': 'facture',
                'reference': facture.reference,
                'donnees': build_donnees_from_facture(facture, overrides),
            }
        return {
            'type_document': 'facture',
            'reference': vente.reference,
            'donnees': build_donnees_from_vente(vente, overrides),
        }

    if entite_type == 'facture':
        facture = db.session.get(Facture, entite_id)
        if facture is None:
            raise ValueError(f'Facture introuvable (id={entite_id})')
        return {
            'type_document': 'facture',
            'reference': facture.reference,
            'donnees': build_donnees_from_facture(facture, overrides),
        }

    raise ValueError("Type d'entité non pris en charge (attendu 'vente' ou 'facture')")


def donnees_pdf_safe(donnees) -> Dict[str, Any]:
    """Clone des données de document avec des totaux numériques pour le PDF.

    Le moteur PDF (``pdf_generator``) recalcule les montants à partir de
    ``total_ht``/``total_ttc``/``taux_tva``/``remise`` : on lui transmet des
    valeurs numériques, pas les chaînes formatées destinées au HTML.
    """
    resultat = dict(donnees or {})
    for key in ('total_ht', 'total_ttc', 'taux_tva', 'remise', 'sous_total', 'montant_tva'):
        valeur = resultat.get(key)
        if isinstance(valeur, str):
            try:
                resultat[key] = float(valeur.replace(' ', '').replace(',', '.'))
            except ValueError:
                resultat[key] = 0.0
    return resultat


class ModeleDocumentService:
    model = ModeleDocument

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
    def get_defaut_by_type(cls, type_document):
        query = cls.model.query.filter_by(type_document=type_document, est_defaut=True, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at', 'is_active', 'created_by', 'updated_by'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

class DocumentGenereService:
    model = DocumentGenere

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
    def get_by_reference(cls, reference):
        query = cls.model.query.filter_by(reference=reference)
        query = cls._get_tenant_filter(query)
        return query.first()

    @classmethod
    def create(cls, data):
        tenant_id = get_current_tenant_id()
        if tenant_id is not None and hasattr(cls.model, 'tenant_id'):
            data['tenant_id'] = tenant_id
        instance = cls.model(**data)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, id, data):
        instance = cls.get_by_id(id)
        if not instance:
            return None
        for key, value in data.items():
            if hasattr(instance, key) and key not in ('id', 'tenant_id', 'created_at', 'updated_at', 'is_active', 'created_by', 'updated_by'):
                setattr(instance, key, value)
        db.session.commit()
        return instance

    @classmethod
    def delete(cls, id):
        instance = cls.get_by_id(id)
        if not instance:
            return False
        instance.delete()
        return True

    @classmethod
    def get_by_entite(cls, entite_type, entite_id):
        query = cls.model.query.filter_by(entite_type=entite_type, entite_id=entite_id, is_active=True)
        query = cls._get_tenant_filter(query)
        return query.all()