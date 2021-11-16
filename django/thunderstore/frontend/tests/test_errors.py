import base64

import pytest
from django.conf import settings
from django.test import RequestFactory

from thunderstore.frontend.views import handle404, handle500


@pytest.mark.django_db
@pytest.mark.parametrize("static", (False, True))
@pytest.mark.parametrize("view", (handle404, handle500))
def test_frontend_error_cache_headers(rf: RequestFactory, static: bool, view):
    # b64 to ensure no accidental overlap with setting value if not intended
    path = (
        settings.STATIC_URL
        if static
        else base64.b64encode(settings.STATIC_URL.encode()).decode()
    )
    response = view(rf.get(path))
    if static:
        assert response["Cache-Control"] == "no-cache"
    else:
        assert "Cache-Control" not in response
