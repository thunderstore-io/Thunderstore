import base64
import json
import os
import sys
import warnings
from typing import Optional, Tuple

import environ
from django.http import HttpRequest

from thunderstore.core.storage import S3MirrorConfig, get_storage_class_or_stub
from thunderstore.core.utils import validate_filepath_prefix
from thunderstore.plugins.registry import plugin_registry

try:
    import debug_toolbar

    DEBUG_TOOLBAR_AVAILABLE = True
except ImportError:
    DEBUG_TOOLBAR_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env = environ.Env(
    DEBUG=(bool, False),
    DEBUG_SIMULATED_LAG=(int, 0),
    DEBUG_TOOLBAR_ENABLED=(bool, False),
    DEBUG_TOOLBAR_SUPERUSER_ONLY=(bool, True),
    DATABASE_LOGS=(bool, False),
    DATABASE_QUERY_COUNT_HEADER=(bool, False),
    DATABASE_URL=(str, "sqlite:///database/default.db"),
    DISABLE_SERVER_SIDE_CURSORS=(bool, True),
    DISABLED_CACHE_BUST_CONDITIONS=(list, []),
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    PROTOCOL=(str, "https://"),
    SOCIAL_AUTH_INIT_HOST=(str, ""),
    AUTH_EXCLUSIVE_HOST=(str, ""),
    PRIMARY_HOST=(str, ""),
    SITE_NAME=(str, "Thunderstore"),
    SITE_DESCRIPTION=(
        str,
        "Thunderstore is a mod database and API for downloading mods",
    ),
    SITE_SLOGAN=(str, "The Open Source Mod Database"),
    SOCIAL_AUTH_SANITIZE_REDIRECTS=(bool, True),
    SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS=(list, []),
    SOCIAL_AUTH_DISCORD_KEY=(str, ""),
    SOCIAL_AUTH_DISCORD_SECRET=(str, ""),
    SOCIAL_AUTH_GITHUB_KEY=(str, ""),
    SOCIAL_AUTH_GITHUB_SECRET=(str, ""),
    SOCIAL_AUTH_OVERWOLF_KEY=(str, ""),
    SOCIAL_AUTH_OVERWOLF_SECRET=(str, ""),
    AWS_ACCESS_KEY_ID=(str, ""),
    AWS_SECRET_ACCESS_KEY=(str, ""),
    AWS_S3_REGION_NAME=(str, ""),
    AWS_S3_ENDPOINT_URL=(str, ""),
    AWS_S3_HOST=(str, ""),
    AWS_S3_CUSTOM_DOMAIN=(str, ""),
    AWS_STORAGE_BUCKET_NAME=(str, ""),
    AWS_DEFAULT_ACL=(str, "public-read"),
    AWS_BUCKET_ACL=(str, "public-read"),
    AWS_AUTO_CREATE_BUCKET=(bool, False),
    AWS_LOCATION=(str, ""),
    AWS_QUERYSTRING_AUTH=(bool, False),
    AWS_S3_SECURE_URLS=(bool, True),
    AWS_S3_FILE_OVERWRITE=(bool, False),
    USERMEDIA_S3_ENDPOINT_URL=(str, ""),
    USERMEDIA_S3_ACCESS_KEY_ID=(str, ""),
    USERMEDIA_S3_SECRET_ACCESS_KEY=(str, ""),
    USERMEDIA_S3_SIGNING_ENDPOINT_URL=(str, ""),
    USERMEDIA_S3_REGION_NAME=(str, ""),
    USERMEDIA_S3_STORAGE_BUCKET_NAME=(str, ""),
    USERMEDIA_S3_LOCATION=(str, ""),
    ABYSS_S3_ENDPOINT_URL=(str, ""),
    ABYSS_S3_ACCESS_KEY_ID=(str, ""),
    ABYSS_S3_SECRET_ACCESS_KEY=(str, ""),
    ABYSS_S3_REGION_NAME=(str, ""),
    ABYSS_S3_STORAGE_BUCKET_NAME=(str, ""),
    ABYSS_S3_LOCATION=(str, ""),
    ABYSS_S3_FILE_OVERWRITE=(bool, False),
    ABYSS_S3_CUSTOM_DOMAIN=(str, ""),
    ABYSS_S3_SECURE_URLS=(bool, True),
    ABYSS_S3_DEFAULT_ACL=(str, "private"),
    CACHE_S3_ENDPOINT_URL=(str, ""),
    CACHE_S3_ACCESS_KEY_ID=(str, ""),
    CACHE_S3_SECRET_ACCESS_KEY=(str, ""),
    CACHE_S3_REGION_NAME=(str, ""),
    CACHE_S3_STORAGE_BUCKET_NAME=(str, ""),
    CACHE_S3_LOCATION=(str, ""),
    CACHE_S3_FILE_OVERWRITE=(bool, False),
    CACHE_S3_CUSTOM_DOMAIN=(str, ""),
    CACHE_S3_SECURE_URLS=(bool, True),
    CACHE_S3_DEFAULT_ACL=(str, "private"),
    MIRROR_S3_ENDPOINT_URL=(str, ""),
    MIRROR_S3_ACCESS_KEY_ID=(str, ""),
    MIRROR_S3_SECRET_ACCESS_KEY=(str, ""),
    MIRROR_S3_REGION_NAME=(str, ""),
    MIRROR_S3_STORAGE_BUCKET_NAME=(str, ""),
    MIRROR_S3_LOCATION=(str, ""),
    MIRROR_S3_FILE_OVERWRITE=(bool, False),
    MIRROR_S3_CUSTOM_DOMAIN=(str, ""),
    MIRROR_S3_SECURE_URLS=(bool, True),
    MIRROR_S3_DEFAULT_ACL=(str, "private"),
    ALLOWED_CDNS=(list, []),
    USE_MULTIPLE_CACHES=(bool, True),
    REDIS_URL=(str, ""),
    REDIS_URL_LEGACY=(str, None),
    REDIS_URL_PROFILES=(str, None),
    REDIS_URL_DOWNLOADS=(str, None),
    DB_CERT_DIR=(str, ""),
    DB_CLIENT_CERT=(str, ""),
    DB_CLIENT_KEY=(str, ""),
    DB_SERVER_CA=(str, ""),
    SENTRY_DSN=(str, ""),
    SENTRY_TRACES_SAMPLE_RATE=(float, 0.0),
    CELERY_BROKER_URL=(str, ""),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    CELERY_TASK_CREATE_MISSING_QUEUES=(bool, True),
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=(bool, False),
    CELERY_TASK_SOFT_TIME_LIMIT=(int, 60 * 60),
    CELERY_TASK_TIME_LIMIT=(int, 60 * 60 + 10),
    REPOSITORY_MAX_PACKAGE_SIZE_MB=(int, 500),
    REPOSITORY_MAX_PACKAGE_TOTAL_SIZE_GB=(int, 1000),
    LEGACYPROFILE_MAX_TOTAL_SIZE_GB=(int, 1000),
    SESSION_COOKIE_DOMAIN=(str, ""),
    OAUTH_SHARED_SECRET=(str, ""),
    OVERWOLF_CLIENT_ID=(str, ""),
    ALWAYS_RAISE_EXCEPTIONS=(bool, False),
    ECOSYSTEM_SCHEMA_URL=(
        str,
        "https://gcdn.thunderstore.io/static/dev/schema/ecosystem-schema.0.0.2.json",
    ),
    CACHALOT_TIMEOUT_SECONDS=(int, 60 * 15),  # 15 minutes by default
    CACHALOT_ENABLED=(bool, True),
    DOWNLOAD_METRICS_TTL_SECONDS=(int, 60 * 10),
    # FEATURE FLAGS UNDER HERE
    IS_CYBERSTORM_ENABLED=(bool, False),
    SHOW_CYBERSTORM_API_DOCS=(bool, False),
    USE_ASYNC_PACKAGE_SUBMISSION_FLOW=(bool, False),
    USE_TIME_SERIES_PACKAGE_DOWNLOAD_METRICS=(bool, True),
)

