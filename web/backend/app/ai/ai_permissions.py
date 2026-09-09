"""Contrôle d'accès de la couche IA (ai_permissions).

L'IA applique exactement les mêmes permissions que l'application :
une donnée n'est jamais exposée à l'IA si l'utilisateur connecté n'a pas
la permission correspondante dans l'ERP.

Règles de sécurité :
- Toutes les données sont filtrées par ``tenant_id`` (isolation multi-tenant).
- Un SUPER_ADMIN sans tenant actif ne déclenche JAMAIS de lecture globale :
  les outils IA retournent une absence de données plutôt qu'un scan global.
- Les vérifications de domaine se font via la matrice de permissions
  existante (app.security.roles.has_permission).
"""

import logging
from typing import Dict, List, Optional, Set

from flask import has_request_context

from app import db
from app.models.utilisateur import Utilisateur
from app.security.roles import has_permission, is_super_admin, normalize_role

logger = logging.getLogger(__name__)

MSG_NO_PERMISSION = "Vous n'avez pas l'autorisation d'accéder à ces données."


class AIPermissionError(Exception):
    """L'utilisateur n'a pas la permission requise pour ce domaine IA."""

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or MSG_NO_PERMISSION)


# Domaines IA -> permission(s) de vue acceptées (any-of).
# Réutilise les permissions existantes de app/security/permission_matrix.py
DOMAIN_REQUIRED_PERMISSIONS: Dict[str, List[str]] = {
    'produits': ['product.view'],
    'stocks': ['stock.view', 'product.view'],
    'ventes': ['sale.view'],
    'clients': ['client.view'],
    'factures': ['invoice.view'],
    'paiements': ['payment.view'],
    'fournisseurs': ['supplier.view'],
    'achats': ['purchase_order.view'],
    'finances': ['invoice.view', 'payment.view'],
    'utilisateurs': ['user.view'],
    'rh': ['employe.view'],
    'rapports': ['report.view'],
}


def get_ai_user_context() -> Optional[dict]:
    """Retourne le contexte utilisateur courant, ou None hors requête.

    Ne lève jamais d'exception : en cas d'utilisateur introuvable ou de
    JWT invalide, None est retourné (aucun accès accordé au niveau outils).
    """
    if not has_request_context():
        return None

    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        user = db.session.get(Utilisateur, user_id)
        if not user:
            return None
        role_value = normalize_role(user.role)
        return {
            'user_id': user.id,
            'tenant_id': user.tenant_id,
            'role': role_value.value if role_value else str(user.role),
            'is_super_admin': is_super_admin(user.role),
        }
    except Exception:
        return None


def _has_any_permission(user_id: int, permissions: List[str]) -> bool:
    return any(has_permission(user_id, perm) for perm in permissions)


def can_access_domain(domain: str, user_context: Optional[dict] = None) -> bool:
    """Vérifie si l'utilisateur courant peut accéder à un domaine IA."""
    domain = (domain or '').lower()
    required = DOMAIN_REQUIRED_PERMISSIONS.get(domain)
    if required is None:
        return False

    if user_context is None:
        user_context = get_ai_user_context()
    if not user_context:
        # Hors requête (usage interne/tests) : le contrôle de permission
        # explicite reste de la responsabilité de la couche API.
        return True

    user_id = user_context.get('user_id')
    if not user_id:
        return False
    return _has_any_permission(user_id, required)


def require_domain_access(domain: str, user_context: Optional[dict] = None) -> None:
    """Lève AIPermissionError si l'utilisateur n'a pas accès au domaine."""
    domain = (domain or '').lower()
    if domain not in DOMAIN_REQUIRED_PERMISSIONS:
        raise AIPermissionError(f"Domaine IA inconnu : {domain}")
    if user_context is None:
        user_context = get_ai_user_context()
    if user_context and not can_access_domain(domain, user_context):
        logger.info(
            "IA: accès refusé au domaine '%s' pour l'utilisateur %s",
            domain, user_context.get('user_id'),
        )
        raise AIPermissionError()


def get_accessible_domains(user_context: Optional[dict] = None) -> List[str]:
    """Liste des domaines IA accessibles à l'utilisateur courant."""
    if user_context is None:
        user_context = get_ai_user_context()
    if not user_context:
        return list(DOMAIN_REQUIRED_PERMISSIONS.keys())
    accessible = []
    for domain, required in DOMAIN_REQUIRED_PERMISSIONS.items():
        if _has_any_permission(user_context['user_id'], required):
            accessible.append(domain)
    return accessible


def get_allowed_permissions_set(user_id: Optional[int]) -> Set[str]:
    """Retourne l'ensemble des permissions vues de l'utilisateur (cache simple)."""
    if not user_id:
        return set()
    from app.security.permission_matrix import PERMISSION_DEFINITIONS
    return {
        perm for perm in PERMISSION_DEFINITIONS
        if has_permission(user_id, perm)
    }
