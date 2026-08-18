from app.models.produit import Produit
from app.models.vente import Vente
from app.models.client import Client
from app.models.fournisseur import Fournisseur
from app.models.facture import Facture
from app.models.ligne_vente import LigneVente
from app.security.tenant import get_current_tenant_id
from app.ai.previsions import predict_sales, predict_stock_rupture
from app.ai.recommendations import suggest_reorders
from app.ai.external_services import external_ai, web_search, context_manager
from app import db
import logging

logger = logging.getLogger(__name__)


def _get_tenant_name(tenant_id):
    try:
        from app.models.tenant import Tenant
        tenant = Tenant.query.get(tenant_id)
        return tenant.nom if tenant else None
    except Exception:
        return None


def _build_context_block(tenant_id):
    """Construit un contexte métier synthétique pour l'IA."""
    try:
        produits = Produit.query.filter_by(is_active=True)
        if tenant_id:
            produits = produits.filter_by(tenant_id=tenant_id)
        nb_produits = produits.count()

        ventes = Vente.query.filter_by(is_active=True)
        if tenant_id:
            ventes = ventes.filter_by(tenant_id=tenant_id)
        nb_ventes = ventes.count()
        ca_total = sum(float(v.total_ttc or 0) for v in ventes.limit(200).all())

        clients = Client.query.filter_by(is_active=True)
        if tenant_id:
            clients = clients.filter_by(tenant_id=tenant_id)
        nb_clients = clients.count()

        factures = Facture.query.filter_by(is_active=True)
        if tenant_id:
            factures = factures.filter_by(tenant_id=tenant_id)
        nb_factures = factures.count()

        alertes = Produit.query.filter(
            Produit.is_active == True,
            Produit.quantite_stock <= Produit.seuil_alerte
        )
        if tenant_id:
            alertes = alertes.filter_by(tenant_id=tenant_id)
        nb_alertes = alertes.count()

        return (
            f"Contexte métier actuel : {nb_produits} produits, {nb_clients} clients, "
            f"{nb_ventes} ventes, CA total {ca_total:.2f} Ar, {nb_factures} factures, "
            f"{nb_alertes} alerte(s) stock."
        )
    except Exception as e:
        logger.error(f"Erreur build_context_block: {str(e)}")
        return "Contexte métier indisponible pour le moment."


def ask_assistant(tenant_id=None, prompt="", conversation=None):
    tenant_id = get_current_tenant_id() or tenant_id
    prompt_lower = prompt.lower().strip() if prompt else ""

    if not prompt_lower:
        return "Bonjour ! Je suis l'assistant IA de votre ERP. Comment puis-je vous aider aujourd'hui ? Vous pouvez me poser des questions sur les stocks, les ventes, les clients, les factures ou les prévisions."

    tenant_name = _get_tenant_name(tenant_id)
    system_prompt = context_manager.build_system_prompt(tenant_name)
    context_block = _build_context_block(tenant_id)

    # Réponse interne forte pour les requêtes métier classiques
    internal_answer = _answer_internal(tenant_id, prompt_lower)
    if internal_answer:
        if external_ai.is_configured():
            enriched = _enrich_with_external_ai(
                prompt=prompt,
                prompt_lower=prompt_lower,
                system_prompt=system_prompt,
                context_block=context_block,
                internal_answer=internal_answer,
                conversation=conversation
            )
            if enriched:
                return enriched
        return internal_answer

    # Si pas de réponse interne, demander à l'IA externe si dispo
    if external_ai.is_configured():
        external_answer = _ask_external(
            prompt=prompt,
            prompt_lower=prompt_lower,
            system_prompt=system_prompt,
            context_block=context_block,
            conversation=conversation
        )
        if external_answer:
            return external_answer

    return ("**Assistant IA ERP** : Je peux vous assister sur plusieurs sujets :\n"
            "- *« Quel est l'état du stock ? »*\n"
            "- *« Quel est notre chiffre d'affaires ? »*\n"
            "- *« Quelles sont les prévisions de ventes ? »*\n"
            "- *« Combien de clients avons-nous ? »*\n"
            "- *« Quel est le montant des factures impayées ? »*")


