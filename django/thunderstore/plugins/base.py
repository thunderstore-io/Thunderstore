from abc import ABC
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Set

from django.urls import URLPattern

from thunderstore.plugins.types import SettingsLink

if TYPE_CHECKING:
    from thunderstore.community.models import PackageListing
    from thunderstore.core.types import UserType
    from thunderstore.repository.views.mixins import PartialTab


class BasePlugin(ABC):
    INSTALLED_APPS: ClassVar[Set[str]] = set()

    @classmethod
    def get_settings_links(cls) -> List[SettingsLink]:
        return []

    @classmethod
    def get_settings_urls(cls) -> List[URLPattern]:
        return []

    @classmethod
    def get_package_tabs(
        cls,
    ) -> Dict[str, Callable[["UserType", "PackageListing"], "PartialTab"]]:
        return {}

    @classmethod
    def get_django_settings(cls, settings: Dict[str, Any]) -> Dict[str, Any]:
        return dict()