ALWAYS_RAISE_EXCEPTIONS = env.bool("ALWAYS_RAISE_EXCEPTIONS")
SENTRY_DSN = env.str("SENTRY_DSN")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(monitor_beat_tasks=True),
        ],
    )

checkout_dir = environ.Path(__file__) - 3
if not os.path.exists(checkout_dir("manage.py")):
    raise RuntimeError("Could not locate manage.py")


DEBUG = env.bool("DEBUG")
DEBUG_SIMULATED_LAG = env.int("DEBUG_SIMULATED_LAG")

# Only used when creating certain test fixtures
DISABLE_TRANSACTION_CHECKS = False

SECRET_KEY = env.str("SECRET_KEY")

PRIMARY_HOST = env.str("PRIMARY_HOST")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
if CORS_ALLOWED_ORIGINS == ["*"]:
    CORS_ALLOWED_ORIGINS = []
    CORS_ALLOW_ALL_ORIGINS = True

DATABASE_LOGS = env.bool("DATABASE_LOGS")
DATABASE_QUERY_COUNT_HEADER = env.bool("DATABASE_QUERY_COUNT_HEADER")

DATABASES = {"default": env.db()}
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = env.bool(
    "DISABLE_SERVER_SIDE_CURSORS",
)

DB_CERT_DIR = env.str("DB_CERT_DIR")
DB_CLIENT_CERT = env.str("DB_CLIENT_CERT")
DB_CLIENT_KEY = env.str("DB_CLIENT_KEY")
DB_SERVER_CA = env.str("DB_SERVER_CA")