def _answer_internal(tenant_id, prompt_lower):
    if any(w in prompt_lower for w in ['prévision', 'prevision', 'projections', 'futur', 'tendance']):
        prev = predict_sales(tenant_id=tenant_id, periods=30)
        return (f"**Prévisions de Ventes (30 prochains jours)** :\n"
                f"- Chiffre d'affaires estimé : **{prev['total_predicted']:.2f} Ar**\n"
                f"- Moyenne journalière : **{prev['average_daily_predicted']:.2f} Ar/jour**\n"
                f"- Tendance observée : **{prev['trend'].upper()}**\n"
                f"- Indice de confiance du modèle : **{int(prev['confidence_score']*100)}%**")

    if any(w in prompt_lower for w in ['réapprovision', 'réapprovisionnement', 'reorder', 'commande fournisseur', 'stock à commander', 'approvisionnement']):
        recommandations = suggest_reorders(tenant_id=tenant_id)
        suggestions = recommandations.get('recommendations') if isinstance(recommandations, dict) else None
        if not suggestions:
            return "Aucune recommandation de réapprovisionnement n'a été trouvée pour le moment."
        lines = []
        for item in suggestions[:5]:
            label = item.get('nom') or item.get('product_name') or 'Produit inconnu'
            quantity = item.get('quantite_suggeree') or item.get('suggested_quantity') or 0
            lines.append(f"- {label} : quantité suggérée {quantity}")
        return "**Réapprovisionnement recommandé** :\n" + "\n".join(lines)

    if any(w in prompt_lower for w in ['stock', 'inventaire', 'rupture', 'seuil', 'alerte']):
        produits = Produit.query.filter_by(is_active=True)
        if tenant_id:
            produits = produits.filter_by(tenant_id=tenant_id)
        produits_list = produits.all()
        alertes = [p for p in produits_list if (p.quantite_stock or 0) <= (p.seuil_alerte or 0)]
        ruptures = [p for p in produits_list if (p.quantite_stock or 0) == 0]
        recommandations = suggest_reorders(tenant_id=tenant_id)
        nb_recommandations = recommandations.get('count', 0) if isinstance(recommandations, dict) else 0
        if ruptures:
            msg = f"**Attention** : {len(ruptures)} produit(s) en rupture totale de stock ({', '.join([p.nom for p in ruptures[:3]])}).\n"
        elif alertes:
            msg = f"**Alerte Stock** : {len(alertes)} produit(s) ont atteint leur seuil d'alerte.\n"
        else:
            msg = f"**Stock au vert** : Les {len(produits_list)} produits du catalogue disposent d'un niveau de stock suffisant.\n"
        if nb_recommandations > 0:
            msg += f"**Conseil IA** : {nb_recommandations} réapprovisionnement(s) suggéré(s)."
        return msg

    if any(w in prompt_lower for w in ['top produit', 'meilleur produit', 'meilleures ventes', 'produits les plus vendus', 'top ventes']):
        results = db.session.query(
            LigneVente.produit_id,
            db.func.sum(LigneVente.quantite).label('quantite_vendue'),
            db.func.sum(LigneVente.total_ttc).label('montant_total')
        ).join(Vente, LigneVente.vente_id == Vente.id)
        results = results.filter(Vente.is_active == True)
        if tenant_id:
            results = results.filter(Vente.tenant_id == tenant_id)
        results = results.group_by(LigneVente.produit_id).order_by(db.desc('quantite_vendue')).limit(3).all()
        if not results:
            return "Je n'ai pas trouvé de données de vente suffisantes pour établir un top des produits."
        lines = []
        for row in results:
            produit_query = Produit.query.filter_by(id=row.produit_id)
            if tenant_id:
                produit_query = produit_query.filter_by(tenant_id=tenant_id)
            produit = produit_query.first()
            label = produit.nom if produit else f'Produit #{row.produit_id}'
            lines.append(f"- {label} : {float(row.quantite_vendue):.0f} unités vendues, {float(row.montant_total or 0):.2f} Ar")
        return "**Produits les plus vendus** :\n" + "\n".join(lines)

    if any(w in prompt_lower for w in ['vente', 'ca', 'chiffre', 'chiffre d\'affaires', 'revenu']):
        ventes = Vente.query.filter_by(is_active=True)
        if tenant_id:
            ventes = ventes.filter_by(tenant_id=tenant_id)
        ventes_list = ventes.all()
        total_ca = sum(float(v.total_ttc or 0) for v in ventes_list)
        return f"**Chiffre d'Affaires Total** : **{total_ca:.2f} Ar** générés sur un total de **{len(ventes_list)} ventes** enregistrées."

    if any(w in prompt_lower for w in ['facture', 'impayé', 'impayee', 'retard', 'paiement']):
        factures = Facture.query.filter_by(is_active=True)
        if tenant_id:
            factures = factures.filter_by(tenant_id=tenant_id)
        factures_list = factures.all()
        impayees = [f for f in factures_list if getattr(f.statut, 'value', str(f.statut)).lower() in ['non_payee', 'payee_partiel', 'en_attente']]
        montant_impaye = sum(float(f.total_ttc or 0) for f in impayees)
        return f"**Factures** : **{len(impayees)} facture(s) en attente ou non payée(s)** pour un montant total restant dû de **{montant_impaye:.2f} Ar** sur {len(factures_list)} factures émises."

    if any(w in prompt_lower for w in ['client', 'acheteur']):
        clients = Client.query.filter_by(is_active=True)
        if tenant_id:
            clients = clients.filter_by(tenant_id=tenant_id)
        nb_clients = clients.count()
        return f"**Portefeuille Clients** : Vous avez actuellement **{nb_clients} client(s) actif(s)** enregistrés dans le système."

    if any(w in prompt_lower for w in ['fournisseur', 'achat', 'commande']):
        fournisseurs = Fournisseur.query.filter_by(is_active=True)
        if tenant_id:
            fournisseurs = fournisseurs.filter_by(tenant_id=tenant_id)
        return f"**Fournisseurs** : **{fournisseurs.count()} fournisseur(s)** enregistrés."

    return None


