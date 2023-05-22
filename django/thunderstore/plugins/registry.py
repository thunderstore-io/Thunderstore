import itertools
from typing import Any, Dict, List, Set, Type

from django.urls import URLPattern

from .base import BasePlugin
from .loading import load_ts_plugins


class PluginRegistry:
    plugins: Set[Type[BasePlugin]]

    def __init__(self, plugins: Set[Type[BasePlugin]]):
        self.plugins = plugins

    @classmethod
    def autodiscover(cls) -> "PluginRegistry":
        return cls(load_ts_plugins())

    def get_django_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        for plugin in self.plugins:
            settings.update(plugin.get_django_settings(settings))
        return settings

    def get_installed_apps(self, base_apps: List[str]) -> List[str]:
        return sorted(
            set().union(*(base_apps, *[x.INSTALLED_APPS for x in self.plugins]))
        )

    def get_settings_urls(self) -> List[URLPattern]:
        return list(itertools.chain(*(x.get_settings_urls() for x in self.plugins)))


plugin_registry = PluginRegistry.autodiscover()