def load_db_certs():
    if not DB_CERT_DIR:
        return

    cert_dir = "/etc/ssl/private/db-certs/"
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    mappings = {
        "sslcert": ("client-cert.pem", DB_CLIENT_CERT),
        "sslkey": ("client-key.pem", DB_CLIENT_KEY),
        "sslrootcert": ("server-ca.pem", DB_SERVER_CA),
    }
    cert_options = {}

    for target_parameter, (filename, cert_encoded) in mappings.items():
        if not cert_encoded:
            continue
        target = os.path.join(cert_dir, filename)
        cert = base64.b64decode(cert_encoded).decode("utf-8")
        with open(os.open(target, os.O_CREAT | os.O_WRONLY, 0o600), "w") as certfile:
            certfile.write(cert)

        cert_options[target_parameter] = target

    if "OPTIONS" not in DATABASES["default"]:
        DATABASES["default"]["OPTIONS"] = {}

    if cert_options:
        cert_options["sslmode"] = "verify-ca"

    DATABASES["default"]["OPTIONS"].update(cert_options)


load_db_certs()

# Application definition

INSTALLED_APPS = plugin_registry.get_installed_apps(
    [
        # Django
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "django.contrib.postgres",
        "django.contrib.sites",
        # 3rd Party
        "easy_thumbnails",
        "social_django",
        "rest_framework",
        "rest_framework.authtoken",
        "drf_yasg",
        "django_celery_beat",
        "django_celery_results",
        "cachalot",
        "corsheaders",
        # Own Standalone
        "django_contracts",
        # Own
        "thunderstore.core",
        "thunderstore.cache",
        "thunderstore.api",
        "thunderstore.frontend",
        "thunderstore.repository",
        "thunderstore.webhooks",
        "thunderstore.social",
        "thunderstore.community",
        "thunderstore.usermedia",
        "thunderstore.account",
        "thunderstore.markdown",
        "thunderstore.modpacks",
        "thunderstore.schema_import",
        "thunderstore.schema_server",
        "thunderstore.legal",
        "thunderstore.wiki",
        "thunderstore.storage",
        "thunderstore.metrics",
        "thunderstore.moderation",
        "thunderstore.permissions",
    ]
)

MIDDLEWARE = [
    "thunderstore.core.middleware.QueryCountHeaderMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "thunderstore.frontend.middleware.SocialAuthExceptionHandlerMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "thunderstore.community.middleware.CommunitySiteMiddleware",
    "thunderstore.account.middleware.UserFlagsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "thunderstore.abyss.middleware.TracingMiddleware",
]