def _enrich_with_external_ai(prompt, prompt_lower, system_prompt, context_block, internal_answer, conversation):
    enriched_query = (
        "Réponds en français, de façon professionnelle et concise.\n"
        f"Contexte interne vérifié : {context_block}\n"
        f"Réponse interne validée : {internal_answer}\n"
        f"Question de l'utilisateur : {prompt}\n"
        "Si des sources externes peuvent préciser la réponse, cite-les clairement."
    )
    messages = context_manager.build_messages(conversation or [], enriched_query)
    result = external_ai.chat(messages=messages, system_prompt=system_prompt)
    if result.get('content'):
        sources = []
        if result.get('provider') and result['provider'] != 'local':
            sources.append({
                'name': result['provider'],
                'type': 'ia',
                'url': ''
            })
        if web_search and _should_web_search(prompt_lower):
            web_results = web_search.search(prompt, max_results=3)
            sources.extend([{**r, 'type': 'web'} for r in web_results])
        if sources:
            source_lines = "\n\n**Sources** :\n" + "\n".join(
                f"- {s['name']}: {s['url'] or 'réponse générée'}" for s in sources
            )
            return result['content'] + source_lines
        return result['content']
    return None


def _ask_external(prompt, prompt_lower, system_prompt, context_block, conversation):
    enriched_query = (
        "Réponds en français, de façon professionnelle et concise.\n"
        f"Contexte interne : {context_block}\n"
        f"Question : {prompt}\n"
        "Tu peux utiliser des recherches web si nécessaire."
    )
    messages = context_manager.build_messages(conversation or [], enriched_query)
    result = external_ai.chat(messages=messages, system_prompt=system_prompt)
    if result.get('content'):
        sources = []
        if result.get('provider') and result['provider'] != 'local':
            sources.append({
                'name': result['provider'],
                'type': 'ia',
                'url': ''
            })
        if web_search and _should_web_search(prompt_lower):
            web_results = web_search.search(prompt, max_results=3)
            sources.extend([{**r, 'type': 'web'} for r in web_results])
        if sources:
            source_lines = "\n\n**Sources** :\n" + "\n".join(
                f"- {s['name']}: {s['url'] or 'réponse générée'}" for s in sources
            )
            return result['content'] + source_lines
        return result['content']
    return None


def _should_web_search(prompt_lower: str) -> bool:
    triggers = [
        'marché', 'tendance', 'concurrent', 'prix du marché',
        'norme', 'réglementation', 'loi', 'actualité', 'news'
    ]
    return any(t in prompt_lower for t in triggers)

