$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$containerName = 'erp-pg'

Write-Host "Starting PostgreSQL container '$containerName'..."
$running = docker inspect -f '{{.State.Running}}' $containerName 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Docker container '$containerName' was not found. Create it first with: docker run --name erp-pg -e POSTGRES_PASSWORD=eemntirey -p 55432:5432 -d postgres:16"
}

if ($running -ne 'true') {
    docker start $containerName | Out-Null
}

Write-Host 'Waiting for PostgreSQL...'
$ready = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    docker exec $containerName pg_isready -U postgres -d erp *> $null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    throw 'PostgreSQL did not become ready within 30 seconds.'
}

$pythonCmd = if (Test-Path ".\venv\Scripts\python.exe") { ".\venv\Scripts\python.exe" } else { "python" }

Write-Host 'Creating or synchronizing database tables...'
& $pythonCmd -c "from app import create_app, db; app = create_app(); ctx = app.app_context(); ctx.push(); db.create_all()"
& $pythonCmd scripts/seed_roles.py

# Stamp head before applying future migrations
& $pythonCmd -m flask --app 'app:create_app' db stamp head
& $pythonCmd -m flask --app 'app:create_app' db upgrade

Write-Host 'PostgreSQL setup completed successfully.'
