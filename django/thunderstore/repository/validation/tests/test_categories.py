import pytest
from django.core.exceptions import ValidationError

from thunderstore.community.factories import CommunityFactory, PackageCategoryFactory
from thunderstore.repository.validation.categories import clean_community_categories


@pytest.mark.django_db
def test_clean_community_categories_valid():
    c1 = CommunityFactory()
    c2 = CommunityFactory()
    cat1 = PackageCategoryFactory(community=c1)
    cat2 = PackageCategoryFactory(community=c2)
    result = clean_community_categories(
        {
            c1.identifier: [cat1.slug],
            c2.identifier: [cat2.slug],
        }
    )
    assert result == {
        c1.identifier: [cat1],
        c2.identifier: [cat2],
    }


def test_clean_community_categories_empty():
    assert clean_community_categories(None) == {}


@pytest.mark.django_db
def test_clean_community_categories_invalid():
    c1 = CommunityFactory()
    c2 = CommunityFactory()
    cat1 = PackageCategoryFactory(community=c1)
    cat2 = PackageCategoryFactory(community=c1)
    cat3 = PackageCategoryFactory(community=c2, slug=cat1.slug)
    serialized = {
        c1.identifier: [cat1.slug],
        c2.identifier: [cat2.slug, cat3.slug],
    }
    with pytest.raises(ValidationError) as e:
        clean_community_categories(serialized)

    assert len(e.value.error_list) == 1
    assert (
        e.value.error_list[0].message
        == f"Category {cat2.slug} does not exist in community {c2.identifier}"
    )
