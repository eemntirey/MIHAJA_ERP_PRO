from app.security.tenant import get_current_tenant_id
from app.models.produit import Produit
from app.models.vente import Vente
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.ligne_vente import LigneVente
from app.models.facture import Facture
from app.models.paiement import Paiement
from app import db
from sqlalchemy import func
from datetime import datetime, time, timedelta
from sqlalchemy.exc import OperationalError


def _local_day_boundaries(now_utc=None):
    """Bornes de jour/mois en heure locale du serveur, converties en UTC.

    `created_at` est stocke en UTC. Pour que "aujourd'hui" corresponde au
    jour calendaire de l'utilisateur (Madagascar = UTC+3), on calcule minuit
    en heure locale puis on le convertit en UTC. Sinon les ventes passees
    entre 00h00 et 03h00 locales sont comptees sur la veille.
    """
    now_utc = now_utc or datetime.utcnow()
    tz_offset = now_utc.astimezone().utcoffset() or timedelta(0)
    today_local = (now_utc + tz_offset).date()
    debut_jour_utc = datetime.combine(today_local, time.min) - tz_offset
    debut_mois_utc = datetime.combine(today_local.replace(day=1), time.min) - tz_offset
    return today_local, debut_jour_utc, debut_mois_utc, tz_offset


def get_dashboard_data():
    try:
        tenant_id = get_current_tenant_id()

        today, debut_jour_utc, debut_mois, tz_offset = _local_day_boundaries()

        ventes_query = Vente.query.filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            ventes_query = ventes_query.filter_by(tenant_id=tenant_id)
        ca_mois = db.session.query(func.sum(Vente.total_ttc)).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            ca_mois = ca_mois.filter_by(tenant_id=tenant_id)
        ca_mois = ca_mois.scalar() or 0

        alertes_query = Produit.query.filter(
            Produit.is_active == True,
            Produit.quantite_stock <= Produit.seuil_alerte
        )
        if tenant_id:
            alertes_query = alertes_query.filter_by(tenant_id=tenant_id)
        alertes_stock = alertes_query.count()

        clients_query = Client.query.filter_by(is_active=True, est_actif=True)
        if tenant_id:
            clients_query = clients_query.filter_by(tenant_id=tenant_id)
        clients_actifs = clients_query.count()

        ventes_aujourdhui_query = Vente.query.filter(
            Vente.is_active == True,
            Vente.created_at >= debut_jour_utc
        )
        if tenant_id:
            ventes_aujourdhui_query = ventes_aujourdhui_query.filter_by(tenant_id=tenant_id)
        ventes_aujourdhui = ventes_aujourdhui_query.count()

        benefice_mois = db.session.query(func.sum(Vente.total_ttc - Vente.total_ht)).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            benefice_mois = benefice_mois.filter_by(tenant_id=tenant_id)
        benefice_mois = float(benefice_mois.scalar() or 0)

        top_produits_query = db.session.query(
            LigneVente.produit_id,
            func.sum(LigneVente.quantite).label('total_quantite'),
            func.sum(LigneVente.total_ttc).label('total_ttc')
        ).join(Vente).filter(
            LigneVente.is_active == True,
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            top_produits_query = top_produits_query.filter(Vente.tenant_id == tenant_id)
        top_produits_query = top_produits_query.group_by(LigneVente.produit_id).order_by(
            func.sum(LigneVente.total_ttc).desc()
        ).limit(5).all()
        top_produits = [
            {
                'produit_id': row[0],
                'total_quantite': float(row[1]),
                'total_ttc': float(row[2])
            }
            for row in top_produits_query
        ]

        top_clients_query = db.session.query(
            Vente.client_id,
            func.sum(Vente.total_ttc).label('total_ttc')
        ).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois
        )
        if tenant_id:
            top_clients_query = top_clients_query.filter_by(tenant_id=tenant_id)
        top_clients_query = top_clients_query.group_by(Vente.client_id).order_by(
            func.sum(Vente.total_ttc).desc()
        ).limit(5).all()
        top_clients = [
            {
                'client_id': row[0],
                'total_ttc': float(row[1])
            }
            for row in top_clients_query
        ]

        evolution_ventes = []
        for i in range(7):
            date_jour = today - timedelta(days=i)
            jour_debut = datetime.combine(date_jour, time.min) - tz_offset
            jour_fin = jour_debut + timedelta(days=1)
            count = db.session.query(func.count(Vente.id)).filter(
                Vente.is_active == True,
                Vente.created_at >= jour_debut,
                Vente.created_at < jour_fin,
            )
            if tenant_id:
                count = count.filter_by(tenant_id=tenant_id)
            evolution_ventes.append({
                'date': date_jour.isoformat(),
                'count': count.scalar() or 0
            })
        evolution_ventes.reverse()

        paiements_subquery = db.session.query(
            Paiement.facture_id.label('facture_id'),
            func.coalesce(func.sum(Paiement.montant), 0).label('paiements_total')
        ).filter(
            Paiement.is_active == True
        )
        if tenant_id:
            paiements_subquery = paiements_subquery.filter_by(tenant_id=tenant_id)
        paiements_subquery = paiements_subquery.group_by(Paiement.facture_id).subquery()

        creances_clients_query = db.session.query(
            Client.id,
            Client.nom,
            Client.prenom,
            func.sum(Facture.total_ttc - func.coalesce(paiements_subquery.c.paiements_total, 0)).label('creance')
        ).join(Facture, Client.id == Facture.client_id).outerjoin(
            paiements_subquery,
            Facture.id == paiements_subquery.c.facture_id
        ).filter(
            Client.is_active == True,
            Facture.is_active == True,
            Facture.statut != 'payee'
        )
        if tenant_id:
            creances_clients_query = creances_clients_query.filter(Client.tenant_id == tenant_id)
        creances_clients_query = creances_clients_query.group_by(Client.id, Client.nom, Client.prenom)
        creances_clients = [
            {
                'client_id': row[0],
                'nom': row[1],
                'prenom': row[2],
                'creance': float(row[3] or 0)
            }
            for row in creances_clients_query.all()
        ]

        fournisseurs_query = Fournisseur.query.filter_by(is_active=True)
        if tenant_id:
            fournisseurs_query = fournisseurs_query.filter_by(tenant_id=tenant_id)
        nombre_fournisseurs = fournisseurs_query.count()

        return {
            'ventes_aujourdhui': ventes_aujourdhui,
            'ca_mois': float(ca_mois),
            'alertes_stock': alertes_stock,
            'clients_actifs': clients_actifs,
            'benefice_mois': benefice_mois,
            'top_produits': top_produits,
            'top_clients': top_clients,
            'evolution_ventes': evolution_ventes,
            'creances_clients': creances_clients,
            'nombre_fournisseurs': nombre_fournisseurs
        }
    except OperationalError as e:
        # Database tables may not be created yet (migrations). Return
        # sensible defaults so the API doesn't raise HTTP 500.
        return {
            'ventes_aujourdhui': 0,
            'ca_mois': 0.0,
            'alertes_stock': 0,
            'clients_actifs': 0,
            'benefice_mois': 0.0,
            'top_produits': [],
            'top_clients': [],
            'evolution_ventes': [],
            'creances_clients': [],
            'nombre_fournisseurs': 0,
            'db_error': str(e)
        }
