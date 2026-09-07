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

# Système d'augmentation automatique du prix à l'expiration.
#
# Objectif : encourager le tenant à renouveler avant l'échéance. Si
# l'abonnement arrive à expiration sans avoir été renouvelé, le prix
# officiel du plan est majoré pour le paiement suivant.
#
# Configuration par plan :
# - expiration_penalty_percent : pourcentage d'augmentation appliqué au
#   prix de base du plan lorsque l'abonnement a expiré avant paiement.
#   Ex: 0.20 = +20% (le tenant paiera 20% plus cher s'il paie après
#   expiration plutôt qu'avant).
# - expiration_grace_days : nombre de jours de tolérance après la date
#   de fin pendant lesquels le prix reste inchangé. Passé ce délai, la
#   pénalité s'applique.
#
# NOTE : La pénalité est calculée à la volée lors de la consultation ou
# du paiement ; aucun champ n'est figé sur l'abonnement.
EXPIRATION_PENALTY_CONFIG = {
    'gratuit': {
        'expiration_penalty_percent': 0.0,
        'expiration_grace_days': 0,
    },
    'starter': {
        'expiration_penalty_percent': 0.20,
        'expiration_grace_days': 3,
    },
    'pro': {
        'expiration_penalty_percent': 0.25,
        'expiration_grace_days': 3,
    },
    'enterprise': {
        'expiration_penalty_percent': 0.30,
        'expiration_grace_days': 5,
    },
}

DEFAULT_EXPIRATION_PENALTY_PERCENT = 0.20
DEFAULT_EXPIRATION_GRACE_DAYS = 3


def get_expiration_penalty_config(plan):
    """Retourne la config de pénalité d'expiration pour un plan (avec fallback)."""
    if not plan:
        plan = DEFAULT_PLAN
    cfg = EXPIRATION_PENALTY_CONFIG.get(plan)
    if cfg is None:
        return {
            'expiration_penalty_percent': DEFAULT_EXPIRATION_PENALTY_PERCENT,
            'expiration_grace_days': DEFAULT_EXPIRATION_GRACE_DAYS,
        }
    return cfg


def compute_effective_subscription_price(base_price, plan, expired=False, days_after_expiry=0):
    """Calcule le prix effectif d'un abonnement selon son état.

    - `base_price` : prix de base du plan.
    - `plan` : code du plan.
    - `expired` : True si l'abonnement est expiré (date_fin dépassée).
    - `days_after_expiry` : nombre de jours depuis l'expiration.

    Retourne un dictionnaire avec :
    - `prix_base` : prix de base du plan.
    - `prix_final` : prix réellement dû (avec pénalité éventuelle).
    - `penalty_percent` : pourcentage appliqué (0 si pas de pénalité).
    - `penalty_amount` : montant de la pénalité (>= 0).
    - `penalty_active` : True si la pénalité s'applique.
    """
    base_price = base_price or 0
    if base_price <= 0 or not expired:
        return {
            'prix_base': base_price,
            'prix_final': base_price,
            'penalty_percent': 0.0,
            'penalty_amount': 0,
            'penalty_active': False,
        }
    cfg = get_expiration_penalty_config(plan)
    grace = cfg.get('expiration_grace_days', 0)
    penalty_pct = cfg.get('expiration_penalty_percent', 0.0)
    penalty_active = days_after_expiry > grace
    if penalty_active and penalty_pct > 0:
        penalty_amount = round(base_price * penalty_pct)
        prix_final = base_price + penalty_amount
    else:
        penalty_amount = 0
        prix_final = base_price
        penalty_pct = 0.0
    return {
        'prix_base': base_price,
        'prix_final': prix_final,
        'penalty_percent': penalty_pct,
        'penalty_amount': penalty_amount,
        'penalty_active': penalty_active,
    }


def days_since_expiration(abonnement):
    """Nombre de jours depuis l'expiration d'un abonnement (0 si non expiré)."""
    from datetime import datetime
    if not abonnement or not abonnement.date_fin:
        return 0
    now = datetime.utcnow()
    if abonnement.date_fin >= now:
        return 0
    delta = now - abonnement.date_fin
    return max(0, delta.days)


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
