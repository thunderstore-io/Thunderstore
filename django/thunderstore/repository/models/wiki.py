from typing import Optional

from django.db import models, transaction
from django.db.models import Manager

from thunderstore.core.mixins import TimestampMixin
from thunderstore.repository.models import Package
from thunderstore.wiki.models import Wiki


def create_wiki_for_package(package: Package, save: bool = False):
    result = Wiki(
        title=f"{package.namespace.name}/{package.name} Wiki",
    )
    if save:
        result.save()
    return result


class PackageWiki(TimestampMixin):
    objects: Manager["PackageWiki"]

    package = models.OneToOneField(
        "repository.Package",
        related_name="wiki",
        on_delete=models.CASCADE,
    )
    wiki = models.OneToOneField(
        "thunderstore_wiki.Wiki",
        related_name="package_wiki",
        on_delete=models.CASCADE,
    )

    @classmethod
    @transaction.atomic
    def get_for_package(
        cls, package: Package, create: bool = False, dummy: bool = True
    ) -> Optional["PackageWiki"]:
        result = cls.objects.filter(package=package).first()
        if not result and (create or dummy):
            result = cls(
                package=package,
                wiki=create_wiki_for_package(package, save=create),
            )
            if create:
                result.save()
        return result

    class Meta:
        constraints = [
            # This constraint is somewhat unnecessary, but it creates an index
            # so it's not a bad idea to have.
            models.UniqueConstraint(
                fields=("package", "wiki"), name="unique_package_wiki"
            ),
        ]
