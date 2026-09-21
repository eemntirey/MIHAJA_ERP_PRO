# desk/electron/backend/build_backend.ps1
# Build du backend embarqué (PyInstaller) dans desk/electron/backend/dist.
$ErrorActionPreference = 'Stop'
$root = Resolve-Path "$PSScriptRoot\..\..\.."
$venvPy = "$root\web\backend\venv\Scripts\python.exe"
& $venvPy -m pip install pyinstaller --quiet
Push-Location "$root\desk\electron\backend"
& $venvPy -m PyInstaller mihaja-backend.spec --distpath dist --workpath build --noconfirm
Pop-Location
Write-Host "Backend embarqué construit: desk/electron/backend/dist/mihaja-backend.exe"
