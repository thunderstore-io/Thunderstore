import base64
import json
import os

import environ

try:
    import debug_toolbar

    DEBUG_TOOLBAR_AVAILABLE = True
except ImportError:
    DEBUG_TOOLBAR_AVAILABLE = False

from google.oauth2 import service_account

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env = environ.Env(
    DEBUG=(bool, False),
    DEBUG_SIMULATED_LAG=(int, 0),
    DEBUG_TOOLBAR_ENABLED=(bool, False),
    DATABASE_LOGS=(bool, False),
    DATABASE_QUERY_COUNT_HEADER=(bool, False),
    DATABASE_URL=(str, "sqlite:///database/default.db"),
    DISABLE_SERVER_SIDE_CURSORS=(bool, True),
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    PROTOCOL=(str, ""),
    SOCIAL_AUTH_DISCORD_KEY=(str, ""),
    SOCIAL_AUTH_DISCORD_SECRET=(str, ""),
    SOCIAL_AUTH_GITHUB_KEY=(str, ""),
    SOCIAL_AUTH_GITHUB_SECRET=(str, ""),
    GS_BUCKET_NAME=(str, ""),
    GS_PROJECT_ID=(str, ""),
    GS_CREDENTIALS=(str, ""),
    GS_AUTO_CREATE_BUCKET=(bool, False),
    GS_AUTO_CREATE_ACL=(str, "publicRead"),
    GS_DEFAULT_ACL=(str, "publicRead"),
    GS_LOCATION=(str, ""),
    GS_FILE_OVERWRITE=(bool, False),
    B2_KEY_ID=(str, ""),
    B2_KEY=(str, ""),
    B2_BUCKET_ID=(str, ""),
    B2_LOCATION=(str, ""),
    B2_FILE_OVERWRITE=(bool, True),
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
    USERMEDIA_S3_ENDPOINT_URL=(str, ""),
    USERMEDIA_S3_ACCESS_KEY_ID=(str, ""),
    USERMEDIA_S3_SECRET_ACCESS_KEY=(str, ""),
    USERMEDIA_S3_SIGNING_ENDPOINT_URL=(str, ""),
    USERMEDIA_S3_REGION_NAME=(str, ""),
    USERMEDIA_S3_STORAGE_BUCKET_NAME=(str, ""),
    USERMEDIA_S3_LOCATION=(str, ""),
    REDIS_URL=(str, ""),
    DB_CERT_DIR=(str, ""),
    DB_CLIENT_CERT=(str, ""),
    DB_CLIENT_KEY=(str, ""),
    DB_SERVER_CA=(str, ""),
    SENTRY_DSN=(str, ""),
    CELERY_BROKER_URL=(str, ""),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=(bool, False),
)

SENTRY_DSN = env.str("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(dsn=SENTRY_DSN, integrations=[DjangoIntegration()])

checkout_dir = environ.Path(__file__) - 3
if not os.path.exists(checkout_dir("manage.py")):
    raise RuntimeError("Could not locate manage.py")

DEBUG = env.bool("DEBUG")
DEBUG_SIMULATED_LAG = env.int("DEBUG_SIMULATED_LAG")

SECRET_KEY = env.str("SECRET_KEY")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
if CORS_ALLOWED_ORIGINS == ["*"]:
    CORS_ALLOWED_ORIGINS = []
    CORS_ALLOW_ALL_ORIGINS = True

DATABASE_LOGS = env.bool("DATABASE_LOGS")
DATABASE_QUERY_COUNT_HEADER = env.bool("DATABASE_QUERY_COUNT_HEADER")

DATABASES = {"default": env.db()}
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = env.bool(
    "DISABLE_SERVER_SIDE_CURSORS"
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

INSTALLED_APPS = [
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
    # Own
    "thunderstore.core",
    "thunderstore.cache",
    "thunderstore.frontend",
    "thunderstore.repository",
    "thunderstore.webhooks",
    "thunderstore.social",
    "thunderstore.community",
    "thunderstore.usermedia",
    "thunderstore.account",
    "backblaze_b2",
]

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
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
                "thunderstore.repository.context_processors.uploader_identity",
                "thunderstore.community.context_processors.community_site",
                "thunderstore.community.context_processors.selectable_sites",
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

# Celery

CELERY_BROKER_URL = env.str("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = "django-db"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER")
CELERY_EAGER_PROPAGATES_EXCEPTIONS = env.bool("CELERY_EAGER_PROPAGATES_EXCEPTIONS")

# Custom settings

LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"

# Debug toolbar

DEBUG_TOOLBAR_ENABLED = all(
    (
        DEBUG,
        DEBUG_TOOLBAR_AVAILABLE,
        env.bool("DEBUG_TOOLBAR_ENABLED"),
    )
)


def show_debug_toolbar(request):
    return DEBUG_TOOLBAR_ENABLED


if DEBUG_TOOLBAR_ENABLED:
    INSTALLED_APPS += ["debug_toolbar"]
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

REDIS_URL = env.str("REDIS_URL")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "TIMEOUT": 300,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
                "SOCKET_CONNECT_TIMEOUT": 0.5,
                "SOCKET_TIMEOUT": 5,
            },
        }
    }

