"""Service de notifications.

Génère automatiquement des notifications métier réelles :
- alertes de stock (produit sous le seuil d'alerte) ;
- factures impayées / partiellement payées ;
- nouvelles ventes enregistrées.

Toutes les fonctions sont "best effort" : une erreur de notification ne doit
jamais casser la requête métier appelante (try/except systématique).

La déduplication se fait sur le couple (type, link) : le champ ``link`` contient
un identifiant stable de l'objet (ex : '/inventory?produit=12'), ce qui permet
de ne jamais dupliquer une alerte existante et de désactiver proprement les
alertes devenues obsolètes (stock réapprovisionné, facture payée...).
"""

from flask import current_app

from app import db
from app.models.notification import Notification


def create_notification(tenant_id=None, title='', message='', notif_type='info',
                        link=None, user_id=None, commit=True):
    """Crée une notification en base. Retourne l'objet ou None en cas d'erreur."""
    try:
        notification = Notification(
            title=title or 'Notification',
            message=message or '',
            type=notif_type or 'info',
            link=link,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        db.session.add(notification)
        if commit:
            db.session.commit()
        return notification
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Erreur lors de la creation de la notification')
        return None


def _existing_active_by_link(tenant_id, notif_type, links):
    """Retourne {link: notification} pour les notifications actives du type donné."""
    if not links:
        return {}
    query = Notification.query.filter(
        Notification.is_active.is_(True),
        Notification.type == notif_type,
        Notification.link.in_(links),
    )
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    return {n.link: n for n in query.all()}


def _deactivate_stale(tenant_id, notif_type, keep_links):
    """Désactive (soft-delete) les notifications du type dont le link n'est plus valide."""
    query = Notification.query.filter(
        Notification.is_active.is_(True),
        Notification.type == notif_type,
    )
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    for notification in query.all():
        if notification.link not in keep_links:
            notification.is_active = False



def sync_alert_notifications(tenant_id=None):
    """Synchronise les notifications d'alerte avec l'état réel des données.

    - crée une notification par produit sous son seuil d'alerte ;
    - crée une notification par facture impayée ou partiellement payée ;
    - désactive les alertes résolues (stock réapprovisionné, facture payée).

    Appelé à chaque GET /notifications : la boîte de notification reflète
    toujours l'état courant du business. Retourne le nombre de notifications
    créées.
    """
    # Super admin (tenant_id None) : pas de génération globale, il voit
    # déjà les notifications de tous les tenants via la liste non filtrée.
    if tenant_id is None:
        return 0

    created = 0
    try:
        from app.models.produit import Produit
        from app.models.facture import Facture

        # --- 1. Alertes de stock ---
        produits = (
            Produit.query.filter(Produit.is_active.is_(True))
            .filter_by(tenant_id=tenant_id)
            .all()
        )
        produits_en_alerte = [
            p for p in produits
            if (p.quantite_stock or 0) <= (p.seuil_alerte or 0)
        ]
        links_stock = {f'/inventory?produit={p.id}' for p in produits_en_alerte}
        existing_stock = _existing_active_by_link(tenant_id, 'stock_alert', links_stock)
        for produit in produits_en_alerte:
            link = f'/inventory?produit={produit.id}'
            if link in existing_stock:
                continue
            if create_notification(
                tenant_id=tenant_id,
                title=f"Stock faible : {produit.nom}",
                message=(
                    f"Quantité restante : {produit.quantite_stock} "
                    f"(seuil d'alerte : {produit.seuil_alerte})"
                ),
                notif_type='stock_alert',
                link=link,
                commit=False,
            ):
                created += 1
        _deactivate_stale(tenant_id, 'stock_alert', links_stock)

        # --- 2. Factures impayées ---
        factures = (
            Facture.query.filter(
                Facture.is_active.is_(True),
                Facture.statut.in_(('non_payee', 'payee_partiel')),
            )
            .filter_by(tenant_id=tenant_id)
            .all()
        )
        links_factures = {f'/invoices?facture={f.id}' for f in factures}
        existing_factures = _existing_active_by_link(tenant_id, 'facture_impayee', links_factures)
        for facture in factures:
            link = f'/invoices?facture={facture.id}'
            if link in existing_factures:
                continue
            montant = float(facture.total_ttc or 0)
            if create_notification(
                tenant_id=tenant_id,
                title=f"Facture impayée : {facture.reference}",
                message=f"Montant TTC : {montant:,.0f} Ar — statut : {facture.statut}",
                notif_type='facture_impayee',
                link=link,
                commit=False,
            ):
                created += 1
        _deactivate_stale(tenant_id, 'facture_impayee', links_factures)

        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Erreur lors de la synchronisation des alertes')
    return created


def notify_new_sale(vente):
    """Notification créée à chaque nouvelle vente enregistrée."""
    try:
        montant = float(vente.total_ttc or 0)
        message = f"Vente {vente.reference} — {montant:,.0f} Ar"
        return create_notification(
            tenant_id=getattr(vente, 'tenant_id', None),
            title='Nouvelle vente enregistrée',
            message=message,
            notif_type='sale',
            link='/sales',
        )
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Erreur notification nouvelle vente')
        return None
