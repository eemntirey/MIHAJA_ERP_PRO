# desk/electron/backend/build_backend.ps1
# Construit le backend embarque (PyInstaller) dans desk/electron/backend/dist.
#
# L'exécutable produit (mihaja-backend.exe) est ensuite copie par
# electron-builder dans resources/backend/ — cf. "extraResources" de
# desk/package.json. Il n'est jamais versionne (cf. .gitignore).
$ErrorActionPreference = 'Stop'

$root = Resolve-Path "$PSScriptRoot\..\..\.."
$venvPy = "$root\web\backend\venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    throw ("Environnement Python introuvable : $venvPy`n" +
           "Creez-le puis installez les dependances du backend :`n" +
           "  cd web\backend`n" +
           "  python -m venv venv`n" +
           "  .\venv\Scripts\pip install -r ..\requirements.txt")
}

Write-Host "Build du backend embarque (PyInstaller)..." -ForegroundColor Cyan
& $venvPy -m pip install pyinstaller --quiet

Push-Location "$root\desk\electron\backend"
try {
    & $venvPy -m PyInstaller mihaja-backend.spec --distpath dist --workpath build --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller a echoue (code $LASTEXITCODE)." }
}
finally {
    Pop-Location
}

$exe = "$root\desk\electron\backend\dist\mihaja-backend.exe"
if (-not (Test-Path $exe)) {
    throw "Executable attendu introuvable apres le build : $exe"
}
Write-Host "Backend embarque construit : $exe" -ForegroundColor Green

