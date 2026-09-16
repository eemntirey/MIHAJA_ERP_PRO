from app import db
from app.models.facture import Facture
from app.models.vente import Vente
from app.security.tenant import get_current_tenant_id

import random
import string
from datetime import datetime


class FactureDejaExistante(ValueError):
    """Levee quand une facture active existe deja pour la meme vente.

    Permet a l'API de distinguer un 409 (conflit idempotent, facture
    existante incluse) d'une erreur de validation classique (400).
    """

    def __init__(self, message, facture=None):
        super().__init__(message)
        self.facture = facture


class SuperAdminFactureInterdite(PermissionError):
    """Levee quand un super administrateur tente de creer une facture.

    Le super administrateur supervise la plateforme : il n'agit jamais
    sur les donnees metier (produits, ventes, factures) des tenants.
    """


def ensure_not_super_admin():
    """Bloque la creation de facture par un super administrateur (403).

    Verification double : claim JWT 'role' ET role de l'utilisateur en
    base (g.current_user), pour couvrir les tokens sans claim 'role'.
    """
    from flask import g, has_request_context
    from app.security.roles import is_super_admin

    role_claim = None
    if has_request_context():
        try:
            from flask_jwt_extended import get_jwt
            role_claim = (get_jwt() or {}).get('role')
        except Exception:
            role_claim = None

    user = getattr(g, 'current_user', None) if has_request_context() else None
    if is_super_admin(role_claim) or (
        user is not None and is_super_admin(user.role)
    ):
        raise SuperAdminFactureInterdite(
            "Un super administrateur n'est pas autorise a creer une facture "
            "pour les produits d'un tenant"
        )


def _default_facture_reference(vente):
    """Reference facture derivee de la vente, sinon fallback horodate.

    La colonne Facture.reference est unique au niveau GLOBAL (index
    unique DB), y compris pour les lignes soft-deleted : on verifie donc
    sans filtre is_active pour eviter un IntegrityError au commit.
    """
    candidate = f"FAC-{vente.reference}"
    if len(candidate) <= 50 and not Facture.query.filter_by(reference=candidate).first():
        return candidate
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    for _ in range(10):
        suffix = ''.join(random.choices(string.digits, k=4))
        candidate = f"FAC-{ts}-{suffix}"
        if not Facture.query.filter_by(reference=candidate).first():
            return candidate
    raise ValueError("Impossible de generer une reference unique de facture")


def issue_invoice(data, _commit=True):
    """CHEMIN UNIQUE de creation d'une facture depuis une vente (P0 #2).

    Reunit les trois anciens chemins (POST /factures, /from-vente/<id>
    et facture_auto de vente_service) en un seul appel. Le client et les
    montants sont TOUJOURS derives de la vente (source de verite), plus
    de totals fournis a la main ni de reference divergente.

    Garanties :
    - idempotence : une seule facture ACTIVE par vente -> FactureDejaExistante ;
    - concurrency : la vente est verrouillee (with_for_update) le temps
      du controle, contre les double-soumissions simultanees ;
    - atomique : _commit=False permet a vente_service d'integrer la
      facture a la meme transaction que la vente et le stock.
    """
    ensure_not_super_admin()
    vente_id = data.get('vente_id')
    if not vente_id:
        raise ValueError('vente_id est requis')
    tenant_id = get_current_tenant_id()
    query = Vente.query.filter_by(id=vente_id, is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    vente = query.with_for_update().first()
    if not vente:
        raise ValueError('Vente introuvable')

    existing_query = Facture.query.filter_by(vente_id=vente.id, is_active=True)
    if tenant_id:
        existing_query = existing_query.filter_by(tenant_id=tenant_id)
    existing = existing_query.first()
    if existing:
        raise FactureDejaExistante("Une facture existe deja pour cette vente", existing)

    reference = data.get('reference')
    if reference and Facture.query.filter_by(reference=reference).first():
        raise ValueError(f"Une facture avec la reference '{reference}' existe deja")

    facture = Facture(
        vente_id=vente.id,
        client_id=data.get('client_id') or vente.client_id,
        tenant_id=vente.tenant_id,
        reference=reference or _default_facture_reference(vente),
        total_ht=vente.total_ht,
        total_ttc=vente.total_ttc,
        statut=data.get('statut') or 'non_payee',
    )
    db.session.add(facture)
    if _commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    return facture


def _sync_vente_status(facture):
    """Synchronise le statut de la vente liee avec celui de la facture.

    Fini l'incoherence historique Vente.statut='en_attente' tandis que
    Facture.statut='payee'. payee -> vente 'payee' ; paiement partiel ou
    annule -> retour vente 'en_attente' (sauf vente devis/annulee, on ne
    regresse pas).
    """
    if not facture:
        return
    vente = facture.vente
    if not vente:
        return
    if facture.statut == 'payee':
        vente.statut = 'payee'
    elif vente.statut in ('payee', 'en_attente'):
        vente.statut = 'en_attente'


def get_all():
    tenant_id = get_current_tenant_id()
    query = Facture.query
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def get_by_id(id):
    tenant_id = get_current_tenant_id()
    query = Facture.query.filter_by(id=id)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def update(id, data):
    facture = get_by_id(id)
    if not facture:
        return None
    PROTECTED = {'id', 'tenant_id', 'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'}
    for key, value in data.items():
        if key in PROTECTED:
            continue
        if hasattr(facture, key):
            setattr(facture, key, value)
    db.session.commit()
    return facture


def delete(id):
    facture = get_by_id(id)
    if not facture:
        return None
    facture.delete()
    db.session.commit()
    return facture


def generate_from_vente(vente_id):
    """Chemin de compat (seed_demo) : delegue au chemin unique."""
    return issue_invoice({'vente_id': vente_id})
