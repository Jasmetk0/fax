# FAX Portal

Prototype Django portal with wiki, maps, and live sports sections.

## Apps

- shell
- wiki
- maps
- sports

## Development

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Admin Woorld calendar popup
Any admin form field ending in `_date` automatically gains a Woorld calendar button.
Dates are entered as `DD-MM-YYYY` and stored as `YYYY-MM-DD`.
The popup uses the canonical calendar core (V1/V2 + proto-V3) with Monday–Sunday
weekdays and dynamic month lengths. Setting `request.session['woorld_today']`
allows the "Today" button to jump to the current Woorld date.

## MSA greenfield (in-place)

- Removed legacy tournament/match logic and related services.
- Retains integration with `fax_calendar` date widgets.
- Provides fresh `Country`, `Player`, and `Tournament` models with simple list/detail/create pages.
- **Breaking change:** existing databases must be reset for development/testing; production migrations will arrive later.

## Dev DB & zálohy
- Nastav `DJANGO_DB_PATH` v `.env` (nebo použij default `~/fax_data/db_dev.sqlite3`).
- Nainstaluj hooky: `bash scripts/install_hooks.sh` → před každým `git push` proběhne záloha (`scripts/backup.sh`).
- Poprvé spusť: `bash scripts/migrate_or_init.sh` a pak `python manage.py runserver`.
- V DEV módu (`DEBUG=True`) jsou `ALLOWED_HOSTS=["*"]` a `CSRF_TRUSTED_ORIGINS` pro `localhost/127.0.0.1` (plus pokus o LAN IP).

