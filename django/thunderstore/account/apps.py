from django.apps import AppConfig


class AccountAppConfig(AppConfig):
    name = "thunderstore.account"
    label = "account"

    def ready(self):
        from . import signals
