# -*- mode: python ; coding: utf-8 -*-
# desk/electron/backend/mihaja-backend.spec
# Spécification PyInstaller du backend embarqué (backend Flask local du desk).
#
# Produit un exécutable one-file `mihaja-backend.exe` déposé par
# electron-builder dans `resources/backend/` (cf. "extraResources" de
# desk/package.json), puis lancé par desk/electron/backendHost.js.
#
# Notes de maintenance :
#  - les chemins sont calculés depuis SPECPATH : le build fonctionne quel que
#    soit le répertoire d'appel (le plan initial utilisait des chemins
#    relatifs, cassants depuis PyInstaller) ;
#  - `run_local.py` doit être packagé comme script d'entrée : c'est lui qui
#    appelle ensure_local_db_ready() et start_replication_scheduler() ;
#  - le dossier migrations est embarqué (stamp Alembic de la base locale).
import os

from PyInstaller.utils.hooks import collect_submodules

# desk/electron/backend -> racine web/backend
_SPEC_DIR = os.path.abspath(SPECPATH)
_BACKEND_ROOT = os.path.abspath(
    os.path.join(_SPEC_DIR, '..', '..', '..', 'web', 'backend')
)

datas = [
    (os.path.join(_BACKEND_ROOT, 'migrations'), 'migrations'),
]

# Imports découverts dynamiquement (imports paresseux dans les services) :
# sans cette liste, l'exécutable démarre puis échoue sur un ModuleNotFoundError
# au premier push/pull ou au premier login hors-ligne.
hiddenimports = [
    'app',
    'app.models',
    'app.api.v1',
    'app.services',
    'app.services.replication',
    'app.services.replication.push',
    'app.services.replication.pull',
    'app.services.replication.scheduler',
    'app.services.replication.maintenance',
    'app.services.replication.outbox',
    'app.services.replication.entities',
    'app.services.local_auth',
    'app.services.local_bootstrap',
    # Abonnement central (miroir + proxy hors-ligne du desk).
    'app.services.central_subscription',
    # Client HTTP du moteur de réplication.
    'requests',
    'urllib3',
    'charset_normalizer',
    'idna',
    # Hachage du login hors-ligne + JWT.
    'bcrypt',
    'jwt',
    # Schéma local SQLite + migrations.
    'sqlalchemy.dialects.sqlite',
    'alembic',
    'flask_migrate',
    'logging.config',
    'engineio.async_drivers.threading',
    # Petit serveur WSGI de développement utilisé par run_local.py.
    'werkzeug.serving',
]
hiddenimports += collect_submodules('app.services.replication')

excludes = [
    'tkinter',
    'pytest',
    'unittest',
    'pandas.tests',
    'numpy.tests',
]

a = Analysis(
    [os.path.join(_BACKEND_ROOT, 'run_local.py')],
    pathex=[_BACKEND_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mihaja-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=False : aucune fenêtre noire ne s'ouvre derrière l'application.
    # Les logs passent par le backend (stdout capturé par backendHost.js).
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

