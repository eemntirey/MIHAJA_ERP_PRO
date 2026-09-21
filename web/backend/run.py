from app import create_app
import os

app = create_app()

if os.getenv('FLASK_ENV') == 'local-embedded':
    from app.services.local_bootstrap import ensure_local_db_ready
    from app.services.replication.scheduler import start_replication_scheduler
    ensure_local_db_ready(app)
    start_replication_scheduler(app)

if __name__ == '__main__':
    auto_migrate = os.getenv('AUTO_MIGRATE', '0').strip().lower() in ('1', 'true', 'yes', 'on')
    if auto_migrate:
        from flask_migrate import upgrade
        with app.app_context():
            upgrade()

    debug = os.getenv('FLASK_DEBUG', 'False').strip().lower() in ('1', 'true', 'yes', 'on')
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))

    # P2 audit : ne jamais laisser le debugger Werkzeug actif en production.
    is_production = os.getenv('FLASK_ENV', '').strip().lower() == 'production'
    if debug and is_production:
        raise SystemExit(
            'ERREUR: FLASK_DEBUG ne peut pas etre activé en production. '
            'Retirez FLASK_DEBUG=1 de l environnement.'
        )

    if debug:
        print('WARNING: Debug mode is enabled. Do not use in production.')

    print(f"Serveur: http://{host}:{port}")
    print(f"Documentation: http://{host}:{port}/docs")
    print("Health: /health  Ready: /ready  Monitor: /monitor")

    # P0 audit 14/09/2026 (ERR_CONNECTION_CLOSED sur nouvel onglet / tunnel) :
    # le serveur dev mono-thread de Werkzeug ferme les connexions keep-alive
    # dès qu'une 2e navigation arrive pendant un long-poll socket.io.
    # On active le mode threaded + keep-alive explicite pour stabiliser.
    server_opts = dict(host=host, port=port, threaded=True)
    if debug:
        server_opts['debug'] = True

    if getattr(app, 'socketio', None):
        print(f"SocketIO: actif sur ws://{host}:{port}/socket.io")
        # allow_unsafe_werkzeug reste uniquement en mode debug explicite
        # pour ne pas exposer le debugger Werkzeug en production.
        app.socketio.run(app, debug=debug, host=host, port=port,
                         allow_unsafe_werkzeug=debug)
    else:
        app.run(**server_opts)