ROOT_URLCONF = "thunderstore.core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "thunderstore.repository.context_processors.team",
                "thunderstore.community.context_processors.community_site",
                "thunderstore.community.context_processors.selectable_communities",
                "thunderstore.legal.context_processors.legal_contracts",
                "thunderstore.frontend.context.nav_links",
                "thunderstore.frontend.context.footer_links",
            ],
        },
    },
]

WSGI_APPLICATION = "thunderstore.core.wsgi.application"

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "var/media/")

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "var/static/")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "static_built"),
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Sessions

# Session cookie used by React components during Django React transition
SESSION_COOKIE_HTTPONLY = False

SESSION_COOKIE_DOMAIN = env.str("SESSION_COOKIE_DOMAIN") or None


# Celery
class CeleryQueues:
    Default = "celery"
    LogDownloads = "log.downloads"
    BackgroundCache = "background.cache"
    BackgroundTask = "background.task"
    BackgroundLongRunning = "background.long_running"


CELERY_BROKER_URL = env.str("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = "django-db"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_CREATE_MISSING_QUEUES = env("CELERY_TASK_CREATE_MISSING_QUEUES")
CELERY_EAGER_PROPAGATES_EXCEPTIONS = env.bool("CELERY_EAGER_PROPAGATES_EXCEPTIONS")
CELERY_TASK_TIME_LIMIT = env("CELERY_TASK_TIME_LIMIT")
CELERY_TASK_SOFT_TIME_LIMIT = env("CELERY_TASK_SOFT_TIME_LIMIT")
CELERY_TASK_DEFAULT_QUEUE = CeleryQueues.Default

# Custom settings

SITE_NAME = env.str("SITE_NAME")
SITE_DESCRIPTION = env.str("SITE_DESCRIPTION")
SITE_SLOGAN = env.str("SITE_SLOGAN")

LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"

REPOSITORY_MAX_PACKAGE_SIZE_MB = env.int("REPOSITORY_MAX_PACKAGE_SIZE_MB")
REPOSITORY_MAX_PACKAGE_TOTAL_SIZE_GB = env.int("REPOSITORY_MAX_PACKAGE_TOTAL_SIZE_GB")
LEGACYPROFILE_MAX_TOTAL_SIZE_GB = env.int("LEGACYPROFILE_MAX_TOTAL_SIZE_GB")

ECOSYSTEM_SCHEMA_URL = env.str("ECOSYSTEM_SCHEMA_URL")

# Debug toolbar

DEBUG_TOOLBAR_ENABLED = all(
    (
        DEBUG_TOOLBAR_AVAILABLE,
        env.bool("DEBUG_TOOLBAR_ENABLED"),
    ),
)
DEBUG_TOOLBAR_SUPERUSER_ONLY = env.bool("DEBUG_TOOLBAR_SUPERUSER_ONLY")


def show_debug_toolbar(request: HttpRequest) -> bool:
    is_superuser = hasattr(request, "user") and request.user.is_superuser
    should_show = bool(request.GET.get("debug", False))
    return (
        DEBUG_TOOLBAR_ENABLED
        and (
            (DEBUG_TOOLBAR_SUPERUSER_ONLY and is_superuser)
            or (DEBUG and not DEBUG_TOOLBAR_SUPERUSER_ONLY)
        )
        and should_show
    )


if DEBUG_TOOLBAR_AVAILABLE:
    INSTALLED_APPS += ["debug_toolbar"]

if DEBUG_TOOLBAR_ENABLED:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    DEBUG_TOOLBAR_PANELS = [
        "debug_toolbar.panels.history.HistoryPanel",
        "debug_toolbar.panels.versions.VersionsPanel",
        "debug_toolbar.panels.timer.TimerPanel",
        "debug_toolbar.panels.settings.SettingsPanel",
        "debug_toolbar.panels.headers.HeadersPanel",
        "debug_toolbar.panels.request.RequestPanel",
        "debug_toolbar.panels.sql.SQLPanel",
        "debug_toolbar.panels.staticfiles.StaticFilesPanel",
        "debug_toolbar.panels.templates.TemplatesPanel",
        "debug_toolbar.panels.cache.CachePanel",
        "debug_toolbar.panels.signals.SignalsPanel",
        "debug_toolbar.panels.logging.LoggingPanel",
        "debug_toolbar.panels.redirects.RedirectsPanel",
        "debug_toolbar.panels.profiling.ProfilingPanel",
        "cachalot.panels.CachalotPanel",
    ]
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": "thunderstore.core.settings.show_debug_toolbar",
    }


