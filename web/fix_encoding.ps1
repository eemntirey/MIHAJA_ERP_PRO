# fix_encoding.ps1 - Version corrigée
Write-Host "Correction de l'encodage des fichiers Python..." -ForegroundColor Green

$files = Get-ChildItem -Path "backend\app" -Recurse -Include "*.py"

foreach ($file in $files) {
    Write-Host "Correction: $($file.Name)" -ForegroundColor Yellow
    try {
        # Lire le contenu avec l'encodage par défaut
        $content = Get-Content -Path $file.FullName -Raw -Encoding Default
        # Réécrire en UTF-8
        $content | Out-File -FilePath $file.FullName -Encoding UTF8 -Force
        Write-Host "  Fichier corrigé" -ForegroundColor Green
    }
    catch {
        Write-Host "  Erreur: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "Correction terminée!" -ForegroundColor Green