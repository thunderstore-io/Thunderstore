from abc import ABC
from typing import Any, ClassVar, Dict, List, Set

from django.urls import URLPattern

from thunderstore.plugins.types import SettingsLink


class BasePlugin(ABC):
    INSTALLED_APPS: ClassVar[Set[str]] = set()

    @classmethod
    def get_settings_links(cls) -> List[SettingsLink]:
        return []

    @classmethod
    def get_settings_urls(cls) -> List[URLPattern]:
        return []

    @classmethod
    def get_django_settings(cls, settings: Dict[str, Any]) -> Dict[str, Any]:
        return dict()
