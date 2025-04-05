import itertools
from typing import TYPE_CHECKING, Any, Dict, List, Set, Type

from django.urls import URLPattern

from .base import BasePlugin
from .loading import load_ts_plugins
from .types import SettingsLink

if TYPE_CHECKING:
    from ..community.models import PackageListing
    from ..core.types import UserType
    from ..repository.views.mixins import PartialTab


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

    def get_legacy_package_urls(self) -> List[URLPattern]:
        return list(
            itertools.chain(*(x.get_legacy_package_urls() for x in self.plugins))
        )

    def get_new_package_urls(self) -> List[URLPattern]:
        return list(itertools.chain(*(x.get_new_package_urls() for x in self.plugins)))

    def get_cyberstorm_api_urls(self) -> List[URLPattern]:
        return list(
            itertools.chain(*(x.get_cyberstorm_api_urls() for x in self.plugins))
        )

    def get_package_tabs(
        self, user: "UserType", listing: "PackageListing"
    ) -> Dict[str, "PartialTab"]:
        result = {}
        for entry in (x.get_package_tabs() for x in self.plugins):
            for key, getter in entry.items():
                result[key] = getter(user, listing)
        return result

    def get_settings_links(self) -> List[SettingsLink]:
        return list(itertools.chain(*(x.get_settings_links() for x in self.plugins)))


plugin_registry = PluginRegistry.autodiscover()
