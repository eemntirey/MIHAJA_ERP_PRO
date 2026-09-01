from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    from flask_migrate import upgrade
    with app.app_context():
        upgrade()
    
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    if debug:
        print('WARNING: Debug mode is enabled. Do not use in production.')
    
    print(f"Serveur: http://{host}:{port}")
    print(f"Documentation: http://{host}:{port}/docs")
    
    if getattr(app, 'socketio', None):
        print(f"SocketIO: actif sur ws://{host}:{port}/socket.io")
        # allow_unsafe_werkzeug reste uniquement en mode debug explicite
        # pour ne pas exposer le debugger Werkzeug en production.
        app.socketio.run(app, debug=debug, host=host, port=port,
                         allow_unsafe_werkzeug=debug)
    else:
        app.run(debug=debug, host=host, port=port)