# Caching

DISABLED_CACHE_BUST_CONDITIONS = env.list("DISABLED_CACHE_BUST_CONDITIONS")
USE_MULTIPLE_CACHES = env.bool("USE_MULTIPLE_CACHES")


def get_redis_cache(env_key: str, fallback_key: Optional[str] = None):
    url = env.str(env_key)
    if not url and fallback_key:
        warnings.warn(
            f"No redis URL for {env_key} was provided, using {fallback_key} as "
            f"fallback. !!This creates extra connections to {fallback_key}!!"
        )
        url = env.str(fallback_key)
    if not url and "manage.py" not in sys.argv:
        raise RuntimeError(f"Missing redis URL: {env_key}")
    return {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": url,
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 0.5,
            "SOCKET_TIMEOUT": 5,
        },
    }


CACHES = {
    "default": get_redis_cache("REDIS_URL"),
    "legacy": get_redis_cache("REDIS_URL_LEGACY", "REDIS_URL"),
    "profiles": {
        **get_redis_cache("REDIS_URL_PROFILES", "REDIS_URL"),
        "TIMEOUT": None,
    },
    "downloads": {
        **get_redis_cache("REDIS_URL_DOWNLOADS", "REDIS_URL"),
        "TIMEOUT": None,
    },
}


CACHALOT_TIMEOUT = env.int("CACHALOT_TIMEOUT_SECONDS")
CACHALOT_ENABLED = env.bool("CACHALOT_ENABLED")
CACHALOT_UNCACHABLE_TABLES = frozenset(
    (
        # Should never return stale data
        "django_migrations",
        # Handles its own TTL
        "cache_databasecache",
        # Enabling this will break a test, so it's left off for now for safety
        "repository_apiv1packagecache",
        # Should never return stale data
        # Frequent writes & invalidations, not many reads -> not worth caching
        "django_celery_results_chordcounter",
        "django_celery_results_taskresult",
        # Too frequent writes for cachalot to work efficiently
        "django_session",
        "metrics_packageversiondownloadevent",
        "repository_packageversion",
        "repository_packageversiondownloadevent",
        "repository_packagerating",
        "modpacks_legacyprofile",
    )
)

# if DEBUG and not DEBUG_SIMULATED_LAG:
#     CACHES = {
#         "default": {
#             "BACKEND": "django.core.cache.backends.dummy.DummyCache",
#         }
#     }

LOGGING = {
    "version": 1,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {},
}

if DATABASE_LOGS:
    LOGGING["loggers"]["django.db.backends"] = {
        "level": "DEBUG",
        "handlers": ["console"],
    }


# REST Framework

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "thunderstore.account.authentication.ServiceAccountTokenAuthentication",
        "thunderstore.account.authentication.UserSessionTokenAuthentication",
    ],
    "EXCEPTION_HANDLER": "thunderstore.core.exception_handler.exception_handler",
}

# Thumbnails

THUMBNAIL_QUALITY = 95

#######################################
#               STORAGE               #
#######################################

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
THUMBNAIL_DEFAULT_STORAGE = "django.core.files.storage.FileSystemStorage"
PACKAGE_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MODPACK_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
SCHEMA_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
BLOB_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# AWS S3 for everything, can be used with S3 compatible providers

AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME")
AWS_S3_ENDPOINT_URL = env.str("AWS_S3_ENDPOINT_URL")
AWS_S3_HOST = env.str("AWS_S3_HOST")
AWS_S3_CUSTOM_DOMAIN = env.str("AWS_S3_CUSTOM_DOMAIN")
AWS_S3_FILE_OVERWRITE = env.bool("AWS_S3_FILE_OVERWRITE")
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
AWS_DEFAULT_ACL = env.str("AWS_DEFAULT_ACL")
AWS_BUCKET_ACL = env.str("AWS_BUCKET_ACL")
AWS_AUTO_CREATE_BUCKET = env.bool("AWS_AUTO_CREATE_BUCKET")
AWS_LOCATION = validate_filepath_prefix(env.str("AWS_LOCATION"))
AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH")
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=2592000",  # 30 days
}
AWS_S3_SECURE_URLS = env.bool("AWS_S3_SECURE_URLS")

# Usermedia S3 settings

USERMEDIA_S3_ENDPOINT_URL = env.str("USERMEDIA_S3_ENDPOINT_URL")
USERMEDIA_S3_ACCESS_KEY_ID = env.str("USERMEDIA_S3_ACCESS_KEY_ID")
USERMEDIA_S3_SECRET_ACCESS_KEY = env.str("USERMEDIA_S3_SECRET_ACCESS_KEY")
USERMEDIA_S3_SIGNING_ENDPOINT_URL = env.str("USERMEDIA_S3_SIGNING_ENDPOINT_URL")
USERMEDIA_S3_REGION_NAME = env.str("USERMEDIA_S3_REGION_NAME")
USERMEDIA_S3_STORAGE_BUCKET_NAME = env.str("USERMEDIA_S3_STORAGE_BUCKET_NAME")
USERMEDIA_S3_LOCATION = validate_filepath_prefix(env.str("USERMEDIA_S3_LOCATION"))
USERMEDIA_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=2592000",  # 30 days
}

# Abyss S3 settings

ABYSS_S3_ENDPOINT_URL = env.str("ABYSS_S3_ENDPOINT_URL")
ABYSS_S3_ACCESS_KEY_ID = env.str("ABYSS_S3_ACCESS_KEY_ID")
ABYSS_S3_SECRET_ACCESS_KEY = env.str("ABYSS_S3_SECRET_ACCESS_KEY")
ABYSS_S3_REGION_NAME = env.str("ABYSS_S3_REGION_NAME")
ABYSS_S3_STORAGE_BUCKET_NAME = env.str("ABYSS_S3_STORAGE_BUCKET_NAME")
ABYSS_S3_LOCATION = validate_filepath_prefix(env.str("ABYSS_S3_LOCATION"))
ABYSS_S3_FILE_OVERWRITE = env.bool("ABYSS_S3_FILE_OVERWRITE")
ABYSS_S3_CUSTOM_DOMAIN = env.str("ABYSS_S3_CUSTOM_DOMAIN")
ABYSS_S3_SECURE_URLS = env.bool("ABYSS_S3_SECURE_URLS")
ABYSS_S3_DEFAULT_ACL = env.str("ABYSS_S3_DEFAULT_ACL")
ABYSS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=2592000",  # 30 days
}


# Cache S3 settings

CACHE_S3_ENDPOINT_URL = env.str("CACHE_S3_ENDPOINT_URL")
CACHE_S3_ACCESS_KEY_ID = env.str("CACHE_S3_ACCESS_KEY_ID")
CACHE_S3_SECRET_ACCESS_KEY = env.str("CACHE_S3_SECRET_ACCESS_KEY")
CACHE_S3_REGION_NAME = env.str("CACHE_S3_REGION_NAME")
CACHE_S3_STORAGE_BUCKET_NAME = env.str("CACHE_S3_STORAGE_BUCKET_NAME")
CACHE_S3_LOCATION = validate_filepath_prefix(env.str("CACHE_S3_LOCATION"))
CACHE_S3_FILE_OVERWRITE = env.bool("CACHE_S3_FILE_OVERWRITE")
CACHE_S3_CUSTOM_DOMAIN = env.str("CACHE_S3_CUSTOM_DOMAIN")
CACHE_S3_SECURE_URLS = env.bool("CACHE_S3_SECURE_URLS")
CACHE_S3_DEFAULT_ACL = env.str("CACHE_S3_DEFAULT_ACL")
CACHE_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=2592000",  # 30 days
}

