from .celery import app as celery_app

default_app_config = "thunderstore.core.apps.CoreAppConfig"

__all__ = ("celery_app", "default_app_config")
