# backend/app/websockets/socket_events.py
# Gestion des événements Socket.IO pour la synchronisation temps-réel.

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_jwt_extended import decode_token
from flask import current_app, request
import os

from app.models.utilisateur import Utilisateur
from app.security.roles import is_super_admin
from app import db

socketio = None


def init_socketio(app):
    global socketio
    cors_origins = app.config.get('CORS_ORIGINS') or os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # Avec async_mode='threading' sous Werkzeug, le driver WSGI
    # websocket (simple_websocket) lève ConnectionError sur l'upgrade
    # (cf. engineio/async_drivers/_websocket_wsgi.py). On force donc
    # le polling uniquement tant qu'aucun serveur WSGI async
    # (eventlet/gevent/gunicorn) n'est installé.
    import importlib.util as _ilu
    transports = ['polling', 'websocket']
    if all(_ilu.find_spec(name) is None for name in ('eventlet', 'gevent', 'gunicorn')):
        transports = ['polling']

    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_origins,
        async_mode='threading',
        logger=app.config.get('DEBUG', False),
        engineio_logger=False,
        # Le driver threading + Werkzeug peut laisser les long-polls GET
        # patienter plus longtemps que les valeurs par défaut (20s/25s).
        # On assouplit ces timeouts pour éviter que le serveur ferme la
        # session (=> HTTP 400 sur le GET polling suivant) sous charge
        # ou en dev. Les clients socket.io-client se reconnectent
        # automatiquement de toute façon.
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=2 * 1024 * 1024,
        transports=transports,
    )

    register_handlers(socketio)
    return socketio


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


def register_handlers(socketio):
    @socketio.on('connect')
    def handle_connect(auth):
        try:
            token = auth.get('token', '') if auth else ''
            if not token:
                current_app.logger.warning("Connexion WebSocket rejetée: token manquant")
                return False

            try:
                decoded = decode_token(token)
            except Exception as e:
                current_app.logger.warning(f"Connexion WebSocket rejetée: token invalide: {e}")
                return False

            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')
            role = decoded.get('role')

            if is_super_admin(role):
                join_room('super_admin')
                current_app.logger.info(
                    f"Super-admin connecté: user={user_id}"
                )
                return True

            if not tenant_id:
                current_app.logger.warning(f"Connexion WebSocket rejetée: pas de tenant_id pour user={user_id}")
                return False

            room = f"tenant:{tenant_id}"
            join_room(room)

            if user_id:
                join_room(f"user:{user_id}")

            current_app.logger.info(
                f"Client connecté: tenant={tenant_id}, user={user_id}"
            )

        except Exception as e:
            current_app.logger.warning(f"Connexion WebSocket rejetée: {e}")
            return False
        return True

    @socketio.on('disconnect')
    def handle_disconnect():
        current_app.logger.info("Client déconnecté")

    @socketio.on('subscribe:favorites')
    def handle_subscribe_favorites(data):
        # On ignore le tenant_id fourni par le client et on utilise celui du JWT
        # pour eviter qu'un client puisse espionner un autre tenant.
        try:
            token = (request.args.get('token') or
                     (data or {}).get('token') or '')
            decoded = decode_token(token)
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:favorites: token invalide')
            return False
        if tenant_id and _tenant_belongs_to_user(tenant_id, user_id):
            join_room(f"tenant:{tenant_id}:favorites")

    @socketio.on('subscribe:columns')
    def handle_subscribe_columns(data):
        try:
            token = (request.args.get('token') or
                     (data or {}).get('token') or '')
            decoded = decode_token(token)
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:columns: token invalide')
            return False
        module = (data or {}).get('module')
        if tenant_id and module and _tenant_belongs_to_user(tenant_id, user_id):
            join_room(f"tenant:{tenant_id}:columns:{module}")

    @socketio.on('subscribe:filters')
    def handle_subscribe_filters(data):
        try:
            token = (request.args.get('token') or
                     (data or {}).get('token') or '')
            decoded = decode_token(token)
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:filters: token invalide')
            return False
        module = (data or {}).get('module')
        if tenant_id and module and _tenant_belongs_to_user(tenant_id, user_id):
            join_room(f"tenant:{tenant_id}:filters:{module}")

    @socketio.on('subscribe:notifications')
    def handle_subscribe_notifications(data):
        # Les notifications sont strictement personnelles (user:ID) : on
        # n'autorise l'abonnement qu'au propre user du token.
        try:
            token = (request.args.get('token') or
                     (data or {}).get('token') or '')
            decoded = decode_token(token)
            user_id = decoded.get('sub')
        except Exception:
            current_app.logger.warning('subscribe:notifications: token invalide')
            return False
        requested = (data or {}).get('user_id')
        if requested and requested == user_id:
            join_room(f"user:{user_id}:notifications")


def broadcast_to_tenant(tenant_id, event, data):
    if socketio:
        socketio.emit(event, data, room=f"tenant:{tenant_id}")
        socketio.emit(event, data, room='super_admin')


def broadcast_to_super_admin(event, data):
    """Diffuse un événement à tous les super admins connectés."""
    if socketio:
        socketio.emit(event, data, room='super_admin')


def broadcast_to_user(user_id, event, data):
    if socketio:
        socketio.emit(event, data, room=f"user:{user_id}")


def broadcast_favorite_update(tenant_id, favorite_data):
    if socketio:
        socketio.emit('favorite:updated', favorite_data, room=f"tenant:{tenant_id}:favorites")


def broadcast_column_update(tenant_id, module, column_data):
    if socketio:
        socketio.emit('column:updated', column_data, room=f"tenant:{tenant_id}:columns:{module}")


def broadcast_filter_update(tenant_id, module, filter_data):
    if socketio:
        socketio.emit('filter:updated', filter_data, room=f"tenant:{tenant_id}:filters:{module}")


def broadcast_notification(user_id, notification_data):
    if socketio:
        socketio.emit('notification:new', notification_data, room=f"user:{user_id}:notifications")


def get_socketio():
    global socketio
    return socketio