if not all((CACHE_S3_ENDPOINT_URL, CACHE_S3_ACCESS_KEY_ID, CACHE_S3_SECRET_ACCESS_KEY)):
    if sys.argv[0] != "manage.py":
        raise RuntimeError("Invalid cache configuration")


if all((AWS_S3_ENDPOINT_URL, AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID)):
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    THUMBNAIL_DEFAULT_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    PACKAGE_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    MODPACK_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    SCHEMA_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    BLOB_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# For uploading files to multiple buckets at once.
S3_MIRRORS: Tuple[S3MirrorConfig, ...] = (
    # {
    #     "access_key": env.str("..."),
    #     "secret_key": env.str("..."),
    #     "region_name": env.str("..."),
    #     "bucket_name": env.str("..."),
    #     "location": env.str("..."),
    #     "custom_domain": env.str("..."),
    #     "endpoint_url": env.str("..."),
    #     "secure_urls": env.bool("..."),
    #     "file_overwrite": env.bool("..."),
    #     "default_acl": env.str("..."),
    #     "object_parameters": AWS_S3_OBJECT_PARAMETERS,
    # },
)

if all(
    (
        env.str("MIRROR_S3_ACCESS_KEY_ID"),
        env.str("MIRROR_S3_SECRET_ACCESS_KEY"),
        env.str("MIRROR_S3_ENDPOINT_URL"),
        env.str("MIRROR_S3_STORAGE_BUCKET_NAME"),
    ),
):
    mirror: Tuple[S3MirrorConfig, ...] = (
        {
            "access_key": env.str("MIRROR_S3_ACCESS_KEY_ID"),
            "secret_key": env.str("MIRROR_S3_SECRET_ACCESS_KEY"),
            "region_name": env.str("MIRROR_S3_REGION_NAME"),
            "bucket_name": env.str("MIRROR_S3_STORAGE_BUCKET_NAME"),
            "location": validate_filepath_prefix(env.str("MIRROR_S3_LOCATION")),
            "custom_domain": env.str("MIRROR_S3_CUSTOM_DOMAIN"),
            "endpoint_url": env.str("MIRROR_S3_ENDPOINT_URL"),
            "secure_urls": env.bool("MIRROR_S3_SECURE_URLS"),
            "file_overwrite": env.bool("MIRROR_S3_FILE_OVERWRITE"),
            "default_acl": env.str("MIRROR_S3_DEFAULT_ACL"),
            "object_parameters": AWS_S3_OBJECT_PARAMETERS,
        },
    )
    S3_MIRRORS = S3_MIRRORS + mirror
    DEFAULT_FILE_STORAGE = "thunderstore.core.storage.MirroredS3Storage"
    THUMBNAIL_DEFAULT_STORAGE = "thunderstore.core.storage.MirroredS3Storage"
    PACKAGE_FILE_STORAGE = "thunderstore.core.storage.MirroredS3Storage"
    MODPACK_FILE_STORAGE = "thunderstore.core.storage.MirroredS3Storage"
    SCHEMA_FILE_STORAGE = "thunderstore.core.storage.MirroredS3Storage"
    BLOB_FILE_STORAGE = "thunderstore.core.storage.MirroredS3Storage"

ALLOWED_CDNS = env.list("ALLOWED_CDNS")

# Storage Defaults
DEFAULT_FILE_STORAGE = get_storage_class_or_stub(DEFAULT_FILE_STORAGE)
THUMBNAIL_DEFAULT_STORAGE = get_storage_class_or_stub(THUMBNAIL_DEFAULT_STORAGE)
PACKAGE_FILE_STORAGE = get_storage_class_or_stub(PACKAGE_FILE_STORAGE)
MODPACK_FILE_STORAGE = get_storage_class_or_stub(MODPACK_FILE_STORAGE)
SCHEMA_FILE_STORAGE = get_storage_class_or_stub(SCHEMA_FILE_STORAGE)
BLOB_FILE_STORAGE = get_storage_class_or_stub(BLOB_FILE_STORAGE)

