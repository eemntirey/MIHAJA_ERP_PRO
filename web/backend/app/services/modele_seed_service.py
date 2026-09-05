"""Seed des modèles de documents systémiques pour un nouveau tenant.

À la création d'un tenant (inscription / register), on installe
automatiquement une bibliothèque de modèles par défaut pour les
types de documents métier courants (facture, devis, bon de
livraison, avoir). Chaque modèle est marqué `est_defaut=True` pour
son type, ce qui permet à `ModeleDocumentService.get_defaut_by_type`
de les retrouver lors de la génération automatique.

Idempotent : si les modèles existent déjà pour un tenant (par
exemple lors d'une ré-inscription ou d'une réactivation), aucun
doublon n'est créé.
"""

from app import db
from app.models.modele_document import ModeleDocument
from app.utils.modeles_systeme import (
    SYSTEM_MODELES_DOCUMENTS,
    MENTIONS_LEGALES_DEFAUT,
    CONDITIONS_GENERALES_DEFAUT,
)


def seed_modeles_systeme(tenant_id):
    """Crée les modèles de documents par défaut pour un tenant.

    Args:
        tenant_id: identifiant du tenant à initialiser.

    Returns:
        Liste des ModeleDocument créés (vide si tous déjà présents).
    """
    if not tenant_id:
        return []

    types_existants = {
        row[0] for row in db.session.query(ModeleDocument.type_document)
        .filter(
            ModeleDocument.tenant_id == tenant_id,
            ModeleDocument.is_active == True,
        )
        .distinct().all()
    }

    created = []
    for spec in SYSTEM_MODELES_DOCUMENTS:
        if spec['type_document'] in types_existants:
            continue
        modele = ModeleDocument(
            tenant_id=tenant_id,
            nom=spec['nom'],
            type_document=spec['type_document'],
            contenu_modele=spec['contenu_modele'],
            est_defaut=spec['est_defaut'],
            mention_legales=MENTIONS_LEGALES_DEFAUT,
            conditions_generales=CONDITIONS_GENERALES_DEFAUT,
        )
        db.session.add(modele)
        created.append(modele)

    if created:
        db.session.flush()

    return created
