# web/backend/app/services/replication/entities.py
# Registre des entites repliquees (V1 : produits et clients).
#
# Ce module est partage par les deux cotes :
#  - le serveur CENTRAL (app/api/v1/replication.py) pour appliquer les
#    mutations des postes ;
#  - le backend LOCAL (app/services/replication/pull.py) pour appliquer les
#    changements tires du central.
# Une seule definition evite toute divergence de champs autorises.
#
# Perimetre V1 (cf. plan Task 10) : produits et clients. Les ventes ne sont
# PAS repliquees automatiquement : le stock doit etre decremente via
# vente_service (idempotence + facture + comptabilite). Toute entite hors
# registre est refusee explicitement ('unsupported') plutot que marquee
# appliquee a tort.
from app.models.client import Client, TypeClient, SecteurActivite
from app.models.produit import Produit


ENTITY_REGISTRY = {
    'produit': {
        'model': Produit,
        'label': 'produit',
        # Champs metier repliques : aucune FK croisee (fournisseur_id) n'est
        # repliquee en V1, sinon elle pointerait vers un id local errone.
        'fields': (
            'reference', 'code_barre', 'nom', 'description_courte',
            'description_longue', 'categorie', 'sous_categorie', 'famille',
            'marque', 'modele', 'unite', 'prix_achat_ht', 'prix_vente_ht',
            'taux_tva', 'quantite_stock', 'stock_min', 'stock_max',
            'seuil_alerte', 'seuil_critique', 'statut', 'published',
            'is_active', 'tags',
        ),
        'required': ('reference', 'nom'),
        'natural_key': 'reference',
        'enums': {},
    },
    'client': {
        'model': Client,
        'label': 'client',
        'fields': (
            'code', 'raison_sociale', 'nom', 'prenom', 'type', 'secteur',
            'siret', 'numero_tva', 'email', 'telephone', 'mobile', 'fax',
            'site_web', 'adresse_facturation', 'complement_facturation',
            'code_postal_facturation', 'ville_facturation',
            'pays_facturation', 'adresse_livraison', 'complement_livraison',
            'code_postal_livraison', 'ville_livraison', 'pays_livraison',
            'contact_nom', 'contact_prenom', 'contact_fonction',
            'contact_email', 'contact_telephone', 'conditions_paiement',
            'remise_standard', 'plafond_credit', 'echeance_credit',
            'est_favori', 'est_actif', 'est_bloque', 'note', 'is_active',
        ),
        'required': ('code',),
        'natural_key': 'code',
        'enums': {'type': TypeClient, 'secteur': SecteurActivite},
    },
}

# Entites capturees par l'outbox local (doit rester coherent avec le registre).
REPLICATED_ENTITIES = tuple(ENTITY_REGISTRY.keys())


def is_known_entity(entity):
    """Vrai si l'entite est prise en charge par la replication V1."""
    return entity in ENTITY_REGISTRY


def get_definition(entity):
    """Definition du registre pour une entite (None si non supportee)."""
    return ENTITY_REGISTRY.get(entity)


def get_model(entity):
    """Classe de modele d'une entite du registre."""
    definition = ENTITY_REGISTRY.get(entity)
    return definition['model'] if definition else None


def clean_payload(entity, payload):
    """Ne conserve que les champs autorises, convertis si necessaire.

    :raises ValueError: si un champ obligatoire manque (INSERT).
    """
    definition = ENTITY_REGISTRY.get(entity)
    if definition is None:
        raise ValueError(f"Entité non supportée par la réplication : {entity}")

    payload = payload or {}
    cleaned = {}
    for field in definition['fields']:
        if field not in payload:
            continue
        value = payload[field]
        enum_cls = definition['enums'].get(field)
        if enum_cls is not None and value is not None and not isinstance(value, enum_cls):
            try:
                value = enum_cls(value)
            except ValueError as exc:
                raise ValueError(
                    f"Valeur invalide pour {entity}.{field} : {value}"
                ) from exc
        cleaned[field] = value
    return cleaned


def missing_required(entity, payload):
    """Liste des champs obligatoires absents du payload."""
    definition = ENTITY_REGISTRY.get(entity) or {}
    payload = payload or {}
    return [
        field for field in definition.get('required', ())
        if payload.get(field) in (None, '')
    ]


def find_existing(entity, tenant_id, payload):
    """Retrouve la ligne existante via la cle naturelle (idempotence inter-postes).

    Un produit cree sur le web puis re-pousse par un poste (ou par un 2e
    poste) ne doit pas creer de doublon : on retombe sur l'enregistrement
    existant au lieu de violer la contrainte d'unicite.
    """
    definition = ENTITY_REGISTRY.get(entity)
    if not definition:
        return None
    natural_key = definition.get('natural_key')
    if not natural_key:
        return None
    value = (payload or {}).get(natural_key)
    if value in (None, ''):
        return None
    model = definition['model']
    return model.query.filter(
        model.tenant_id == tenant_id,
        getattr(model, natural_key) == value,
    ).first()
