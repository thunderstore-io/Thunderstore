import functools
import io
import os
from abc import ABC
from dataclasses import dataclass, field
from typing import Collection, List, Type

from django.core.files.base import File
from django.db.models import Model
from PIL import Image

from django_contracts.models import LegalContract
from thunderstore.community.models import Community
from thunderstore.repository.models import Package, PackageWiki, Team


@dataclass
class ContentPopulatorContext:
    teams: Collection[Team] = field(default_factory=list)
    packages: Collection[Package] = field(default_factory=list)
    communities: Collection[Community] = field(default_factory=list)
    contracts: Collection[LegalContract] = field(default_factory=list)
    package_wikis: Collection[PackageWiki] = field(default_factory=list)

    community_count: int = 0
    dependency_count: int = 0
    version_count: int = 0
    team_count: int = 0
    package_count: int = 0
    contract_count: int = 0
    contract_version_count: int = 0
    wiki_page_count: int = 0
    reuse_icon: bool = False


class ContentPopulator(ABC):
    def populate(self, context: ContentPopulatorContext) -> None:
        ...

    def update_context(self, context) -> None:
        ...

    def clear(self) -> None:
        ...


class BaseContentPopulator(ContentPopulator):
    model_cls: Type[Model] = None
    name: str = None

    def clear(self) -> None:
        print(f"Deleting {self.name}...")
        self.model_cls.objects.all().delete()

    def get_last(self) -> int:
        return last_obj.pk if (last_obj := self.model_cls.objects.last()) else 0

    def update_context(self, context: ContentPopulatorContext) -> None:
        pass

    def set_context_objs(
        self, context: ContentPopulatorContext, objs: List[Model]
    ) -> None:
        pass


@functools.lru_cache(maxsize=None)
def dummy_markdown() -> str:
    markdown_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "markdown.md"
    )
    with open(markdown_path, "r") as f:
        return f.read()


LOREM_IPSUM = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint
occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
"""


def dummy_package_icon() -> File:
    file_obj = io.BytesIO()
    image = Image.new("RGB", (256, 256), "#231F36")
    image.save(file_obj, format="PNG")
    file_obj.seek(0)
    return File(file_obj, name="dummy.png")
