#!/usr/bin/env bash
set -euo pipefail
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

# Přesuň starou DB, pokud existuje v repu a nová neexistuje
python scripts/first_time_move_db.py || true
# Proveď migrace
python manage.py migrate
# (volitelně) vytvoř superusera z env proměnných
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py createsuperuser --noinput || true
fi