CACHALOT_ONLY_CACHABLE_TABLES = frozenset(
    (
        "auth_group",
        "auth_group_permissions",
        "auth_permission",
        "auth_user",
        "auth_user_groups",
        "auth_user_user_permissions",
        "authtoken_token",
        "backblaze_b2_backblazeb2file",
        "community_community",
        "community_communitymembership",
        "community_communitysite",
        "community_packagecategory",
        "community_packagelisting",
        "community_packagelisting_categories",
        "community_packagelistingsection",
        "community_packagelistingsection_exclude_categories",
        "community_packagelistingsection_require_categories",
        "core_incomingjwtauthconfiguration",
        "django_admin_log",
        "django_celery_beat_clockedschedule",
        "django_celery_beat_crontabschedule",
        "django_celery_beat_intervalschedule",
        "django_celery_beat_periodictask",
        "django_celery_beat_periodictasks",
        "django_celery_beat_solarschedule",
        "django_celery_results_chordcounter",
        "django_celery_results_taskresult",
        "django_content_type",
        "django_site",
        "easy_thumbnails_source",
        "easy_thumbnails_thumbnail",
        "easy_thumbnails_thumbnaildimensions",
        "frontend_dynamichtml",
        "frontend_dynamichtml_exclude_communities",
        "frontend_dynamichtml_require_communities",
        "repository_discorduserbotpermission",
        "repository_package",
        "repository_packageversion_dependencies",
        "repository_uploaderidentity",
        "repository_uploaderidentitymember",
        "social_auth_association",
        "social_auth_code",
        "social_auth_nonce",
        "social_auth_partial",
        "social_auth_usersocialauth",
        "usermedia_usermedia",
        "webhooks_webhook",
        "webhooks_webhook_exclude_categories",
        "webhooks_webhook_require_categories",
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
        "thunderstore.account.authentication.TokenAuthentication",
        "thunderstore.account.authentication.UserSessionTokenAuthentication",
    ],
}

#######################################
#               STORAGE               #
#######################################

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
THUMBNAIL_DEFAULT_STORAGE = "django.core.files.storage.FileSystemStorage"
PACKAGE_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Google Cloud Storage

GS_BUCKET_NAME = env.str("GS_BUCKET_NAME")
GS_PROJECT_ID = env.str("GS_PROJECT_ID")

GS_CREDENTIALS = env.str("GS_CREDENTIALS")
if GS_CREDENTIALS:
    GS_CREDENTIALS = json.loads(base64.b64decode(GS_CREDENTIALS).decode("utf-8"))
    GS_CREDENTIALS = service_account.Credentials.from_service_account_info(
        GS_CREDENTIALS
    )

GS_AUTO_CREATE_BUCKET = env.str("GS_AUTO_CREATE_BUCKET")
GS_AUTO_CREATE_ACL = env.str("GS_AUTO_CREATE_ACL")
GS_DEFAULT_ACL = env.str("GS_DEFAULT_ACL")
GS_LOCATION = env.str("GS_LOCATION")
GS_FILE_OVERWRITE = env.bool("GS_FILE_OVERWRITE")

if GS_CREDENTIALS and GS_PROJECT_ID and GS_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
    THUMBNAIL_DEFAULT_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"

# Backblaze B2 Cloud Storage for packages

B2_KEY_ID = env.str("B2_KEY_ID")
B2_KEY = env.str("B2_KEY")
B2_BUCKET_ID = env.str("B2_BUCKET_ID")
B2_LOCATION = env.str("B2_LOCATION")
B2_FILE_OVERWRITE = env.str("B2_FILE_OVERWRITE")

if B2_KEY_ID and B2_KEY and B2_BUCKET_ID:
    PACKAGE_FILE_STORAGE = "backblaze_b2.storage.BackblazeB2Storage"

# AWS S3 for everything, can be used with S3 compatible providers

AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY")
AWS_S3_REGION_NAME = env.str("AWS_S3_REGION_NAME")
AWS_S3_ENDPOINT_URL = env.str("AWS_S3_ENDPOINT_URL")
AWS_S3_HOST = env.str("AWS_S3_HOST")
AWS_S3_CUSTOM_DOMAIN = env.str("AWS_S3_CUSTOM_DOMAIN")
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME")
AWS_DEFAULT_ACL = env.str("AWS_DEFAULT_ACL")
AWS_BUCKET_ACL = env.str("AWS_BUCKET_ACL")
AWS_AUTO_CREATE_BUCKET = env.bool("AWS_AUTO_CREATE_BUCKET")
AWS_LOCATION = env.str("AWS_LOCATION")
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
USERMEDIA_S3_LOCATION = env.str("USERMEDIA_S3_LOCATION")
USERMEDIA_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=2592000",  # 30 days
}


if all((AWS_S3_ENDPOINT_URL, AWS_SECRET_ACCESS_KEY, AWS_ACCESS_KEY_ID)):
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    THUMBNAIL_DEFAULT_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    PACKAGE_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Social auth

SOCIAL_AUTH_POSTGRES_JSONFIELD = True
SOCIAL_AUTH_URL_NAMESPACE = "social"
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ["username", "first_name", "email"]
AUTHENTICATION_BACKENDS = (
    "social_core.backends.github.GithubOAuth2",
    "social_core.backends.discord.DiscordOAuth2",
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
SOCIAL_AUTH_STRATEGY = "thunderstore.community.social_auth.CommunitySocialAuthStrategy"

PROTOCOL = env.str("PROTOCOL")
if PROTOCOL == "https://":
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_REDIRECT_EXEMPT = "/healthcheck/"
