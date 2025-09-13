$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "backups" | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 > "backups/dev-$stamp.json"
Get-ChildItem backups/dev-*.json -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 20 | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Host "Backup hotov."
