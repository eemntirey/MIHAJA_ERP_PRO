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
    # Mode embarqué : la base locale (SQLite) ne doit jamais être exposée
    # hors du poste ; on n'écoute que sur l'interface de bouclage.
    if os.getenv('FLASK_ENV') == 'local-embedded':
        host = os.getenv('FLASK_HOST', '127.0.0.1')
    # Mode local-embedded : le backend embarqué écoute sur le port dynamique
    # assigné par Electron (LOCAL_API_PORT), sinon sur FLASK_PORT.
    port = int(os.getenv('LOCAL_API_PORT') or os.getenv('FLASK_PORT', 5000))

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
        # Werkzeug est autorisé hors production : dev central (debug explicite)
        # et backend embarqué du poste (FLASK_ENV=local-embedded : écoute sur
        # 127.0.0.1 avec port dynamique, jamais exposé au réseau, debugger
        # désactivé). Incident du 22/09/2026 : sans ce flag, flask_socketio
        # lève "The Werkzeug web server is not designed to run in production."
        # et le serveur local du desktop mourait au démarrage.
        allow_unsafe_werkzeug = debug or \
            os.getenv('FLASK_ENV', '').strip().lower() == 'local-embedded'
        app.socketio.run(app, debug=debug, host=host, port=port,
                         allow_unsafe_werkzeug=allow_unsafe_werkzeug)
    else:
        app.run(**server_opts)
