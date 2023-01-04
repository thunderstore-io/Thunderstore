from collections import defaultdict
from typing import Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db.models import F, Q

from thunderstore.community.models import PackageCategory


def clean_community_categories(
    community_categories: Optional[Dict[str, List[str]]]
) -> Optional[Dict[str, List[PackageCategory]]]:
    if not community_categories:
        return {}

    query = Q()
    errors = []
    result = defaultdict(list)

    for community, categories in community_categories.items():
        query |= Q(community__identifier=community, slug__in=categories)
    queryset = PackageCategory.objects.filter(query).annotate(
        community_identifier=F("community__identifier")
    )
    matches = {(x.community_identifier, x.slug): x for x in queryset}

    for community, categories in community_categories.items():
        for category in categories:
            match = matches.get((community, category))
            if not match:
                errors.append(
                    ValidationError(
                        f"Category {category} does not exist in community {community}"
                    )
                )
            else:
                result[community].append(match)

    if errors:
        raise ValidationError(errors)

    return result
