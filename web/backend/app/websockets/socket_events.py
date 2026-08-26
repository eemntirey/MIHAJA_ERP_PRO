# backend/app/websockets/socket_events.py
# Gestion des événements Socket.IO pour la synchronisation temps-réel.

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_jwt_extended import decode_token
from flask import current_app

socketio = None


def init_socketio(app):
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins=current_app.config.get('CORS_ORIGINS', []),
        async_mode='eventlet',
        logger=current_app.config.get('DEBUG', False),
        engineio_logger=current_app.config.get('DEBUG', False),
    )

    register_handlers(socketio)
    return socketio


def register_handlers(socketio):
    @socketio.on('connect')
    def handle_connect(auth):
        try:
            token = auth.get('token', '') if auth else ''
            if not token:
                return False

            decoded = decode_token(token)
            tenant_id = decoded.get('tenant_id')
            user_id = decoded.get('sub')

            if not tenant_id:
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

    @socketio.on('disconnect')
    def handle_disconnect():
        current_app.logger.info("Client déconnecté")

    @socketio.on('subscribe:favorites')
    def handle_subscribe_favorites(data):
        tenant_id = data.get('tenant_id')
        if tenant_id:
            join_room(f"tenant:{tenant_id}:favorites")

    @socketio.on('subscribe:columns')
    def handle_subscribe_columns(data):
        tenant_id = data.get('tenant_id')
        module = data.get('module')
        if tenant_id and module:
            join_room(f"tenant:{tenant_id}:columns:{module}")

    @socketio.on('subscribe:filters')
    def handle_subscribe_filters(data):
        tenant_id = data.get('tenant_id')
        module = data.get('module')
        if tenant_id and module:
            join_room(f"tenant:{tenant_id}:filters:{module}")

    @socketio.on('subscribe:notifications')
    def handle_subscribe_notifications(data):
        user_id = data.get('user_id')
        if user_id:
            join_room(f"user:{user_id}:notifications")


def broadcast_to_tenant(tenant_id, event, data):
    if socketio:
        socketio.emit(event, data, room=f"tenant:{tenant_id}")


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
