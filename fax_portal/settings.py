import os
from pathlib import Path

from django.conf.global_settings import DATE_INPUT_FORMATS as DJ_DATE_INPUT_FORMATS
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "insecure-secret-key"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "fax_calendar.apps.FaxCalendarConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "shell",
    "wiki",
    "maps",
    "openfaxmap",
    "sports",
    "mma",
    "msa",
]

# Ensure apps are unique while preserving order
INSTALLED_APPS = list(dict.fromkeys(INSTALLED_APPS))

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fax_portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "fax_calendar.context_processors.woorld_date",
                "fax_calendar.context_processors.woorld_calendar_meta",
                "msa.context_processors.msa_admin_mode",
                "fax_portal.context_processors.admin_flags",
                "fax_portal.context_dates.active_date_ctx",
            ],
        },
    },
]

WSGI_APPLICATION = "fax_portal.wsgi.application"
ASGI_APPLICATION = "fax_portal.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # nový čistý dev soubor -> nic starého tam nebude
        "NAME": BASE_DIR / "db_dev.sqlite3",
        # v devu pomůže proti "database is locked"
        "OPTIONS": {"timeout": 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Přijímej DD-MM-YYYY i ISO YYYY-MM-DD všude, bez ohledu na LANGUAGE_CODE
DATE_INPUT_FORMATS = ["%d-%m-%Y", "%Y-%m-%d", *DJ_DATE_INPUT_FORMATS]

FORMAT_MODULE_PATH = "fax_portal.formats"

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Ztišení Django 6.0 URLField warningu
FORMS_URLFIELD_ASSUME_HTTPS = True

# OpenFaxMap tile configuration
OFM_TILE_URL = os.getenv("OFM_TILE_URL", "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png")
OFM_TILE_ATTRIBUTION = os.getenv("OFM_TILE_ATTRIBUTION", "© OpenStreetMap contributors")
OFM_STYLE_URL = os.getenv("OFM_STYLE_URL", "")

# Draw engine feature flag
MSA_DRAW_ENGINE = os.getenv("MSA_DRAW_ENGINE", "v1")

# MSA
MSA_ADMIN_MODE = True
MSA_ARCHIVE_LIMIT_COUNT = int(os.getenv("MSA_ARCHIVE_LIMIT_COUNT", "50"))
MSA_ARCHIVE_LIMIT_MB = int(os.getenv("MSA_ARCHIVE_LIMIT_MB", "50"))

if "rest_framework" in INSTALLED_APPS:
    REST_FRAMEWORK = {
        **(globals().get("REST_FRAMEWORK") or {}),
        "DATE_INPUT_FORMATS": [
            "%d-%m-%Y",
            "%Y-%m-%d",
        ],
    }

# === BEGIN: Persistent DEV database config (idempotent block) ===
import os  # noqa: E402
from pathlib import Path  # noqa: E402

USE_POSTGRES = os.getenv("USE_POSTGRES") == "1"

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "fax"),
            "USER": os.getenv("POSTGRES_USER", "fax"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "fax"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    # SQLite cesta mimo repo – bezpečné proti git clean / pull.
    DJANGO_DB_PATH = os.environ.get("DJANGO_DB_PATH")
    if DJANGO_DB_PATH:
        DB_DEFAULT_PATH = Path(DJANGO_DB_PATH)
    else:
        DB_DEFAULT_PATH = Path.home() / "fax_data" / "db_dev.sqlite3"
    DB_DEFAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(DB_DEFAULT_PATH),
        }
    }
# === END: Persistent DEV database config ===
# === DEV convenience: hosts & CSRF (idempotent) ===
if DEBUG:
    ALLOWED_HOSTS = ["*"]
    CSRF_TRUSTED_ORIGINS = list(
        set(
            [
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ]
            + globals().get("CSRF_TRUSTED_ORIGINS", [])
        )
    )
    try:
        import socket

        _ip = socket.gethostbyname(socket.gethostname())
        CSRF_TRUSTED_ORIGINS.append(f"http://{_ip}:8000")
    except Exception:
        pass
# === END DEV block ===
