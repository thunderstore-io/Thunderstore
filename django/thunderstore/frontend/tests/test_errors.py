import base64

import pytest
from django.conf import settings
from django.test import RequestFactory

from thunderstore.community.models.community import Community
from thunderstore.community.models.community_site import CommunitySite
from thunderstore.frontend.views import Handler404, Handler500


@pytest.mark.django_db
@pytest.mark.parametrize("static", (False, True))
@pytest.mark.parametrize("view", (Handler404.as_view, Handler500.as_view))
def test_frontend_error_cache_headers(
    community: Community,
    community_site: CommunitySite,
    rf: RequestFactory,
    static: bool,
    view,
):
    # b64 to ensure no accidental overlap with setting value if not intended
    path = (
        settings.STATIC_URL
        if static
        else base64.b64encode(settings.STATIC_URL.encode()).decode()
    )
    request = rf.get(path)
    request.community = community
    response = view()(request)
    if static:
        assert response["Cache-Control"] == "no-cache"
    else:
        assert "Cache-Control" not in response
