# desk/electron/backend/mihaja-backend.spec
# Spécification PyInstaller pour le backend embarqué.
a = Analysis(
    ['../../web/backend/run_local.py'],
    pathex=['../../web/backend'],
    datas=[('../../web/backend/migrations', 'migrations')],
    hiddenimports=['app', 'app.models', 'app.api.v1', 'engineio.async_drivers'],
    excludes=['tkinter', 'pytest'],
)
exe = EXE(pyz, a, name='mihaja-backend', console=False, one_file=True)
