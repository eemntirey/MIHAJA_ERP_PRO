from app.models.produit import Produit
from app.models.vente import Vente
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.security.tenant import get_current_tenant_id
from app import db
from sqlalchemy import func


def suggest_reorders(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    produits = query.all()

    recommendations = []
    for p in produits:
        stock_actuel = float(p.quantite_stock or 0)
        seuil_alerte = float(p.seuil_alerte or 0)
        seuil_critique = float(p.seuil_critique or 0)

        if stock_actuel <= seuil_alerte or stock_actuel <= 5:
            # Calcul de la quantité optimale de réapprovisionnement
            quantite_suggeree = max(20, int((seuil_alerte * 2.5) - stock_actuel))

            is_critique = stock_actuel <= seuil_critique or stock_actuel == 0
            score = (seuil_alerte - stock_actuel) / max(seuil_alerte, 1) if seuil_alerte > 0 else 1.0

            fournisseur = db.session.get(Fournisseur, p.fournisseur_id) if getattr(p, 'fournisseur_id', None) else None

            recommendations.append({
                'produit_id': p.id,
                'nom': p.nom,
                'reference': getattr(p, 'reference', f'REF-{p.id}'),
                'stock_actuel': stock_actuel,
                'seuil_alerte': seuil_alerte,
                'seuil_critique': seuil_critique,
                'quantite_suggeree': quantite_suggeree,
                'prix_achat_estime': round(quantite_suggeree * float(p.prix_achat_ht or 0), 2),
                'fournisseur_nom': fournisseur.raison_sociale if fournisseur else 'Non spécifié',
                'priorite': 'CRITIQUE' if is_critique else 'HAUTE',
                'score': round(float(score), 2)
            })

    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return {'recommendations': recommendations, 'count': len(recommendations)}


def suggest_cross_sell(client_id):
    from app.models.ligne_vente import LigneVente
    tenant_id = get_current_tenant_id()
    ventes = Vente.query.filter_by(client_id=client_id, is_active=True)
    if tenant_id:
        ventes = ventes.filter_by(tenant_id=tenant_id)
    ventes = ventes.all()
    if not ventes:
        popular = Produit.query.filter_by(is_active=True)
        if tenant_id:
            popular = popular.filter_by(tenant_id=tenant_id)
        popular = popular.limit(5).all()
        return {
            'recommendations': [{'produit_id': p.id, 'nom': p.nom, 'prix': float(p.prix_vente_ht or 0)} for p in popular],
            'count': len(popular)
        }

    vente_ids = [v.id for v in ventes]
    lignes = LigneVente.query.filter(LigneVente.vente_id.in_(vente_ids), LigneVente.is_active == True).all()
    produits_achetes = set(l.produit_id for l in lignes)

    autres_produits = Produit.query.filter(
        Produit.is_active == True,
        ~Produit.id.in_(produits_achetes)
    )
    if tenant_id:
        autres_produits = autres_produits.filter_by(tenant_id=tenant_id)
    autres_produits = autres_produits.limit(5).all()

    return {
        'recommendations': [{'produit_id': p.id, 'nom': p.nom, 'prix': float(p.prix_vente_ht or 0)} for p in autres_produits],
        'count': len(autres_produits)
    }


def suggest_pricing_adjustments(tenant_id=None):
    tenant_id = get_current_tenant_id() or tenant_id
    query = Produit.query.filter_by(is_active=True)
    if tenant_id:
        query = query.filter_by(tenant_id=tenant_id)
    produits = query.all()

    suggestions = []
    for p in produits:
        prix_achat = float(p.prix_achat_ht or 0)
        prix_vente = float(p.prix_vente_ht or 0)

        if prix_achat > 0:
            marge_pct = ((prix_vente - prix_achat) / prix_achat) * 100
            if marge_pct < 15.0:
                nouveau_prix = round(prix_achat * 1.25, 2)
                suggestions.append({
                    'produit_id': p.id,
                    'nom': p.nom,
                    'prix_actuel': prix_vente,
                    'marge_actuelle_pct': round(marge_pct, 1),
                    'prix_suggere': nouveau_prix,
                    'marge_cible_pct': 25.0,
                    'raison': 'Marge trop faible (< 15%)'
                })
            elif float(p.quantite_stock or 0) > 100 and marge_pct > 50.0:
                nouveau_prix = round(prix_vente * 0.9, 2)
                suggestions.append({
                    'produit_id': p.id,
                    'nom': p.nom,
                    'prix_actuel': prix_vente,
                    'marge_actuelle_pct': round(marge_pct, 1),
                    'prix_suggere': nouveau_prix,
                    'marge_cible_pct': round(marge_pct * 0.9, 1),
                    'raison': 'Surstock et marge élevée : promotion recommandée (-10%)'
                })

    return {'suggestions': suggestions, 'count': len(suggestions)}
