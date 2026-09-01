"""Configuration centralisée des plans d'abonnement et des modules.

Source unique de vérité pour :
- les limites (utilisateurs, admins, employés, stagiaires, produits, clients)
- les modules accessibles par plan
- les prix et durées

Toute limite est dérivée de l'abonnement actif du tenant ; en l'absence
d'abonnement (période d'essai), on retombe sur la configuration du plan
associé au tenant.

HIERARCHIE :
- SUPER_ADMIN ≠ Tenant (le super admin est séparé des tenants, pas d'abonnement)
- ADMIN = Employé du tenant (l'admin est le premier utilisateur du tenant)
- Les plans s'appliquent au TENANT, pas au super admin
- Les paiements d'abonnement vont au SUPER_ADMIN
"""

# Règle absolue : peu importe le plan, le nombre d'administrateurs ne peut
# jamais dépasser cette valeur.
MAX_ADMINS_ABSOLUTE = 5

# Modules connus de l'application. Une route ne doit PAS être accessible juste
# parce qu'elle existe : le module doit être présent dans l'abonnement du tenant.
AVAILABLE_MODULES = [
    'dashboard',
    'produits',
    'clients',
    'ventes',
    'factures',
    'paiements',
    'catalogue',
    'stocks',
    'rh',
    'documents',
    'comptabilite',
    'livraison',
    'ia',
    'achats',
]

_BASIC = ['dashboard', 'produits', 'clients', 'ventes', 'factures', 'paiements', 'catalogue', 'rh']
_EXTENDED = _BASIC + ['stocks', 'documents']
_ALL = _EXTENDED + ['comptabilite', 'livraison', 'ia', 'achats']

# Limites par plan. -1 signifie "illimité".
#
# NB : `max_tenants` n'est PAS un plafond global du nombre de tenants hébergés
# par la plateforme (un SaaS multi-locataire doit pouvoir en accueillir
# autant que nécessaire). Il représente le nombre de filiales/sous-entreprises
# qu'un tenant peut créer sous son propre compte. En l'absence de relation
# parent->enfant entre tenants, la valeur est fixée à -1 (illimité) pour ne
# jamais bloquer l'inscription d'un nouveau tenant.
#
# LOGIQUE DES PLANS :
# - max_utilisateurs = nombre total d'employés que le tenant peut créer
#   (le premier utilisateur est l'admin qui est aussi un employé)
# - Gratuit : 1 employé (l'admin seul, ne peut pas créer d'autres employés)
# - Starter : 3 employés (admin + 2 employés)
# - Pro : 7 employés (admin + 6 employés), modules presque complets
# - Enterprise : employés illimités, tous modules
PLAN_CONFIG = {
    'gratuit': {
        'label': 'Gratuit',
        'max_utilisateurs': 1,
        'max_produits': 10,
        'max_clients': 10,
        'max_admins': 1,
        'max_employees': 0,
        'max_interns': 0,
        'max_tenants': -1,
        'modules': _BASIC,
        'prix': 0,
        'duree_jours': -1,  # Illimité
    },
    'starter': {
        'label': 'Starter',
        'max_utilisateurs': 3,
        'max_produits': 50,
        'max_clients': 100,
        'max_admins': 1,
        'max_employees': 2,
        'max_interns': 0,
        'max_tenants': -1,
        'modules': _EXTENDED,
        'prix': 5000,
        'duree_jours': 30,
    },
    'pro': {
        'label': 'Pro',
        'max_utilisateurs': 7,
        'max_produits': 200,
        'max_clients': 1000,
        'max_admins': 1,
        'max_employees': 6,
        'max_interns': 0,
        'max_tenants': -1,
        'modules': _ALL,
        'prix': 15000,
        'duree_jours': 30,
    },
    'enterprise': {
        'label': 'Enterprise',
        'max_utilisateurs': -1,
        'max_produits': -1,
        'max_clients': -1,
        'max_admins': 1,
        'max_employees': -1,
        'max_interns': -1,
        'max_tenants': -1,
        'modules': _ALL,
        'prix': 25000,
        'duree_jours': 30,
    },
}

DEFAULT_PLAN = 'gratuit'

LIMIT_KEYS = (
    'max_utilisateurs',
    'max_produits',
    'max_clients',
    'max_admins',
    'max_employees',
    'max_interns',
    'max_tenants',
)


def get_plan_config(plan):
    """Retourne la configuration du plan (avec repli sur le plan par défaut)."""
    if not plan:
        return PLAN_CONFIG[DEFAULT_PLAN]
    return PLAN_CONFIG.get(plan, PLAN_CONFIG[DEFAULT_PLAN])


def get_plan_duration_days(plan):
    """Retourne la durée en jours pour un plan. -1 signifie illimité."""
    cfg = get_plan_config(plan)
    return cfg.get('duree_jours', 30)


def get_plan_price(plan):
    """Retourne le prix pour un plan."""
    cfg = get_plan_config(plan)
    return cfg.get('prix', 0)


def is_unlimited(value):
    """Une limite -1 ou None est considérée comme illimitée."""
    return value is None or value == -1


def admin_limit(raw):
    """Applique la règle absolue MAX_ADMINS_ABSOLUTE."""
    if raw is None or raw <= 0:
        return MAX_ADMINS_ABSOLUTE
    return min(raw, MAX_ADMINS_ABSOLUTE)


def resolve_limits(tenant, abonnement=None):
    """Résout les limites pour un tenant.

    Priorité : abonnement actif (si fourni et renseigné), sinon configuration
    du plan du tenant.
    """
    if abonnement is not None:
        limits = {}
        for key in LIMIT_KEYS:
            val = getattr(abonnement, key, None)
            if val is not None:
                limits[key] = val
        if limits:
            limits.setdefault('max_admins', MAX_ADMINS_ABSOLUTE)
            return limits
    cfg = get_plan_config(tenant.plan if tenant else None)
    return {key: cfg.get(key) for key in LIMIT_KEYS}


def resolve_modules(tenant, abonnement=None):
    """Retourne la liste des modules autorisés pour le tenant."""
    if abonnement is not None and getattr(abonnement, 'modules', None):
        mods = abonnement.modules
        if isinstance(mods, str):
            mods = [m.strip() for m in mods.split(',') if m.strip()]
        if mods:
            return list(mods)
    cfg = get_plan_config(tenant.plan if tenant else None)
    return list(cfg.get('modules', []))


def apply_plan_to_abonnement(abonnement, plan=None):
    """Recopie les limites et modules du plan dans l'abonnement."""
    cfg = get_plan_config(plan or abonnement.plan)
    for key in LIMIT_KEYS:
        setattr(abonnement, key, cfg.get(key))
    abonnement.modules = ','.join(cfg.get('modules', []))
    return abonnement


def get_tenant_limit(plan):
    """Retourne la limite de tenants pour un plan donné."""
    cfg = get_plan_config(plan)
    return cfg.get('max_tenants', 1)


def count_active_tenants_for_plan(plan):
    """Compte le nombre de tenants actifs associés à un plan donné."""
    from app.models.tenant import Tenant
    return Tenant.query.filter_by(plan=plan, is_active=True).count()


def check_tenant_limit(plan):
    """Vérifie si la limite de tenants pour un plan est atteinte.

    Aucune limite n'est appliquée : l'inscription d'un nouveau tenant est
    toujours autorisée.

    Retourne un tuple (allowed, message).
    """
    return True, None
