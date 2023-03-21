import pytest

from thunderstore.frontend.context import nav_links
from thunderstore.frontend.models import NavLink


@pytest.mark.django_db
def test_nav_link_context():
    links = [
        NavLink.objects.create(
            title=f"link {i}",
            href="#test",
            order=-i,
            is_active=i % 2 == 0,
        )
        for i in range(3)
    ]
    context = nav_links(None)
    assert list(context["global_nav_links"].values_list("pk", flat=True)) == [
        links[2].pk,
        links[0].pk,
    ]
