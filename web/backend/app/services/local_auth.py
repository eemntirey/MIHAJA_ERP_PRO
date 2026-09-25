# web/backend/app/services/local_auth.py
# Authentification du backend embarque (desktop hors-ligne).
#
# Principe (cf. plan Task 7) :
#  1. le poste tente un login EN LIGNE (proxy vers le central) ;
#  2. en cas de succes, le mot de passe est mis en cache (scrypt) et la
#     ligne utilisateur/tenant est miroirée en local ;
#  3. hors reseau, la verification se fait contre ce cache local.
#
# Sans etape 2, un poste jamais connecte ne peut pas s'authentifier hors
# ligne : c'est la contrepartie assumee du mode embarque.
import hashlib
import hmac
import logging
import os

import requests
from flask import current_app
from flask_jwt_extended import create_access_token, create_refresh_token

from app import db

logger = logging.getLogger(__name__)

# Duree maximale d'un login proxifie vers le central (secondes).
_PROXY_TIMEOUT = 8
_SCRYPT_PREFIX = 'scrypt'


def _hash_local_password(password):
    """Hash scrypt (jamais reversible, sel aleatoire par utilisateur)."""
    salt = os.urandom(16)
    derived = hashlib.scrypt(
        password.encode('utf-8'), salt=salt, n=16384, r=8, p=1, dklen=32,
    )
    return f'{_SCRYPT_PREFIX}${salt.hex()}${derived.hex()}'


def verify_local_password(password, stored):
    """Verifie un mot de passe contre un hash scrypt local."""
    if not stored or not password:
        return False
    try:
        prefix, salt_hex, hash_hex = stored.split('$')
        if prefix != _SCRYPT_PREFIX:
            return False
        derived = hashlib.scrypt(
            password.encode('utf-8'), salt=bytes.fromhex(salt_hex),
            n=16384, r=8, p=1, dklen=32,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived.hex(), hash_hex)


def cache_local_credentials(user, raw_password):
    """Memorise le hash scrypt du mot de passe pour le mode hors-ligne."""
    user.local_password_hash = _hash_local_password(raw_password)
    db.session.commit()
    return user.local_password_hash


def _offline_error():
    return (
        'Identifiants incorrects (mode hors-ligne : seule la dernière '
        'session enregistrée peut se connecter).'
    )


def _central_url():
    return (current_app.config.get('REPLICATION_URL') or '').rstrip('/')


def _proxy_login(identifier, password, tenant_slug, device_id):
    """Login en ligne (proxy vers le central).

    Retourne (status_code, body). `None` en status_code => central injoignable.
    """
    base = _central_url()
    if not base:
        return None, None
    payload = {'username': identifier, 'password': password}
    if tenant_slug:
        payload['tenant_slug'] = tenant_slug
    if device_id:
        payload['device_id'] = device_id
    try:
        response = requests.post(
            f'{base}/api/v1/auth/login', json=payload, timeout=_PROXY_TIMEOUT,
        )
    except Exception as exc:
        logger.warning('Central injoignable (%s) : bascule hors-ligne.', exc)
        return None, None
    try:
        body = response.json()
    except Exception:
        body = {}
    return response.status_code, body


def _proxy_me(token):
    """Récupère le tenant (et l'utilisateur) depuis le central."""
    base = _central_url()
    if not base:
        return {}
    try:
        response = requests.get(
            f'{base}/api/v1/auth/me',
            headers={'Authorization': f'Bearer {token}'},
            timeout=_PROXY_TIMEOUT,
        )
        if response.status_code != 200:
            return {}
        return response.json() or {}
    except Exception:
        return {}


def _mirror_tenant(tenant_data):
    """Crée/met à jour le tenant local à partir des données du central."""
    from app.models.tenant import StatutTenant, Tenant

    if not tenant_data:
        return None
    slug = tenant_data.get('slug')
    tenant = None
    if slug:
        tenant = Tenant.query.filter_by(slug=slug).first()
    if tenant is None:
        tenant = Tenant(
            nom=tenant_data.get('nom') or slug or 'Tenant',
            slug=slug or f'local-{tenant_data.get("id")}',
            domaine=tenant_data.get('domaine') or 'local',
            statut=StatutTenant.ACTIF,
            plan=tenant_data.get('plan') or 'gratuit',
        )
        db.session.add(tenant)
    else:
        tenant.nom = tenant_data.get('nom') or tenant.nom
    db.session.flush()
    return tenant


