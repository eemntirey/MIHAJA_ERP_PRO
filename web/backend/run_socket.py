# web/backend/run_socket.py
# Point d'entrée avec Socket.IO (temps-réel).
# Usage : ENABLE_SOCKETIO=1 python run_socket.py
# Le temps-réel est optionnel : sans flask-socketio installé, le client
# desktop/web bascule automatiquement sur le polling (/api/v1/desk/events).

from app import create_app
import os

app = create_app()

# Active SocketIO si la dépendance est présente et l'env est activé.
os.environ.setdefault("ENABLE_SOCKETIO", "1")

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))

    try:
        from app.realtime import socketio
        if socketio:
            print("Temps-réel Socket.IO activé sur le port", port)
            # allow_unsafe_werkzeug uniquement en mode debug explicite.
            socketio.run(app, debug=debug, host=host, port=port,
                         allow_unsafe_werkzeug=debug)
        else:
            print("SocketIO indisponible : démarrage HTTP classique.")
            app.run(debug=debug, host=host, port=port)
    except ImportError:
        app.run(debug=debug, host=host, port=port)
