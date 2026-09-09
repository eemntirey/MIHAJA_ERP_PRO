"""Construction des prompts système pour l'IA (ai_prompts).

Les prompts intègrent le contexte du tenant, les domaines accessibles
selon les permissions, et les consignes de sécurité (pas d'invention
de données, explications, actions avec confirmation).
"""

from typing import List, Optional

from app.ai.ai_permissions import get_accessible_domains


def build_system_prompt(tenant_name: Optional[str] = None,
                        accessible_domains: Optional[List[str]] = None) -> str:
    """Construit le prompt système de l'assistant IA."""
    tenant_label = tenant_name or 'votre entreprise'

    if accessible_domains is None:
        accessible_domains = get_accessible_domains()

    domaines_fr = {
        'produits': 'produits',
        'stocks': 'stocks',
        'ventes': 'ventes',
        'clients': 'clients',
        'factures': 'factures',
        'paiements': 'paiements',
        'fournisseurs': 'fournisseurs',
        'achats': 'achats / commandes fournisseurs',
        'finances': 'finances (créances, factures)',
        'utilisateurs': 'utilisateurs',
        'rh': 'ressources humaines',
        'rapports': 'rapports et analyses',
    }
    domaines_str = ', '.join(domaines_fr.get(d, d) for d in accessible_domains) or 'aucun'

    return (
        "Vous êtes l'assistant IA d'un ERP commercial multi-tenant. "
        f"Vous répondez en français, de manière concise, professionnelle et factuelle. "
        f"Vous vous appuyez UNIQUEMENT sur les données métier réelles du tenant "
        f"'{tenant_label}', accessibles via les outils internes. "
        f"Domaines accessibles pour cet utilisateur : {domaines_str}. "
        "Règles absolues :\n"
        "1. N'inventez JAMAIS de donnée. Si une information n'existe pas, dites-le.\n"
        "2. Si les données sont insuffisantes, indiquez-le clairement.\n"
        "3. Expliquez vos conclusions (pourquoi, sur quelle base chiffrée).\n"
        "4. Ne donnez jamais accès à un domaine non autorisé ; indiquez le refus.\n"
        "5. Pour toute action sensible (création, modification, transaction), "
        "proposez l'action et demandez une CONFIRMATION explicite avant exécution.\n"
        "6. N'accusez jamais un utilisateur de fraude ; parlez d'anomalie à vérifier."
    )


def build_context_block(tenant_id, accessible_domains: Optional[List[str]] = None) -> str:
    """Bloc de contexte métier synthétique (données réelles, agrégées)."""
    try:
        from app.ai import ai_tools
        parts = []

        if _can('stocks', accessible_domains):
            health = ai_tools.get_stock_health(tenant_id=tenant_id)
            if health.get('data_sufficient'):
                parts.append(
                    f"Stock : {health.get('nb_produits', 0)} produits, "
                    f"{health.get('ruptures', 0)} rupture(s), "
                    f"{health.get('alertes', 0)} alerte(s).")

        if _can('ventes', accessible_domains):
            sales = ai_tools.get_sales_summary(tenant_id=tenant_id, days=30)
            if sales.get('data_sufficient'):
                parts.append(
                    f"Ventes 30j : CA {sales.get('total_ttc', 0):,.2f} MGA, "
                    f"{sales.get('nb_ventes', 0)} vente(s), "
                    f"variation {sales.get('variation_pct', 'n/a')} %.")

        if _can('finances', accessible_domains):
            debts = ai_tools.get_customer_debts(tenant_id=tenant_id, limit=5)
            if debts.get('count', 0) > 0:
                parts.append(
                    f"Créances : {debts.get('count', 0)} pour "
                    f"{debts.get('total_creances', 0):,.2f} MGA.")

        if _can('achats', accessible_domains):
            pending = ai_tools.get_pending_purchase_orders(tenant_id=tenant_id, limit=5)
            if pending.get('count', 0) > 0:
                parts.append(f"Commandes fournisseurs en cours : {pending.get('count', 0)}.")

        return "Contexte métier actuel : " + ' '.join(parts) if parts else "Contexte métier : données insuffisantes."
    except Exception:
        return "Contexte métier indisponible pour le moment."


def _can(domain: str, accessible_domains: Optional[List[str]]) -> bool:
    if accessible_domains is None:
        return True
    return domain in accessible_domains
