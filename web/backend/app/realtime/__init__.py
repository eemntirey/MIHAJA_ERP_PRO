# web/backend/app/realtime/__init__.py
from app.realtime.socket_server import init_socketio, emit_preference_update, socketio

__all__ = ["init_socketio", "emit_preference_update", "socketio"]
