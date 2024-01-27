from typing import Tuple

from django.db import models
from django.db.models import Q


class PackageFormats(models.TextChoices):
    """
    NOTE: Extending this will require a migration as there's a db level constraint
          enforcing only valid formats are set to the format_spec column of a
          PackageVersion!
    """

    # Initial version
    v0_0 = "thunderstore.io:v0.0"

    # Added `dependencies` field to manifest
    v0_1 = "thunderstore.io:v0.1"

    # Added support for `CHANGELOG.md`
    v0_2 = "thunderstore.io:v0.2"

    # Added `installers` field to manifest
    # - if populated, must have at least a single valid installer
    # - if populated, has a maximum of 100 installers defined
    # - if not populated, must be emitted entirely
    v0_3 = "thunderstore.io:v0.3"

    @classmethod
    def as_query_filter(cls, field_name: str, allow_none: bool) -> Q:
        result = Q()
        if allow_none:
            result |= Q(**{field_name: None})
        for entry in cls.values:
            result |= Q(**{field_name: entry})
        return result

    @classmethod
    def get_supported_formats(cls) -> Tuple["PackageFormats"]:
        return (cls.v0_1, cls.v0_2, cls.v0_3)

    @classmethod
    def get_active_format(cls) -> "PackageFormats":
        return PackageFormats.v0_3
