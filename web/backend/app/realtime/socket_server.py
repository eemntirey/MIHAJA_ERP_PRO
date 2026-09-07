# web/backend/app/realtime/socket_server.py
# Serveur temps-réel (Flask-SocketIO). Désactivé proprement si flask-socketio
# n'est pas installé : le client bascule alors sur le polling (voir /desk/events).

import logging
from flask import request

logger = logging.getLogger(__name__)

socketio = None


def init_socketio(app):
    """Initialise SocketIO sur l'app Flask. Retourne None si non disponible."""
    global socketio
    try:
        from flask_socketio import SocketIO
    except ImportError:
        logger.warning(
            "flask-socketio non installé : temps-réel désactivé. "
            "Le client utilisera le fallback polling (/api/v1/desk/events)."
        )
        return None

    # Même liste d'origines que flask-cors (app.config['CORS_ORIGINS'],
    # renseignée dans create_app). Le fallback couvre les deux identités
    # d'hôte locales : localhost et 127.0.0.1.
    allowed_origins = app.config.get('CORS_ORIGINS') or [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]

    socketio = SocketIO(
        app,
        cors_allowed_origins=allowed_origins,
        async_mode="threading",
        path="/socket.io",
        ping_timeout=120,
        ping_interval=20,
        max_http_buffer_size=2 * 1024 * 1024,
    )
    _register_handlers()
    return socketio


def _register_handlers():
    if not socketio:
        return
    from flask_jwt_extended import decode_token

    @socketio.on("connect")
    def _on_connect():
        token = request.args.get("token") or (
            request.headers.get("Authorization", "").replace("Bearer ", "")
        )
        if not token:
            return False
        try:
            claims = decode_token(token)
            user_id = claims.get("sub")
            request.sid and socketio.enter_room(request.sid, f"user:{user_id}")
            return True
        except Exception:
            return False

    @socketio.on("disconnect")
    def _on_disconnect():
        return

    @socketio.on("ping")
    def _on_ping():
        socketio.emit("pong")


def emit_preference_update(entity, user_id, payload):
    """Émet une MAJ vers la room de l'utilisateur (si SocketIO actif)."""
    if not socketio or not user_id:
        return
    try:
        socketio.emit(f"{entity}:updated", payload, room=f"user:{user_id}")
    except Exception as exc:  # pragma: no cover
        logger.warning("Échec émission socket %s: %s", entity, exc)