# Social auth

SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_URL_NAMESPACE = "social"
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ["username", "first_name", "email"]
SOCIAL_AUTH_ADMIN_SEARCH_FIELDS = ["uid"]
AUTHENTICATION_BACKENDS = (
    "social_core.backends.github.GithubOAuth2",
    "social_core.backends.discord.DiscordOAuth2",
    "overwolf_auth.backends.OverwolfOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

# Social auth - GitHub
SOCIAL_AUTH_GITHUB_KEY = env.str("SOCIAL_AUTH_GITHUB_KEY")
SOCIAL_AUTH_GITHUB_SECRET = env.str("SOCIAL_AUTH_GITHUB_SECRET")
SOCIAL_AUTH_GITHUB_SCOPE = ["user:email", "read:user", "read:org"]
SOCIAL_AUTH_GITHUB_PROFILE_EXTRA_PARAMS = {"fields": "email"}
SOCIAL_AUTH_GITHUB_GET_ALL_EXTRA_DATA = True

# Social auth - Discord
SOCIAL_AUTH_DISCORD_KEY = env.str("SOCIAL_AUTH_DISCORD_KEY")
SOCIAL_AUTH_DISCORD_SECRET = env.str("SOCIAL_AUTH_DISCORD_SECRET")
SOCIAL_AUTH_DISCORD_SCOPE = ["email"]
SOCIAL_AUTH_DISCORD_PROFILE_EXTRA_PARAMS = {"fields": "email"}
SOCIAL_AUTH_DISCORD_GET_ALL_EXTRA_DATA = True

# Social auth - Overwolf
SOCIAL_AUTH_OVERWOLF_KEY = env.str("SOCIAL_AUTH_OVERWOLF_KEY")
SOCIAL_AUTH_OVERWOLF_SECRET = env.str("SOCIAL_AUTH_OVERWOLF_SECRET")
SOCIAL_AUTH_OVERWOLF_SCOPE = ["openid", "profile", "email"]  # "openid" is required
SOCIAL_AUTH_OVERWOLF_GET_ALL_EXTRA_DATA = True

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)
SOCIAL_AUTH_SANITIZE_REDIRECTS = env.bool("SOCIAL_AUTH_SANITIZE_REDIRECTS")
SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS = env.list("SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS")
SOCIAL_AUTH_INIT_HOST = env.str("SOCIAL_AUTH_INIT_HOST") or None
AUTH_EXCLUSIVE_HOST = env.str("AUTH_EXCLUSIVE_HOST") or None

PROTOCOL = env.str("PROTOCOL")
if PROTOCOL == "https://":
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_REDIRECT_EXEMPT = "/healthcheck/"

# Token shared between Thunderstore apps to restrict access to OAuth
# related endpoints.
OAUTH_SHARED_SECRET = env.str("OAUTH_SHARED_SECRET")

# Mod manager client id
OVERWOLF_CLIENT_ID = env.str("OVERWOLF_CLIENT_ID")

# Cyberstorm APIs enabled?
IS_CYBERSTORM_ENABLED = env.bool("IS_CYBERSTORM_ENABLED")

# Enable QA API endpoint docs
SHOW_CYBERSTORM_API_DOCS = env.bool("SHOW_CYBERSTORM_API_DOCS")

# Enable the async package submission frontend flow
USE_ASYNC_PACKAGE_SUBMISSION_FLOW = env.bool("USE_ASYNC_PACKAGE_SUBMISSION_FLOW")

# Enable the new package download metrics implementation
USE_TIME_SERIES_PACKAGE_DOWNLOAD_METRICS = env.bool(
    "USE_TIME_SERIES_PACKAGE_DOWNLOAD_METRICS"
)

# Seconds to wait between logging download events
DOWNLOAD_METRICS_TTL_SECONDS = env.int("DOWNLOAD_METRICS_TTL_SECONDS")

globals().update(plugin_registry.get_django_settings(globals()))