def get_dashboard_overview_data():
    """Retourne les données réellement consommées par le dashboard web.

    L'endpoint historique /dashboard conserve son contrat. Cette version
    compacte évite les lectures inutiles et calcule l'evolution des 14 derniers
    jours en une seule agrégation SQL.
    """
    try:
        tenant_id = get_current_tenant_id()
        today, debut_jour_utc, debut_mois, _tz_offset = _local_day_boundaries()

        products_query = db.session.query(func.count(Produit.id)).filter(
            Produit.is_active == True
        )
        clients_query = db.session.query(func.count(Client.id)).filter(
            Client.is_active == True,
            Client.est_actif == True
        )
        if tenant_id:
            products_query = products_query.filter(Produit.tenant_id == tenant_id)
            clients_query = clients_query.filter(Client.tenant_id == tenant_id)

        total_produits = int(products_query.scalar() or 0)
        clients_actifs = int(clients_query.scalar() or 0)

        month_query = db.session.query(
            func.coalesce(func.sum(Vente.total_ttc), 0),
            func.coalesce(func.sum(Vente.total_ttc - Vente.total_ht), 0),
        ).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_mois,
        )
        if tenant_id:
            month_query = month_query.filter(Vente.tenant_id == tenant_id)
        ca_mois, benefice_mois = month_query.one()
        ca_mois = float(ca_mois or 0)
        benefice_mois = float(benefice_mois or 0)

        today_query = db.session.query(
            func.count(Vente.id),
            func.coalesce(func.sum(Vente.total_ttc), 0),
        ).filter(
            Vente.is_active == True,
            Vente.created_at >= debut_jour_utc,
        )
        if tenant_id:
            today_query = today_query.filter(Vente.tenant_id == tenant_id)
        ventes_aujourdhui, ca_aujourdhui = today_query.one()
        ventes_aujourdhui = int(ventes_aujourdhui or 0)
        ca_aujourdhui = float(ca_aujourdhui or 0) if ventes_aujourdhui else None

        alerts_query = db.session.query(
            func.count(Produit.id),
            func.coalesce(
                func.sum(
                    case(
                        (Produit.quantite_stock <= Produit.seuil_critique, 1),
                        else_=0,
                    )
                ),
                0,
            ),
        ).filter(
            Produit.is_active == True,
            Produit.quantite_stock <= Produit.seuil_alerte,
        )
        if tenant_id:
            alerts_query = alerts_query.filter(Produit.tenant_id == tenant_id)
        alertes_stock, alertes_stock_critiques = alerts_query.one()

        first_day_start = debut_jour_utc - timedelta(days=13)
        day_buckets = []
        bucket_columns = []
        for index in range(14):
            day_start = first_day_start + timedelta(days=index)
            day_end = day_start + timedelta(days=1)
            bucket_columns.append(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                (Vente.created_at >= day_start)
                                & (Vente.created_at < day_end),
                                Vente.total_ttc,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(f'day_{index}')
            )
            day_buckets.append(today - timedelta(days=13 - index))

        evolution_row = db.session.query(*bucket_columns).filter(
            Vente.is_active == True,
            Vente.created_at >= first_day_start,
            Vente.created_at < debut_jour_utc + timedelta(days=1),
        )
        if tenant_id:
            evolution_row = evolution_row.filter(Vente.tenant_id == tenant_id)
        evolution_values = evolution_row.one()

        evolution = [
            {
                'date': day_buckets[index].isoformat(),
                'total': float(evolution_values[index] or 0),
            }
            for index in range(7, 14)
        ]
        previous_values = [float(evolution_values[index] or 0) for index in range(7)]
        previous_period_total = sum(previous_values) if any(previous_values) else None
        current_period_has_sales = any(item['total'] > 0 for item in evolution)

        top_products_query = db.session.query(
            LigneVente.produit_id,
            Produit.nom,
            func.sum(LigneVente.quantite).label('total_quantite'),
            func.sum(LigneVente.total_ht).label('total_ca'),
        ).join(
            Produit, Produit.id == LigneVente.produit_id
        ).join(
            Vente, Vente.id == LigneVente.vente_id
        ).filter(
            LigneVente.is_active == True,
            Produit.is_active == True,
            Vente.is_active == True,
        )
        if tenant_id:
            top_products_query = top_products_query.filter(Vente.tenant_id == tenant_id)

        top_products = [
            {
                'produit_id': row[0],
                'nom': row[1],
                'total_quantite': float(row[2] or 0),
                'total_ca': float(row[3] or 0),
            }
            for row in top_products_query.group_by(
                LigneVente.produit_id, Produit.nom
            ).order_by(
                func.sum(LigneVente.quantite).desc()
            ).limit(5).all()
        ]

        recent_query = db.session.query(
            Vente.id,
            Vente.reference,
            Vente.date,
            Vente.created_at,
            Vente.statut,
            Vente.total_ttc,
        ).filter(
            Vente.is_active == True,
        )
        if tenant_id:
            recent_query = recent_query.filter(Vente.tenant_id == tenant_id)
        recent_sales = [
            {
                'id': row[0],
                'reference': row[1],
                'date': row[2].isoformat() if row[2] else None,
                'created_at': row[3].isoformat() if row[3] else None,
                'statut': row[4],
                'total_ttc': float(row[5] or 0),
            }
            for row in recent_query.order_by(Vente.created_at.desc()).limit(10).all()
        ]

        paiements_subquery = db.session.query(
            Paiement.facture_id.label('facture_id'),
            func.coalesce(func.sum(Paiement.montant), 0).label('paiements_total'),
        ).filter(
            Paiement.is_active == True,
        )
        if tenant_id:
            paiements_subquery = paiements_subquery.filter(Paiement.tenant_id == tenant_id)
        paiements_subquery = paiements_subquery.group_by(
            Paiement.facture_id
        ).subquery()

        receivables_query = db.session.query(
            func.count(func.distinct(Client.id)),
            func.coalesce(
                func.sum(
                    Facture.total_ttc
                    - func.coalesce(paiements_subquery.c.paiements_total, 0)
                ),
                0,
            ),
        ).join(
            Facture, Client.id == Facture.client_id
        ).outerjoin(
            paiements_subquery,
            Facture.id == paiements_subquery.c.facture_id,
        ).filter(
            Client.is_active == True,
            Facture.is_active == True,
            Facture.statut != 'payee',
        )
        if tenant_id:
            receivables_query = receivables_query.filter(Client.tenant_id == tenant_id)
        receivables_count, receivables_total = receivables_query.one()

        return {
            'total_produits': total_produits,
            'clients_actifs': clients_actifs,
            'ventes_aujourdhui': ventes_aujourdhui,
            'ca_aujourdhui': ca_aujourdhui,
            'ca_mois': ca_mois,
            'benefice_mois': benefice_mois,
            'alertes_stock': int(alertes_stock or 0),
            'alertes_stock_critiques': int(alertes_stock_critiques or 0),
            'evolution': evolution,
            'previous_period_total': previous_period_total,
            'current_period_has_sales': current_period_has_sales,
            'top_products': top_products,
            'recent_sales': recent_sales,
            'receivables_count': int(receivables_count or 0),
            'receivables_total': float(receivables_total or 0),
        }
    except OperationalError as e:
        return {
            'total_produits': 0,
            'clients_actifs': 0,
            'ventes_aujourdhui': 0,
            'ca_aujourdhui': None,
            'ca_mois': 0.0,
            'benefice_mois': 0.0,
            'alertes_stock': 0,
            'alertes_stock_critiques': 0,
            'evolution': [],
            'previous_period_total': None,
            'current_period_has_sales': False,
            'top_products': [],
            'recent_sales': [],
            'receivables_count': 0,
            'receivables_total': 0.0,
            'db_error': str(e),
        }

