# web/backend/app/realtime/socket_server.py
# Serveur temps-réel (Flask-SocketIO). Désactivé proprement si flask-socketio
# n'est pas installé : le client bascule alors sur le polling (voir /desk/events).

import logging
from flask import request

logger = logging.getLogger(__name__)

socketio = None

# Claims décodés au moment du handshake, stockés par sid. Les handlers
# subscribe:* lisent ces claims au lieu de refaire un décodage par
# événement (audit P1-3 : évite la duplication et supprime les accès
# aux query-strings /token que les proxies loguent).
_conn_claims = {}          # sid → claims dict


def get_claims_for_sid(sid):
    """Retourne les claims validées d'un sid, ou None."""
    return _conn_claims.get(sid)


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

    # P0 audit 14/09/2026 : accepter les origines dynamiques (tunnels
    # devtunnels.ms, LAN) comme flask-cors, sinon le handshake socket
    # échoue avec « Not an accepted origin » et le tunnel semble mort.
    import re as _re

    static_origins = list(app.config.get('CORS_ORIGINS') or [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ])
    patterns = list(app.config.get('CORS_DYNAMIC_PATTERNS') or [])

    def _socket_origin_allowed(origin):
        if not origin:
            return False
        if origin in static_origins:
            return True
        for _pat in patterns:
            try:
                if _re.match(_pat, origin):
                    return True
            except Exception:
                continue
        return False

    socketio = SocketIO(
        app,
        cors_allowed_origins=_socket_origin_allowed,
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
    from app import db
    from app.models.token_blocklist import TokenBlocklist
    from app.models.utilisateur import Utilisateur

    def _authorized_claims(token):
        """Décode + vérifie signature, expiration, blocklist et pwd_v.
        Retourne les claims si le token est toujours valide, sinon None.
        Source unique de vérité utilisée par le handshake ET les
        abonnements subscribe:* (V9 : plus de double implémentation)."""
        if not token:
            return None
        try:
            claims = decode_token(token)
            jti = claims.get('jti')
            if TokenBlocklist.is_revoked(jti):
                return None
            user_id = claims.get("sub")
            user = db.session.get(Utilisateur, user_id) if user_id else None
            if user and (user.token_version or 0) > claims.get("pwd_v", 0):
                return None
            return claims
        except Exception:
            return None

    @socketio.on("connect")
    def _on_connect(auth=None):
        # P1-3 : ne JAMAIS lire le token dans query-string (proxies / CDN le
        # loguent). Les navigateurs ne peuvent pas mettre de header
        # Authorization sur le handshake WebSocket → on accepte un payload
        # Socket.IO auth: {token} transmis dans le CONNECT packet. La
        # priority est : header (clients non-navigateurs) > auth dict > cookie.
        auth_data = auth if isinstance(auth, dict) else {}
        token = None
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:].strip()
        if not token:
            token = auth_data.get("token")
        # A1 : web — le token est en cookie HttpOnly, Socket.IO envoie les
        # cookies avec withCredentials=true lors du handshake polling.
        if not token:
            token = request.cookies.get("access_token_cookie")
        claims = _authorized_claims(token)
        if not claims:
            return False
        # Exiger des access tokens uniquement (refresh = refresh_event pas WS).
        if claims.get("type") != "access":
            return False
        _conn_claims[request.sid] = claims
        user_id = claims.get("sub")
        role = claims.get("role")
        from app.security.roles import is_super_admin
        if is_super_admin(role):
            socketio.enter_room(request.sid, "super_admin")
        tenant_id = claims.get("tenant_id")
        if tenant_id:
            socketio.enter_room(request.sid, f"tenant:{tenant_id}")
        if user_id:
            socketio.enter_room(request.sid, f"user:{user_id}")
        return True

    @socketio.on("disconnect")
    def _on_disconnect():
        _conn_claims.pop(request.sid, None)
        return

    @socketio.on("ping")
    def _on_ping():
        socketio.emit("pong")

    # Abonnements subscribe:* — un seul enregistrement, même autorisation.
    try:
        from app.websockets.socket_events import register_extended_handlers
        register_extended_handlers(socketio, _authorized_claims)
    except Exception as exc:  # pragma: no cover
        logger.warning("Échec enregistrement abonnements socket: %s", exc)


def emit_preference_update(entity, user_id, payload):
    """Émet une MAJ vers la room de l'utilisateur (si SocketIO actif)."""
    if not socketio or not user_id:
        return
    try:
        socketio.emit(f"{entity}:updated", payload, room=f"user:{user_id}")
    except Exception as exc:  # pragma: no cover
        logger.warning("Échec émission socket %s: %s", entity, exc)


def get_socketio():
    """Instance SocketIO active (None si temps-réel désactivé).

    Source unique de vérité : tous les broadcast_to_* des modules API
    passent par ici (V9 : plus de double instance morte)."""
    return socketio