def _mirror_user(user_data, tenant, raw_password):
    """Crée/met à jour l'utilisateur local (avec cache scrypt du mot de passe)."""
    from app.models.utilisateur import Role, StatutUtilisateur, Utilisateur
    from app.security.auth import hash_password

    username = user_data.get('username')
    user = Utilisateur.query.filter_by(username=username).first()
    role_value = user_data.get('role') or 'user'
    try:
        role = Role(role_value)
    except ValueError:
        role = Role.USER

    if user is None:
        # `password_hash` (NOT NULL) reste un hash bcrypt aleatoire : le
        # chemin en ligne passe par le proxy, le chemin hors-ligne par le
        # hash scrypt dédié.
        user = Utilisateur(
            username=username,
            email=user_data.get('email') or f'{username}@local',
            password_hash=hash_password(os.urandom(24).hex()),
            role=role,
            tenant_id=tenant.id if tenant else None,
            statut=StatutUtilisateur.ACTIF,
            is_active=True,
        )
        db.session.add(user)
    else:
        user.email = user_data.get('email') or user.email
        user.role = role
        user.tenant_id = tenant.id if tenant else user.tenant_id
        user.is_active = True
    db.session.flush()
    cache_local_credentials(user, raw_password)
    return user


def _issue_local_tokens(user, tenant):
    """Génère les jetons JWT locaux (mêmes claims que le central)."""
    from app.security.auth import _build_token_claims

    claims = _build_token_claims(user, tenant)
    access_token = create_access_token(identity=user.id, additional_claims=claims)
    refresh_token = create_refresh_token(
        identity=user.id,
        additional_claims={'pwd_v': user.token_version or 0},
    )
    return access_token, refresh_token


def authenticate_local_device(identifier, password, tenant_slug=None,
                             device_id=None):
    """Authentification du backend embarqué.

    Retourne (result, error) comme `app.security.auth.authenticate_user`.
    `result['offline']` vaut True lorsque la vérification s'est faite sur le
    cache local (central injoignable).
    """
    from app import db as _db
    from app.models.sync_replica import SyncState
    from app.models.tenant import Tenant
    from app.models.utilisateur import StatutUtilisateur, Utilisateur
    from app.services.local_bootstrap import ensure_local_cursors
    from app.services.replication import SUPPRESS_OUTBOX_KEY

    status_code, body = _proxy_login(
        identifier, password, tenant_slug, device_id
    )

    if status_code == 200 and isinstance(body, dict) and body.get('access_token'):
        token = body['access_token']
        me = _proxy_me(token) or {}
        user_data = me.get('user') or body.get('user') or {}
        tenant_data = me.get('tenant') or body.get('tenant')

        _db.session.info[SUPPRESS_OUTBOX_KEY] = True
        try:
            tenant = _mirror_tenant(tenant_data)
            user = _mirror_user(user_data, tenant, password)
            current_app.extensions['repl_token'] = token
            local_access_token, local_refresh_token = _issue_local_tokens(user, tenant)
            SyncState.set_service_token(token, body.get('refresh_token'))
            if tenant is not None:
                current_app.config['LOCAL_TENANT_ID'] = tenant.id
                ensure_local_cursors(tenant.id)
            _db.session.commit()
            try:
                from app.services.replication.pull import pull_changes
                pull_changes(current_app._get_current_object())
            except Exception as exc:
                logger.warning('Premiere synchronisation centrale impossible : %s', exc)
        finally:
            _db.session.info.pop(SUPPRESS_OUTBOX_KEY, None)

        return {
            'access_token': local_access_token,
            'refresh_token': local_refresh_token,
            'user': user.to_dict(),
            'tenant': tenant.to_dict() if tenant else None,
            'must_change_password': bool(user.must_change_password),
            'offline': False,
        }, None

    if status_code in (400, 401, 403):
        # Identifiants refusés par le central : ne PAS se rabattre sur le
        # cache local (sinon un mot de passe révoqué resterait utilisable).
        message = None
        if isinstance(body, dict):
            message = body.get('message')
        return None, message or 'Identifiants invalides'

    # --- Mode hors-ligne : vérification contre le cache scrypt local -------
    from sqlalchemy import or_

    user = Utilisateur.query.filter(
        or_(Utilisateur.username == identifier, Utilisateur.email == identifier)
    ).first()
    if user is None or not user.is_active:
        return None, _offline_error()
    if user.statut != StatutUtilisateur.ACTIF:
        return None, _offline_error()
    if not verify_local_password(password, user.local_password_hash):
        return None, _offline_error()

    tenant = _db.session.get(Tenant, user.tenant_id) if user.tenant_id else None
    access_token, refresh_token = _issue_local_tokens(user, tenant)
    if user.tenant_id:
        current_app.config['LOCAL_TENANT_ID'] = user.tenant_id
        ensure_local_cursors(user.tenant_id)

    state = SyncState.get_or_create()
    state.online = False
    state.last_error = (
        'Serveur central injoignable : session ouverte en mode hors-ligne.'
    )
    _db.session.commit()

    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
        'tenant': tenant.to_dict() if tenant else None,
        'must_change_password': False,
        'offline': True,
    }, None

