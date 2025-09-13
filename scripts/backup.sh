#!/usr/bin/env bash
set -euo pipefail
mkdir -p backups
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 > "backups/dev-$(date +%Y%m%d-%H%M).json"
# nech si posledních 20 záloh
ls -1t backups/dev-*.json 2>/dev/null | tail -n +21 | xargs -r rm --
echo "Backup hotov."
