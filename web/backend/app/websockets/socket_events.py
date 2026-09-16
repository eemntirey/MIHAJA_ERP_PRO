# backend/app/websockets/socket_events.py
# Événements Socket.IO : abonnements (subscribe:*) et diffusion (broadcast_*).
#
# NOTE V9 : l'initialisation du serveur SocketIO est UNIQUE et vit dans
# app.realtime.socket_server (créé par create_app). Ce module ne créé plus
# une deuxième instance morte : il s'appuie sur socket_server.get_socketio()
# pour les broadcasts et enregistre uniquement les abonnements subscribe:*
# sur l'instance partagée via register_extended_handlers().

from flask_socketio import emit, join_room, leave_room
from flask import current_app, request

from app.models.utilisateur import Utilisateur
from app.security.roles import is_super_admin
from app import db

socketio = None


def _live_socketio():
    """Instance SocketIO réellement initialisée (single source of truth)."""
    from app.realtime.socket_server import get_socketio as _get_server_socketio
    global socketio
    socketio = _get_server_socketio()
    return socketio


def init_socketio(app):
    """Rétro-compat : délègue la création de l'instance à socket_server.

    L'initialisation réelle (CORS explicite + tokens vérifiés + sockets
    cotés origin) est faite par app.realtime.socket_server.init_socketio
    appelé dans create_app. Ce module n'a plus le droit de créer une
    seconde instance — celle-ci voyait les broadcast_to_* rester morts.
    """
    from app.realtime.socket_server import init_socketio as _server_init
    _server_init(app)
    return _live_socketio()


def _tenant_belongs_to_user(tenant_id, user_id):
    """Vérifie qu'un utilisateur appartient bien au tenant demandé.

    Évite qu'un client malveillant puisse s'abonner aux events d'un autre
    tenant en fournissant un tenant_id arbitraire dans le payload.
    """
    try:
        user = db.session.get(Utilisateur, user_id)
        if not user:
            return False
        if is_super_admin(user.role):
            return True
        return user.tenant_id == tenant_id
    except Exception:
        current_app.logger.exception('Erreur verification tenant pour WebSocket')
        return False


def register_extended_handlers(socketio_inst, authorize_claims=None):
    """Enregistre les abonnements subscribe:* sur l'instance partagée.

    ``authorize_claims`` est historiquement passé par socket_server, mais
    les handlers lisent désormais les claims stockées par sid au
    paramètre connect → dict ``_conn_claims`` (P1-3). Ce paramètre est
    conservé pour la compatibilité mais n'est plus utilisé par les
    handlers, qui lisent ``get_claims_for_sid(request.sid)``.
    """
    if authorize_claims is None:
        def authorize_claims(token):
            from flask_jwt_extended import decode_token
            return decode_token(token) if token else None

    def _get_auth_claims():
        """Lit les claims validées au handshake (stockées par socket_server)."""
        from app.realtime.socket_server import get_claims_for_sid
        return get_claims_for_sid(request.sid)

    @socketio_inst.on('subscribe:favorites')
    def handle_subscribe_favorites(data):
        try:
            decoded = _get_auth_claims()
            if not decoded:
                return False
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:favorites: token invalide')
            return False
        if tenant_id and _tenant_belongs_to_user(tenant_id, user_id):
            join_room(f"tenant:{tenant_id}:favorites")

    @socketio_inst.on('subscribe:columns')
    def handle_subscribe_columns(data):
        try:
            decoded = _get_auth_claims()
            if not decoded:
                return False
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:columns: token invalide')
            return False
        module = (data or {}).get('module')
        if tenant_id and module and _tenant_belongs_to_user(tenant_id, user_id):
            join_room(f"tenant:{tenant_id}:columns:{module}")

    @socketio_inst.on('subscribe:filters')
    def handle_subscribe_filters(data):
        try:
            decoded = _get_auth_claims()
            if not decoded:
                return False
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:filters: token invalide')
            return False
        module = (data or {}).get('module')
        if tenant_id and module and _tenant_belongs_to_user(tenant_id, user_id):
            join_room(f"tenant:{tenant_id}:filters:{module}")

    @socketio_inst.on('subscribe:notifications')
    def handle_subscribe_notifications(data):
        try:
            decoded = _get_auth_claims()
            if not decoded:
                return False
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:notifications: token invalide')
            return False
        requested = (data or {}).get('user_id')
        if requested and requested == user_id:
            join_room(f"user:{user_id}:notifications")


def register_handlers(socketio_inst):
    """Alias rétro-compatible : les abonnements subscribe:* uniquement.

    Le handshake connect/disconnect/ping est géré par socket_server (le
    seul à vérifier blocklist + pwd_v). Enregistrer ici un second
    @on('connect') remplacerait le handler sécurisé — interdit (V9).
    """
    register_extended_handlers(socketio_inst)


def broadcast_to_tenant(tenant_id, event, data):
    sio = _live_socketio()
    if sio:
        sio.emit(event, data, room=f"tenant:{tenant_id}")
        sio.emit(event, data, room='super_admin')


def broadcast_to_super_admin(event, data):
    """Diffuse un événement à tous les super admins connectés."""
    sio = _live_socketio()
    if sio:
        sio.emit(event, data, room='super_admin')


def broadcast_to_user(user_id, event, data):
    sio = _live_socketio()
    if sio:
        sio.emit(event, data, room=f"user:{user_id}")


def broadcast_favorite_update(tenant_id, favorite_data):
    sio = _live_socketio()
    if sio:
        sio.emit('favorite:updated', favorite_data, room=f"tenant:{tenant_id}:favorites")


def broadcast_column_update(tenant_id, module, column_data):
    sio = _live_socketio()
    if sio:
        sio.emit('column:updated', column_data, room=f"tenant:{tenant_id}:columns:{module}")


def broadcast_filter_update(tenant_id, module, filter_data):
    sio = _live_socketio()
    if sio:
        sio.emit('filter:updated', filter_data, room=f"tenant:{tenant_id}:filters:{module}")


def broadcast_notification(user_id, notification_data):
    sio = _live_socketio()
    if sio:
        sio.emit('notification:new', notification_data, room=f"user:{user_id}:notifications")


def get_socketio():
    return _live_socketio()
